import discord
import os

from discord.ext import commands
from discord.ext.commands import AutoShardedBot
from utils import permissions, default
from utils.config import Config

COG_META = {
    "Fun_Commands":  ("🎮", "Fun & Games",    "Games, memes, and silly commands"),
    "Extras":        ("⭐", "Extras",          "Snipe, polls, reminders, trivia & more"),
    "Information":   ("📊", "Information",    "Bot stats, ping, invites and more"),
    "Discord_Info":  ("🔍", "Server & Users", "Server info, user profiles, avatars"),
    "Moderator":     ("🛡️", "Moderation",     "Kick, ban, mute, prune and more"),
    "Warns":         ("⚠️", "Warnings",       "Warn system — warn, view, clear"),
    "Logging":       ("📋", "Logging",        "Server event & mod action logging"),
    "Encryption":    ("🔐", "Encryption",     "Encode and decode text in many formats"),
    "Admin":         ("⚙️", "Admin",          "Owner-only bot management commands"),
    "Events":        None,
}

ACCENT_COLOUR = discord.Colour.from_str("#5865F2")


class CategorySelect(discord.ui.Select):
    def __init__(self, cogs, bot, invoker_id):
        self.bot = bot
        self.invoker_id = invoker_id
        options = []
        for cog in cogs:
            meta = COG_META.get(type(cog).__name__)
            if not meta:
                continue
            emoji, label, desc = meta
            options.append(discord.SelectOption(label=label, description=desc, emoji=emoji, value=type(cog).__name__))
        super().__init__(placeholder="📂  Browse command categories...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.invoker_id:
            return await interaction.response.send_message("❌ Only the person who used the help command can browse this menu.", ephemeral=True)
        cog_name = self.values[0]
        cog = self.bot.cogs.get(cog_name)
        if not cog:
            return await interaction.response.send_message("❌ Category not found.", ephemeral=True)
        meta = COG_META.get(cog_name)
        emoji, label, desc = meta
        cmds = [c for c in cog.get_commands() if not c.hidden]
        if not cmds:
            return await interaction.response.send_message("No visible commands in this category.", ephemeral=True)
        embed = discord.Embed(title=f"{emoji}  {label}", description=f"*{desc}*", colour=ACCENT_COLOUR)
        for cmd in cmds:
            aliases = f"  |  `{'` `'.join(cmd.aliases)}`" if cmd.aliases else ""
            value = cmd.help or "No description provided."
            if hasattr(cmd, "commands"):
                sub_names = ", ".join(f"`{s.name}`" for s in cmd.commands)
                value += f"\n> **Subcommands:** {sub_names}"
            embed.add_field(name=f"`{cmd.name}`{aliases}", value=value, inline=False)
        embed.set_footer(text=f"{len(cmds)} command{'s' if len(cmds) != 1 else ''}  •  Use !cmd or /cmd", icon_url=self.bot.user.display_avatar.url)
        await interaction.response.edit_message(embed=embed)


class HomeButton(discord.ui.Button):
    def __init__(self, cogs, bot, invoker_id):
        super().__init__(style=discord.ButtonStyle.secondary, emoji="🏠", label="Home", row=1)
        self.cogs = cogs
        self.bot = bot
        self.invoker_id = invoker_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.invoker_id:
            return await interaction.response.send_message("❌ Only the person who used the help command can use this.", ephemeral=True)
        visible_cogs = [c for c in self.cogs if COG_META.get(type(c).__name__) is not None]
        total_cmds = sum(len([cmd for cmd in cog.get_commands() if not cmd.hidden]) for cog in visible_cogs)
        embed = _build_home_embed(self.bot, interaction.user, visible_cogs, total_cmds)
        await interaction.response.edit_message(embed=embed)


def _build_home_embed(bot, author, visible_cogs, total_cmds):
    embed = discord.Embed(
        title=f"✨  {bot.user.name}  —  Help",
        description=(
            f"Hey **{author.display_name}**! 👋\n"
            f"I have **{total_cmds} commands** across **{len(visible_cogs)} categories**.\n\n"
            f"Use the **dropdown** to browse, or run `!help <command>` / `/<command>` directly."
        ),
        colour=ACCENT_COLOUR
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    for cog in visible_cogs:
        meta = COG_META.get(type(cog).__name__)
        if not meta:
            continue
        emoji, label, desc = meta
        cmd_count = len([c for c in cog.get_commands() if not c.hidden])
        embed.add_field(name=f"{emoji}  {label}", value=f"{desc}\n`{cmd_count} command{'s' if cmd_count != 1 else ''}`", inline=True)
    embed.set_footer(text=f"Only {author.display_name} can use this menu  •  Expires in 2 min", icon_url=author.display_avatar.url)
    return embed


class HelpView(discord.ui.View):
    def __init__(self, cogs, bot, invoker_id):
        super().__init__(timeout=120)
        self.invoker_id = invoker_id
        self.message = None
        self.add_item(CategorySelect(cogs, bot, invoker_id))
        self.add_item(HomeButton(cogs, bot, invoker_id))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

    async def interaction_check(self, interaction):
        return True


class HelpFormat(commands.HelpCommand):
    def get_destination(self):
        return self.context.channel

    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot
        visible_cogs = [cog for cog in bot.cogs.values() if COG_META.get(type(cog).__name__) is not None]
        total_cmds = sum(len([c for c in cog.get_commands() if not c.hidden]) for cog in visible_cogs)
        embed = _build_home_embed(bot, ctx.author, visible_cogs, total_cmds)
        view = HelpView(visible_cogs, bot, ctx.author.id)
        view.message = await ctx.send(embed=embed, view=view)

    async def send_command_help(self, command):
        ctx = self.context
        embed = discord.Embed(title=f"📖  `{command.name}`", description=command.help or "No description provided.", colour=ACCENT_COLOUR)
        usage = f"`{ctx.prefix}{command.name}" + (f" {command.signature}`" if command.signature else "`")
        embed.add_field(name="Prefix Usage", value=usage, inline=True)
        embed.add_field(name="Slash Usage", value=f"`/{command.name}`", inline=True)
        if command.aliases:
            embed.add_field(name="Aliases", value="  ".join(f"`{a}`" for a in command.aliases), inline=False)
        if command.cog:
            meta = COG_META.get(type(command.cog).__name__)
            if meta:
                embed.add_field(name="Category", value=f"{meta[0]}  {meta[1]}", inline=True)
        embed.set_footer(text="<required>   [optional]", icon_url=ctx.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    async def send_group_help(self, group):
        ctx = self.context
        embed = discord.Embed(title=f"📖  Command Group: `{group.name}`", description=group.help or "No description provided.", colour=ACCENT_COLOUR)
        if group.aliases:
            embed.add_field(name="Aliases", value="  ".join(f"`{a}`" for a in group.aliases), inline=False)
        subs = [c for c in group.commands if not c.hidden]
        if subs:
            embed.add_field(name="Subcommands", value="\n".join(f"`{ctx.prefix}{group.name} {s.name}` — {s.help or 'No description.'}" for s in subs), inline=False)
        embed.set_footer(text=f"Run {ctx.prefix}help {group.name} <subcommand> for more info", icon_url=ctx.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    async def send_cog_help(self, cog):
        ctx = self.context
        meta = COG_META.get(type(cog).__name__)
        emoji, label, desc = meta if meta else ("📂", type(cog).__name__, "")
        cmds = [c for c in cog.get_commands() if not c.hidden]
        embed = discord.Embed(title=f"{emoji}  {label}", description=desc, colour=ACCENT_COLOUR)
        for cmd in cmds:
            embed.add_field(name=f"`{cmd.name}`", value=cmd.help or "No description.", inline=False)
        embed.set_footer(text=f"{len(cmds)} command{'s' if len(cmds) != 1 else ''}", icon_url=ctx.bot.user.display_avatar.url)
        await ctx.send(embed=embed)

    async def send_error_message(self, error):
        embed = discord.Embed(title="❌  Not Found", description=error, colour=discord.Colour.red())
        await self.context.send(embed=embed)


class DiscordBot(AutoShardedBot):
    def __init__(self, config: Config, prefix=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = prefix
        self.config = config

    async def setup_hook(self):
        for file in os.listdir("cogs"):
            if not file.endswith(".py"):
                continue
            name = file[:-3]
            await self.load_extension(f"cogs.{name}")
        await self.tree.sync()
        print("✅ Slash commands synced globally.")

    async def on_message(self, msg: discord.Message):
        if not self.is_ready() or msg.author.bot or not permissions.can_handle(msg, "send_messages"):
            return
        await self.process_commands(msg)

    async def process_commands(self, msg):
        ctx = await self.get_context(msg, cls=default.CustomContext)
        await self.invoke(ctx)
