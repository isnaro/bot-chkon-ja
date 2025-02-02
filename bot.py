import os
import subprocess
import sys
import discord
from discord.ext import commands
import asyncio
import aiohttp  # For async HTTP requests
from keep_alive import keep_alive  # Keeps the bot alive (e.g., for Replit)
from dotenv import load_dotenv

# Ensure all necessary packages are installed
required_modules = [
    "discord.py", "flask", "python-dotenv", "pynacl", "typing_extensions", "aiohttp"
]

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

for package in required_modules:
    try:
        __import__(package.split('.')[0])
    except ImportError:
        print(f"{package} is not installed. Installing now...")
        install(package)

# Load environment variables from the .env file
load_dotenv()

# Retrieve environment variables from .env
TOKEN = os.getenv('DISCORD_TOKEN')
STAY_CHANNEL_ID = os.getenv('STAY_CHANNEL_ID')
MONITOR_CHANNEL_ID = os.getenv('MONITOR_CHANNEL_ID')

# Define the specific chat channel ID directly in the code
CHAT_CHANNEL_ID = 1335564442691440691

# Debugging: print environment variables (optional)
print(f"TOKEN: {TOKEN}")
print(f"STAY_CHANNEL_ID: {STAY_CHANNEL_ID}")
print(f"MONITOR_CHANNEL_ID: {MONITOR_CHANNEL_ID}")
print(f"CHAT_CHANNEL_ID: {CHAT_CHANNEL_ID}")

if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set")

# Define the relative path for the audio file (used in voice events)
AUDIO_FILE = os.path.join(os.path.dirname(__file__), 'voices', 'chkon ja.mp3')

# Set the path to the FFmpeg binary
FFMPEG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ffmpeg', 'ffmpeg'))
print(f"AUDIO_FILE: {AUDIO_FILE}")
print(f"FFMPEG_PATH: {FFMPEG_PATH}")

# DeepSeek API configuration
DEEPSEEK_API_KEY = "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"
DEEPSEEK_API_ENDPOINT = "https://api.deepseek.com/chat/completions"  # Official endpoint

# Define intents including message content so the bot can read incoming messages
intents = discord.Intents.default()
intents.voice_states = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def ensure_connected():
    await bot.wait_until_ready()
    while not bot.is_closed():
        stay_channel = bot.get_channel(int(STAY_CHANNEL_ID))
        # Check that the channel exists and is a voice channel
        if stay_channel and stay_channel.type == discord.ChannelType.voice:
            voice_client = discord.utils.get(bot.voice_clients, guild=stay_channel.guild)
            if voice_client is None:
                try:
                    await stay_channel.connect()
                    print(f"Connected to stay channel: {stay_channel.name}")
                except Exception as e:
                    if "Already connected" in str(e):
                        pass
                    else:
                        print(f"Error connecting to stay channel: {e}")
            else:
                if not voice_client.is_connected():
                    try:
                        await stay_channel.connect()
                        print(f"Connected to stay channel: {stay_channel.name}")
                    except Exception as e:
                        if "Already connected" in str(e):
                            pass
                        else:
                            print(f"Error connecting to stay channel: {e}")
        await asyncio.sleep(5)

async def ensure_unmuted():
    await bot.wait_until_ready()
    while not bot.is_closed():
        stay_channel = bot.get_channel(int(STAY_CHANNEL_ID))
        if stay_channel and stay_channel.type == discord.ChannelType.voice:
            voice_client = discord.utils.get(bot.voice_clients, guild=stay_channel.guild)
            if voice_client and voice_client.is_connected():
                try:
                    await voice_client.guild.change_voice_state(
                        channel=voice_client.channel, self_mute=False, self_deaf=False
                    )
                    await bot.get_guild(stay_channel.guild.id).me.edit(mute=False, deafen=False)
                except Exception as e:
                    print(f"Error ensuring bot unmuted: {e}")
        await asyncio.sleep(5)

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")
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
async def on_message(message):
    # Ignore messages from bots
    if message.author.bot:
        return

    # Check if the message is in the designated chat channel
    if message.channel.id == CHAT_CHANNEL_ID:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            # Prepare payload with a system message and the user's message
            payload = {
                "model": "deepseek-reasoner",  # DeepSeek-R1 (reasoner model)
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message.content}
                ],
                "max_tokens": 150,  # Adjust as needed for your use-case
                "temperature": 0.6
            }
            try:
                async with session.post(DEEPSEEK_API_ENDPOINT, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Assuming the API returns generated text in the first choice's message field
                        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if reply:
                            await message.channel.send(reply)
                        else:
                            await message.channel.send("I received an empty response from DeepSeek.")
                    else:
                        print(f"DeepSeek API error: {resp.status}")
                        await message.channel.send("Sorry, I encountered an error while processing your request.")
            except Exception as e:
                print(f"Error calling DeepSeek API: {e}")
                await message.channel.send("Sorry, there was an error connecting to the DeepSeek API.")

    # Allow command processing
    await bot.process_commands(message)

@bot.event
async def on_disconnect():
    print("Bot disconnected, attempting to reconnect...")
    bot.loop.create_task(ensure_connected())

# Keep the bot alive (useful for hosting platforms like Replit)
keep_alive()

bot.run(TOKEN)
