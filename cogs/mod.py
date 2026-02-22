import discord
import re
import asyncio

from discord.ext import commands
from discord import app_commands
from utils.default import CustomContext
from utils.data import DiscordBot
from utils import permissions, default

COL_SUCCESS = discord.Colour.green()
COL_ERROR   = discord.Colour.red()
COL_WARN    = discord.Colour.orange()
COL_INFO    = discord.Colour.blurple()
COL_MOD     = discord.Colour.from_str("#E74C3C")


def err(text):
    return discord.Embed(description=f"❌  {text}", colour=COL_ERROR)

def ok(text):
    return discord.Embed(description=f"✅  {text}", colour=COL_SUCCESS)


class MemberID(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            m = await commands.MemberConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                return int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(f"`{argument}` is not a valid member or member ID.") from None
        return m.id


class ActionReason(commands.Converter):
    async def convert(self, ctx, argument):
        if len(argument) > 512:
            raise commands.BadArgument(f"Reason too long ({len(argument)}/512 chars).")
        return argument


class Moderator(commands.Cog):
    def __init__(self, bot):
        self.bot: DiscordBot = bot

    # ── Kick ──────────────────────────────────────────────────────────

    def _kick_embed(self, member, moderator, reason):
        embed = discord.Embed(title="👢  Member Kicked", colour=COL_MOD)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Member",    value=f"{member.mention}\n`{member}`", inline=True)
        embed.add_field(name="🛡️ Moderator", value=moderator.mention,              inline=True)
        embed.add_field(name="📝 Reason",    value=reason or "No reason provided",  inline=False)
        embed.set_footer(text=f"User ID: {member.id}")
        return embed

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(kick_members=True)
    async def kick(self, ctx: CustomContext, member: discord.Member, *, reason: str = None):
        """ Kick a member from the server. """
        if await permissions.check_priv(ctx, member): return
        try:
            await member.kick(reason=default.responsible(ctx.author, reason))
            await ctx.send(embed=self._kick_embed(member, ctx.author, reason))
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="Member to kick", reason="Reason for kick")
    @app_commands.default_permissions(kick_members=True)
    async def slash_kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        try:
            await member.kick(reason=f"[ {interaction.user} ] {reason or 'No reason provided'}")
            await interaction.response.send_message(embed=self._kick_embed(member, interaction.user, reason))
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    # ── Nickname ───────────────────────────────────────────────────────

    @commands.command(aliases=["nick"])
    @commands.guild_only()
    @permissions.has_permissions(manage_nicknames=True)
    async def nickname(self, ctx: CustomContext, member: discord.Member = None, *, name: str = None):
        """ Change a nickname. No member = bot's nickname. """
        if member is None:
            try:
                await ctx.guild.me.edit(nick=name)
                return await ctx.send(embed=discord.Embed(title="✏️  Bot Nickname Updated",
                    description=f"Set to **{name}**." if name else "Nickname cleared.", colour=COL_SUCCESS))
            except Exception as e:
                return await ctx.send(embed=err(e))
        if await permissions.check_priv(ctx, member): return
        try:
            old = member.nick or member.name
            await member.edit(nick=name, reason=default.responsible(ctx.author, "Nickname changed"))
            embed = discord.Embed(title="✏️  Nickname Updated", colour=COL_SUCCESS)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="👤 Member", value=member.mention, inline=True)
            embed.add_field(name="Before",    value=f"`{old}`",     inline=True)
            embed.add_field(name="After",     value=f"`{name}`" if name else "*Cleared*", inline=True)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="nickname", description="Change a member's nickname. No member = bot's nickname.")
    @app_commands.describe(member="Member to rename (leave blank for bot)", name="New nickname (leave blank to clear)")
    @app_commands.default_permissions(manage_nicknames=True)
    async def slash_nickname(self, interaction: discord.Interaction, member: discord.Member = None, name: str = None):
        if member is None:
            try:
                await interaction.guild.me.edit(nick=name)
                return await interaction.response.send_message(embed=discord.Embed(title="✏️  Bot Nickname Updated",
                    description=f"Set to **{name}**." if name else "Nickname cleared.", colour=COL_SUCCESS))
            except Exception as e:
                return await interaction.response.send_message(embed=err(e), ephemeral=True)
        try:
            old = member.nick or member.name
            await member.edit(nick=name, reason=f"[ {interaction.user} ] Nickname changed")
            embed = discord.Embed(title="✏️  Nickname Updated", colour=COL_SUCCESS)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="👤 Member", value=member.mention, inline=True)
            embed.add_field(name="Before",    value=f"`{old}`",     inline=True)
            embed.add_field(name="After",     value=f"`{name}`" if name else "*Cleared*", inline=True)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    # ── Ban ────────────────────────────────────────────────────────────

    def _ban_embed(self, user, moderator, reason):
        embed = discord.Embed(title="🔨  Member Banned", colour=COL_MOD)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="👤 User",      value=f"{user.mention}\n`{user}`", inline=True)
        embed.add_field(name="🛡️ Moderator", value=moderator.mention,          inline=True)
        embed.add_field(name="📝 Reason",    value=reason or "No reason provided", inline=False)
        embed.set_footer(text=f"User ID: {user.id}")
        return embed

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(ban_members=True)
    async def ban(self, ctx: CustomContext, member: MemberID, *, reason: str = None):
        """ Ban a user from the server. """
        m = ctx.guild.get_member(member)
        if m is not None and await permissions.check_priv(ctx, m): return
        try:
            await ctx.guild.ban(discord.Object(id=member), reason=default.responsible(ctx.author, reason))
            target = m or await self.bot.fetch_user(member)
            await ctx.send(embed=self._ban_embed(target, ctx.author, reason))
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.describe(member="Member to ban", reason="Reason for ban")
    @app_commands.default_permissions(ban_members=True)
    async def slash_ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        try:
            await member.ban(reason=f"[ {interaction.user} ] {reason or 'No reason provided'}")
            await interaction.response.send_message(embed=self._ban_embed(member, interaction.user, reason))
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    # ── Unban ──────────────────────────────────────────────────────────

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(ban_members=True)
    async def unban(self, ctx: CustomContext, member: MemberID, *, reason: str = None):
        """ Unban a user from the server. """
        try:
            target = await self.bot.fetch_user(member)
            await ctx.guild.unban(discord.Object(id=member), reason=default.responsible(ctx.author, reason))
            embed = discord.Embed(title="✅  Member Unbanned", colour=COL_SUCCESS)
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.add_field(name="👤 User",      value=f"`{target}`",          inline=True)
            embed.add_field(name="🛡️ Moderator", value=ctx.author.mention,     inline=True)
            embed.add_field(name="📝 Reason",    value=reason or "No reason provided", inline=False)
            embed.set_footer(text=f"User ID: {member}")
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="unban", description="Unban a user by their ID.")
    @app_commands.describe(user_id="The user ID to unban", reason="Reason for unban")
    @app_commands.default_permissions(ban_members=True)
    async def slash_unban(self, interaction: discord.Interaction, user_id: str, reason: str = None):
        try:
            uid = int(user_id)
            target = await self.bot.fetch_user(uid)
            await interaction.guild.unban(discord.Object(id=uid), reason=f"[ {interaction.user} ] {reason or 'No reason'}")
            embed = discord.Embed(title="✅  Member Unbanned", colour=COL_SUCCESS)
            embed.set_thumbnail(url=target.display_avatar.url)
            embed.add_field(name="👤 User",      value=f"`{target}`",             inline=True)
            embed.add_field(name="🛡️ Moderator", value=interaction.user.mention,  inline=True)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    # ── Mute ───────────────────────────────────────────────────────────

    def _get_muted_role(self, guild):
        return next((r for r in guild.roles if r.name == "Muted"), None)

    def _mute_embed(self, member, moderator, reason, title, colour):
        embed = discord.Embed(title=title, colour=colour)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Member",    value=f"{member.mention}\n`{member}`", inline=True)
        embed.add_field(name="🛡️ Moderator", value=moderator.mention,              inline=True)
        embed.add_field(name="📝 Reason",    value=reason or "No reason provided",  inline=False)
        embed.set_footer(text=f"User ID: {member.id}")
        return embed

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    async def mute(self, ctx: CustomContext, member: discord.Member, *, reason: str = None):
        """ Mute a member (requires a role named 'Muted'). """
        if await permissions.check_priv(ctx, member): return
        muted_role = self._get_muted_role(ctx.guild)
        if not muted_role:
            return await ctx.send(embed=err("No **Muted** role found. Create one named exactly `Muted`."))
        try:
            await member.add_roles(muted_role, reason=default.responsible(ctx.author, reason))
            await ctx.send(embed=self._mute_embed(member, ctx.author, reason, "🔇  Member Muted", COL_WARN))
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="mute", description="Mute a member (requires a 'Muted' role).")
    @app_commands.describe(member="Member to mute", reason="Reason for mute")
    @app_commands.default_permissions(manage_roles=True)
    async def slash_mute(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        muted_role = self._get_muted_role(interaction.guild)
        if not muted_role:
            return await interaction.response.send_message(embed=err("No **Muted** role found. Create one named exactly `Muted`."), ephemeral=True)
        try:
            await member.add_roles(muted_role, reason=f"[ {interaction.user} ] {reason or 'No reason'}")
            await interaction.response.send_message(embed=self._mute_embed(member, interaction.user, reason, "🔇  Member Muted", COL_WARN))
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    async def unmute(self, ctx: CustomContext, member: discord.Member, *, reason: str = None):
        """ Unmute a member. """
        if await permissions.check_priv(ctx, member): return
        muted_role = self._get_muted_role(ctx.guild)
        if not muted_role:
            return await ctx.send(embed=err("No **Muted** role found. Create one named exactly `Muted`."))
        try:
            await member.remove_roles(muted_role, reason=default.responsible(ctx.author, reason))
            await ctx.send(embed=self._mute_embed(member, ctx.author, reason, "🔊  Member Unmuted", COL_SUCCESS))
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="unmute", description="Unmute a member.")
    @app_commands.describe(member="Member to unmute", reason="Reason for unmute")
    @app_commands.default_permissions(manage_roles=True)
    async def slash_unmute(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        muted_role = self._get_muted_role(interaction.guild)
        if not muted_role:
            return await interaction.response.send_message(embed=err("No **Muted** role found."), ephemeral=True)
        try:
            await member.remove_roles(muted_role, reason=f"[ {interaction.user} ] {reason or 'No reason'}")
            await interaction.response.send_message(embed=self._mute_embed(member, interaction.user, reason, "🔊  Member Unmuted", COL_SUCCESS))
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    # ── Slowmode ───────────────────────────────────────────────────────

    def _slowmode_embed(self, seconds, channel, moderator):
        if seconds == 0:
            return discord.Embed(title="🐇  Slowmode Disabled", colour=COL_SUCCESS,
                description=f"Slowmode removed from {channel.mention}.")
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        parts = [f"{hours}h" if hours else "", f"{mins}m" if mins else "", f"{secs}s" if secs else ""]
        duration = " ".join(p for p in parts if p)
        embed = discord.Embed(title="🐢  Slowmode Set", colour=COL_INFO)
        embed.add_field(name="📺 Channel",  value=channel.mention,  inline=True)
        embed.add_field(name="⏱️ Delay",    value=f"`{duration}`",  inline=True)
        embed.add_field(name="🛡️ Set by",   value=moderator.mention, inline=True)
        return embed

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(manage_channels=True)
    async def slowmode(self, ctx: CustomContext, seconds: int = 0):
        """ Set slowmode for this channel. 0 to disable. Max 21600 (6h). """
        if seconds < 0 or seconds > 21600:
            return await ctx.send(embed=err("Slowmode must be between **0** and **21600** seconds."))
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            await ctx.send(embed=self._slowmode_embed(seconds, ctx.channel, ctx.author))
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="slowmode", description="Set slowmode for this channel. 0 to disable.")
    @app_commands.describe(seconds="Delay in seconds (0 to disable, max 21600)")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_slowmode(self, interaction: discord.Interaction, seconds: int = 0):
        if seconds < 0 or seconds > 21600:
            return await interaction.response.send_message(embed=err("Slowmode must be between **0** and **21600** seconds."), ephemeral=True)
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            await interaction.response.send_message(embed=self._slowmode_embed(seconds, interaction.channel, interaction.user))
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    # ── Lock / Unlock ──────────────────────────────────────────────────

    def _lock_embed(self, channel, moderator, reason, locked: bool):
        embed = discord.Embed(title="🔒  Channel Locked" if locked else "🔓  Channel Unlocked",
            colour=COL_MOD if locked else COL_SUCCESS)
        embed.add_field(name="📺 Channel",   value=channel.mention,        inline=True)
        embed.add_field(name="🛡️ Moderator", value=moderator.mention,      inline=True)
        embed.add_field(name="📝 Reason",    value=reason or "No reason provided", inline=False)
        return embed

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(manage_channels=True)
    async def lock(self, ctx: CustomContext, channel: discord.TextChannel = None, *, reason: str = None):
        """ Lock a channel so only mods can send messages. """
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages is False:
            return await ctx.send(embed=err(f"{channel.mention} is already locked."))
        overwrite.send_messages = False
        try:
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite,
                reason=default.responsible(ctx.author, reason))
            await ctx.send(embed=self._lock_embed(channel, ctx.author, reason, True))
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="lock", description="Lock a channel so only mods can send messages.")
    @app_commands.describe(channel="Channel to lock (default: current)", reason="Reason for lock")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_lock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = None):
        channel = channel or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        if overwrite.send_messages is False:
            return await interaction.response.send_message(embed=err(f"{channel.mention} is already locked."), ephemeral=True)
        overwrite.send_messages = False
        try:
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite,
                reason=f"[ {interaction.user} ] {reason or 'No reason'}")
            await interaction.response.send_message(embed=self._lock_embed(channel, interaction.user, reason, True))
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(manage_channels=True)
    async def unlock(self, ctx: CustomContext, channel: discord.TextChannel = None, *, reason: str = None):
        """ Unlock a previously locked channel. """
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        if overwrite.send_messages is not False:
            return await ctx.send(embed=err(f"{channel.mention} is not locked."))
        overwrite.send_messages = None
        try:
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite,
                reason=default.responsible(ctx.author, reason))
            await ctx.send(embed=self._lock_embed(channel, ctx.author, reason, False))
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="unlock", description="Unlock a previously locked channel.")
    @app_commands.describe(channel="Channel to unlock (default: current)", reason="Reason for unlock")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_unlock(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = None):
        channel = channel or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        if overwrite.send_messages is not False:
            return await interaction.response.send_message(embed=err(f"{channel.mention} is not locked."), ephemeral=True)
        overwrite.send_messages = None
        try:
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite,
                reason=f"[ {interaction.user} ] {reason or 'No reason'}")
            await interaction.response.send_message(embed=self._lock_embed(channel, interaction.user, reason, False))
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    # ── Hide / Unhide ──────────────────────────────────────────────────

    def _hide_embed(self, channel, moderator, reason, hidden: bool):
        embed = discord.Embed(title="👁️  Channel Hidden" if hidden else "👁️  Channel Visible",
            colour=COL_MOD if hidden else COL_SUCCESS)
        embed.add_field(name="📺 Channel",   value=channel.mention,        inline=True)
        embed.add_field(name="🛡️ Moderator", value=moderator.mention,      inline=True)
        embed.add_field(name="📝 Reason",    value=reason or "No reason provided", inline=False)
        return embed

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(manage_channels=True)
    async def hide(self, ctx: CustomContext, channel: discord.TextChannel = None, *, reason: str = None):
        """ Hide a channel from regular members. """
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        if overwrite.view_channel is False:
            return await ctx.send(embed=err(f"{channel.mention} is already hidden."))
        overwrite.view_channel = False
        try:
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite,
                reason=default.responsible(ctx.author, reason))
            await ctx.send(embed=self._hide_embed(channel, ctx.author, reason, True))
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="hide", description="Hide a channel from regular members.")
    @app_commands.describe(channel="Channel to hide (default: current)", reason="Reason")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_hide(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = None):
        channel = channel or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        if overwrite.view_channel is False:
            return await interaction.response.send_message(embed=err(f"{channel.mention} is already hidden."), ephemeral=True)
        overwrite.view_channel = False
        try:
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite,
                reason=f"[ {interaction.user} ] {reason or 'No reason'}")
            await interaction.response.send_message(embed=self._hide_embed(channel, interaction.user, reason, True))
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    @commands.command()
    @commands.guild_only()
    @permissions.has_permissions(manage_channels=True)
    async def unhide(self, ctx: CustomContext, channel: discord.TextChannel = None, *, reason: str = None):
        """ Make a hidden channel visible again. """
        channel = channel or ctx.channel
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        if overwrite.view_channel is not False:
            return await ctx.send(embed=err(f"{channel.mention} is not hidden."))
        overwrite.view_channel = None
        try:
            await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite,
                reason=default.responsible(ctx.author, reason))
            await ctx.send(embed=self._hide_embed(channel, ctx.author, reason, False))
        except Exception as e:
            await ctx.send(embed=err(e))

    @app_commands.command(name="unhide", description="Make a hidden channel visible again.")
    @app_commands.describe(channel="Channel to unhide (default: current)", reason="Reason")
    @app_commands.default_permissions(manage_channels=True)
    async def slash_unhide(self, interaction: discord.Interaction, channel: discord.TextChannel = None, reason: str = None):
        channel = channel or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        if overwrite.view_channel is not False:
            return await interaction.response.send_message(embed=err(f"{channel.mention} is not hidden."), ephemeral=True)
        overwrite.view_channel = None
        try:
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite,
                reason=f"[ {interaction.user} ] {reason or 'No reason'}")
            await interaction.response.send_message(embed=self._hide_embed(channel, interaction.user, reason, False))
        except Exception as e:
            await interaction.response.send_message(embed=err(e), ephemeral=True)

    # ── Massban ────────────────────────────────────────────────────────

    @commands.command()
    @commands.guild_only()
    @commands.max_concurrency(1, per=commands.BucketType.user)
    @permissions.has_permissions(ban_members=True)
    async def massban(self, ctx: CustomContext, reason: ActionReason, *members: MemberID):
        """ Mass ban multiple members from the server. """
        if not members:
            return await ctx.send(embed=err("Provide at least one member to ban."))
        try:
            for mid in members:
                await ctx.guild.ban(discord.Object(id=mid), reason=default.responsible(ctx.author, reason))
            embed = discord.Embed(title="🔨  Mass Ban", colour=COL_MOD,
                description=f"Banned **{len(members)}** user(s).")
            embed.add_field(name="📝 Reason",    value=reason,              inline=True)
            embed.add_field(name="🛡️ Moderator", value=ctx.author.mention,  inline=True)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(embed=err(e))

    # ── Announce Role ──────────────────────────────────────────────────

    @commands.command(aliases=["ar"])
    @commands.guild_only()
    @permissions.has_permissions(manage_roles=True)
    async def announcerole(self, ctx: CustomContext, *, role: discord.Role):
        """ Temporarily make a role mentionable for an announcement. """
        if role == ctx.guild.default_role:
            return await ctx.send(embed=err("Cannot make @everyone/@here mentionable."))
        if ctx.author.top_role.position <= role.position:
            return await ctx.send(embed=err("That role is above your permission level."))
        if ctx.me.top_role.position <= role.position:
            return await ctx.send(embed=err("That role is above my permission level."))
        await role.edit(mentionable=True, reason=f"[ {ctx.author} ] announcerole")
        embed = discord.Embed(title="🔔  Role Mentionable",
            description=f"**{role.name}** is now mentionable. Mention it within **30 seconds** or it will revert.",
            colour=COL_INFO)
        msg = await ctx.send(embed=embed)
        while True:
            try:
                checker = await self.bot.wait_for("message", timeout=30.0, check=lambda m: role.mention in m.content)
                if checker.author.id == ctx.author.id:
                    await role.edit(mentionable=False, reason=f"[ {ctx.author} ] announcerole")
                    done = discord.Embed(title="✅  Announcement Sent",
                        description=f"**{role.name}** mentioned by {ctx.author.mention} in {checker.channel.mention}.",
                        colour=COL_SUCCESS)
                    return await msg.edit(embed=done)
                else:
                    await checker.delete()
            except asyncio.TimeoutError:
                await role.edit(mentionable=False, reason=f"[ {ctx.author} ] announcerole")
                return await msg.edit(embed=discord.Embed(title="⏳  Timed Out",
                    description=f"**{role.name}** was never mentioned. Reverted.", colour=COL_WARN))

    # ── Find ───────────────────────────────────────────────────────────

    @commands.group()
    @commands.guild_only()
    @permissions.has_permissions(ban_members=True)
    async def find(self, ctx: CustomContext):
        """ Find members by various criteria. """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @find.command(name="playing")
    async def find_playing(self, ctx, *, search: str):
        """ Find members playing a specific game. """
        loop = []
        for i in ctx.guild.members:
            if i.activities and not i.bot:
                for g in i.activities:
                    if g.name and search.lower() in g.name.lower():
                        loop.append(f"{i} | {type(g).__name__}: {g.name} ({i.id})")
        await default.pretty_results(ctx, "playing", f"Found **{len(loop)}** result(s) for **{search}**", loop)

    @find.command(name="username", aliases=["name"])
    async def find_name(self, ctx, *, search: str):
        """ Find members by username. """
        loop = [f"{i} ({i.id})" for i in ctx.guild.members if search.lower() in i.name.lower() and not i.bot]
        await default.pretty_results(ctx, "name", f"Found **{len(loop)}** result(s) for **{search}**", loop)

    @find.command(name="nickname", aliases=["nick"])
    async def find_nickname(self, ctx, *, search: str):
        """ Find members by nickname. """
        loop = [f"{i.nick} | {i} ({i.id})" for i in ctx.guild.members if i.nick and search.lower() in i.nick.lower() and not i.bot]
        await default.pretty_results(ctx, "nickname", f"Found **{len(loop)}** result(s) for **{search}**", loop)

    @find.command(name="id")
    async def find_id(self, ctx, *, search: int):
        """ Find members by ID. """
        loop = [f"{i} ({i.id})" for i in ctx.guild.members if str(search) in str(i.id) and not i.bot]
        await default.pretty_results(ctx, "id", f"Found **{len(loop)}** result(s) for `{search}`", loop)

    # ── Prune ──────────────────────────────────────────────────────────

    @commands.group()
    @commands.guild_only()
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @permissions.has_permissions(manage_messages=True)
    async def prune(self, ctx: CustomContext):
        """ Delete messages from this channel. """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @app_commands.command(name="purge", description="Delete a number of messages from this channel.")
    @app_commands.describe(amount="Number of messages to delete (max 100)")
    @app_commands.default_permissions(manage_messages=True)
    async def slash_purge(self, interaction: discord.Interaction, amount: int = 10):
        if amount < 1 or amount > 100:
            return await interaction.response.send_message(embed=err("Amount must be between 1 and 100."), ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(embed=discord.Embed(
            title="🗑️  Messages Purged",
            description=f"Deleted **{len(deleted)}** message{'s' if len(deleted) != 1 else ''}.",
            colour=COL_SUCCESS), ephemeral=True)

    async def do_removal(self, ctx, limit, predicate, *, before=None, after=None, message=True):
        if limit > 2000:
            return await ctx.send(embed=err(f"Too many messages to search ({limit}/2000)."))
        before = ctx.message if not before else discord.Object(id=before)
        if after: after = discord.Object(id=after)
        try:
            deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
        except discord.Forbidden:
            return await ctx.send(embed=err("I don't have permission to delete messages here."))
        except discord.HTTPException as e:
            return await ctx.send(embed=err(f"{e} — try a smaller amount."))
        if message:
            n = len(deleted)
            msg = await ctx.send(embed=discord.Embed(title="🗑️  Messages Pruned",
                description=f"Deleted **{n}** message{'s' if n != 1 else ''} from {ctx.channel.mention}.",
                colour=COL_SUCCESS))
            await asyncio.sleep(5)
            await msg.delete()

    @prune.command()
    async def embeds(self, ctx, search: int = 100):
        """ Remove messages that contain embeds. """
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @prune.command()
    async def files(self, ctx, search: int = 100):
        """ Remove messages that contain attachments. """
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @prune.command()
    async def mentions(self, ctx, search: int = 100):
        """ Remove messages that contain mentions. """
        await self.do_removal(ctx, search, lambda e: len(e.mentions) or len(e.role_mentions))

    @prune.command()
    async def images(self, ctx, search: int = 100):
        """ Remove messages that contain embeds or attachments. """
        await self.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))

    @prune.command(name="all")
    async def _remove_all(self, ctx, search: int = 100):
        """ Remove all messages. """
        await self.do_removal(ctx, search, lambda e: True)

    @prune.command()
    async def user(self, ctx, member: discord.Member, search: int = 100):
        """ Remove all messages from a specific member. """
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @prune.command()
    async def contains(self, ctx, *, substr: str):
        """ Remove messages containing a substring (min 3 chars). """
        if len(substr) < 3:
            return await ctx.send(embed=err("Substring must be at least 3 characters."))
        await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @prune.command(name="bots")
    async def _bots(self, ctx, search: int = 100, prefix: str = None):
        """ Remove bot messages. """
        getprefix = prefix if prefix else self.bot.config.discord_prefix
        await self.do_removal(ctx, search, lambda m: (m.webhook_id is None and m.author.bot) or m.content.startswith(tuple(getprefix)))

    @prune.command(name="users")
    async def _users(self, ctx, search: int = 100):
        """ Remove only human messages. """
        await self.do_removal(ctx, search, lambda m: not m.author.bot)

    @prune.command(name="emojis")
    async def _emojis(self, ctx, search: int = 100):
        """ Remove messages containing custom emojis. """
        custom_emoji = re.compile(r"<a?:(.*?):(\d{17,21})>|[\u263a-\U0001f645]")
        await self.do_removal(ctx, search, lambda m: custom_emoji.search(m.content))

    @prune.command(name="reactions")
    async def _reactions(self, ctx, search: int = 100):
        """ Remove all reactions from recent messages. """
        if search > 2000:
            return await ctx.send(embed=err(f"Too many messages ({search}/2000)."))
        total = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if message.reactions:
                total += sum(r.count for r in message.reactions)
                await message.clear_reactions()
        await ctx.send(embed=discord.Embed(title="✅  Reactions Cleared",
            description=f"Removed **{total}** reaction(s) from the last **{search}** messages.", colour=COL_SUCCESS))


async def setup(bot):
    await bot.add_cog(Moderator(bot))
