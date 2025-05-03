import os
import json
import aiohttp
import requests
import disnake
from datetime import datetime
from typing import Dict, List, Any, Optional
from . import helper

async def CreateServerBackup(guild: disnake.Guild, backup_directory: str, backup_creator: str) -> Dict[str, Any]:
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    backup_data = {
        "backup_info": {
            "timestamp": timestamp,
            "creator": backup_creator
        },
        "server_info": {},
        "roles_data": [],
        "channels_data": [],
        "emojis_data": [],
        "stickers_data": [],
        "banned_users": {},
        "automod_rules": []
    }
    
    await _SaveServerAssets(guild, backup_directory)
    
    backup_data["server_info"] = {
        "name": guild.name,
        "is_community": "COMMUNITY" in guild.features
    }
    
    await _BackupSystemChannels(guild, backup_data)
    
    _BackupRoles(guild, backup_data)
    
    await _BackupBannedUsers(guild, backup_data)
    
    await _BackupEmojis(guild, backup_directory, backup_data)
    
    await _BackupStickers(guild, backup_directory, backup_data)
    
    _BackupAutomodRules(guild, backup_data)
    
    await _BackupChannels(guild, backup_data)
    
    _SortBackupData(backup_data)
    
    with open(os.path.join(backup_directory, "backup.json"), 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=4)
    
    return backup_data

async def _SaveServerAssets(guild: disnake.Guild, backup_directory: str) -> None:
    if guild.icon:
        icon_data = await guild.icon.read()
        with open(os.path.join(backup_directory, "icon.png"), "wb") as f:
            f.write(icon_data)

    if guild.banner:
        banner_data = await guild.banner.read()
        with open(os.path.join(backup_directory, "banner.png"), "wb") as f:
            f.write(banner_data)

async def _BackupSystemChannels(guild: disnake.Guild, backup_data: Dict[str, Any]) -> None:
    system_channels_count = 0
    
    if guild.rules_channel:
        backup_data["server_info"]["rules_channel"] = _GetChannelData(guild.rules_channel)
        system_channels_count += 1
    else:
        backup_data["server_info"]["rules_channel"] = None
    
    if guild.public_updates_channel:
        backup_data["server_info"]["public_updates_channel"] = _GetChannelData(guild.public_updates_channel)
        system_channels_count += 1
    else:
        backup_data["server_info"]["public_updates_channel"] = None
    
    if guild.system_channel:
        backup_data["server_info"]["system_channel"] = {
            "name": guild.system_channel.name,
            "type": str(guild.system_channel.type),
            "position": guild.system_channel.position,
            "nsfw": guild.system_channel.is_nsfw() if isinstance(guild.system_channel, disnake.TextChannel) else None,
            "category": guild.system_channel.category.name if guild.system_channel.category else None
        }
    else:
        backup_data["server_info"]["system_channel"] = None

def _GetChannelData(channel: disnake.abc.GuildChannel) -> Dict[str, Any]:
    channel_overwrites = []
    for target, permissions in channel.overwrites.items():
        allow, deny = permissions.pair()
        channel_overwrites.append({
            "name": target.name,
            "allow": allow.value,
            "deny": deny.value
        })
    
    return {
        "name": channel.name,
        "type": str(channel.type),
        "position": channel.position,
        "nsfw": channel.is_nsfw() if isinstance(channel, disnake.TextChannel) else None,
        "slowmode_delay": channel.slowmode_delay if isinstance(channel, disnake.TextChannel) else None,
        "category": channel.category.name if channel.category else None,
        "overwrites": channel_overwrites
    }

def _BackupRoles(guild: disnake.Guild, backup_data: Dict[str, Any]) -> None:
    for role in guild.roles:
        backup_data["roles_data"].append({
            "name": role.name,
            "permissions": role.permissions.value,
            "colour": role.colour.value,
            "hoist": role.hoist,
            "mentionable": role.mentionable,
            "position": role.position
        })

async def _BackupBannedUsers(guild: disnake.Guild, backup_data: Dict[str, Any]) -> None:
    banned_users = await guild.bans(limit=None).flatten()
    ban_list = [{'id': ban.user.id, "reason": ban.reason} for ban in banned_users]
    backup_data['banned_users'] = ban_list

async def _BackupEmojis(guild: disnake.Guild, backup_directory: str, backup_data: Dict[str, Any]) -> None:
    emojis_dir = os.path.join(backup_directory, "emojis")
    os.makedirs(emojis_dir, exist_ok=True)
    
    for emoji in guild.emojis:
        emoji_path = os.path.join(emojis_dir, f"{emoji.id}.png")
        async with aiohttp.ClientSession() as session:
            async with session.get(str(emoji.url)) as resp:
                with open(emoji_path, "wb") as f:
                    f.write(await resp.read())
        
        backup_data["emojis_data"].append({
            "name": emoji.name,
            "path": emoji_path
        })

async def _BackupStickers(guild: disnake.Guild, backup_directory: str, backup_data: Dict[str, Any]) -> None:
    stickers_dir = os.path.join(backup_directory, "stickers")
    os.makedirs(stickers_dir, exist_ok=True)
    
    for sticker in guild.stickers:
        sticker_path = os.path.join(stickers_dir, f"{sticker.id}.png")
        async with aiohttp.ClientSession() as session:
            async with session.get(str(sticker.url)) as resp:
                with open(sticker_path, "wb") as f:
                    f.write(await resp.read())
        
        backup_data["stickers_data"].append({
            "name": sticker.name,
            "description": sticker.description,
            "emoji": sticker.emoji,
            "path": sticker_path
        })

def _BackupAutomodRules(guild: disnake.Guild, backup_data: Dict[str, Any]) -> None:
    headers = {"Authorization": f"Bot {helper.LoadConfig.token}"}
    response = requests.get(f"https://discord.com/api/v9/guilds/{guild.id}/auto-moderation/rules", headers=headers)
    
    if response.status_code == 200:
        rules = response.json()
        for rule in rules:
            automod_rule = {
                "name": rule["name"],
                "trigger_type": rule["trigger_type"],
                "event_type": rule["event_type"],
                "trigger_metadata": rule["trigger_metadata"],
                "actions": rule["actions"],
                "enabled": rule["enabled"],
                "exempt_roles": rule["exempt_roles"],
                "exempt_channels": []
            }
            backup_data["automod_rules"].append(automod_rule)

async def _BackupChannels(guild: disnake.Guild, backup_data: Dict[str, Any]) -> None:
    system_channels = [
        guild.rules_channel, 
        guild.public_updates_channel, 
        guild.system_channel
    ]
    
    for channel in guild.channels:
        if channel in system_channels:
            continue
        
        channel_overwrites = []
        for target, permissions in channel.overwrites.items():
            allow, deny = permissions.pair()
            channel_overwrites.append({
                "name": target.name,
                "allow": allow.value,
                "deny": deny.value
            })
        
        channel_data = {
            "name": channel.name,
            "type": str(channel.type),
            "position": channel.position,
            "overwrites": channel_overwrites
        }
        
        if isinstance(channel, disnake.CategoryChannel):
            channel_data["channels"] = [c.name for c in channel.channels]
        elif isinstance(channel, (disnake.TextChannel, disnake.VoiceChannel, disnake.ForumChannel)):
            channel_data["category"] = channel.category.name if channel.category else None
            
            if isinstance(channel, disnake.TextChannel):
                channel_data["nsfw"] = channel.is_nsfw()
                channel_data["slowmode_delay"] = channel.slowmode_delay
        
        backup_data["channels_data"].append(channel_data)

def _SortBackupData(backup_data: Dict[str, Any]) -> None:
    sorted_channels = sorted(backup_data["channels_data"], key=lambda x: (x["type"], x.get("position", 0)))
    backup_data["channels_data"] = sorted_channels
    
    category_channels = [channel for channel in sorted_channels if channel['type'] == "category"]
    for category in category_channels:
        if 'channels' in category:
            category['channels'] = sorted(category['channels']) 

# V1.3.2