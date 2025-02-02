import discord
import os
from dotenv import load_dotenv
import google.generativeai as genai  # Import the Gemini API library

# Print current working directory for debugging
print(f"Current working directory: {os.getcwd()}")

# Load environment variables from .env file, explicitly specifying path
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

# Retrieve environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHAT_CHANNEL_ID = os.getenv('CHAT_CHANNEL_ID')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Changed to GEMINI_API_KEY

# Ensure required environment variables are set
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable not set in .env")
if not CHAT_CHANNEL_ID:
    raise ValueError("CHAT_CHANNEL_ID environment variable not set in .env")
if not GEMINI_API_KEY:  # Changed to GEMINI_API_KEY
    raise ValueError("GEMINI_API_KEY environment variable not set in .env")

# Debugging: Print the API key being loaded
print(f"GEMINI_API_KEY from .env: {GEMINI_API_KEY}") # Changed to GEMINI_API_KEY

# Convert CHAT_CHANNEL_ID to integer
CHAT_CHANNEL_ID = int(CHAT_CHANNEL_ID)

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent
bot = discord.Client(intents=intents)

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') # Or 'gemini-pro' if flash is not available

@bot.event
async def on_ready():
    print(f'LLM Responder Bot (Gemini API) connected as {bot.user}') # Updated message

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore messages sent by the bot itself

    if message.channel.id == CHAT_CHANNEL_ID:
        print(f"Received message in chat channel {CHAT_CHANNEL_ID} from {message.author}: {message.content}")
        user_message = message.content

        try:
            response = model.generate_content(
                [{"role": "user", "parts": [{"text": user_message}]}],  # Gemini API message format
                stream=False
            )
            gemini_reply = response.text # Extract text from Gemini response
            print(f"Gemini API Response: {gemini_reply}") # Updated message
            await message.channel.send(gemini_reply)

        except Exception as e:
            import traceback
            error_message = traceback.format_exc() # Get full traceback
            print(f"Error calling Gemini API:\n{error_message}") # Updated message
            await message.channel.send("Sorry, I encountered an error while processing your request. Please try again later.")

# Run the bot
bot.run(DISCORD_TOKEN)