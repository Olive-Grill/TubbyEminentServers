import discord
from discord.ext import commands
import random
import difflib
import json
import os

class IDCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dso_data = self.load_dso_data()
        self.current_quiz = {}  # user_id: {names, images, index}
        self.channel_active_quiz = set()

        self.funny_insults = [
            "❌ ok bugbo 🥀",
            "❌ If ignorance is bliss, you must be the happiest person alive.",
            "❌ Incorrect!"
        ]

    def load_dso_data(self):
        path = os.path.join(os.path.dirname(__file__), "dsos.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def is_close_enough(self, user_answer, valid_answers, threshold=0.7):
        user_answer = user_answer.lower()
        return any(difflib.SequenceMatcher(None, user_answer, ans.lower()).ratio() >= threshold for ans in valid_answers)

    async def send_quiz_image(self, ctx, user_id):
        quiz = self.current_quiz.get(user_id)
        if not quiz:
            return

        images = quiz["images"]
        index = quiz["index"] % len(images)
        image_url = images[index]
        self.current_quiz[user_id]["index"] += 1

        embed = discord.Embed(
            title="🔭 Identify this Deep Space Object!",
            color=discord.Color.dark_blue()
        )
        embed.set_image(url=image_url)
        embed.set_footer(text='Reply with "a.[your guess]", "a.pic" for another view, or "a.skip".')
        await ctx.send(embed=embed)

    @commands.command(name="a")
    async def quiz(self, ctx):
        if ctx.author.id in self.current_quiz:
            await ctx.send("❗ You already have an active quiz. Use `a.skip` to skip or `a.pic` for another image.")
            return

        if ctx.channel.id in self.channel_active_quiz:
            await ctx.send("❗ Someone else is already quizzing in this channel.")
            return

        dso = random.choice(self.dso_data)

        # Combine primary name + aliases for valid answers
        names = [dso["name"]] + dso.get("aliases", [])
        names = [name.lower() for name in names]

        self.current_quiz[ctx.author.id] = {
            "names": names,
            "images": dso["images"],
            "index": 0,
            "primary": dso["name"]
        }
        self.channel_active_quiz.add(ctx.channel.id)

        await self.send_quiz_image(ctx, ctx.author.id)

    @commands.command(name="pic")
    async def another_pic(self, ctx):
        if ctx.author.id not in self.current_quiz:
            await ctx.send("You don't have an active quiz. Use `a` to start one.")
            return
        await self.send_quiz_image(ctx, ctx.author.id)

    @commands.command(name="skip")
    async def skip_quiz(self, ctx):
        if ctx.author.id in self.current_quiz:
            primary = self.current_quiz[ctx.author.id]["primary"]
            del self.current_quiz[ctx.author.id]
            self.channel_active_quiz.discard(ctx.channel.id)
            await ctx.send(f"⏭️ Skipped! The correct answer was **{primary}**.")
            await self.quiz(ctx)
        else:
            await ctx.send("You don't have an active quiz! Use `a` to start.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        content = message.content.strip().lower()
        prefix = "a."

        if content.startswith(prefix):
            guess = content[len(prefix):].strip()
            quiz = self.current_quiz.get(message.author.id)

            if not quiz:
                return

            valid_names = quiz["names"]
            primary_name = quiz["primary"]

            if guess == "skip":
                await message.channel.send(f"⏭️ Skipped! The correct answer was **{primary_name}**.")
                del self.current_quiz[message.author.id]
                self.channel_active_quiz.discard(message.channel.id)
                ctx = await self.bot.get_context(message)
                await self.quiz(ctx)
                return

            if self.is_close_enough(guess, valid_names):
                await message.channel.send(f"✅ Correct! It's **{primary_name}**.")
                del self.current_quiz[message.author.id]
                self.channel_active_quiz.discard(message.channel.id)
            elif len(guess) > 2:
                await message.channel.send(random.choice(self.funny_insults))

async def setup(bot):
    await bot.add_cog(IDCommands(bot))
