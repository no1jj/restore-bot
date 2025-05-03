import os
import json
import aiohttp
import requests
import discord
from datetime import datetime
from typing import Dict, List, Any, Optional
from . import helper

async def CreateServerBackup(guild: discord.Guild, backup_directory: str, backup_creator: str) -> Dict[str, Any]:
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
        "banned_users": []
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
    
    await _BackupChannels(guild, backup_data)
    
    _SortBackupData(backup_data)
    
    with open(os.path.join(backup_directory, "backup.json"), 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=4)
    
    return backup_data

async def _SaveServerAssets(guild: discord.Guild, backup_directory: str) -> None:
    if guild.icon:
        icon_data = await guild.icon.read()
        with open(os.path.join(backup_directory, "icon.png"), "wb") as f:
            f.write(icon_data)

    if guild.banner:
        banner_data = await guild.banner.read()
        with open(os.path.join(backup_directory, "banner.png"), "wb") as f:
            f.write(banner_data)

async def _BackupSystemChannels(guild: discord.Guild, backup_data: Dict[str, Any]) -> None:
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
            "nsfw": guild.system_channel.is_nsfw() if isinstance(guild.system_channel, discord.TextChannel) else None,
            "category": guild.system_channel.category.name if guild.system_channel.category else None
        }
    else:
        backup_data["server_info"]["system_channel"] = None

def _GetChannelData(channel: discord.abc.GuildChannel) -> Dict[str, Any]:
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
        "nsfw": channel.is_nsfw() if isinstance(channel, discord.TextChannel) else None,
        "slowmode_delay": channel.slowmode_delay if isinstance(channel, discord.TextChannel) else None,
        "category": channel.category.name if channel.category else None,
        "overwrites": channel_overwrites
    }

def _BackupRoles(guild: discord.Guild, backup_data: Dict[str, Any]) -> None:
    for role in guild.roles:
        role_data = {
            "id": str(role.id),
            "name": role.name,
            "permissions": role.permissions.value,
            "colour": role.colour.value,
            "color": role.color.value,  
            "hoist": role.hoist,
            "mentionable": role.mentionable,
            "position": role.position
        }
        backup_data["roles_data"].append(role_data)

async def _BackupBannedUsers(guild: discord.Guild, backup_data: Dict[str, Any]) -> None:
    ban_list = []
    async for ban in guild.bans(limit=None):
        ban_list.append({'id': ban.user.id, "reason": ban.reason})
    backup_data['banned_users'] = ban_list

async def _BackupEmojis(guild: discord.Guild, backup_directory: str, backup_data: Dict[str, Any]) -> None:
    emojis_dir = os.path.join(backup_directory, "emojis")
    os.makedirs(emojis_dir, exist_ok=True)
    
    for emoji in guild.emojis:
        emoji_path = os.path.join(emojis_dir, f"{emoji.id}.png")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(emoji.url)) as resp:
                    if resp.status == 200:
                        with open(emoji_path, "wb") as f:
                            f.write(await resp.read())
            
            emoji_data = {
                "id": str(emoji.id),
                "name": emoji.name,
                "path": emoji_path,
                "url": str(emoji.url),
                "animated": emoji.animated,
                "managed": emoji.managed,
                "available": emoji.available,
                "roles": [str(role.id) for role in emoji.roles] if emoji.roles else []
            }
            backup_data["emojis_data"].append(emoji_data)
        except Exception as e:
            print(f"이모지 백업 실패: {emoji.name} - {str(e)}")

async def _BackupStickers(guild: discord.Guild, backup_directory: str, backup_data: Dict[str, Any]) -> None:
    stickers_dir = os.path.join(backup_directory, "stickers")
    os.makedirs(stickers_dir, exist_ok=True)
    
    for sticker in guild.stickers:
        sticker_path = os.path.join(stickers_dir, f"{sticker.id}.png")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(sticker.url)) as resp:
                    if resp.status == 200:
                        with open(sticker_path, "wb") as f:
                            f.write(await resp.read())
            
            format_type = None
            try:
                if hasattr(sticker.format, 'name'):
                    format_type = sticker.format.name
                elif hasattr(sticker.format, 'value'):
                    format_type = sticker.format.value
                else:
                    format_type = str(sticker.format)
            except Exception as e:
                print(f"스티커 포맷 타입 추출 오류 ({sticker.name}): {str(e)}")
                format_type = "PNG"  
            
            sticker_data = {
                "id": str(sticker.id),
                "name": sticker.name,
                "description": sticker.description,
                "emoji": sticker.emoji,
                "path": sticker_path,
                "url": str(sticker.url),
                "format_type": format_type,
                "available": getattr(sticker, 'available', True)
            }
            backup_data["stickers_data"].append(sticker_data)
        except Exception as e:
            print(f"스티커 백업 실패: {sticker.name} - {str(e)}")

async def _BackupChannels(guild: discord.Guild, backup_data: Dict[str, Any]) -> None:
    system_channels = [
        guild.rules_channel, 
        guild.public_updates_channel, 
        guild.system_channel
    ]
    
    for channel in guild.channels:
        if channel in system_channels:
            continue
        
        if isinstance(channel, discord.CategoryChannel):
            channel_overwrites = []
            for target, permissions in channel.overwrites.items():
                target_id = str(target.id)
                target_type = "role" if isinstance(target, discord.Role) else "member"
                allow, deny = permissions.pair()
                channel_overwrites.append({
                    "id": target_id,
                    "type": target_type,
                    "name": target.name,
                    "allow": allow.value,
                    "deny": deny.value
                })
            
            channel_data = {
                "id": str(channel.id),
                "name": channel.name,
                "type": discord.ChannelType.category.value,  
                "position": channel.position,
                "permission_overwrites": channel_overwrites,
                "channels": []  
            }
            
            for child_channel in channel.channels:
                channel_data["channels"].append(str(child_channel.id))
            
            backup_data["channels_data"].append(channel_data)
    
    for channel in guild.channels:
        if channel in system_channels or isinstance(channel, discord.CategoryChannel):
            continue
        
        channel_overwrites = []
        for target, permissions in channel.overwrites.items():
            target_id = str(target.id)
            target_type = "role" if isinstance(target, discord.Role) else "member"
            allow, deny = permissions.pair()
            channel_overwrites.append({
                "id": target_id,
                "type": target_type,
                "name": target.name,
                "allow": allow.value,
                "deny": deny.value
            })
        
        channel_type = None
        try:
            if hasattr(channel.type, 'value'):
                channel_type = channel.type.value
            elif hasattr(channel.type, '__str__'):
                type_str = str(channel.type)
                if '.' in type_str:
                    try:
                        channel_type = int(type_str.split('.')[-1])
                    except (ValueError, IndexError):
                        channel_type = type_str
                else:
                    channel_type = type_str
            else:
                channel_type = str(channel.type)
        except Exception as e:
            print(f"채널 타입 추출 오류 ({channel.name}): {str(e)}")
            channel_type = str(channel.type)
        
        channel_data = {
            "id": str(channel.id),
            "name": channel.name,
            "type": channel_type,
            "position": channel.position,
            "permission_overwrites": channel_overwrites,
            "parent_id": str(channel.category.id) if channel.category else None,
            "category": channel.category.name if channel.category else None
        }
        
        if isinstance(channel, discord.TextChannel):
            channel_data.update({
                "nsfw": channel.is_nsfw(),
                "topic": channel.topic,
                "slowmode_delay": channel.slowmode_delay,
                "default_auto_archive_duration": channel.default_auto_archive_duration
            })
        elif isinstance(channel, discord.VoiceChannel):
            channel_data.update({
                "bitrate": channel.bitrate,
                "user_limit": channel.user_limit,
                "rtc_region": channel.rtc_region
            })
        elif isinstance(channel, discord.StageChannel):
            channel_data.update({
                "topic": channel.topic,
                "user_limit": channel.user_limit,
                "rtc_region": channel.rtc_region
            })
        
        backup_data["channels_data"].append(channel_data)

def _SortBackupData(backup_data: Dict[str, Any]) -> None:
    try:
        sorted_channels = sorted(backup_data["channels_data"], key=lambda x: (
            0 if _IsCategory(x) else 1,
            x.get("position", 0)
        ))
        backup_data["channels_data"] = sorted_channels
        
        category_channels = [channel for channel in sorted_channels if _IsCategory(channel)]
        for category in category_channels:
            if 'channels' in category:
                category['channels'] = sorted(category['channels'])
    except Exception as e:
        print(f"백업 데이터 정렬 오류: {str(e)}")

def _IsCategory(channel_data: Dict[str, Any]) -> bool:
    channel_type = channel_data.get("type")
    
    if isinstance(channel_type, int):
        return channel_type == 4
    
    if isinstance(channel_type, str):
        return channel_type == "4" or channel_type == "category"
    
    return False

# V1.4