import time
import discord
import psutil
import os

from utils.default import CustomContext
from discord.ext import commands
from discord import app_commands
from utils import default, http
from utils.data import DiscordBot


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot: DiscordBot = bot
        self.process = psutil.Process(os.getpid())

    # ── Ping ──────────────────────────────────────────────────────────

    async def _ping_embed(self) -> discord.Embed:
        embed = discord.Embed(colour=discord.Colour.blurple())
        embed.add_field(name="📡 WebSocket", value=f"`{int(round(self.bot.latency * 1000, 1))}ms`")
        return embed

    @commands.command()
    async def ping(self, ctx: CustomContext):
        """ Check the bot's latency. """
        before = time.monotonic()
        msg = await ctx.send("🏓 Pinging...")
        ping = (time.monotonic() - before) * 1000
        embed = discord.Embed(colour=discord.Colour.blurple())
        embed.add_field(name="📡 WebSocket", value=f"`{int(round(self.bot.latency * 1000, 1))}ms`")
        embed.add_field(name="📬 REST",      value=f"`{int(ping)}ms`")
        await msg.edit(content=None, embed=embed)

    @app_commands.command(name="ping", description="Check the bot's latency.")
    async def slash_ping(self, interaction: discord.Interaction):
        before = time.monotonic()
        await interaction.response.send_message("🏓 Pinging...")
        ping = (time.monotonic() - before) * 1000
        embed = discord.Embed(colour=discord.Colour.blurple())
        embed.add_field(name="📡 WebSocket", value=f"`{int(round(self.bot.latency * 1000, 1))}ms`")
        embed.add_field(name="📬 REST",      value=f"`{int(ping)}ms`")
        await interaction.edit_original_response(content=None, embed=embed)

    # ── Invite ────────────────────────────────────────────────────────

    def _invite_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🔗 Invite Me",
            description=f"[Click here to invite me to your server!]({discord.utils.oauth_url(self.bot.user.id)})",
            colour=discord.Colour.blurple()
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        return embed

    @commands.command(aliases=["joinme", "join", "botinvite"])
    async def invite(self, ctx: CustomContext):
        """ Get the bot invite link. """
        await ctx.send(embed=self._invite_embed())

    @app_commands.command(name="invite", description="Get the bot's invite link.")
    async def slash_invite(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._invite_embed())

    # ── COVID ─────────────────────────────────────────────────────────

    async def _covid_embed(self, country: str) -> discord.Embed:
        r = await http.get(f"https://disease.sh/v3/covid-19/countries/{country.lower()}", res_method="json")
        if "message" in r.response:
            return discord.Embed(description=f"❌ {r.response['message']}", colour=discord.Colour.red())
        d = r.response
        embed = discord.Embed(
            title=f":flag_{d['countryInfo']['iso2'].lower()}: COVID-19 — {country.capitalize()}",
            description=f"Last updated <t:{int(d['updated'] / 1000)}:R>",
            colour=discord.Colour.red()
        )
        for name, val in [
            ("🧪 Total Cases", d["cases"]), ("💀 Total Deaths", d["deaths"]),
            ("💚 Total Recovered", d["recovered"]), ("🔴 Active Cases", d["active"]),
            ("🏥 Critical", d["critical"]), ("📈 New Cases Today", d["todayCases"]),
            ("📉 New Deaths Today", d["todayDeaths"]), ("✅ New Recoveries Today", d["todayRecovered"]),
        ]:
            embed.add_field(name=name, value=f"{val:,}" if isinstance(val, int) else val)
        return embed

    @commands.command()
    async def covid(self, ctx: CustomContext, *, country: str):
        """ COVID-19 statistics for any country. """
        async with ctx.channel.typing():
            await ctx.send(embed=await self._covid_embed(country))

    @app_commands.command(name="covid", description="COVID-19 statistics for any country.")
    @app_commands.describe(country="Country name")
    async def slash_covid(self, interaction: discord.Interaction, country: str):
        await interaction.response.defer()
        await interaction.followup.send(embed=await self._covid_embed(country))

    # ── About ─────────────────────────────────────────────────────────

    def _about_embed(self, guild=None) -> discord.Embed:
        ram_usage = self.process.memory_full_info().rss / 1024**2
        avg_members = sum(g.member_count for g in self.bot.guilds) / len(self.bot.guilds)
        colour = discord.Colour.blurple()
        embed = discord.Embed(title=f"📊 About {self.bot.user.name}", colour=colour)
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="⏱ Last Boot",  value=default.date(self.bot.uptime, ago=True))
        embed.add_field(name="👑 Owner",      value=str(self.bot.get_user(self.bot.config.discord_owner_id)))
        embed.add_field(name="📚 Library",    value="discord.py")
        embed.add_field(name="🌐 Servers",    value=f"{len(self.bot.guilds)} (avg: {avg_members:,.0f} members)")
        embed.add_field(name="⚙️ Commands",   value=len([x.name for x in self.bot.commands]))
        embed.add_field(name="💾 RAM",        value=f"{ram_usage:.2f} MB")
        return embed

    @commands.command(aliases=["info", "stats", "status"])
    async def about(self, ctx: CustomContext):
        """ About the bot. """
        await ctx.send(embed=self._about_embed(ctx.guild))

    @app_commands.command(name="about", description="Information and stats about the bot.")
    async def slash_about(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._about_embed(interaction.guild))


async def setup(bot):
    await bot.add_cog(Information(bot))
