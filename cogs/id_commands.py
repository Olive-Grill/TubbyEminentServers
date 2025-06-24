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
        self.unused_queues = {
            "a": [],  # all
            "b": [],  # old
            "c": []  # new
        }
        self.reset_queues()

    def load_dso_data(self):
        path = os.path.join(os.path.dirname(__file__), "dsos.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def reset_queues(self):
        all_dsos = self.dso_data
        old_dsos = [d for d in all_dsos if not d.get("isnew?")]
        new_dsos = [d for d in all_dsos if d.get("isnew?")]

        self.unused_queues["a"] = random.sample(all_dsos, len(all_dsos))
        self.unused_queues["b"] = random.sample(old_dsos, len(old_dsos))
        self.unused_queues["c"] = random.sample(new_dsos, len(new_dsos))

    def is_close_enough(self, user_answer, valid_answers, threshold=0.7):
        user_answer = user_answer.casefold()
        return any(
            difflib.SequenceMatcher(None, user_answer, ans.casefold()).ratio()
            >= threshold for ans in valid_answers)

    def format_answer(self, quiz):
        primary = quiz["primary"]
        aliases = [
            name for name in quiz["names"] if name.lower() != primary.lower()
        ]
        all_names = [primary] + [alias.title() for alias in aliases]
        return ", ".join(all_names)

    async def send_quiz_image(self, ctx, channel_id):
        quiz = self.current_quiz.get(channel_id)
        if not quiz:
            return

        images = quiz["images"]
        if not images:
            await ctx.send("\u26a0\ufe0f No images available for this object.")
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
        await ctx.send(embed=embed)

    async def start_quiz(self, ctx, mode):
        if mode not in self.unused_queues:
            await ctx.send("❌ Invalid mode.")
            return

        if ctx.channel.id in self.current_quiz:
            await ctx.send(
                "❗ There's already an active quiz in this channel. Use `.skip` to skip or `.pic` for another image."
            )
            return

        if not self.unused_queues[mode]:
            self.reset_queues()

        queue = self.unused_queues[mode]
        if not queue:
            await ctx.send("No objects available for this mode.")
            return

        dso = queue.pop(0)
        names = [dso["name"]] + dso.get("aliases", [])
        names = [name.lower() for name in names]

        self.current_quiz[ctx.channel.id] = {
            "names": names,
            "images": dso["images"],
            "index": 0,
            "primary": dso["name"],
            "mode": mode,
            "hint_stage": 0
        }

        await self.send_quiz_image(ctx, ctx.channel.id)

    @commands.command(name="a")
    async def quiz_a(self, ctx):
        await self.start_quiz(ctx, mode="a")

    @commands.command(name="b")
    async def quiz_b(self, ctx):
        await self.start_quiz(ctx, mode="b")

    @commands.command(name="c")
    async def quiz_c(self, ctx):
        await self.start_quiz(ctx, mode="c")

    @commands.command(name="pic")
    async def another_pic(self, ctx):
        if ctx.channel.id not in self.current_quiz:
            await ctx.send(
                "No active quiz. Use `.a`, `.b`, or `.c` to start one.")
            return
        await self.send_quiz_image(ctx, ctx.channel.id)

    @commands.command(name="skip")
    async def skip_quiz(self, ctx):
        if ctx.channel.id in self.current_quiz:
            quiz = self.current_quiz[ctx.channel.id]
            answer_str = self.format_answer(quiz)
            dso_entry = next(
                (d for d in self.dso_data if d["name"] == quiz["primary"]),
                None)
            wiki_link = dso_entry.get("wikipedia") if dso_entry else None
            del self.current_quiz[ctx.channel.id]

            if wiki_link:
                await ctx.send(
                    f"⏭️ Skipped! The correct answer was **{answer_str}**. More info: {wiki_link}"
                )
            else:
                await ctx.send(
                    f"⏭️ Skipped! The correct answer was **{answer_str}**.")
        else:
            await ctx.send(
                "No active quiz to skip. Use `.a`, `.b`, or `.c` to start.")

    @commands.command(name="hint")
    async def show_hint(self, ctx):
        quiz = self.current_quiz.get(ctx.channel.id)
        if not quiz:
            await ctx.send(
                "No active quiz right now. Start one with `.a`, `.b`, or `.c`!"
            )
            return

        hint_stage = quiz.get("hint_stage", 0)
        primary_name = quiz["primary"]
        dso_entry = next(
            (d for d in self.dso_data if d["name"] == primary_name), None)

        if hint_stage == 0:
            first_three = primary_name[:3]
            masked_hint = first_three + "###"
            await ctx.send(
                f"🔑 HINT #1: The first three letters are **{masked_hint}**")
            quiz["hint_stage"] = 1
        else:
            if dso_entry and "hint" in dso_entry:
                await ctx.send(f"🔑 HINT #2: {dso_entry['hint']}")
            else:
                await ctx.send("No further hints available for this object.")
            quiz["hint_stage"] = 2

    @commands.command(name="announce")
    async def announce(self, ctx, channel_id: int, *, message: str):
        """
        Announce a message to any channel by its ID.
        Only allowed for user ID 711226437147033630.
        Usage: .announce 123456789012345678 Your announcement here
        """
        if ctx.author.id != 711226437147033630:
            await ctx.send("❌ You do not have permission to use this command.")
            return

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            await ctx.send("❌ Could not find a channel with that ID.")
            return

        if not isinstance(channel, discord.TextChannel):
            await ctx.send("❌ That ID does not belong to a text channel.")
            return

        try:
            await channel.send(f"📢 **Announcement:** {message}")
            await ctx.send(
                f"✅ Announcement sent to {channel.mention} in server **{channel.guild.name}**."
            )
        except Exception as e:
            await ctx.send(f"❌ Failed to send announcement: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Nathanielちゃん call-and-response joke 💀
        content = message.content.strip()
        if content in ("Astroboちゃん!", "Nathanielちゃん!"):
            await message.channel.send("はい~!")
            return
        if content == "何が好き?":
            await message.channel.send("チョコミント よりも あ・な・た 💖")
            return

        # Mustard image response
        if "mustard" in message.content.lower():
            embed = discord.Embed(title="")
            embed.set_image(
                url="https://i.ytimg.com/vi/eVPp3fJTZvc/maxresdefault.jpg")
            await message.channel.send(embed=embed)
            return

        # Mango image response
        if "mango" in message.content.lower():
            embed = discord.Embed(title="")
            embed.set_image(
                url="https://i.ytimg.com/vi/eVPp3fJTZvc/maxresdefault.jpg")
            await message.channel.send(embed=embed)
            return

        # 67 image response
        if "67" in message.content.lower():
            embed = discord.Embed(title="67?")
            await message.channel.send(embed=embed)
            return

        # Astrobo sybau response
        if "astrobo" in message.content.lower() and "sybau" in message.content.lower():
            embed = discord.Embed(title="🥺")
            await message.channel.send(embed=embed)
            return

        # Fuck you response
        if "a.fuck you" in message.content.lower():
            await message.channel.send("fuck you")
            return

        ctx = await self.bot.get_context(message)
        if ctx.command is not None:
            return

        content = content.lower()
        for prefix in ["a.", "b.", "c."]:
            if content.startswith(prefix):
                guess = content[len(prefix):].strip()
                quiz = self.current_quiz.get(message.channel.id)

                if not quiz or quiz.get("mode") != prefix[0]:
                    return

                primary_name = quiz["primary"]
                valid_names = quiz["names"]

                if guess == "skip":
                    answer_str = self.format_answer(quiz)
                    dso_entry = next(
                        (d
                         for d in self.dso_data if d["name"] == primary_name),
                        None)
                    wiki_link = dso_entry.get(
                        "wikipedia") if dso_entry else None
                    await message.channel.send(
                        f"⏭️ Skipped! The correct answer was **{answer_str}**."
                        + (f" More info: {wiki_link}" if wiki_link else ""))
                    del self.current_quiz[message.channel.id]
                    return

                if self.is_close_enough(guess, valid_names):
                    answer_str = self.format_answer(quiz)
                    dso_entry = next(
                        (d
                         for d in self.dso_data if d["name"] == primary_name),
                        None)
                    wiki_link = dso_entry.get(
                        "wikipedia") if dso_entry else None

                    if wiki_link:
                        await message.channel.send(
                            f"✅ Correct! It's **{answer_str}**. More info: {wiki_link}"
                        )
                    else:
                        await message.channel.send(
                            f"✅ Correct! It's **{answer_str}**.")
                    del self.current_quiz[message.channel.id]
                else:
                    if len(guess) > 2:
                        await message.channel.send(
                            random.choice(self.funny_insults))
                return


async def setup(bot):
    await bot.add_cog(IDCommands(bot))
