import discord
import json
import os

from datetime import datetime
from discord.ext import commands
from discord import app_commands
from utils.default import CustomContext
from utils.data import DiscordBot
from utils import permissions

LOG_FILE = "data/log_channels.json"


def load_log_channels() -> dict:
    if not os.path.exists("data"):
        os.makedirs("data")
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            json.dump({}, f)
    with open(LOG_FILE, "r") as f:
        return json.load(f)


def save_log_channels(data: dict):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_log_channel(bot, guild_id: int):
    data = load_log_channels()
    channel_id = data.get(str(guild_id))
    return bot.get_channel(channel_id) if channel_id else None


def log_embed(title: str, colour: discord.Colour) -> discord.Embed:
    return discord.Embed(title=title, colour=colour, timestamp=datetime.utcnow())


class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot: DiscordBot = bot

    # ── Setup ──────────────────────────────────────────────────────────

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def setlog(self, ctx: CustomContext, channel: discord.TextChannel = None):
        """ Set the log channel for this server. """
        channel = channel or ctx.channel
        data = load_log_channels()
        data[str(ctx.guild.id)] = channel.id
        save_log_channels(data)
        embed = discord.Embed(title="✅  Log Channel Set", colour=discord.Colour.green(),
            description=f"Events will now be logged in {channel.mention}.")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(manage_guild=True)
    async def unsetlog(self, ctx: CustomContext):
        """ Disable logging for this server. """
        data = load_log_channels()
        data.pop(str(ctx.guild.id), None)
        save_log_channels(data)
        embed = discord.Embed(title="🗑️  Logging Disabled", colour=discord.Colour.orange(),
            description="Log channel removed. No events will be logged.")
        await ctx.send(embed=embed)

    @app_commands.command(name="setlog", description="Set the log channel for this server.")
    @app_commands.describe(channel="Channel to send logs in (default: current channel)")
    @app_commands.default_permissions(manage_guild=True)
    async def slash_setlog(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        channel = channel or interaction.channel
        data = load_log_channels()
        data[str(interaction.guild_id)] = channel.id
        save_log_channels(data)
        embed = discord.Embed(title="✅  Log Channel Set", colour=discord.Colour.green(),
            description=f"Events will now be logged in {channel.mention}.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="unsetlog", description="Disable logging for this server.")
    @app_commands.default_permissions(manage_guild=True)
    async def slash_unsetlog(self, interaction: discord.Interaction):
        data = load_log_channels()
        data.pop(str(interaction.guild_id), None)
        save_log_channels(data)
        embed = discord.Embed(title="🗑️  Logging Disabled", colour=discord.Colour.orange(),
            description="Log channel removed. No events will be logged.")
        await interaction.response.send_message(embed=embed)

    # ── Messages ───────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        ch = get_log_channel(self.bot, message.guild.id)
        if not ch:
            return
        embed = log_embed("🗑️  Message Deleted", discord.Colour.red())
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name="👤 Author",  value=message.author.mention,  inline=True)
        embed.add_field(name="📺 Channel", value=message.channel.mention, inline=True)
        if message.content:
            content = message.content[:1021] + "..." if len(message.content) > 1024 else message.content
            embed.add_field(name="📝 Content", value=content, inline=False)
        embed.set_footer(text=f"User ID: {message.author.id}")
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot or before.content == after.content:
            return
        ch = get_log_channel(self.bot, before.guild.id)
        if not ch:
            return
        embed = log_embed("✏️  Message Edited", discord.Colour.gold())
        embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
        embed.add_field(name="👤 Author",  value=before.author.mention,  inline=True)
        embed.add_field(name="📺 Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="🔗 Jump",    value=f"[View Message]({after.jump_url})", inline=True)
        embed.add_field(name="Before", value=before.content[:512] or "*empty*", inline=False)
        embed.add_field(name="After",  value=after.content[:512]  or "*empty*", inline=False)
        embed.set_footer(text=f"User ID: {before.author.id}")
        await ch.send(embed=embed)

    # ── Members ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        ch = get_log_channel(self.bot, member.guild.id)
        if not ch:
            return
        age_days = (datetime.utcnow() - member.created_at.replace(tzinfo=None)).days
        new_flag = "  ⚠️ **New account!**" if age_days < 7 else ""
        embed = log_embed("📥  Member Joined", discord.Colour.green())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.add_field(name="👤 Member",       value=f"{member.mention}\n`{member}`",                        inline=True)
        embed.add_field(name="📅 Account Age",  value=f"<t:{int(member.created_at.timestamp())}:R>{new_flag}", inline=True)
        embed.add_field(name="👥 Member Count", value=str(member.guild.member_count),                          inline=True)
        embed.set_footer(text=f"User ID: {member.id}")
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        ch = get_log_channel(self.bot, member.guild.id)
        if not ch:
            return

        # Check audit log — if this was a kick, log it as a kick instead of a leave
        try:
            async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id:
                    embed = log_embed("👢  Member Kicked", discord.Colour.orange())
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                    embed.add_field(name="👤 Member",    value=f"{member.mention}\n`{member}`",        inline=True)
                    embed.add_field(name="🛡️ Moderator", value=str(entry.user),                        inline=True)
                    embed.add_field(name="📝 Reason",    value=entry.reason or "No reason provided",   inline=False)
                    embed.set_footer(text=f"User ID: {member.id}")
                    await ch.send(embed=embed)
                    return
        except discord.Forbidden:
            pass

        # Not a kick — regular leave
        roles = [r.mention for r in member.roles if r != member.guild.default_role]
        embed = log_embed("📤  Member Left", discord.Colour.red())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.add_field(name="👤 Member",    value=f"`{member}`", inline=True)
        embed.add_field(name="📥 Joined",    value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown", inline=True)
        embed.add_field(name="👥 Remaining", value=str(member.guild.member_count), inline=True)
        if roles:
            embed.add_field(name="🎭 Roles", value=", ".join(roles)[:1024], inline=False)
        embed.set_footer(text=f"User ID: {member.id}")
        await ch.send(embed=embed)

    # ── Bans ───────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        ch = get_log_channel(self.bot, guild.id)
        if not ch:
            return
        moderator = "Unknown"
        reason = "No reason provided"
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    moderator = str(entry.user)
                    reason = entry.reason or "No reason provided"
                    break
        except discord.Forbidden:
            pass
        embed = log_embed("🔨  Member Banned", discord.Colour.from_str("#E74C3C"))
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.add_field(name="👤 User",      value=f"{user.mention}\n`{user}`", inline=True)
        embed.add_field(name="🛡️ Moderator", value=moderator,                   inline=True)
        embed.add_field(name="📝 Reason",    value=reason,                      inline=False)
        embed.set_footer(text=f"User ID: {user.id}")
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        ch = get_log_channel(self.bot, guild.id)
        if not ch:
            return
        moderator = "Unknown"
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban):
                if entry.target.id == user.id:
                    moderator = str(entry.user)
                    break
        except discord.Forbidden:
            pass
        embed = log_embed("✅  Member Unbanned", discord.Colour.green())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.add_field(name="👤 User",      value=f"`{user}`", inline=True)
        embed.add_field(name="🛡️ Moderator", value=moderator,  inline=True)
        embed.set_footer(text=f"User ID: {user.id}")
        await ch.send(embed=embed)

    # ── Member Updates (nickname + roles + mute detection) ────────────

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        ch = get_log_channel(self.bot, before.guild.id)
        if not ch:
            return

        # Nickname change
        if before.nick != after.nick:
            embed = log_embed("✏️  Nickname Changed", discord.Colour.blurple())
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.add_field(name="👤 Member", value=after.mention,           inline=True)
            embed.add_field(name="Before",    value=before.nick or "*None*", inline=True)
            embed.add_field(name="After",     value=after.nick  or "*None*", inline=True)
            embed.set_footer(text=f"User ID: {after.id}")
            await ch.send(embed=embed)

        # Role changes
        added   = [r for r in after.roles  if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]

        # Mute/unmute detection via Muted role
        for role in added:
            if role.name == "Muted":
                embed = log_embed("🔇  Member Muted", discord.Colour.orange())
                embed.set_author(name=str(after), icon_url=after.display_avatar.url)
                embed.add_field(name="👤 Member", value=f"{after.mention}\n`{after}`", inline=True)
                embed.set_footer(text=f"User ID: {after.id}")
                await ch.send(embed=embed)

        for role in removed:
            if role.name == "Muted":
                embed = log_embed("🔊  Member Unmuted", discord.Colour.green())
                embed.set_author(name=str(after), icon_url=after.display_avatar.url)
                embed.add_field(name="👤 Member", value=f"{after.mention}\n`{after}`", inline=True)
                embed.set_footer(text=f"User ID: {after.id}")
                await ch.send(embed=embed)

        # General role add/remove (excluding Muted which is handled above)
        other_added   = [r for r in added   if r.name != "Muted"]
        other_removed = [r for r in removed if r.name != "Muted"]
        if other_added or other_removed:
            embed = log_embed("🎭  Roles Updated", discord.Colour.blurple())
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.add_field(name="👤 Member", value=after.mention, inline=False)
            if other_added:
                embed.add_field(name="➕ Added",   value=", ".join(r.mention for r in other_added),   inline=False)
            if other_removed:
                embed.add_field(name="➖ Removed", value=", ".join(r.mention for r in other_removed), inline=False)
            embed.set_footer(text=f"User ID: {after.id}")
            await ch.send(embed=embed)

    # ── Channel Updates ────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        ch = get_log_channel(self.bot, before.guild.id)
        if not ch:
            return
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        if hasattr(before, "topic") and before.topic != after.topic:
            changes.append(f"**Topic:** `{before.topic or 'None'}` → `{after.topic or 'None'}`")
        if hasattr(before, "slowmode_delay") and before.slowmode_delay != after.slowmode_delay:
            changes.append(f"**Slowmode:** `{before.slowmode_delay}s` → `{after.slowmode_delay}s`")
        if not changes:
            return
        embed = log_embed("📺  Channel Updated", discord.Colour.blurple())
        embed.add_field(name="📺 Channel", value=after.mention,        inline=True)
        embed.add_field(name="📝 Changes", value="\n".join(changes),   inline=False)
        await ch.send(embed=embed)

    # ── Voice ──────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel:
            return
        ch = get_log_channel(self.bot, member.guild.id)
        if not ch:
            return

        if before.channel is None:
            embed = log_embed("🎙️  Joined Voice", discord.Colour.green())
            embed.add_field(name="👤 Member",  value=member.mention,      inline=True)
            embed.add_field(name="🔊 Channel", value=after.channel.name,  inline=True)
        elif after.channel is None:
            embed = log_embed("🎙️  Left Voice", discord.Colour.red())
            embed.add_field(name="👤 Member",  value=member.mention,      inline=True)
            embed.add_field(name="🔊 Channel", value=before.channel.name, inline=True)
        else:
            embed = log_embed("🎙️  Switched Voice Channel", discord.Colour.gold())
            embed.add_field(name="👤 Member", value=member.mention,       inline=True)
            embed.add_field(name="From",      value=before.channel.name,  inline=True)
            embed.add_field(name="To",        value=after.channel.name,   inline=True)

        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        await ch.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Logging(bot))
