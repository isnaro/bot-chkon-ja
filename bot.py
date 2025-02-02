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
# The following are still loaded, but not used in this version.
STAY_CHANNEL_ID = os.getenv('STAY_CHANNEL_ID')
MONITOR_CHANNEL_ID = os.getenv('MONITOR_CHANNEL_ID')

# Define the specific chat channel ID directly in the code
CHAT_CHANNEL_ID = 1335564442691440691

# Debugging: print environment variables (optional)
print(f"TOKEN: {TOKEN}")
print(f"CHAT_CHANNEL_ID: {CHAT_CHANNEL_ID}")

if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set")

# DeepSeek API configuration (per the docs)
DEEPSEEK_API_KEY = "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"
DEEPSEEK_API_ENDPOINT = "https://api.deepseek.com/chat/completions"  # Official endpoint per docs

# Define intents so the bot can read incoming messages
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Bot connected as {bot.user}")

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
            # Prepare payload according to DeepSeek API docs
            payload = {
                "model": "deepseek-reasoner",  # Change to "deepseek-chat" if desired
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message.content}
                ],
                "max_tokens": 150,      # Adjust as needed
                "temperature": 0.6,     # Adjust as needed
                "stream": False         # Non-streaming mode as per the docs
            }
            try:
                async with session.post(DEEPSEEK_API_ENDPOINT, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Assuming the API returns generated text in the first choice's message
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

    # Allow command processing if there are any commands
    await bot.process_commands(message)

@bot.event
async def on_disconnect():
    print("Bot disconnected.")

# Keep the bot alive (useful for hosting platforms like Replit)
keep_alive()

bot.run(TOKEN)
