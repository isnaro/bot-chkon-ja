import os
import subprocess
import sys
import discord
from discord.ext import commands
import asyncio
from keep_alive import keep_alive  # Import the keep_alive function
from dotenv import load_dotenv

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

# Load environment variables from .env file
load_dotenv()

# Retrieve environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
STAY_CHANNEL_ID = os.getenv('STAY_CHANNEL_ID')
MONITOR_CHANNEL_ID = os.getenv('MONITOR_CHANNEL_ID')

# Define the relative path for the audio file
AUDIO_FILE = os.path.join(os.path.dirname(__file__), 'voices', 'chkon ja.mp3')

# Set the path to the FFmpeg binary
FFMPEG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ffmpeg', 'ffmpeg'))

# Debugging: print environment variables and file paths
print(f"TOKEN: {TOKEN}")
print(f"STAY_CHANNEL_ID: {STAY_CHANNEL_ID}")
print(f"MONITOR_CHANNEL_ID: {MONITOR_CHANNEL_ID}")
print(f"AUDIO_FILE: {AUDIO_FILE}")
print(f"FFMPEG_PATH: {FFMPEG_PATH}")

if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set")

# Define intents and initialize the bot
intents = discord.Intents.default()
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def ensure_connected():
    await bot.wait_until_ready()
    while not bot.is_closed():
        stay_channel = bot.get_channel(int(STAY_CHANNEL_ID))
        # Check that the channel exists and is a voice channel
        if stay_channel and stay_channel.type == discord.ChannelType.voice:
            voice_client = discord.utils.get(bot.voice_clients, guild=stay_channel.guild)
            if voice_client is None or not voice_client.is_connected():
                try:
                    await stay_channel.connect()
                    print(f'Connected to stay channel: {stay_channel.name}')
                except Exception as e:
                    print(f'Error connecting to stay channel: {e}')
        await asyncio.sleep(5)

async def ensure_unmuted():
    await bot.wait_until_ready()
    while not bot.is_closed():
        stay_channel = bot.get_channel(int(STAY_CHANNEL_ID))
        if stay_channel and stay_channel.type == discord.ChannelType.voice:
            voice_client = discord.utils.get(bot.voice_clients, guild=stay_channel.guild)
            if voice_client and voice_client.is_connected():
                try:
                    await voice_client.guild.change_voice_state(channel=voice_client.channel, self_mute=False, self_deaf=False)
                    await bot.get_guild(stay_channel.guild.id).me.edit(mute=False, deafen=False)
                except Exception as e:
                    print(f"Error ensuring bot unmuted: {e}")
        await asyncio.sleep(5)

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')
    bot.loop.create_task(ensure_connected())
    bot.loop.create_task(ensure_unmuted())

@bot.event
async def on_voice_state_update(member, before, after):
    # Automatically unmute the specific user when they are server muted
    target_user_id = 387923086730723329  # The user ID to auto-unmute
    if member.id == target_user_id and after.mute:
        try:
            await member.edit(mute=False)
            print(f"Automatically unmuted {member.display_name}.")
        except Exception as e:
            print(f"Failed to unmute {member.display_name}: {e}")

    # Play a sound when someone joins the monitor channel
    if after.channel and after.channel.id == int(MONITOR_CHANNEL_ID) and before.channel != after.channel:
        voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)
        if voice_client and voice_client.is_connected():
            voice_client.stop()  # Stop any current audio before playing the new sound
            source = discord.FFmpegPCMAudio(AUDIO_FILE, executable=FFMPEG_PATH)
            voice_client.play(source)

    # Ensure the bot remains unmuted if it accidentally gets muted
    if member.id == bot.user.id:
        if after.self_mute or after.self_deaf or after.mute or after.deaf:
            try:
                await member.guild.change_voice_state(channel=after.channel, self_mute=False, self_deaf=False)
                await member.edit(mute=False, deafen=False)
            except Exception as e:
                print(f"Error ensuring bot unmuted: {e}")

@bot.event
async def on_disconnect():
    print('Bot disconnected, attempting to reconnect...')
    bot.loop.create_task(ensure_connected())

# Keep the bot alive (for hosting platforms like Replit)
keep_alive()

bot.run(TOKEN)
