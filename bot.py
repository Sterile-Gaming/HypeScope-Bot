import discord
from discord.ext import bridge
import os
from dotenv import load_dotenv
from utils import EmbedBuilder

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = bridge.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
bot.load_extensions("cogs")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

@bot.bridge_command(description="Say hello!")
async def hello(ctx):
    await ctx.respond(f"Hello {ctx.author.mention}!")

@bot.bridge_command(description="Get bot info")
async def info(ctx):
    embed = EmbedBuilder(
        title="Bot Information",
        description="HypeScope Bot",
        color=discord.Color.blue()
    ).add_field(
        name="Guilds", 
        value=len(bot.guilds), 
        inline=True
    ).add_field(
        name="Users", 
        value=len(bot.users), 
        inline=True
    ).set_footer(
        text=f"Requested by {ctx.author.display_name}",
        icon_url=ctx.author.avatar.url if ctx.author.avatar else None
    ).build()
    
    await ctx.respond(embed=embed)

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if token:
        bot.run(token)
    else:
        print("Error: DISCORD_TOKEN not found in environment variables")
