import aiohttp
import discord
import importlib
import os

from discord.ext import commands
from discord import app_commands
from utils.default import CustomContext
from utils import permissions, default, http
from utils.data import DiscordBot


def owner_only_slash(interaction: discord.Interaction) -> bool:
    return interaction.user.id == interaction.client.config.discord_owner_id


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot: DiscordBot = bot

    # ── Am I Admin ────────────────────────────────────────────────────

    @commands.command()
    async def amiadmin(self, ctx: CustomContext):
        """ Check if you are the bot owner. """
        if ctx.author.id == self.bot.config.discord_owner_id:
            return await ctx.send(f"✅ Yes, **{ctx.author.name}** — you are the bot owner.")
        await ctx.send(f"❌ No, **{ctx.author.name}**, you are not the bot owner.")

    @app_commands.command(name="amiadmin", description="Check if you are the bot owner.")
    async def slash_amiadmin(self, interaction: discord.Interaction):
        if interaction.user.id == self.bot.config.discord_owner_id:
            await interaction.response.send_message(f"✅ Yes, **{interaction.user.name}** — you are the bot owner.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ No, **{interaction.user.name}**, you are not the bot owner.", ephemeral=True)

    # ── Load ──────────────────────────────────────────────────────────

    @commands.command()
    @commands.check(permissions.is_owner)
    async def load(self, ctx: CustomContext, name: str):
        """ Load a cog extension. """
        try:
            await self.bot.load_extension(f"cogs.{name}")
        except Exception as e:
            return await ctx.send(default.traceback_maker(e))
        await ctx.send(f"✅ Loaded **{name}.py**")

    @app_commands.command(name="load", description="Load a cog extension. (Owner only)")
    @app_commands.describe(name="Cog name to load")
    @app_commands.check(owner_only_slash)
    async def slash_load(self, interaction: discord.Interaction, name: str):
        try:
            await self.bot.load_extension(f"cogs.{name}")
        except Exception as e:
            return await interaction.response.send_message(f"❌ {e}", ephemeral=True)
        await interaction.response.send_message(f"✅ Loaded **{name}.py**", ephemeral=True)

    # ── Unload ────────────────────────────────────────────────────────

    @commands.command()
    @commands.check(permissions.is_owner)
    async def unload(self, ctx: CustomContext, name: str):
        """ Unload a cog extension. """
        try:
            await self.bot.unload_extension(f"cogs.{name}")
        except Exception as e:
            return await ctx.send(default.traceback_maker(e))
        await ctx.send(f"✅ Unloaded **{name}.py**")

    @app_commands.command(name="unload", description="Unload a cog extension. (Owner only)")
    @app_commands.describe(name="Cog name to unload")
    @app_commands.check(owner_only_slash)
    async def slash_unload(self, interaction: discord.Interaction, name: str):
        try:
            await self.bot.unload_extension(f"cogs.{name}")
        except Exception as e:
            return await interaction.response.send_message(f"❌ {e}", ephemeral=True)
        await interaction.response.send_message(f"✅ Unloaded **{name}.py**", ephemeral=True)

    # ── Reload ────────────────────────────────────────────────────────

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reload(self, ctx: CustomContext, name: str):
        """ Reload a cog extension. """
        try:
            await self.bot.reload_extension(f"cogs.{name}")
        except Exception as e:
            return await ctx.send(default.traceback_maker(e))
        await ctx.send(f"✅ Reloaded **{name}.py**")

    @app_commands.command(name="reload", description="Reload a cog extension. (Owner only)")
    @app_commands.describe(name="Cog name to reload")
    @app_commands.check(owner_only_slash)
    async def slash_reload(self, interaction: discord.Interaction, name: str):
        try:
            await self.bot.reload_extension(f"cogs.{name}")
        except Exception as e:
            return await interaction.response.send_message(f"❌ {e}", ephemeral=True)
        await interaction.response.send_message(f"✅ Reloaded **{name}.py**", ephemeral=True)

    # ── Reload All ────────────────────────────────────────────────────

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reloadall(self, ctx: CustomContext):
        """ Reload all cog extensions. """
        errors = []
        for file in os.listdir("cogs"):
            if not file.endswith(".py"):
                continue
            try:
                await self.bot.reload_extension(f"cogs.{file[:-3]}")
            except Exception as e:
                errors.append([file, default.traceback_maker(e, advance=False)])
        if errors:
            output = "\n".join(f"**{g[0]}** ```diff\n- {g[1]}```" for g in errors)
            return await ctx.send(f"⚠️ Reloaded all, but these failed:\n\n{output}")
        await ctx.send("✅ Successfully reloaded all extensions.")

    @app_commands.command(name="reloadall", description="Reload all cog extensions. (Owner only)")
    @app_commands.check(owner_only_slash)
    async def slash_reloadall(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        errors = []
        for file in os.listdir("cogs"):
            if not file.endswith(".py"):
                continue
            try:
                await self.bot.reload_extension(f"cogs.{file[:-3]}")
            except Exception as e:
                errors.append(f"**{file}**: {e}")
        if errors:
            return await interaction.followup.send("⚠️ Some failed:\n" + "\n".join(errors), ephemeral=True)
        await interaction.followup.send("✅ Successfully reloaded all extensions.", ephemeral=True)

    # ── Reload Utils ──────────────────────────────────────────────────

    @commands.command()
    @commands.check(permissions.is_owner)
    async def reloadutils(self, ctx: CustomContext, name: str):
        """ Reload a utils module. """
        try:
            module_name = importlib.import_module(f"utils.{name}")
            importlib.reload(module_name)
        except ModuleNotFoundError:
            return await ctx.send(f"❌ Couldn't find module **utils/{name}.py**")
        except Exception as e:
            return await ctx.send(f"⚠️ Module returned an error:\n{default.traceback_maker(e)}")
        await ctx.send(f"✅ Reloaded **utils/{name}.py**")

    @app_commands.command(name="reloadutils", description="Reload a utils module. (Owner only)")
    @app_commands.describe(name="Utils module name")
    @app_commands.check(owner_only_slash)
    async def slash_reloadutils(self, interaction: discord.Interaction, name: str):
        try:
            module_name = importlib.import_module(f"utils.{name}")
            importlib.reload(module_name)
        except ModuleNotFoundError:
            return await interaction.response.send_message(f"❌ Module **utils/{name}.py** not found.", ephemeral=True)
        except Exception as e:
            return await interaction.response.send_message(f"⚠️ Error: {e}", ephemeral=True)
        await interaction.response.send_message(f"✅ Reloaded **utils/{name}.py**", ephemeral=True)

    # ── DM ────────────────────────────────────────────────────────────

    @commands.command()
    @commands.check(permissions.is_owner)
    async def dm(self, ctx: CustomContext, user: discord.User, *, message: str):
        """ DM a user directly. """
        try:
            await user.send(message)
            await ctx.send(f"✉️ Sent a DM to **{user}**")
        except discord.Forbidden:
            await ctx.send("❌ This user has DMs disabled or is a bot.")

    @app_commands.command(name="dm", description="DM a user directly. (Owner only)")
    @app_commands.describe(user="User to DM", message="Message to send")
    @app_commands.check(owner_only_slash)
    async def slash_dm(self, interaction: discord.Interaction, user: discord.User, message: str):
        try:
            await user.send(message)
            await interaction.response.send_message(f"✉️ Sent a DM to **{user}**", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ This user has DMs disabled or is a bot.", ephemeral=True)

    # ── Change Username ───────────────────────────────────────────────

    @commands.group()
    @commands.check(permissions.is_owner)
    async def change(self, ctx: CustomContext):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    @change.command(name="username")
    @commands.check(permissions.is_owner)
    async def change_username(self, ctx: CustomContext, *, name: str):
        """ Change the bot's username. """
        try:
            await self.bot.user.edit(username=name)
            await ctx.send(f"✅ Username changed to **{name}**")
        except discord.HTTPException as err:
            await ctx.send(err)

    @app_commands.command(name="change-username", description="Change the bot's username. (Owner only)")
    @app_commands.describe(name="New username")
    @app_commands.check(owner_only_slash)
    async def slash_change_username(self, interaction: discord.Interaction, name: str):
        try:
            await self.bot.user.edit(username=name)
            await interaction.response.send_message(f"✅ Username changed to **{name}**", ephemeral=True)
        except discord.HTTPException as err:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)

    # ── Change Avatar ─────────────────────────────────────────────────

    @change.command(name="avatar")
    @commands.check(permissions.is_owner)
    async def change_avatar(self, ctx: CustomContext, url: str = None):
        """ Change the bot's avatar. """
        if url is None and len(ctx.message.attachments) == 1:
            url = ctx.message.attachments[0].url
        elif url:
            url = url.strip("<>")
        try:
            bio = await http.get(url, res_method="read")
            await self.bot.user.edit(avatar=bio.response)
            await ctx.send("✅ Avatar updated successfully.")
        except aiohttp.InvalidURL:
            await ctx.send("❌ The URL provided is invalid.")
        except discord.InvalidArgument:
            await ctx.send("❌ That URL doesn't contain a valid image.")
        except discord.HTTPException as err:
            await ctx.send(err)
        except TypeError:
            await ctx.send("❌ Please provide an image URL or attach an image.")

    @app_commands.command(name="change-avatar", description="Change the bot's avatar via URL. (Owner only)")
    @app_commands.describe(url="Image URL for the new avatar")
    @app_commands.check(owner_only_slash)
    async def slash_change_avatar(self, interaction: discord.Interaction, url: str):
        try:
            bio = await http.get(url.strip("<>"), res_method="read")
            await self.bot.user.edit(avatar=bio.response)
            await interaction.response.send_message("✅ Avatar updated successfully.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Admin(bot))
