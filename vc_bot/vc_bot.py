import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
SERVER_ID = int(os.getenv("SERVER_ID", "0"))
CHANNEL_NAME = os.getenv("VC_NAME", "تحدث عام")

intents = discord.Intents.default()
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

async def join_vc():
    await bot.wait_until_ready()
    guild = bot.get_guild(SERVER_ID)
    if not guild:
        return
    for ch in guild.voice_channels:
        if ch.name == CHANNEL_NAME:
            try:
                await ch.connect()
                print(f"🎧 دخلت {ch.name}")
            except:
                print("😴 أنا أصلاً في الروم")
            return

@bot.event
async def on_ready():
    print(f"✅ {bot.user} متصل")
    await join_vc()

@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and not after.channel:
        print("🔌 انقطعت، برجع...")
        await asyncio.sleep(3)
        await join_vc()

bot.run(TOKEN)
