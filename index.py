import discord

from utils.config import Config
from utils.data import DiscordBot, HelpFormat

config = Config(
    discord_token="token",
    discord_prefix="!",
    discord_owner_id=828960010359930880,
    discord_join_message="Welcome to the server! 👋",
    discord_activity_name="with code",
    discord_activity_type="playing",
    discord_status_type="online",
    discord_autorole_id=None,
)

print("Logging in...")

bot = DiscordBot(
    config=config,
    command_prefix=config.discord_prefix,
    prefix=config.discord_prefix,
    command_attrs=dict(hidden=True),
    help_command=HelpFormat(),
    allowed_mentions=discord.AllowedMentions(
        everyone=False, roles=False, users=True
    ),
    intents=discord.Intents(
        guilds=True, members=True, messages=True, reactions=True,
        presences=True, message_content=True,
    )
)

try:
    bot.run(config.discord_token)
except Exception as e:
    print(f"Error when logging in: {e}")
