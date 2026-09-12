import os
import asyncio
import threading
import traceback
from flask import Flask
import discord
from discord.ext import commands
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
import config

# --- Keep Alive Flask Server ---
app = Flask('')

@app.route('/')
def home():
    return 'Bot is live and active!', 200

def run_flask():
    # Render default port 10000 hota hai
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

keep_alive()
# -------------------------------

MONGO_URI = os.getenv('MONGO_URI', getattr(config, 'MONGO_URI', None))
db = None
async_db = None
motor_client = None

if MONGO_URI:
    try:
        # Keep Mongo handles available to cogs. Commands use Motor (async) so
        # MongoDB cannot block Discord's event loop.
        cluster = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        cluster.admin.command("ping")
        db = cluster['Lloyd']

        motor_client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        async_db = motor_client['Lloyd']
        print('[MongoDB] Connected to Lloyd database.')
    except Exception as e:
        print(f'[MongoDB Connection Error]: {e}')
        db = None
        async_db = None
else:
    print('[MongoDB Warning] MONGO_URI variable missing in environment!')

# Enable Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Required for welcome system
intents.voice_states = True
intents.presences = False

PREFIXES = commands.when_mentioned_or('.', ',', '-', '?', '$', ';', '/', ':', "'", '!')

bot = commands.Bot(command_prefix=PREFIXES, intents=intents, help_command=None)
bot.db = db
bot.async_db = async_db  # Pass async database to cogs

@bot.event
async def on_ready():
    print('----------------------------------------')
    print(f'Bot Online: {bot.user} ({bot.user.id})')
    print('----------------------------------------')
    try:
        synced = await bot.tree.sync()
        print(f'Slash Commands Synced: {len(synced)}')
    except Exception as e:
        print(f'Slash Sync Error: {e}')

    await bot.change_presence(status=discord.Status.online, activity=None)

async def main():
    async with bot:
        cogs = [
            'cogs.help',
            'cogs.vchelper',
            'cogs.music',
            'cogs.moderation',
            'cogs.fungames',
            'cogs.utility',
            'cogs.vctracker',
            'cogs.gif',
            'cogs.msgtracker',
            'cogs.role',
            'cogs.kingdom',
            'cogs.antinuke',
            'cogs.welcome',
            'cogs.imposter',
            'cogs.modlogs',
            'cogs.xo',
            'cogs.autosend',
            'cogs.afk',
            'cogs.autoresponder',
            'cogs.premium',
            'cogs.card',
            'cogs.cgame.leaderboard'
        ]

        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f'Loaded {cog}')
            except Exception as e:
                print(f'Error loading {cog}: {e}')
                traceback.print_exc()

        token = os.getenv('BOT_TOKEN', getattr(config, 'BOT_TOKEN', None))
        if not token:
            print("❌ ERROR: BOT_TOKEN Environment variable is not set!")
            return
            
        await bot.start(token)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot shutdown gracefully.")
            
