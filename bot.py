import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from flask import Flask
from threading import Thread
import sys

# Load .env token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Flask app to keep Replit alive
app = Flask('')


@app.route('/')
def home():
    return "I'm alive!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()


# Set up bot intents and prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="a.", intents=intents)

# Your Discord user ID (no quotes, as int)
OWNER_ID = 711226437147033630


# Custom status and on_ready
@bot.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.watching,
                                name="the stars 🌠✨")
    await bot.change_presence(activity=activity)
    print(f"✅ Astrobo ready — logged in as {bot.user}!")
    
    # Send restart completion message if restarted
    if hasattr(bot, 'restart_channel_id'):
        channel = bot.get_channel(bot.restart_channel_id)
        if channel:
            await channel.send("✅ Bot has restarted successfully!")
        delattr(bot, 'restart_channel_id')


# Restart command only for OWNER_ID
@bot.command(name="restart")
async def restart_bot(ctx):
    """Restart the bot (owner only)"""
    if ctx.author.id != OWNER_ID:
        await ctx.send("❌ You don't have permission to restart me.")
        return

    await ctx.send("🔄 Restarting bot...")
    
    # Store channel ID to send confirmation message after restart
    bot.restart_channel_id = ctx.channel.id
    
    await bot.close()  # clean shutdown

    # Restart the bot script
    os.execv(sys.executable, [sys.executable] + sys.argv)


# Main async function
async def main():
    keep_alive()  # Start Flask server for UptimeRobot pings
    async with bot:
        await bot.load_extension("cogs.id_commands")
        await bot.start(TOKEN)


# Entry point
if __name__ == "__main__":
    asyncio.run(main())
