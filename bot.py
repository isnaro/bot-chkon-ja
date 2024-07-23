import os
import subprocess
import sys

# Ensure all necessary packages are installed
required_modules = ["discord.py", "flask", "python-dotenv", "pynacl", "typing_extensions"]

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

for package in required_modules:
    try:
        __import__(package.split('.')[0])  # Import the base module name
    except ImportError:
        print(f"{package} is not installed. Installing now...")
        install(package)

# Now import all necessary modules
import discord
from discord.ext import commands
import asyncio
from keep_alive import keep_alive  # Import the keep_alive function
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
STAY_CHANNEL_ID = int(os.getenv('STAY_CHANNEL_ID'))
MONITOR_CHANNEL_ID = int(os.getenv('MONITOR_CHANNEL_ID'))

# Directly specify the audio file path
AUDIO_FILE = r'C:\Users\Nasro\Desktop\bot chkon ja\voices\chkon ja.mp3'

# Debugging: print environment variables
print(f"TOKEN: {TOKEN}")
print(f"STAY_CHANNEL_ID: {STAY_CHANNEL_ID}")
print(f"MONITOR_CHANNEL_ID: {MONITOR_CHANNEL_ID}")
print(f"AUDIO_FILE: {AUDIO_FILE}")

intents = discord.Intents.default()
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    stay_channel = bot.get_channel(STAY_CHANNEL_ID)
    if stay_channel and stay_channel.type == discord.ChannelType.voice:
        await stay_channel.connect()
    else:
        print(f'Error: Could not connect to stay channel (ID: {STAY_CHANNEL_ID})')

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == MONITOR_CHANNEL_ID and before.channel != after.channel:
        voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
        if voice_client and voice_client.is_connected():
            voice_client.stop()
            source = discord.FFmpegPCMAudio(AUDIO_FILE)
            voice_client.play(source)

# Keep the bot alive
keep_alive()

bot.run(TOKEN)
