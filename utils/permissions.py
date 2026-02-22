import discord
from typing import Union, TYPE_CHECKING
from discord.ext import commands

if TYPE_CHECKING:
    from utils.default import CustomContext


def is_owner(ctx: "CustomContext") -> bool:
    return ctx.author.id == ctx.bot.config.discord_owner_id


async def check_permissions(ctx: "CustomContext", perms, *, check=all) -> bool:
    if ctx.author.id == ctx.bot.config.discord_owner_id:
        return True

    resolved = ctx.channel.permissions_for(ctx.author)
    return check(getattr(resolved, name, None) == value for name, value in perms.items())


def has_permissions(*, check=all, **perms) -> commands.check:
    async def pred(ctx: "CustomContext"):
        return await check_permissions(ctx, perms, check=check)
    return commands.check(pred)


async def check_priv(ctx: "CustomContext", member: discord.Member) -> Union[discord.Message, bool, None]:
    try:
        if member.id == ctx.author.id:
            return await ctx.send(f"❌ You can't {ctx.command.name} yourself.")
        if member.id == ctx.bot.user.id:
            return await ctx.send("❌ Nice try, but I won't do that to myself.")

        if ctx.author.id == ctx.guild.owner.id:
            return False
        if member.id == ctx.bot.config.discord_owner_id:
            if ctx.author.id != ctx.bot.config.discord_owner_id:
                return await ctx.send(f"❌ I can't {ctx.command.name} my owner.")
        if member.id == ctx.guild.owner.id:
            return await ctx.send(f"❌ You can't {ctx.command.name} the server owner.")
        if ctx.author.top_role == member.top_role:
            return await ctx.send(f"❌ You can't {ctx.command.name} someone with the same role as you.")
        if ctx.author.top_role < member.top_role:
            return await ctx.send(f"❌ You can't {ctx.command.name} someone with a higher role than you.")
    except Exception:
        pass


def can_handle(ctx: "CustomContext", permission: str) -> bool:
    return (
        isinstance(ctx.channel, discord.DMChannel) or
        getattr(ctx.channel.permissions_for(ctx.guild.me), permission)
    )
