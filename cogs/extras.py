import discord
import asyncio
import random
import aiohttp
import html

from datetime import datetime, timedelta
from discord.ext import commands
from discord import app_commands
from utils.default import CustomContext
from utils.data import DiscordBot

ACCENT = discord.Colour.from_str("#5865F2")
snipe_cache: dict = {}


# ─── Tic Tac Toe ────────────────────────────────────────────────
class TTTButton(discord.ui.Button):
    def __init__(self, row: int, col: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=row)
        self.row_pos = row
        self.col_pos = col

    async def callback(self, interaction: discord.Interaction):
        view: TTTView = self.view
        if interaction.user.id != view.current_player.id:
            return await interaction.response.send_message("❌ It's not your turn!", ephemeral=True)
        self.label = view.current_symbol
        self.style = discord.ButtonStyle.danger if view.current_symbol == "❌" else discord.ButtonStyle.primary
        self.disabled = True
        view.board[self.row_pos][self.col_pos] = view.current_symbol
        if view.check_winner():
            view.stop()
            for item in view.children: item.disabled = True
            return await interaction.response.edit_message(
                embed=discord.Embed(title="🎮  Tic Tac Toe", description=f"🎉 **{interaction.user.display_name}** wins!", colour=discord.Colour.green()), view=view)
        if view.is_full():
            view.stop()
            for item in view.children: item.disabled = True
            return await interaction.response.edit_message(
                embed=discord.Embed(title="🎮  Tic Tac Toe", description="🤝 It's a **tie**!", colour=discord.Colour.gold()), view=view)
        view.switch_turn()
        await interaction.response.edit_message(
            embed=discord.Embed(title="🎮  Tic Tac Toe",
                description=f"It's **{view.current_player.display_name}**'s turn ({view.current_symbol})", colour=ACCENT), view=view)


class TTTView(discord.ui.View):
    def __init__(self, p1, p2):
        super().__init__(timeout=120)
        self.player1 = p1
        self.player2 = p2
        self.current_player = p1
        self.current_symbol = "❌"
        self.board = [["" for _ in range(3)] for _ in range(3)]
        self.message = None
        for r in range(3):
            for c in range(3):
                self.add_item(TTTButton(r, c))

    def switch_turn(self):
        self.current_player = self.player2 if self.current_player == self.player1 else self.player1
        self.current_symbol = "⭕" if self.current_symbol == "❌" else "❌"

    def check_winner(self):
        b = self.board
        for line in ([b[r] for r in range(3)] + [[b[r][c] for r in range(3)] for c in range(3)] +
                     [[b[0][0], b[1][1], b[2][2]], [b[0][2], b[1][1], b[2][0]]]):
            if line[0] and line[0] == line[1] == line[2]:
                return line[0]
        return None

    def is_full(self):
        return all(self.board[r][c] for r in range(3) for c in range(3))

    async def on_timeout(self):
        for item in self.children: item.disabled = True
        if self.message:
            try: await self.message.edit(view=self)
            except discord.NotFound: pass


# ─── Trivia ─────────────────────────────────────────────────────
class TriviaView(discord.ui.View):
    def __init__(self, correct, all_answers, invoker_id):
        super().__init__(timeout=20)
        self.correct = correct
        self.invoker_id = invoker_id
        self.answered = False
        self.message = None
        random.shuffle(all_answers)
        for answer in all_answers:
            btn = discord.ui.Button(label=answer, style=discord.ButtonStyle.secondary)
            btn.callback = self.make_callback(answer)
            self.add_item(btn)

    def make_callback(self, answer):
        async def callback(interaction: discord.Interaction):
            if self.answered:
                return await interaction.response.send_message("⏱️ Already answered!", ephemeral=True)
            self.answered = True
            self.stop()
            for item in self.children:
                item.disabled = True
                if item.label == self.correct: item.style = discord.ButtonStyle.success
                elif item.label == answer and answer != self.correct: item.style = discord.ButtonStyle.danger
            won = answer == self.correct
            embed = discord.Embed(
                description=f"✅ **Correct!** The answer was **{self.correct}**." if won else f"❌ **Wrong!** The correct answer was **{self.correct}**.",
                colour=discord.Colour.green() if won else discord.Colour.red())
            await interaction.response.edit_message(embed=embed, view=self)
        return callback

    async def on_timeout(self):
        if not self.answered:
            for item in self.children:
                item.disabled = True
                if item.label == self.correct: item.style = discord.ButtonStyle.success
            if self.message:
                try:
                    await self.message.edit(embed=discord.Embed(
                        description=f"⏱️ Time's up! The answer was **{self.correct}**.", colour=discord.Colour.orange()), view=self)
                except discord.NotFound: pass


async def fetch_trivia():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://opentdb.com/api.php?amount=1&type=multiple", timeout=aiohttp.ClientTimeout(total=5)) as resp:
            return await resp.json()


def trivia_embed_and_view(data, invoker_id):
    result = data["results"][0]
    question = html.unescape(result["question"])
    correct  = html.unescape(result["correct_answer"])
    incorrect = [html.unescape(a) for a in result["incorrect_answers"]]
    diff = result["difficulty"]
    diff_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(diff, "⚪")
    colours = {"easy": discord.Colour.green(), "medium": discord.Colour.gold(), "hard": discord.Colour.red()}
    embed = discord.Embed(title="🧠  Trivia Question", description=f"**{question}**", colour=colours.get(diff, ACCENT))
    embed.add_field(name="Category",   value=html.unescape(result["category"]), inline=True)
    embed.add_field(name="Difficulty", value=f"{diff_emoji} {diff.capitalize()}",  inline=True)
    embed.set_footer(text="You have 20 seconds to answer!")
    view = TriviaView(correct, [correct] + incorrect, invoker_id)
    return embed, view


# ─── Main Cog ───────────────────────────────────────────────────
class Extras(commands.Cog):
    def __init__(self, bot):
        self.bot: DiscordBot = bot

    # ── Snipe ──────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        snipe_cache[message.channel.id] = {
            "content": message.content,
            "author": str(message.author),
            "avatar": message.author.display_avatar.url,
            "timestamp": message.created_at
        }

    def _snipe_embed(self, channel_id: int, channel_name: str):
        data = snipe_cache.get(channel_id)
        if not data:
            return discord.Embed(description="🔍 Nothing to snipe — the cache is empty.", colour=discord.Colour.orange()), False
        embed = discord.Embed(description=data["content"] or "*[no text content]*", colour=ACCENT, timestamp=data["timestamp"])
        embed.set_author(name=data["author"], icon_url=data["avatar"])
        embed.set_footer(text=f"Sniped in #{channel_name}")
        return embed, True

    @commands.command()
    @commands.guild_only()
    async def snipe(self, ctx: CustomContext):
        """ Show the last deleted message in this channel. """
        embed, _ = self._snipe_embed(ctx.channel.id, ctx.channel.name)
        await ctx.send(embed=embed)

    @app_commands.command(name="snipe", description="Show the last deleted message in this channel.")
    async def slash_snipe(self, interaction: discord.Interaction):
        embed, _ = self._snipe_embed(interaction.channel_id, interaction.channel.name)
        await interaction.response.send_message(embed=embed)

    # ── Poll ───────────────────────────────────────────────────

    async def _create_poll(self, question: str, options: list, author: discord.Member, send_fn):
        number_emojis = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"]
        if len(options) < 2:
            return None, "❌ Please provide at least **2 options**."
        if len(options) > 9:
            return None, "❌ Maximum **9 options** allowed."
        embed = discord.Embed(title=f"📊  {question}", colour=ACCENT)
        embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
        embed.description = "\n\n".join(f"{number_emojis[i]}  {opt}" for i, opt in enumerate(options))
        embed.set_footer(text="Vote by reacting below!")
        return embed, None

    @commands.command()
    @commands.guild_only()
    async def poll(self, ctx: CustomContext, question: str, *options: str):
        """ Create a reaction poll. Up to 9 options. Usage: !poll "Question" "Option 1" "Option 2" """
        embed, error = await self._create_poll(question, list(options), ctx.author, None)
        if error:
            return await ctx.send(embed=discord.Embed(description=error, colour=discord.Colour.red()))
        try: await ctx.message.delete()
        except discord.Forbidden: pass
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            await msg.add_reaction(["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"][i])

    @app_commands.command(name="poll", description="Create a reaction poll with up to 4 options.")
    @app_commands.describe(question="Poll question", option1="Option 1", option2="Option 2", option3="Option 3 (optional)", option4="Option 4 (optional)")
    async def slash_poll(self, interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None):
        options = [o for o in [option1, option2, option3, option4] if o]
        embed, error = await self._create_poll(question, options, interaction.user, None)
        if error:
            return await interaction.response.send_message(embed=discord.Embed(description=error, colour=discord.Colour.red()), ephemeral=True)
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        for i in range(len(options)):
            await msg.add_reaction(["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣"][i])

    # ── Remind Me ──────────────────────────────────────────────

    def _parse_time(self, time_str: str):
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        unit = time_str[-1].lower()
        if unit not in units or not time_str[:-1].isdigit():
            return None, "❌ Invalid time format. Use `10s`, `5m`, `2h`, or `1d`."
        seconds = int(time_str[:-1]) * units[unit]
        if seconds > 604800:
            return None, "❌ Maximum reminder time is **7 days**."
        return seconds, None

    @commands.command(aliases=["remind", "reminder"])
    async def remindme(self, ctx: CustomContext, time: str, *, reminder: str):
        """ Set a reminder. Format: 10s, 5m, 2h, 1d. Example: !remindme 30m do homework """
        seconds, error = self._parse_time(time)
        if error:
            return await ctx.send(embed=discord.Embed(description=error, colour=discord.Colour.red()))
        unix = int((datetime.utcnow() + timedelta(seconds=seconds)).timestamp())
        embed = discord.Embed(title="⏰  Reminder Set", description=f"I'll remind you about:\n> {reminder}", colour=discord.Colour.green())
        embed.add_field(name="Fires", value=f"<t:{unix}:R>  (<t:{unix}:t>)")
        embed.set_footer(text="Reminder will be sent in this channel.")
        await ctx.send(embed=embed)
        await asyncio.sleep(seconds)
        fire = discord.Embed(title="⏰  Reminder!", description=f"> {reminder}", colour=ACCENT)
        fire.set_footer(text=f"Set {time} ago")
        await ctx.send(content=ctx.author.mention, embed=fire)

    @app_commands.command(name="remindme", description="Set a reminder. Format: 10s, 5m, 2h, 1d.")
    @app_commands.describe(time="Time until reminder (e.g. 30m, 2h, 1d)", reminder="What to remind you about")
    async def slash_remindme(self, interaction: discord.Interaction, time: str, reminder: str):
        seconds, error = self._parse_time(time)
        if error:
            return await interaction.response.send_message(embed=discord.Embed(description=error, colour=discord.Colour.red()), ephemeral=True)
        unix = int((datetime.utcnow() + timedelta(seconds=seconds)).timestamp())
        embed = discord.Embed(title="⏰  Reminder Set", description=f"I'll remind you about:\n> {reminder}", colour=discord.Colour.green())
        embed.add_field(name="Fires", value=f"<t:{unix}:R>  (<t:{unix}:t>)")
        embed.set_footer(text="Reminder will be sent in this channel.")
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(seconds)
        fire = discord.Embed(title="⏰  Reminder!", description=f"> {reminder}", colour=ACCENT)
        fire.set_footer(text=f"Set {time} ago")
        await interaction.followup.send(content=interaction.user.mention, embed=fire)

    # ── Tic Tac Toe ────────────────────────────────────────────

    @commands.command(aliases=["ttt"])
    @commands.guild_only()
    async def tictactoe(self, ctx: CustomContext, opponent: discord.Member):
        """ Challenge someone to Tic Tac Toe! """
        if opponent.id == ctx.author.id:
            return await ctx.send(embed=discord.Embed(description="❌ You can't play against yourself!", colour=discord.Colour.red()))
        if opponent.bot:
            return await ctx.send(embed=discord.Embed(description="❌ You can't play against a bot.", colour=discord.Colour.red()))
        embed = discord.Embed(title="🎮  Tic Tac Toe",
            description=f"**{ctx.author.display_name}** (❌) vs **{opponent.display_name}** (⭕)\n\nIt's **{ctx.author.display_name}**'s turn (❌)", colour=ACCENT)
        view = TTTView(ctx.author, opponent)
        view.message = await ctx.send(embed=embed, view=view)

    @app_commands.command(name="tictactoe", description="Challenge someone to Tic Tac Toe!")
    @app_commands.describe(opponent="Who to challenge")
    async def slash_tictactoe(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.id == interaction.user.id:
            return await interaction.response.send_message(embed=discord.Embed(description="❌ You can't play against yourself!", colour=discord.Colour.red()), ephemeral=True)
        if opponent.bot:
            return await interaction.response.send_message(embed=discord.Embed(description="❌ You can't play against a bot.", colour=discord.Colour.red()), ephemeral=True)
        embed = discord.Embed(title="🎮  Tic Tac Toe",
            description=f"**{interaction.user.display_name}** (❌) vs **{opponent.display_name}** (⭕)\n\nIt's **{interaction.user.display_name}**'s turn (❌)", colour=ACCENT)
        view = TTTView(interaction.user, opponent)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    # ── Trivia ─────────────────────────────────────────────────

    @commands.command()
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def trivia(self, ctx: CustomContext):
        """ Answer a random trivia question! """
        async with ctx.channel.typing():
            try:
                data = await fetch_trivia()
            except Exception:
                return await ctx.send(embed=discord.Embed(description="❌ Could not reach the trivia API.", colour=discord.Colour.red()))
        embed, view = trivia_embed_and_view(data, ctx.author.id)
        view.message = await ctx.send(embed=embed, view=view)

    @app_commands.command(name="trivia", description="Answer a random trivia question!")
    async def slash_trivia(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            data = await fetch_trivia()
        except Exception:
            return await interaction.followup.send(embed=discord.Embed(description="❌ Could not reach the trivia API.", colour=discord.Colour.red()))
        embed, view = trivia_embed_and_view(data, interaction.user.id)
        msg = await interaction.followup.send(embed=embed, view=view)
        view.message = msg

    # ── Autorole listener ──────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        autorole_id = getattr(self.bot.config, "discord_autorole_id", None)
        if not autorole_id:
            return
        role = member.guild.get_role(autorole_id)
        if role:
            try:
                await member.add_roles(role, reason="Auto-role on join")
            except discord.Forbidden:
                pass


async def setup(bot):
    await bot.add_cog(Extras(bot))
