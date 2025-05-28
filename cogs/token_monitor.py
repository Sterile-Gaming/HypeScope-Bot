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
        self.last_checked_block = self.config.get("last_checked_block", self.web3.eth.block_number - 1)
        self.monitor_channel_id = self.config.get("monitor_channel_id", None)
    
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
                    "monitor_channel_id": None,
                    "last_checked_block": None,
                    "enabled": True
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
                    "monitor_channel_id": self.monitor_channel_id,
                    "last_checked_block": self.last_checked_block,
                    "enabled": self.token_monitor.is_running() if hasattr(self, 'token_monitor') else True
                }
            
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"❌ Error saving config: {e}")
        
    @commands.Cog.listener()
    async def on_ready(self):
        if self.web3.is_connected():
            self.token_monitor.start()
            print("🔁 Token monitoring started")
    
    @tasks.loop(seconds=10)
    async def token_monitor(self):
        try:
            latest_block = self.web3.eth.block_number
            
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
            # Save config after updating block
            self.save_config()
            
        except Exception as e:
            print(f"❌ Error polling events: {e}")
    
    async def send_token_notification(self, args):
        if not self.monitor_channel_id:
            return
            
        channel = self.bot.get_channel(self.monitor_channel_id)
        if not channel:
            return
        
        # Create links
        links = []
        if args['website']: links.append(f"[Website]({args['website']})")
        if args['twitter']: links.append(f"[Twitter]({args['twitter']})")
        if args['telegram']: links.append(f"[Telegram]({args['telegram']})")
        if args['discord']: links.append(f"[Discord]({args['discord']})")
        
        embed = EmbedBuilder(
            title=f"🚀 New Token Created: {args['name']} ({args['symbol']})",
            description=args['description'][:1000] if args['description'] else "No description provided",
            color=discord.Color.green()
        ).add_field(
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
        
        await channel.send(embed=embed.build())

    @bridge.bridge_command(name="setmonitorchannel", description="Set the channel for token notifications")
    @commands.has_permissions(administrator=True)
    async def set_monitor_channel(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel
        
        self.monitor_channel_id = channel.id
        self.save_config()  # Save config when channel is changed
        
        embed = EmbedBuilder(
            title="✅ Monitor Channel Set",
            description=f"Token notifications will be sent to {channel.mention}",
            color=discord.Color.green()
        ).build()
        
        await ctx.respond(embed=embed)

    @bridge.bridge_command(name="monitorstatus", description="Get current monitoring status")
    async def monitor_status(self, ctx):
        status = "🟢 Active" if self.token_monitor.is_running() else "🔴 Inactive"
        channel = f"<#{self.monitor_channel_id}>" if self.monitor_channel_id else "Not set"
        
        embed = EmbedBuilder(
            title="📊 Token Monitor Status",
            color=discord.Color.blue()
        ).add_field(
            name="Status", 
            value=status, 
            inline=True
        ).add_field(
            name="Channel", 
            value=channel, 
            inline=True
        ).add_field(
            name="Last Block", 
            value=self.last_checked_block, 
            inline=True
        ).build()
        
        await ctx.respond(embed=embed)
    
    def cog_unload(self):
        self.save_config()  # Save config when cog is unloaded
        self.token_monitor.cancel()

def setup(bot):
    bot.add_cog(TokenMonitor(bot))
