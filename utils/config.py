from dataclasses import dataclass, field


@dataclass
class Config:
    discord_token: str
    discord_prefix: str
    discord_owner_id: int
    discord_join_message: str
    discord_activity_name: str
    discord_activity_type: str
    discord_status_type: str
    discord_autorole_id: int = None   # Optional: role ID to auto-assign on join
