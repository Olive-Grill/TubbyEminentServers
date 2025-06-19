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
        self.current_quiz = {
        }  # channel_id: {names, images, index, mode, primary, hint_stage}
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

    async def send_quiz_image(self, ctx, channel_id):
        quiz = self.current_quiz.get(channel_id)
        if not quiz:
            return

        images = quiz["images"]
        if not images:
            await ctx.send("⚠️ No images available for this object.")
            return

        index = quiz["index"] % len(images)
        image_url = images[index]
        self.current_quiz[channel_id]["index"] += 1

        mode = quiz.get("mode", "a")
        footer_text = (
            f'Reply with "{mode}.[your guess]", "{mode}.pic" for another view, '
            f'"{mode}.skip" to skip, or "{mode}.hint" for up to 2 hints.')

        embed = discord.Embed(title="🔭 Identify this Deep Space Object!",
                              color=discord.Color.dark_blue())
        embed.set_image(url=image_url)
        embed.set_footer(text=footer_text)
        print(
            f"[send_quiz_image] Sending image to channel {channel_id}: {image_url}"
        )
        await ctx.send(embed=embed)

    async def start_quiz(self, ctx, mode: str = "a"):
        if ctx.channel.id in self.current_quiz:
            await ctx.send(
                "❗ There's already an active quiz in this channel. Use `.skip` to skip or `.pic` for another image."
            )
            print(
                f"[start_quiz] Channel {ctx.channel.id} already has an active quiz."
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

        self.current_quiz[ctx.channel.id] = {
            "names": names,
            "images": dso["images"],
            "index": 0,
            "primary": dso["name"],
            "mode": mode,
            "hint_stage": 0  # init hint stage here
        }

        print(
            f"[start_quiz] Started quiz in channel {ctx.channel.id}, mode {mode}"
        )
        await self.send_quiz_image(ctx, ctx.channel.id)

    @commands.command(name="a")
    async def quiz_a(self, ctx):
        """Start a deep space object identification quiz (division B/C)"""
        await self.start_quiz(ctx, mode="a")

    @commands.command(name="b")
    async def quiz_b(self, ctx):
        """Start a DSO quiz limited to Division B objects"""
        await self.start_quiz(ctx, mode="b")

    @commands.command(name="pic")
    async def another_pic(self, ctx):
        """Get another image for your current quiz"""
        if ctx.channel.id not in self.current_quiz:
            await ctx.send("No active quiz. Use `.a` or `.b` to start one.")
            return
        print(f"[another_pic] Sending another pic in channel {ctx.channel.id}")
        await self.send_quiz_image(ctx, ctx.channel.id)

    @commands.command(name="skip")
    async def skip_quiz(self, ctx):
        """Skip the current quiz and reveal the answer"""
        if ctx.channel.id in self.current_quiz:
            primary = self.current_quiz[ctx.channel.id]["primary"]
            del self.current_quiz[ctx.channel.id]
            print(f"[skip_quiz] Quiz skipped in channel {ctx.channel.id}.")
            await ctx.send(f"⏭️ Skipped! The correct answer was **{primary}**."
                           )
        else:
            await ctx.send("No active quiz to skip. Use `.a` or `.b` to start."
                           )

    @commands.command(name="hint")
    async def show_hint(self, ctx):
        """Show a hint for the current DSO quiz with 2-step hints"""
        quiz = self.current_quiz.get(ctx.channel.id)
        if not quiz:
            await ctx.send(
                "No active quiz right now. Start one with `.a` or `.b`!")
            return

        hint_stage = quiz.get("hint_stage", 0)
        primary_name = quiz["primary"]
        dso_entry = next(
            (d for d in self.dso_data if d["name"] == primary_name), None)

        if hint_stage == 0:
            # First hint: first 3 letters + mask rest
            first_three = primary_name[:3]
            masked_hint = first_three + "###"
            await ctx.send(
                f"💡 HINT #1: The first three letters are **{masked_hint}**")
            quiz["hint_stage"] = 1
        else:
            # Second or further hints: full hint if available
            if dso_entry and "hint" in dso_entry:
                await ctx.send(f"💡 HINT #2: {dso_entry['hint']}")
            else:
                await ctx.send("No further hints available for this object.")
            quiz["hint_stage"] = 2

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)
        if ctx.command is not None:
            return

        content = message.content.strip().lower()
        for prefix in ["a.", "b."]:
            if content.startswith(prefix):
                guess = content[len(prefix):].strip()
                quiz = self.current_quiz.get(message.channel.id)

                if not quiz or quiz.get("mode") != prefix[0]:
                    print(
                        f"[on_message] No active quiz or mode mismatch in channel {message.channel.id}"
                    )
                    return

                primary_name = quiz["primary"]
                valid_names = quiz["names"]

                if guess == "skip":
                    print(
                        f"[on_message] Quiz skipped in channel {message.channel.id}"
                    )
                    await message.channel.send(
                        f"⏭️ Skipped! The correct answer was **{primary_name}**."
                    )
                    del self.current_quiz[message.channel.id]
                    return

                if self.is_close_enough(guess, valid_names):
                    print(
                        f"[on_message] Correct answer in channel {message.channel.id} by {message.author.id}"
                    )
                    await message.channel.send(
                        f"✅ Correct! It's **{primary_name}**.")
                    del self.current_quiz[message.channel.id]
                else:
                    if len(guess) > 2:
                        print(
                            f"[on_message] Incorrect guess in channel {message.channel.id} by {message.author.id}"
                        )
                        await message.channel.send(
                            random.choice(self.funny_insults))
                return


async def setup(bot):
    await bot.add_cog(IDCommands(bot))
