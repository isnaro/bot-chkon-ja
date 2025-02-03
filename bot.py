import os
import subprocess
import sys
import discord
from discord.ext import commands
import asyncio
from keep_alive import keep_alive  # Import the keep_alive function
from dotenv import load_dotenv
import google.generativeai as genai  # Import the Gemini API library

# Ensure all necessary packages are installed
required_modules = ["discord.py", "flask", "python-dotenv", "pynacl", "typing_extensions", "google-generativeai"]

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
AUDIO_FILE = os.getenv('AUDIO_FILE')
FFMPEG_PATH = os.getenv('FFMPEG_PATH')
CHAT_CHANNEL_ID = os.getenv('CHAT_CHANNEL_ID')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Define default values if environment variables are not set
if AUDIO_FILE is None:
    AUDIO_FILE = os.path.join(os.path.dirname(__file__), 'voices', 'chkon ja.mp3')
if FFMPEG_PATH is None:
    FFMPEG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ffmpeg', 'ffmpeg'))

# Debugging: print environment variables and file paths
print(f"TOKEN: {TOKEN}")
print(f"STAY_CHANNEL_ID: {STAY_CHANNEL_ID}")
print(f"MONITOR_CHANNEL_ID: {MONITOR_CHANNEL_ID}")
print(f"AUDIO_FILE: {AUDIO_FILE}")
print(f"FFMPEG_PATH: {FFMPEG_PATH}")
print(f"CHAT_CHANNEL_ID: {CHAT_CHANNEL_ID}")
print(f"GEMINI_API_KEY: {GEMINI_API_KEY}")

if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set")
if CHAT_CHANNEL_ID is None:
    raise ValueError("CHAT_CHANNEL_ID environment variable not set")
if GEMINI_API_KEY is None:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# Convert CHAT_CHANNEL_ID to integer
CHAT_CHANNEL_ID = int(CHAT_CHANNEL_ID)

# Initialize Discord bot with commands
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True # Enable message content intent for LLM feature
bot = commands.Bot(command_prefix='!', intents=intents)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Define the tuned generation configuration
generation_config = {
  "temperature": 0.75,
  "top_p": 0.95,
  "top_k": 40,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

# Initialize Gemini model with the tuned configuration
model = genai.GenerativeModel(
  model_name="gemini-2.0-flash-exp",
  generation_config=generation_config,
)

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

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore messages sent by the bot itself

    if message.channel.id == CHAT_CHANNEL_ID:
        print(f"Received message in chat channel {CHAT_CHANNEL_ID} from {message.author}: {message.content}")
        user_message = message.content

        # --- Gemini Tuned Model Configuration ---
        generation_config = {
          "temperature": 0.75,
          "top_p": 0.95,
          "top_k": 40,
          "max_output_tokens": 8192,
          "response_mime_type": "text/plain",
        }

        model = genai.GenerativeModel(
          model_name="gemini-2.0-flash-exp",
          generation_config=generation_config,
        )
        # --- End of Gemini Tuned Model Configuration ---


        try:
            response = model.generate_content(
                [{"role": "user", "parts": [{"text": user_message}]}],  # Gemini API message format
                stream=False
            )
            gemini_reply = response.text # Extract text from Gemini response
            print(f"Gemini API Response: {gemini_reply}")
            await message.channel.send(gemini_reply)

        except Exception as e:
            import traceback
            error_message = traceback.format_exc() # Get full traceback
            print(f"Error calling Gemini API:\n{error_message}")
            await message.channel.send("Sorry, I encountered an error while processing your request. Please try again later.")

# Keep the bot alive (for hosting platforms like Replit)
keep_alive()

bot.run(TOKEN)