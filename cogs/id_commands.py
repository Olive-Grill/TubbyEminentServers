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
        self.current_quiz = {}  # user_id: {names, images, index, mode}
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
        return any(
            difflib.SequenceMatcher(None, user_answer, ans.lower()).ratio() >=
            threshold for ans in valid_answers)

    async def send_quiz_image(self, ctx, user_id):
        quiz = self.current_quiz.get(user_id)
        if not quiz:
            return

        images = quiz["images"]
        if not images:
            await ctx.send("⚠️ No images available for this object.")
            return

        index = quiz["index"] % len(images)
        image_url = images[index]
        self.current_quiz[user_id]["index"] += 1

        mode = quiz.get("mode", "a")
        footer_text = f'Reply with "{mode}.[your guess]", "{mode}.pic" for another view, "{mode}.skip" to skip, or "{mode}.hint" for a hint.'

        embed = discord.Embed(title="🔭 Identify this Deep Space Object!",
                              color=discord.Color.dark_blue())
        embed.set_image(url=image_url)
        embed.set_footer(text=footer_text)
        print(f"[send_quiz_image] Sending image to user {user_id}: {image_url}"
              )  # Debug
        await ctx.send(embed=embed)

    async def start_quiz(self, ctx, mode: str = "a"):
        if ctx.author.id in self.current_quiz:
            active_mode = self.current_quiz[ctx.author.id].get("mode", mode)
            await ctx.send(
                f"❗ You already have an active quiz. Use `{active_mode}.skip` to skip or `{active_mode}.pic` for another image."
            )
            print(
                f"[start_quiz] User {ctx.author.id} tried to start a quiz but already has one active."
            )
            return

        if ctx.channel.id in self.channel_active_quiz:
            await ctx.send(
                "❗ Someone else is already quizzing in this channel.")
            print(
                f"[start_quiz] Channel {ctx.channel.id} already has active quiz."
            )
            return

        if mode == "b":
            filtered_data = [
                d for d in self.dso_data if d.get("division") == "B"
            ]
        else:
            filtered_data = self.dso_data

        if not filtered_data:
            await ctx.send("No objects available in this mode.")
            print("[start_quiz] No objects available to quiz.")
            return

        dso = random.choice(filtered_data)
        names = [dso["name"]] + dso.get("aliases", [])
        names = [name.lower() for name in names]

        self.current_quiz[ctx.author.id] = {
            "names": names,
            "images": dso["images"],
            "index": 0,
            "primary": dso["name"],
            "mode": mode
        }
        self.channel_active_quiz.add(ctx.channel.id)

        print(
            f"[start_quiz] Started quiz for user {ctx.author.id} in channel {ctx.channel.id}, mode {mode}"
        )
        await self.send_quiz_image(ctx, ctx.author.id)

    @commands.command(name="a")
    async def quiz_a(self, ctx):
        """Start a deep space object identification quiz (division B/C)"""
        await self.start_quiz(ctx, mode="a")

    @commands.command(name="b")
    async def quiz_b(self, ctx):
        """coming soon"""
        await self.start_quiz(ctx, mode="b")

    @commands.command(name="pic")
    async def another_pic(self, ctx):
        """Get another image for your current quiz"""
        if ctx.author.id not in self.current_quiz:
            await ctx.send(
                "You don't have an active quiz. Use `a` or `b` to start one.")
            return
        print(f"[another_pic] Sending another pic for user {ctx.author.id}")
        await self.send_quiz_image(ctx, ctx.author.id)

    @commands.command(name="skip")
    async def skip_quiz(self, ctx):
        """Skip the current quiz and reveal the answer"""
        if ctx.author.id in self.current_quiz:
            primary = self.current_quiz[ctx.author.id]["primary"]
            del self.current_quiz[ctx.author.id]
            self.channel_active_quiz.discard(ctx.channel.id)
            print(f"[skip_quiz] User {ctx.author.id} skipped the quiz.")
            await ctx.send(f"⏭️ Skipped! The correct answer was **{primary}**."
                           )
        else:
            await ctx.send(
                "You don't have an active quiz! Use `a` or `b` to start.")

    @commands.command(name="hint")
    async def get_hint(self, ctx):
        """Get a hint for your current quiz"""
        if ctx.author.id not in self.current_quiz:
            await ctx.send(
                "You don't have an active quiz. Use `a` or `b` to start one.")
            return
        
        quiz = self.current_quiz[ctx.author.id]
        primary_name = quiz["primary"]
        
        # Find the hint for this object
        hint = None
        for dso in self.dso_data:
            if dso["name"] == primary_name:
                hint = dso.get("hint", "No hint available for this object.")
                break
        
        if hint:
            await ctx.send(f"💡 **Hint:** {hint}")
        else:
            await ctx.send("💡 No hint available for this object.")
        
        print(f"[get_hint] User {ctx.author.id} requested hint for {primary_name}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)
        if ctx.command is not None:
            # Let commands be processed normally and exit early
            return

        content = message.content.strip().lower()
        for prefix in ["a.", "b."]:
            if content.startswith(prefix):
                guess = content[len(prefix):].strip()
                quiz = self.current_quiz.get(message.author.id)

                if not quiz or quiz.get("mode") != prefix[0]:
                    print(
                        f"[on_message] No active quiz or mode mismatch for user {message.author.id}"
                    )
                    return

                primary_name = quiz["primary"]
                valid_names = quiz["names"]

                if guess == "skip":
                    print(
                        f"[on_message] User {message.author.id} skipped the quiz."
                    )
                    await message.channel.send(
                        f"⏭️ Skipped! The correct answer was **{primary_name}**."
                    )
                    del self.current_quiz[message.author.id]
                    self.channel_active_quiz.discard(message.channel.id)
                    return

                if self.is_close_enough(guess, valid_names):
                    print(
                        f"[on_message] User {message.author.id} answered correctly."
                    )
                    await message.channel.send(
                        f"✅ Correct! It's **{primary_name}**.")
                    del self.current_quiz[message.author.id]
                    self.channel_active_quiz.discard(message.channel.id)
                else:
                    if len(guess) > 2:
                        print(
                            f"[on_message] User {message.author.id} answered incorrectly."
                        )
                        incorrect_response = random.choice([
                            "❌ Incorrect! Try again.",
                            "❌ That's not right. Keep guessing!",
                            "❌ Nope, try another guess.",
                            *self.funny_insults
                        ])
                        await message.channel.send(incorrect_response)
                return


async def setup(bot):
    await bot.add_cog(IDCommands(bot))
