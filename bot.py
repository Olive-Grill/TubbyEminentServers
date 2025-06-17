import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="a.", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Astrobo ready — logged in as {bot.user}!")

async def main():
    async with bot:
        await bot.load_extension("cogs.id_commands")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())