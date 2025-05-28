import discord
from discord.ext import tasks, bridge , commands
from web3 import Web3
from datetime import datetime, timezone
from utils import EmbedBuilder
import json
import os

class TokenMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_file = "config/token_monitor.json"
        
        # Initialize default values first
        self.last_checked_block = None
        self.server_configs = {}  # Store configs per guild
        
        # Load config
        self.config = self.load_config()
        
        # Web3 setup
        self.RPC_URL = "https://rpc.hyperliquid.xyz/evm"
        self.CONTRACT_ADDRESS = "0xDEC3540f5BA6f2aa3764583A9c29501FeB020030"
        self.POLL_INTERVAL = 10  # seconds
        
        # Connect to RPC
        self.web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        if not self.web3.is_connected():
            print("❌ Could not connect to RPC")
            return
            
        # ABI with only the TokenCreated event
        self.ABI = [
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "internalType": "address", "name": "token", "type": "address"},
                    {"indexed": True, "internalType": "address", "name": "creator", "type": "address"},
                    {"indexed": False, "internalType": "string", "name": "name", "type": "string"},
                    {"indexed": False, "internalType": "string", "name": "symbol", "type": "string"},
                    {"indexed": False, "internalType": "string", "name": "image_uri", "type": "string"},
                    {"indexed": False, "internalType": "string", "name": "description", "type": "string"},
                    {"indexed": False, "internalType": "string", "name": "website", "type": "string"},
                    {"indexed": False, "internalType": "string", "name": "twitter", "type": "string"},
                    {"indexed": False, "internalType": "string", "name": "telegram", "type": "string"},
                    {"indexed": False, "internalType": "string", "name": "discord", "type": "string"},
                    {"indexed": False, "internalType": "uint256", "name": "creationTimestamp", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "startingLiquidity", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "currentHypeReserves", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "currentTokenReserves", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "totalSupply", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "currentPrice", "type": "uint256"},
                    {"indexed": False, "internalType": "uint256", "name": "initialPurchaseAmount", "type": "uint256"}
                ],
                "name": "TokenCreated",
                "type": "event"
            }
        ]
        
        self.contract = self.web3.eth.contract(address=self.CONTRACT_ADDRESS, abi=self.ABI)
        self.event_signature_hash = self.web3.keccak(text="TokenCreated(address,address,string,string,string,string,string,string,string,string,uint256,uint256,uint256,uint256,uint256,uint256,uint256)").hex()
        
        # Fix initialization of last_checked_block
        saved_block = self.config.get("last_checked_block")
        if saved_block is None:
            self.last_checked_block = self.web3.eth.block_number - 1
        else:
            self.last_checked_block = saved_block
            
        # Load server configs
        self.server_configs = self.config.get("servers", {})

    def load_config(self):
        """Load configuration from JSON file"""
        try:
            # Create config directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                # Create default config
                default_config = {
                    "last_checked_block": None,
                    "enabled": True,
                    "servers": {}
                }
                self.save_config(default_config)
                return default_config
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}
    
    def save_config(self, config=None):
        """Save configuration to JSON file"""
        try:
            if config is None:
                config = {
                    "last_checked_block": self.last_checked_block,
                    "enabled": self.token_monitor.is_running() if hasattr(self, 'token_monitor') else True,
                    "servers": self.server_configs
                }
            
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def get_server_config(self, guild_id):
        """Get configuration for a specific server"""
        return self.server_configs.get(str(guild_id), {
            "monitor_channel_id": None,
            "enabled": True
        })
    
    def set_server_config(self, guild_id, key, value):
        """Set configuration for a specific server"""
        guild_id = str(guild_id)
        if guild_id not in self.server_configs:
            self.server_configs[guild_id] = {}
        self.server_configs[guild_id][key] = value
        self.save_config()
        
    @commands.Cog.listener()
    async def on_ready(self):
        if hasattr(self, 'web3') and self.web3.is_connected():
            if not self.token_monitor.is_running():
                self.token_monitor.start()
                print("🔁 Token monitoring started")
        else:
            print("❌ Token monitoring not started - Web3 connection failed")

    @tasks.loop(seconds=10)
    async def token_monitor(self):
        try:
            # Check if web3 is still connected
            if not self.web3.is_connected():
                print("❌ Web3 connection lost, attempting to reconnect...")
                self.web3 = Web3(Web3.HTTPProvider(self.RPC_URL))
                if not self.web3.is_connected():
                    print("❌ Failed to reconnect to Web3")
                    return
            
            latest_block = self.web3.eth.block_number
            
            # Ensure last_checked_block is not None
            if self.last_checked_block is None:
                self.last_checked_block = latest_block - 1
            
            logs = self.web3.eth.get_logs({
                "fromBlock": self.last_checked_block + 1,
                "toBlock": latest_block,
                "address": self.CONTRACT_ADDRESS,
                "topics": [self.event_signature_hash]
            })
            
            for log in logs:
                event = self.contract.events.TokenCreated().process_log(log)
                await self.send_token_notification(event["args"])
            
            self.last_checked_block = latest_block
            # Save config after updating block (less frequently to reduce I/O)
            if latest_block % 10 == 0:  # Save every 10 blocks
                self.save_config()
            
        except KeyboardInterrupt:
            print("🛑 Token monitoring stopped by user")
            self.token_monitor.cancel()
        except Exception as e:
            print(f"❌ Error polling events: {e}")
            # Don't crash the task, just log the error and continue

    @token_monitor.before_loop
    async def before_token_monitor(self):
        """Wait until bot is ready before starting the monitor"""
        await self.bot.wait_until_ready()
        print("🔄 Token monitor waiting for bot to be ready...")

    @token_monitor.after_loop
    async def after_token_monitor(self):
        """Clean up after the monitor stops"""
        if self.token_monitor.is_being_cancelled():
            print("🛑 Token monitor task cancelled")
        else:
            print("❌ Token monitor task stopped unexpectedly")
        
        # Save config one final time
        self.save_config()

    def _create_links_list(self, args):
        links = []
        for platform in ['website', 'twitter', 'telegram', 'discord']:
            if args[platform]:
                links.append(f"[{platform.title()}]({args[platform]})")
        return links

    def _create_token_embed(self, args, links):
        embed = EmbedBuilder(
            title=f"🚀 New Token Created: {args['name']} ({args['symbol']})",
            description=args['description'][:1000] if args['description'] else "No description provided",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📍 Addresses",
            value=f"**Token:** `{args['token']}`\n**Creator:** `{args['creator']}`",
            inline=False
        ).add_field(
            name="💰 Token Info",
            value=f"**Total Supply:** {args['totalSupply'] / 10 ** 6:,.2f}\n**Current Price:** ${args['currentPrice'] / 10 ** 6:.6f}\n**Initial Purchase:** {args['initialPurchaseAmount'] / 10 ** 6:,.2f}",
            inline=True
        ).add_field(
            name="🏦 Liquidity Info",
            value=f"**Starting Liquidity:** {args['startingLiquidity'] / 10 ** 18:.2f} HYPE\n**Current HYPE Reserves:** {args['currentHypeReserves'] / 10 ** 18:.2f}\n**Current Token Reserves:** {args['currentTokenReserves'] / 10 ** 6:,.2f}",
            inline=True
        ).add_field(
            name="🔗 Links",
            value=" | ".join(links) if links else "No links provided",
            inline=False
        ).set_footer(
            text=f"Created at {datetime.fromtimestamp(args['creationTimestamp'], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        
        if args['image_uri']:
            embed.set_thumbnail(args['image_uri'])
            
        return embed

    async def _send_to_channel(self, channel, embed):
        try:
            await channel.send(embed=embed.build())
        except Exception as e:
            print(f"❌ Failed to send notification to {channel.guild.name}: {e}")

    async def send_token_notification(self, args):
        links = self._create_links_list(args)
        embed = self._create_token_embed(args, links)
        
        for guild_id, server_config in self.server_configs.items():
            if not server_config.get("enabled", True):
                continue
                
            channel_id = server_config.get("monitor_channel_id")
            if not channel_id:
                continue
                
            channel = self.bot.get_channel(channel_id)
            if channel:
                await self._send_to_channel(channel, embed)

    @bridge.bridge_command(name="setmonitorchannel", description="Set the channel for token notifications")
    @commands.has_permissions(administrator=True)
    async def set_monitor_channel(self, ctx, channel: discord.TextChannel = None):
        # Delete the command message if it's a prefix command
        message_deleted = False
        if hasattr(ctx, 'message') and ctx.message:
            try:
                await ctx.message.delete()
                message_deleted = True
            except discord.Forbidden:
                pass
        
        if channel is None:
            channel = ctx.channel
        
        self.set_server_config(ctx.guild.id, "monitor_channel_id", channel.id)
        
        embed = EmbedBuilder(
            title="✅ Monitor Channel Set",
            description=f"Token notifications will be sent to {channel.mention} for this server",
            color=discord.Color.green()
        ).build()
        
        if message_deleted:
            # Send a new message instead of replying if original was deleted
            await ctx.send(embed=embed, delete_after=5)
        else:
            await ctx.respond(embed=embed, delete_after=5)

    @bridge.bridge_command(name="monitorstatus", description="Get current monitoring status")
    async def monitor_status(self, ctx):
        # Delete the command message if it's a prefix command
        if hasattr(ctx, 'message') and ctx.message:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass
        
        server_config = self.get_server_config(ctx.guild.id)
        status = "🟢 Active" if self.token_monitor.is_running() else "🔴 Inactive"
        channel_id = server_config.get("monitor_channel_id")
        channel = f"<#{channel_id}>" if channel_id else "Not set"
        server_enabled = "🟢 Enabled" if server_config.get("enabled", True) else "🔴 Disabled"
        
        embed = EmbedBuilder(
            title="📊 Token Monitor Status",
            color=discord.Color.blue()
        ).add_field(
            name="Global Status", 
            value=status, 
            inline=True
        ).add_field(
            name="Server Status", 
            value=server_enabled, 
            inline=True
        ).add_field(
            name="Channel", 
            value=channel, 
            inline=True
        ).add_field(
            name="Last Block", 
            value=self.last_checked_block, 
            inline=True
        ).add_field(
            name="Total Servers", 
            value=len(self.server_configs), 
            inline=True
        ).build()
        
        await ctx.respond(embed=embed)
    
    @bridge.bridge_command(name="togglemonitor", description="Enable/disable monitoring for this server")
    @commands.has_permissions(administrator=True)
    async def toggle_monitor(self, ctx):
        # Delete the command message if it's a prefix command
        message_deleted = False
        if hasattr(ctx, 'message') and ctx.message:
            try:
                await ctx.message.delete()
                message_deleted = True
            except discord.Forbidden:
                pass
        
        server_config = self.get_server_config(ctx.guild.id)
        current_status = server_config.get("enabled", True)
        new_status = not current_status
        
        self.set_server_config(ctx.guild.id, "enabled", new_status)
        
        status_text = "enabled" if new_status else "disabled"
        color = discord.Color.green() if new_status else discord.Color.red()
        
        embed = EmbedBuilder(
            title=f"✅ Monitor {status_text.title()}",
            description=f"Token monitoring has been {status_text} for this server",
            color=color
        ).build()
        
        if message_deleted:
            # Send a new message instead of replying if original was deleted
            await ctx.send(embed=embed, delete_after=5)
        else:
            await ctx.respond(embed=embed, delete_after=5)

    def cog_unload(self):
        """Properly clean up when cog is unloaded"""
        print("🔄 Unloading token monitor cog...")
        self.save_config()  # Save config when cog is unloaded
        if hasattr(self, 'token_monitor') and self.token_monitor.is_running():
            self.token_monitor.cancel()
        print("✅ Token monitor cog unloaded")

def setup(bot):
    bot.add_cog(TokenMonitor(bot))
