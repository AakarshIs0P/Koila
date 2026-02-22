import discord
import json
import os

from datetime import datetime
from discord.ext import commands
from discord import app_commands
from utils.default import CustomContext
from utils.data import DiscordBot
from utils import permissions

WARNS_FILE = "data/warns.json"


def load_warns() -> dict:
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(WARNS_FILE):
        with open(WARNS_FILE, "w") as f:
            json.dump({}, f)
    with open(WARNS_FILE, "r") as f:
        return json.load(f)


def save_warns(data: dict):
    with open(WARNS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _add_warn(guild_id: str, user_id: str, reason: str, moderator: str, moderator_id: int) -> int:
    data = load_warns()
    if guild_id not in data:
        data[guild_id] = {}
    if user_id not in data[guild_id]:
        data[guild_id][user_id] = []
    data[guild_id][user_id].append({
        "reason": reason,
        "moderator": moderator,
        "moderator_id": moderator_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    save_warns(data)
    return len(data[guild_id][user_id])


def _warn_embed(member: discord.Member, moderator: discord.Member, reason: str, count: int) -> discord.Embed:
    embed = discord.Embed(title="⚠️  Member Warned", colour=discord.Colour.orange())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="👤 Member",          value=f"{member.mention}\n`{member}`", inline=True)
    embed.add_field(name="🛡️ Moderator",       value=moderator.mention,              inline=True)
    embed.add_field(name="📊 Total Warnings",  value=f"**{count}**",                 inline=True)
    embed.add_field(name="📝 Reason",          value=reason,                         inline=False)
    embed.set_footer(text=f"User ID: {member.id}")
    return embed


def _warnings_embed(member: discord.Member, guild_id: str) -> discord.Embed:
    data = load_warns()
    warns = data.get(guild_id, {}).get(str(member.id), [])
    embed = discord.Embed(
        title=f"📋  Warnings — {member.display_name}",
        colour=discord.Colour.orange() if warns else discord.Colour.green()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    if not warns:
        embed.description = f"✅ **{member.display_name}** has no warnings."
    else:
        embed.description = f"**{len(warns)}** warning{'s' if len(warns) != 1 else ''} on record."
        for i, w in enumerate(warns, 1):
            try:
                unix = int(datetime.fromisoformat(w.get("timestamp", "")).timestamp())
                time_str = f"<t:{unix}:R>"
            except Exception:
                time_str = "Unknown time"
            embed.add_field(name=f"Warning #{i}",
                value=f"**Reason:** {w['reason']}\n**By:** {w['moderator']}\n**When:** {time_str}", inline=False)
    embed.set_footer(text=f"User ID: {member.id}")
    return embed


class Warns(commands.Cog):
    def __init__(self, bot):
        self.bot: DiscordBot = bot

    # ── Warn ──────────────────────────────────────────────────────────

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def warn(self, ctx: CustomContext, member: discord.Member, *, reason: str = "No reason provided"):
        """ Warn a member. """
        if await permissions.check_priv(ctx, member):
            return
        count = _add_warn(str(ctx.guild.id), str(member.id), reason, str(ctx.author), ctx.author.id)
        await ctx.send(embed=_warn_embed(member, ctx.author, reason, count))
        try:
            dm = discord.Embed(title=f"⚠️  You were warned in {ctx.guild.name}",
                description=f"**Reason:** {reason}", colour=discord.Colour.orange())
            dm.add_field(name="Total Warnings", value=str(count))
            dm.set_footer(text="Please follow the server rules.")
            await member.send(embed=dm)
        except discord.Forbidden:
            pass

    @app_commands.command(name="warn", description="Warn a member.")
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    @app_commands.default_permissions(kick_members=True)
    async def slash_warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.id == interaction.user.id:
            return await interaction.response.send_message("❌ You can't warn yourself.", ephemeral=True)
        count = _add_warn(str(interaction.guild_id), str(member.id), reason, str(interaction.user), interaction.user.id)
        await interaction.response.send_message(embed=_warn_embed(member, interaction.user, reason, count))
        try:
            dm = discord.Embed(title=f"⚠️  You were warned in {interaction.guild.name}",
                description=f"**Reason:** {reason}", colour=discord.Colour.orange())
            dm.add_field(name="Total Warnings", value=str(count))
            dm.set_footer(text="Please follow the server rules.")
            await member.send(embed=dm)
        except discord.Forbidden:
            pass

    # ── Warnings ──────────────────────────────────────────────────────

    @commands.command(aliases=["infractions"])
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def warnings(self, ctx: CustomContext, member: discord.Member = None):
        """ View warnings for a member. """
        await ctx.send(embed=_warnings_embed(member or ctx.author, str(ctx.guild.id)))

    @app_commands.command(name="warnings", description="View warnings for a member.")
    @app_commands.describe(member="Member to check (default: yourself)")
    @app_commands.default_permissions(kick_members=True)
    async def slash_warnings(self, interaction: discord.Interaction, member: discord.Member = None):
        await interaction.response.send_message(embed=_warnings_embed(member or interaction.user, str(interaction.guild_id)))

    # ── Clear Warn ────────────────────────────────────────────────────

    @commands.command(aliases=["clearwarnings", "resetwarn"])
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def clearwarn(self, ctx: CustomContext, member: discord.Member, index: int = None):
        """ Clear all warnings or a specific one (by number) for a member. """
        data = load_warns()
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        warns = data.get(guild_id, {}).get(user_id, [])
        if not warns:
            return await ctx.send(embed=discord.Embed(description=f"✅ **{member.display_name}** has no warnings to clear.", colour=discord.Colour.green()))
        if index is not None:
            if index < 1 or index > len(warns):
                return await ctx.send(embed=discord.Embed(description=f"❌ Invalid number. They have **{len(warns)}** warning(s).", colour=discord.Colour.red()))
            removed = warns.pop(index - 1)
            data[guild_id][user_id] = warns
            save_warns(data)
            embed = discord.Embed(title="🗑️  Warning Removed", colour=discord.Colour.green())
            embed.add_field(name="Member",          value=member.mention,    inline=True)
            embed.add_field(name="Removed #",       value=str(index),        inline=True)
            embed.add_field(name="Reason was",      value=removed["reason"], inline=False)
        else:
            count = len(warns)
            data[guild_id][user_id] = []
            save_warns(data)
            embed = discord.Embed(title="🗑️  All Warnings Cleared",
                description=f"Removed **{count}** warning{'s' if count != 1 else ''} from {member.mention}.",
                colour=discord.Colour.green())
        embed.set_footer(text=f"Cleared by {ctx.author} • User ID: {member.id}")
        await ctx.send(embed=embed)

    @app_commands.command(name="clearwarn", description="Clear warnings for a member.")
    @app_commands.describe(member="Member to clear warnings for", index="Warning number to remove (leave blank to clear all)")
    @app_commands.default_permissions(kick_members=True)
    async def slash_clearwarn(self, interaction: discord.Interaction, member: discord.Member, index: int = None):
        data = load_warns()
        guild_id = str(interaction.guild_id)
        user_id = str(member.id)
        warns = data.get(guild_id, {}).get(user_id, [])
        if not warns:
            return await interaction.response.send_message(embed=discord.Embed(description=f"✅ **{member.display_name}** has no warnings.", colour=discord.Colour.green()))
        if index is not None:
            if index < 1 or index > len(warns):
                return await interaction.response.send_message(embed=discord.Embed(description=f"❌ Invalid number. They have **{len(warns)}** warning(s).", colour=discord.Colour.red()))
            removed = warns.pop(index - 1)
            data[guild_id][user_id] = warns
            save_warns(data)
            embed = discord.Embed(title="🗑️  Warning Removed", colour=discord.Colour.green())
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.add_field(name="Removed #", value=str(index), inline=True)
            embed.add_field(name="Reason was", value=removed["reason"], inline=False)
        else:
            count = len(warns)
            data[guild_id][user_id] = []
            save_warns(data)
            embed = discord.Embed(title="🗑️  All Warnings Cleared",
                description=f"Removed **{count}** warning{'s' if count != 1 else ''} from {member.mention}.",
                colour=discord.Colour.green())
        embed.set_footer(text=f"Cleared by {interaction.user} • User ID: {member.id}")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Warns(bot))
