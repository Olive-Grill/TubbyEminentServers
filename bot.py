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

# Flask app to keep Replit alive and provide web interface
app = Flask('')


@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Astrobo - Discord Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #2c2f33;
                color: #ffffff;
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
            }
            .feature {
                background-color: #36393f;
                padding: 20px;
                margin: 15px 0;
                border-radius: 8px;
                border-left: 4px solid #7289da;
            }
            .command {
                background-color: #23272a;
                padding: 10px;
                border-radius: 4px;
                font-family: monospace;
                margin: 10px 0;
            }
            .status {
                display: inline-block;
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
            }
            .online {
                background-color: #43b581;
                color: white;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌠 Astrobo Discord Bot</h1>
            <p>Deep Space Object Identification Quiz Bot</p>
            <span class="status online">● ONLINE</span>
        </div>
        
        <div class="feature">
            <h3>🔭 Deep Space Object Quiz</h3>
            <p>Test your knowledge of deep space objects with interactive quizzes!</p>
            <div class="command">a.a - Start Division B/C quiz</div>
            <div class="command">a.b - Division B only (coming soon)</div>
            <div class="command">a.pic - Get another image</div>
            <div class="command">a.skip - Skip current question</div>
            <div class="command">a.hint - Get a hint</div>
        </div>
        
        <div class="feature">
            <h3>🎯 How to Play</h3>
            <p>1. Use <code>a.a</code> to start a quiz</p>
            <p>2. Look at the deep space object image</p>
            <p>3. Reply with <code>a.[your guess]</code></p>
            <p>4. Get feedback and try again or move to the next object!</p>
        </div>
        
        <div class="feature">
            <h3>📊 Features</h3>
            <ul>
                <li>Interactive deep space object identification</li>
                <li>Multiple images per object</li>
                <li>Fuzzy matching for answers</li>
                <li>Hints available for each object</li>
                <li>Channel-based quiz management</li>
            </ul>
        </div>
        
        <div class="feature">
            <h3>🔗 Invite Bot</h3>
            <p>Contact the bot owner to add Astrobo to your Discord server!</p>
        </div>
        
        <footer style="text-align: center; margin-top: 30px; opacity: 0.7;">
            <p>Watching the stars 🌠✨</p>
        </footer>
    </body>
    </html>
    '''


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
    """Restart the bot (developer only)"""
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
