import discord
from discord import Interaction, Color, Button, SelectOption
from discord.ui import View, Select
import pytz
from datetime import datetime
import json
import os
from . import helper
import math
import aiohttp
import traceback
import io

def _IsCategory(channel_data):
    channel_type = channel_data.get("type")
    
    if isinstance(channel_type, int):
        return channel_type == 4
    
    if isinstance(channel_type, str):
        return channel_type == "4" or channel_type == "category"
    
    return False

class RestoreTypeSelect(View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            SelectOption(label="인원 복구", value="users", description="서버의 인원만 복구합니다", emoji="👥"),
            SelectOption(label="서버 복구", value="server", description="서버의 채널, 역할 등 구조를 복구합니다", emoji="🏗️")
        ]
        self.add_item(RestoreTypeDropdown(options))
        
class RestoreTypeDropdown(Select):
    def __init__(self, options):
        super().__init__(placeholder="복구 유형을 선택하세요", options=options)

    async def callback(self, interaction: Interaction):
        selectedValue = self.values[0]
        await interaction.response.send_modal(RestoreKeyModal(selectedValue))

async def ShowBackupList(interaction: Interaction, targetServerId: str, restoreKey: str):
    try:
        config = helper.LoadConfig()
        
        backupsFolder = os.path.join(config.DBFolderPath, "backups")
        if not os.path.exists(backupsFolder):
            await helper.ErrorEmbed(interaction, "백업 폴더를 찾을 수 없습니다.")
            return
        
        backupFolders = []
        for folder in os.listdir(backupsFolder):
            if folder.startswith(f"{targetServerId}_"):
                folderPath = os.path.join(backupsFolder, folder)
                jsonPath = os.path.join(folderPath, "backup.json")
                if os.path.exists(jsonPath):
                    try:
                        with open(jsonPath, 'r', encoding='utf-8') as f:
                            backupInfo = json.load(f)
                        
                        timestamp = backupInfo.get("backup_info", {}).get("timestamp", "알 수 없음")
                        serverName = backupInfo.get("server_info", {}).get("name", "알 수 없음")
                        backupFolders.append({
                            "path": folderPath,
                            "jsonFile": jsonPath,
                            "timestamp": timestamp,
                            "folderName": folder,
                            "serverName": serverName
                        })
                    except:
                        continue
        
        if not backupFolders:
            await helper.ErrorEmbed(interaction, "해당 서버의 백업 파일을 찾을 수 없습니다.")
            return
        
        backupFolders.sort(key=lambda x: x["timestamp"], reverse=True)
        
        view = BackupSelectView(backupFolders, 0, restoreKey, targetServerId)
        embed = discord.Embed(
            title="🔍 백업 선택",
            description=f"**{backupFolders[0]['serverName']}** 서버의 복구할 백업을 선택해주세요.\n아래 드롭다운에서 백업을 선택할 수 있습니다.",
            color=Color.blue(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    except Exception as e:
        await helper.ErrorEmbed(interaction, f"백업 목록을 불러오는 중 오류가 발생했습니다: {str(e)}")

class BackupSelectView(View):
    def __init__(self, backups, page=0, restoreKey=None, targetServerId=None, per_page=10):
        super().__init__(timeout=120)
        self.backups = backups
        self.page = page
        self.per_page = per_page
        self.total_pages = math.ceil(len(backups) / per_page)
        self.restoreKey = restoreKey
        self.targetServerId = targetServerId
        
        start_idx = page * per_page
        end_idx = min(start_idx + per_page, len(backups))
        
        options = []
        for i, backup in enumerate(backups[start_idx:end_idx]):
            timestamp = backup["timestamp"]
            serverName = backup["serverName"]
            option_label = f"{timestamp}"
            option_description = f"{serverName}"
            options.append(SelectOption(
                label=option_label[:25],
                description=option_description[:50],
                value=str(start_idx + i),
                emoji="📦"
            ))
        
        self.add_item(BackupDropdown(options))
        
        if self.total_pages > 1:
            if page > 0:
                self.add_item(PrevPageButton(self.page))
            if page < self.total_pages - 1:
                self.add_item(NextPageButton(self.page))

class BackupDropdown(Select):
    def __init__(self, options):
        super().__init__(placeholder="복구할 백업을 선택하세요", options=options)
    
    async def callback(self, interaction: Interaction):
        view = self.view
        selected_idx = int(self.values[0])
        backup = view.backups[selected_idx]
        
        backupDir = backup["path"]
        backupFile = backup["jsonFile"]
        
        with open(backupFile, 'r', encoding='utf-8') as f:
            backupData = json.load(f)
        
        serverName = backupData["server_info"]["name"]
        targetServerId = view.targetServerId
        backupTime = backupData["backup_info"]["timestamp"]
        
        structureRestoreView = StructureRestoreView(
            restoreKey=view.restoreKey,
            serverName=serverName,
            targetServerId=targetServerId,
            backupFile=backupFile,
            backupDir=backupDir,
            guildName=interaction.guild.name,
            guildId=interaction.guild.id,
            backupData=backupData,
            backupTime=backupTime
        )
        
        await interaction.response.edit_message(embed=structureRestoreView.embed, view=structureRestoreView)

class PrevPageButton(Button):
    def __init__(self, current_page):
        super().__init__(style=discord.ButtonStyle.secondary, label="◀ 이전", custom_id=f"prev_page_{current_page}")
        self.current_page = current_page
    
    async def callback(self, interaction: Interaction):
        view = self.view
        new_page = self.current_page - 1
        new_view = BackupSelectView(view.backups, new_page, view.restoreKey, view.targetServerId, view.per_page)
        await interaction.response.edit_message(view=new_view)

class NextPageButton(Button):
    def __init__(self, current_page):
        super().__init__(style=discord.ButtonStyle.secondary, label="다음 ▶", custom_id=f"next_page_{current_page}")
        self.current_page = current_page
    
    async def callback(self, interaction: Interaction):
        view = self.view
        new_page = self.current_page + 1
        new_view = BackupSelectView(view.backups, new_page, view.restoreKey, view.targetServerId, view.per_page)
        await interaction.response.edit_message(view=new_view)

class RestoreKeyModal(discord.ui.Modal):
    def __init__(self, restoreType: str):
        self.restoreType = restoreType
        title = "인원 복구" if restoreType == "users" else "서버 복구"
        super().__init__(title=f"🔑 {title} - 복구키 입력")
        
        self.add_item(discord.ui.TextInput(
            label="복구키",
            placeholder="복구키를 입력하세요",
            style=discord.TextStyle.short,
            required=True
        ))

    async def on_submit(self, interaction: Interaction):
        restoreKey = self.children[0].value
        
        try:
            config = helper.LoadConfig()
            
            def FetchServerInfo():
                conn = None
                try:
                    conn = helper.sqlite3.connect(config.DBPath)
                    cursor = conn.cursor()
                    cursor.execute("SELECT serverId FROM Keys WHERE Key = ?", (restoreKey,))
                    keyResult = cursor.fetchone()
                    
                    if not keyResult:
                        return None, "유효하지 않은 복구키입니다."
                        
                    targetServerId = keyResult[0]
                    serverDbPath = os.path.join(config.DBFolderPath, f"{targetServerId}.db")
                    
                    if not os.path.exists(serverDbPath):
                        return None, "서버 DB 파일을 찾을 수 없습니다."
                    
                    return targetServerId, None
                except Exception as e:
                    return None, f"데이터베이스 오류: {str(e)}"
                finally:
                    if conn:
                        conn.close()
            
            def FetchUserInfo(serverDbPath, targetServerId):
                conn = None
                try:
                    conn = helper.sqlite3.connect(serverDbPath)
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT name FROM Info")
                    serverNameResult = cursor.fetchone()
                    serverName = serverNameResult[0] if serverNameResult else "알 수 없음"
                    
                    cursor.execute("SELECT userId, refreshToken FROM Users WHERE refreshToken IS NOT NULL")
                    targetUsers = cursor.fetchall()
                    
                    return {
                        "serverName": serverName,
                        "targetUsers": targetUsers,
                        "error": None
                    }
                except Exception as e:
                    return {
                        "serverName": None,
                        "targetUsers": None,
                        "error": f"사용자 정보 가져오기 오류: {str(e)}"
                    }
                finally:
                    if conn:
                        conn.close()
            
            targetServerId, error = await interaction.client.loop.run_in_executor(
                None, helper.RunDBQuery, FetchServerInfo
            )
            
            if error:
                await helper.ErrorEmbed(interaction, error)
                return
            
            serverDbPath = os.path.join(config.DBFolderPath, f"{targetServerId}.db")
            
            if self.restoreType == "users":
                userInfo = await interaction.client.loop.run_in_executor(
                    None, helper.RunDBQuery, lambda: FetchUserInfo(serverDbPath, targetServerId)
                )
                
                if userInfo["error"]:
                    await helper.ErrorEmbed(interaction, userInfo["error"])
                    return
                
                if not userInfo["targetUsers"] or len(userInfo["targetUsers"]) == 0:
                    await helper.ErrorEmbed(interaction, "복구할 유저 정보가 없습니다.")
                    return
                
                restoreView = RestoreView(
                    restoreKey=restoreKey,
                    serverName=userInfo["serverName"],
                    targetServerId=targetServerId,
                    usersCount=len(userInfo["targetUsers"]),
                    guildName=interaction.guild.name,
                    guildId=interaction.guild.id
                )
                
                await interaction.response.send_message(embed=restoreView.embed, view=restoreView, ephemeral=True)
            else:
                await ShowBackupList(interaction, targetServerId, restoreKey)
                    
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")

class StructureRestoreView(discord.ui.View):
    def __init__(self, restoreKey, serverName, targetServerId, backupFile, backupDir, guildName, guildId, backupData, backupTime=None):
        super().__init__(timeout=60.0)
        self.restoreKey = restoreKey
        self.serverName = serverName
        self.targetServerId = targetServerId
        self.backupFile = backupFile
        self.backupDir = backupDir
        self.guildName = guildName
        self.guildId = guildId
        self.backupData = backupData
        self.backupTime = backupTime or backupData['backup_info']['timestamp']
        self.value = None
        
        self.roleCount = len(backupData["roles_data"])
        self.channelCount = len([c for c in backupData["channels_data"] if not _IsCategory(c)])
        self.categoryCount = len([c for c in backupData["channels_data"] if _IsCategory(c)])
        self.emojiCount = len(backupData["emojis_data"])
        self.stickerCount = len(backupData["stickers_data"])
        
        self.embedDescription = (
            f"## 🔄 **서버 복구 확인**\n\n"
            f"### 📋 **백업 정보**\n"
            f"```ini\n"
            f"[서버이름] {serverName}\n"
            f"[서버 ID] {targetServerId}\n"
            f"[백업시간] {self.backupTime}\n"
            f"```\n"
            f"### 📊 **복구할 항목**\n"
            f"```ini\n"
            f"[카테고리] {self.categoryCount}개\n"
            f"[채널] {self.channelCount}개\n"
            f"[역할] {self.roleCount}개\n"
            f"[이모지] {self.emojiCount}개\n"
            f"[스티커] {self.stickerCount}개\n"
            f"```\n"
            f"### 🎯 **복구대상 서버**\n"
            f"```ini\n"
            f"[서버이름] {guildName}\n"
            f"[서버 ID] {guildId}\n"
            f"```\n\n"
            f"### ⚠️ **주의사항**\n"
            f"> 🔄 기존 서버 구조가 변경될 수 있습니다.\n"
            f"> ⏳ 복구 중에는 봇이 일시적으로 응답하지 않을 수 있습니다.\n"
            f"> 🔄 중복된 이름의 채널이나 역할이 있으면 새로 생성됩니다.\n\n"
            f"### 📢 **안내**\n"
            f"> 💡 아래 버튼을 클릭하여 복구를 시작하거나 취소할 수 있습니다.\n"
            f"> ⏱️ 60초 후에는 자동으로 취소됩니다."
        )
        
        self.embed = discord.Embed(
            title="🏗️ 서버 복구 확인",
            description=self.embedDescription,
            color=Color.blue(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )

    async def on_timeout(self):
        timeoutEmbed = discord.Embed(
            title="⏱️ 시간 초과",
            description="복구 작업이 시간 초과로 취소되었습니다.",
            color=Color.red(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )
        if hasattr(self, 'message'):
            await self.message.edit(embed=timeoutEmbed, view=None)

    @discord.ui.button(label="❌ 취소", style=discord.ButtonStyle.danger, custom_id="restore_cancel")
    async def cancelButton(self, interaction: Interaction, button: Button):
        cancelEmbed = discord.Embed(
            title="❌ 복구 취소",
            description="복구 작업이 취소되었습니다.",
            color=Color.red(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )
        await interaction.response.edit_message(embed=cancelEmbed, view=None)
        self.value = False
        self.stop()

    @discord.ui.button(label="✅ 복구 시작", style=discord.ButtonStyle.success, custom_id="restore_confirm")
    async def confirmButton(self, interaction: Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
            
            guild = interaction.guild
            config = helper.LoadConfig()
            newRestoreKey = helper.GenRandom(16)
            
            startEmbed = discord.Embed(
                title="🔄 복구 시작",
                description=(
                    f"## 🚀 **서버 복구가 시작되었습니다**\n\n"
                    f"### 📋 **진행 상황**\n"
                    f"> 🔹 복구가 완료될 때까지 기다려주세요.\n"
                    f"> 🔹 진행 상황은 자동으로 업데이트됩니다.\n"
                    f"> 🔹 완료 시 결과가 표시됩니다.\n\n"
                    f"### ⚠️ **주의사항**\n"
                    f"> ⏳ 복구 시간은 서버 구조 복잡도에 따라 다소 소요될 수 있습니다.\n"
                    f"> 🔔 복구가 완료되면 알림을 드립니다."
                ),
                color=Color.green(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            )
            
            try:
                await interaction.edit_original_response(embed=startEmbed, view=None)
            except discord.errors.NotFound:
                try:
                    await interaction.followup.send(embed=startEmbed, ephemeral=True)
                except:
                    pass
                    
            self.value = True
            self.stop()
            
            guild = interaction.guild
            
            cleanupEmbed = discord.Embed(
                title="🧹 서버 정리 중",
                description="복구를 위해 기존 채널, 역할, 이모지 등을 정리하고 있습니다...",
                color=Color.blue(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            )
            
            try:
                await interaction.edit_original_response(embed=cleanupEmbed)
            except discord.errors.NotFound:
                try:
                    await interaction.followup.send(embed=cleanupEmbed, ephemeral=True)
                except:
                    pass
            
            deletedChannels = 0
            for channel in guild.channels[:]: 
                try:
                    if channel == interaction.channel:
                        continue  
                    await channel.delete(reason="서버 복구를 위한 정리")
                    deletedChannels += 1
                except Exception as e:
                    print(f"채널 삭제 실패: {channel.name} - {str(e)}")
            
            deletedRoles = 0
            for role in guild.roles[:]:  
                if role.name != "@everyone" and role.is_assignable() and role < guild.me.top_role:
                    try:
                        await role.delete(reason="서버 복구를 위한 정리")
                        deletedRoles += 1
                    except Exception as e:
                        print(f"역할 삭제 실패: {role.name} - {str(e)}")
            
            deletedEmojis = 0
            for emoji in guild.emojis[:]: 
                try:
                    await emoji.delete(reason="서버 복구를 위한 정리")
                    deletedEmojis += 1
                except Exception as e:
                    print(f"이모지 삭제 실패: {emoji.name} - {str(e)}")
            
            deletedStickers = 0
            for sticker in guild.stickers[:]:  
                try:
                    await sticker.delete(reason="서버 복구를 위한 정리")
                    deletedStickers += 1
                except Exception as e:
                    print(f"스티커 삭제 실패: {sticker.name} - {str(e)}")
            
            cleanupResultEmbed = discord.Embed(
                title="✅ 서버 정리 완료",
                description=f"서버 정리가 완료되었습니다.\n- 채널 {deletedChannels}개 삭제\n- 역할 {deletedRoles}개 삭제\n- 이모지 {deletedEmojis}개 삭제\n- 스티커 {deletedStickers}개 삭제\n\n이제 백업본을 복원합니다...",
                color=Color.green(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            )
            await interaction.edit_original_response(embed=cleanupResultEmbed)
            
            categoriesCreated = 0
            channelsCreated = 0
            rolesCreated = 0
            emojisCreated = 0
            stickersCreated = 0
            failedChannels = 0
            failedRoles = 0
            failedEmojis = 0
            failedStickers = 0
            
            restoreProgressEmbed = discord.Embed(
                title="🔄 서버 복원 진행 중",
                description="백업 데이터에서 서버 구조를 복원하고 있습니다...",
                color=Color.blue(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            )
            await interaction.edit_original_response(embed=restoreProgressEmbed)
            
            try:
                icon_path = os.path.join(self.backupDir, "icon.png")
                if os.path.exists(icon_path):
                    with open(icon_path, "rb") as f:
                        icon_data = f.read()
                        await guild.edit(icon=icon_data, reason="서버 복구로 인한 아이콘 변경")
                        print(f"서버 아이콘 복원 완료: {icon_path}")
                
                banner_path = os.path.join(self.backupDir, "banner.png")
                if os.path.exists(banner_path):
                    with open(banner_path, "rb") as f:
                        banner_data = f.read()
                        await guild.edit(banner=banner_data, reason="서버 복구로 인한 배너 변경")
                        print(f"서버 배너 복원 완료: {banner_path}")
            except Exception as e:
                print(f"서버 아이콘/배너 복원 실패: {str(e)}")
            
            try:
                roles_created = {}
                
                for role_data in sorted(self.backupData["roles_data"], key=lambda r: r.get("position", 0)):
                    try:
                        if role_data["name"] == "@everyone":
                            roles_created[role_data["id"]] = guild.default_role
                            continue
                        
                        role_color = role_data.get("color", 0)
                        if role_data.get("colour") is not None:
                            role_color = role_data.get("colour", 0)
                            
                        if isinstance(role_color, str) and role_color.startswith("#"):
                            role_color = int(role_color[1:], 16)
                            
                        permissions = discord.Permissions(role_data.get("permissions", 0))
                        
                        new_role = await guild.create_role(
                            name=role_data["name"],
                            permissions=permissions,
                            color=discord.Color(role_color),
                            hoist=role_data.get("hoist", False),
                            mentionable=role_data.get("mentionable", False),
                            reason="서버 복구로 인한 역할 생성"
                        )
                        roles_created[role_data["id"]] = new_role
                        rolesCreated += 1
                    except Exception as e:
                        print(f"역할 생성 실패: {role_data['name']} - {str(e)}")
                        failedRoles += 1
                        
                categories_created = {}
                
                category_channels_map = {}
                for channel_data in self.backupData["channels_data"]:
                    if channel_data["type"] == 4 or str(channel_data["type"]) == "category":
                        channel_id = channel_data.get("id", "")
                        channel_name = channel_data["name"]
                        if "channels" in channel_data:
                            category_channels_map[channel_id] = channel_data["channels"]
                        category_channels_map[channel_name] = []
                
                for channel_data in self.backupData["channels_data"]:
                    if channel_data["type"] != 4 and str(channel_data["type"]) != "category":
                        category_name = channel_data.get("category")
                        if category_name and category_name in category_channels_map:
                            category_channels_map[category_name].append(channel_data["name"])
                
                for channel_data in self.backupData["channels_data"]:
                    if channel_data["type"] == 4 or str(channel_data["type"]) == "category":
                        try:
                            permission_overwrites = {}
                            for overwrite in channel_data.get("permission_overwrites", []):
                                role_id = overwrite.get("id")
                                if role_id in roles_created:
                                    permissions = discord.PermissionOverwrite()
                                    allow = overwrite.get("allow", 0)
                                    deny = overwrite.get("deny", 0)
                                    
                                    for perm_name, perm_value in discord.Permissions(allow):
                                        if perm_value:
                                            setattr(permissions, perm_name, True)
                                    
                                    for perm_name, perm_value in discord.Permissions(deny):
                                        if perm_value:
                                            setattr(permissions, perm_name, False)
                                    
                                    permission_overwrites[roles_created[role_id]] = permissions
                            
                            new_category = await guild.create_category(
                                name=channel_data["name"],
                                overwrites=permission_overwrites,
                                position=channel_data.get("position", 0),
                                reason="서버 복구로 인한 카테고리 생성"
                            )
                            categories_created[channel_data.get("id", "")] = new_category
                            categories_created[channel_data["name"]] = new_category
                            categoriesCreated += 1
                        except Exception as e:
                            print(f"카테고리 생성 실패: {channel_data['name']} - {str(e)}")
                            failedChannels += 1
                
                for channel_data in self.backupData["channels_data"]:
                    if channel_data["type"] != 4 and str(channel_data["type"]) != "category":
                        try:
                            permission_overwrites = {}
                            for overwrite in channel_data.get("permission_overwrites", []):
                                role_id = overwrite.get("id")
                                if role_id in roles_created:
                                    permissions = discord.PermissionOverwrite()
                                    allow = overwrite.get("allow", 0)
                                    deny = overwrite.get("deny", 0)
                                    
                                    for perm_name, perm_value in discord.Permissions(allow):
                                        if perm_value:
                                            setattr(permissions, perm_name, True)
                                    
                                    for perm_name, perm_value in discord.Permissions(deny):
                                        if perm_value:
                                            setattr(permissions, perm_name, False)
                                    
                                    permission_overwrites[roles_created[role_id]] = permissions
                            
                            category = None
                            parent_id = channel_data.get("parent_id", "")
                            category_name = channel_data.get("category")
                            
                            if parent_id and parent_id in categories_created:
                                category = categories_created[parent_id]
                            elif category_name and category_name in categories_created:
                                category = categories_created[category_name]
                            
                            channel_type = channel_data.get("type")
                            if isinstance(channel_type, str):
                                try:
                                    channel_type = int(channel_type)
                                except:
                                    if channel_type == "text":
                                        channel_type = 0
                                    elif channel_type == "voice":
                                        channel_type = 2
                                    elif channel_type == "news":
                                        channel_type = 5
                                    elif channel_type == "stage":
                                        channel_type = 13
                                    elif channel_type == "forum":
                                        channel_type = 15
                                    else:
                                        channel_type = 0
                            
                            if channel_type == 0:
                                new_channel = await guild.create_text_channel(
                                    name=channel_data["name"],
                                    topic=channel_data.get("topic"),
                                    position=channel_data.get("position", 0),
                                    nsfw=channel_data.get("nsfw", False),
                                    slowmode_delay=channel_data.get("slowmode_delay", 0),
                                    overwrites=permission_overwrites,
                                    category=category,
                                    reason="서버 복구로 인한 텍스트 채널 생성"
                                )
                            elif channel_type == 2:  
                                new_channel = await guild.create_voice_channel(
                                    name=channel_data["name"],
                                    bitrate=channel_data.get("bitrate", 64000),
                                    user_limit=channel_data.get("user_limit", 0),
                                    position=channel_data.get("position", 0),
                                    overwrites=permission_overwrites,
                                    category=category,
                                    reason="서버 복구로 인한 음성 채널 생성"
                                )
                            elif channel_type == 5:  
                                new_channel = await guild.create_text_channel(
                                    name=channel_data["name"],
                                    topic=channel_data.get("topic"),
                                    position=channel_data.get("position", 0),
                                    nsfw=channel_data.get("nsfw", False),
                                    overwrites=permission_overwrites,
                                    category=category,
                                    reason="서버 복구로 인한 공지 채널 생성"
                                )
                            elif channel_type == 13:  
                                new_channel = await guild.create_stage_channel(
                                    name=channel_data["name"],
                                    topic=channel_data.get("topic"),
                                    position=channel_data.get("position", 0),
                                    overwrites=permission_overwrites,
                                    category=category,
                                    reason="서버 복구로 인한 스테이지 채널 생성"
                                )
                            elif channel_type == 15: 
                                new_channel = await guild.create_text_channel(
                                    name=channel_data["name"],
                                    topic=channel_data.get("topic"),
                                    position=channel_data.get("position", 0),
                                    nsfw=channel_data.get("nsfw", False),
                                    overwrites=permission_overwrites,
                                    category=category,
                                    reason="서버 복구로 인한 포럼 채널 생성"
                                )
                            else: 
                                new_channel = await guild.create_text_channel(
                                    name=channel_data["name"],
                                    topic=channel_data.get("topic"),
                                    position=channel_data.get("position", 0),
                                    overwrites=permission_overwrites,
                                    category=category,
                                    reason="서버 복구로 인한 채널 생성"
                                )
                                
                            channelsCreated += 1
                        except Exception as e:
                            print(f"채널 생성 실패: {channel_data['name']} - {str(e)}")
                            failedChannels += 1
                
                for emoji_data in self.backupData["emojis_data"]:
                    try:
                        emoji_url = emoji_data.get("url")
                        emoji_path = emoji_data.get("path")
                        
                        if emoji_url or emoji_path:
                            async with aiohttp.ClientSession() as session:
                                if emoji_url:
                                    async with session.get(emoji_url) as resp:
                                        if resp.status == 200:
                                            emoji_image = await resp.read()
                                            await guild.create_custom_emoji(
                                                name=emoji_data["name"],
                                                image=emoji_image,
                                                reason="서버 복구로 인한 이모지 생성"
                                            )
                                            emojisCreated += 1
                                elif emoji_path and os.path.exists(emoji_path):
                                    with open(emoji_path, "rb") as f:
                                        emoji_image = f.read()
                                        await guild.create_custom_emoji(
                                            name=emoji_data["name"],
                                            image=emoji_image,
                                            reason="서버 복구로 인한 이모지 생성"
                                        )
                                        emojisCreated += 1
                    except Exception as e:
                        print(f"이모지 생성 실패: {emoji_data['name']} - {str(e)}")
                        failedEmojis += 1
                
                for sticker_data in self.backupData["stickers_data"]:
                    try:
                        sticker_url = sticker_data.get("url")
                        sticker_path = sticker_data.get("path")
                        
                        if sticker_url or sticker_path:
                            async with aiohttp.ClientSession() as session:
                                if sticker_url:
                                    async with session.get(sticker_url) as resp:
                                        if resp.status == 200:
                                            sticker_image = await resp.read()
                                            await guild.create_sticker(
                                                name=sticker_data["name"],
                                                description=sticker_data.get("description", "복구된 스티커"),
                                                emoji=sticker_data.get("emoji", "👍"),
                                                file=discord.File(io.BytesIO(sticker_image), filename="sticker.png"),
                                                reason="서버 복구로 인한 스티커 생성"
                                            )
                                            stickersCreated += 1
                                elif sticker_path and os.path.exists(sticker_path):
                                    with open(sticker_path, "rb") as f:
                                        sticker_image = f.read()
                                        await guild.create_sticker(
                                            name=sticker_data["name"],
                                            description=sticker_data.get("description", "복구된 스티커"),
                                            emoji=sticker_data.get("emoji", "👍"),
                                            file=discord.File(io.BytesIO(sticker_image), filename="sticker.png"),
                                            reason="서버 복구로 인한 스티커 생성"
                                        )
                                        stickersCreated += 1
                    except Exception as e:
                        print(f"스티커 생성 실패: {sticker_data['name']} - {str(e)}")
                        failedStickers += 1
                        
            except Exception as e:
                print(f"서버 복구 중 오류 발생: {str(e)}")
                errorEmbed = discord.Embed(
                    title="❌ 복구 중 오류 발생",
                    description=f"서버 복구 중 오류가 발생했습니다.\n```{str(e)}```",
                    color=Color.red(),
                    timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
                )
                await interaction.edit_original_response(embed=errorEmbed)
                return
            
            resultEmbed = StructureRestoreResultEmbed.create(
                categoriesCreated=categoriesCreated,
                channelsCreated=channelsCreated,
                rolesCreated=rolesCreated,
                emojisCreated=emojisCreated,
                stickersCreated=stickersCreated,
                failedCategoriesChannels=failedChannels,
                failedRoles=failedRoles,
                failedEmojis=failedEmojis,
                failedStickers=failedStickers,
                newRestoreKey=newRestoreKey
            )
            
            await interaction.edit_original_response(embed=resultEmbed)
            
            def updateRestoreKey():
                try:
                    keyUpdateConn = helper.sqlite3.connect(config.DBPath)
                    keyUpdateCursor = keyUpdateConn.cursor()
                    keyUpdateCursor.execute("UPDATE Keys SET Key = ? WHERE Key = ?", (newRestoreKey, self.restoreKey))
                    rowsAffected = keyUpdateCursor.rowcount
                    keyUpdateConn.commit()
                    keyUpdateConn.close()
                    
                    serverDbPath = os.path.join(config.DBFolderPath, f"{self.targetServerId}.db")
                    serverKeyUpdateConn = helper.sqlite3.connect(serverDbPath)
                    serverKeyUpdateCursor = serverKeyUpdateConn.cursor()
                    serverKeyUpdateCursor.execute("UPDATE Info SET key = ? WHERE id = ?", (newRestoreKey, self.targetServerId))
                    serverKeyUpdateConn.commit()
                    serverKeyUpdateConn.close()
                    
                    print(f"키 업데이트 결과: {rowsAffected}행 영향받음 (0은 실패)")
                    if rowsAffected == 0:
                        print(f"키 업데이트 실패: 키 '{self.restoreKey}'를 찾을 수 없습니다.")
                        insertConn = helper.sqlite3.connect(config.DBPath)
                        insertCursor = insertConn.cursor()
                        insertCursor.execute("INSERT INTO Keys (Key, serverId) VALUES (?, ?)", (newRestoreKey, self.targetServerId))
                        insertConn.commit()
                        insertConn.close()
                        print(f"새 키 삽입 시도: {newRestoreKey}")
                    return True
                except Exception as e:
                    print(f"복구 키 업데이트 오류: {str(e)}")
                    return False
            
            await interaction.client.loop.run_in_executor(
                None, updateRestoreKey
            )
            
            userInfo = [
                ("실행자", f"<@{interaction.user.id}>"),
                ("실행자 ID", f"`{interaction.user.id}`"),
                ("실행자 이름", f"`{interaction.user.name}`")
            ]
            
            fields = [
                ("서버 이름", f"`{guild.name}`"),
                ("서버 ID", f"`{guild.id}`"),
                ("백업 서버", f"`{self.serverName}`"),
                ("복구 결과", f"카테고리: {categoriesCreated}개\n채널: {channelsCreated}개\n역할: {rolesCreated}개\n이모지: {emojisCreated}개\n스티커: {stickersCreated}개"),
                ("새 복구코드", f"||`{newRestoreKey}`||")
            ]
            
            await helper.SendOwnerLogWebhook(
                "서버 복구 완료",
                f"### 🎉 **{guild.name}** 서버의 구조 복구가 완료되었습니다.\n\n" +
                f"### 📊 **처리 결과**\n" +
                f"> ✅ 카테고리: `{categoriesCreated}개`\n" +
                f"> ✅ 채널: `{channelsCreated}개`\n" +
                f"> ✅ 역할: `{rolesCreated}개`\n" +
                f"> ✅ 이모지: `{emojisCreated}개`\n" +
                f"> ✅ 스티커: `{stickersCreated}개`\n" +
                f"> 🔑 새 복구코드: ||`{newRestoreKey}`||",
                0x57F287,
                fields,
                userInfo
            )
            
        except Exception as e:
            await helper.SendOwnerLogWebhook(
                "🔴 복구 프로세스 오류",
                f"```{traceback.format_exc()}```",
                Color.red()
            )
            
            errorEmbed = discord.Embed(
                title="❌ 복구 중 오류 발생",
                description=f"복구 과정에서 오류가 발생했습니다.\n```{str(e)}```",
                color=Color.red()
            )
            try:
                await interaction.edit_original_response(embed=errorEmbed)
            except discord.errors.NotFound:
                try:
                    await interaction.followup.send(embed=errorEmbed, ephemeral=True)
                except:
                    pass

class StructureRestoreResultEmbed:
    @staticmethod
    def create(categoriesCreated, channelsCreated, rolesCreated, emojisCreated, stickersCreated, 
              failedCategoriesChannels, failedRoles, failedEmojis, failedStickers, newRestoreKey=None):
        successCount = categoriesCreated + channelsCreated + rolesCreated + emojisCreated + stickersCreated
        failedCount = failedCategoriesChannels + failedRoles + failedEmojis + failedStickers
        
        color = Color.green() if successCount > failedCount else Color.red()
        description = (
            f"## 📊 **서버 복구 결과**\n\n"
            f"### 🎯 **처리 현황**\n"
            f"```ini\n"
            f"[✅ 성공] {successCount}개\n"
            f"[❌ 실패] {failedCount}개\n"
            f"```\n"
            f"### 📋 **세부 항목**\n"
            f"```ini\n"
            f"[카테고리] {categoriesCreated}개 성공\n"
            f"[채널] {channelsCreated}개 성공\n"
            f"[역할] {rolesCreated}개 성공\n"
            f"[이모지] {emojisCreated}개 성공\n"
            f"[스티커] {stickersCreated}개 성공\n"
            f"```\n\n"
        )
        
        if newRestoreKey:
            description += (
                f"### 🔑 **새로운 복구코드**\n"
                f"> 안전하게 보관해주세요!\n"
                f"> ||`{newRestoreKey}`||\n\n"
                f"### ⚠️ **주의사항**\n"
                f"> 🚫 이전 복구코드는 더 이상 사용할 수 없습니다.\n"
                f"> 🔒 새로운 복구코드를 안전한 곳에 보관하세요.\n"
            )
            
        description += (
            f"### ℹ️ **안내**\n"
            f"> 🔄 서버 복구가 완료되었습니다.\n"
            f"> 🔍 자세한 내용은 서버를 확인해 주세요.\n"
            f"> 📌 문제가 발생한 경우 관리자에게 문의하세요."
        )
        
        return discord.Embed(
            title="✅ 서버 복구 완료",
            description=description,
            color=color,
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )

class RestoreView(View):
    def __init__(self, restoreKey: str, serverName: str, targetServerId: str, usersCount: int, guildName: str, guildId: int):
        super().__init__(timeout=60.0)
        self.value = None
        self.restoreKey = restoreKey
        self.serverName = serverName
        self.targetServerId = targetServerId
        self.usersCount = usersCount
        self.guildName = guildName
        self.guildId = guildId
        self.embedDescription = (
            f"## 🔄 **인원 복구 작업 확인**\n\n"
            f"### 📋 **복구코드 정보**\n"
            f"```ini\n"
            f"[복구코드] {restoreKey}\n"
            f"[서버이름] {serverName}\n"
            f"[서버 ID] {targetServerId}\n"
            f"[예상인원] {usersCount}명\n"
            f"```\n"
            f"### 🎯 **복구대상 서버**\n"
            f"```ini\n"
            f"[서버이름] {guildName}\n"
            f"[서버 ID] {guildId}\n"
            f"```\n\n"
            f"### ⚠️ **주의사항**\n"
            f"> 🔄 복구가 완료되면 복구코드가 자동으로 변경됩니다.\n"
            f"> ⏳ 복구 중에는 봇이 일시적으로 응답하지 않을 수 있습니다.\n"
            f"> 👥 이미 서버에 있는 유저는 자동으로 건너뜁니다.\n\n"
            f"### 📢 **안내**\n"
            f"> 💡 아래 버튼을 클릭하여 복구를 시작하거나 취소할 수 있습니다.\n"
            f"> ⏱️ 60초 후에는 자동으로 취소됩니다."
        )
        
        self.embed = discord.Embed(
            title="👥 인원 복구 확인",
            description=self.embedDescription,
            color=Color.blue(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )

    async def on_timeout(self):
        timeoutEmbed = discord.Embed(
            title="⏱️ 시간 초과",
            description="복구 작업이 시간 초과로 취소되었습니다.",
            color=Color.red(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )
        if hasattr(self, 'message'):
            await self.message.edit(embed=timeoutEmbed, view=None)

    @discord.ui.button(label="❌ 취소", style=discord.ButtonStyle.danger, custom_id="restore_cancel")
    async def cancelButton(self, interaction: Interaction, button: Button):
        cancelEmbed = discord.Embed(
            title="❌ 복구 취소",
            description="복구 작업이 취소되었습니다.",
            color=Color.red(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )
        await interaction.response.edit_message(embed=cancelEmbed, view=None)
        self.value = False
        self.stop()

    @discord.ui.button(label="✅ 복구 시작", style=discord.ButtonStyle.success, custom_id="restore_confirm")
    async def confirmButton(self, interaction: Interaction, button: discord.ui.Button):
        try:
            await interaction.response.defer(ephemeral=True)
            
            guild = interaction.guild
            config = helper.LoadConfig()
            
            newRestoreKey = helper.GenRandom(16)
            
            def getTargetUsers(targetServerId):
                conn = None
                try:
                    conn = helper.sqlite3.connect(os.path.join(config.DBFolderPath, f"{targetServerId}.db"))
                    cursor = conn.cursor()
                    cursor.execute("SELECT userId, refreshToken FROM users WHERE refreshToken IS NOT NULL")
                    return cursor.fetchall()
                except Exception as e:
                    print(f"사용자 정보 조회 오류: {str(e)}")
                    return []
                finally:
                    if conn:
                        conn.close()
            
            try:
                targetUsers = await interaction.client.loop.run_in_executor(
                    None, lambda: getTargetUsers(self.targetServerId)
                )
            except Exception as e:
                errorEmbed = discord.Embed(
                    title="❌ 오류 발생",
                    description=f"사용자 정보를 가져오는 중 오류가 발생했습니다.\n```{str(e)}```",
                    color=Color.red()
                )
                try:
                    await interaction.edit_original_response(embed=errorEmbed)
                except discord.errors.NotFound:
                    try:
                        await interaction.followup.send(embed=errorEmbed, ephemeral=True)
                    except:
                        pass
                return

            apiSession = aiohttp.ClientSession()
            
            existingMembers = []
            successCount = 0
            failCount = 0
            alreadyInServer = 0
            totalCount = 0
            
            try:
                membersUrl = f'https://discord.com/api/guilds/{guild.id}/members?limit=1000'
                apiHeaders = {
                    "Authorization": f"Bot {config.botToken}",
                    "Content-Type": "application/json"
                }
                
                async with apiSession.get(membersUrl, headers=apiHeaders) as membersResponse:
                    if membersResponse.status == 200:
                        membersData = await membersResponse.json()
                        existingMembers = [member["user"]["id"] for member in membersData]
            except Exception as e:
                if apiSession:
                    await apiSession.close()
                errorEmbed = discord.Embed(
                    title="❌ 복구 오류",
                    description=f"멤버 목록을 가져오는 중 오류가 발생했습니다: {str(e)}",
                    color=Color.red(),
                    timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
                )
                await interaction.edit_original_response(embed=errorEmbed)
                return
                
            lastUpdateTime = datetime.now()
            updateInterval = 5 
            
            await helper.SendOwnerLogWebhook(
                "🔄 복구 프로세스 시작",
                f"### 🎯 **{guild.name}** 서버에서 인원 복구가 시작되었습니다.\n\n" +
                f"복구를 시작한 관리자: <@{interaction.user.id}>",
                0x3498DB,
                [
                    ("📋 복구 서버", f"`{self.serverName}`\n`ID: {self.targetServerId}`"),
                    ("🎯 대상 서버", f"`{guild.name}`\n`ID: {guild.id}`"),
                    ("👥 복구 예상 인원", f"`{len(targetUsers)}명`"),
                    ("🔑 복구 코드", f"||`{self.restoreKey}`||")
                ],
                [
                    ("👤 실행자", f"<@{interaction.user.id}>"),
                    ("🆔 실행자 ID", f"`{interaction.user.id}`"),
                    ("📝 실행자 이름", f"`{interaction.user.name}`")
                ]
            )
            
            for userId, refreshToken in targetUsers:
                totalCount += 1
                
                if str(userId) in existingMembers:
                    alreadyInServer += 1
                    continue
                
                try:
                    refreshResult = await helper.RefreshToken(refreshToken, apiSession)
                    
                    if not refreshResult.get("access_token"):
                        failCount += 1
                        continue
                    
                    accessToken = refreshResult["access_token"]
                    
                    addMemberUrl = f'https://discord.com/api/guilds/{guild.id}/members/{userId}'
                    addMemberData = {'access_token': accessToken}
                    addMemberHeaders = {
                        "Authorization": f"Bot {config.botToken}",
                        "Content-Type": "application/json"
                    }
                    
                    async with apiSession.put(addMemberUrl, json=addMemberData, headers=addMemberHeaders) as addMemberResponse:
                        if addMemberResponse.status in (200, 201):
                            successCount += 1
                        elif addMemberResponse.status == 204:
                            alreadyInServer += 1
                        else:
                            failCount += 1
                    
                    now = datetime.now()
                    if (now - lastUpdateTime).total_seconds() > updateInterval:
                        progressEmbed = discord.Embed(
                            title="🔄 인원 복구 진행 중",
                            description=(
                                f"## 📊 **진행 상황**\n\n"
                                f"```ini\n"
                                f"[✅ 성공] {successCount}명\n"
                                f"[❌ 실패] {failCount}명\n"
                                f"[💫 이미 있음] {alreadyInServer}명\n"
                                f"[📝 처리 중] {totalCount}/{len(targetUsers)} ({totalCount/len(targetUsers)*100:.1f}%)\n"
                                f"```\n\n"
                                f"### ⏳ **진행 중입니다...**\n"
                                f"> 🔄 인원 복구가 완료되면 결과가 표시됩니다."
                            ),
                            color=Color.blue(),
                            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
                        )
                        await interaction.edit_original_response(embed=progressEmbed)
                        lastUpdateTime = now
                        
                except Exception as e:
                    failCount += 1
                    print(f"사용자 {userId} 복구 중 오류: {str(e)}")
            
            if apiSession:
                await apiSession.close()
                
            def updateRestoreKey():
                try:
                    keyUpdateConn = helper.sqlite3.connect(config.DBPath)
                    keyUpdateCursor = keyUpdateConn.cursor()
                    keyUpdateCursor.execute("UPDATE Keys SET Key = ? WHERE Key = ?", (newRestoreKey, self.restoreKey))
                    rowsAffected = keyUpdateCursor.rowcount
                    keyUpdateConn.commit()
                    keyUpdateConn.close()
                    
                    serverDbPath = os.path.join(config.DBFolderPath, f"{self.targetServerId}.db")
                    serverKeyUpdateConn = helper.sqlite3.connect(serverDbPath)
                    serverKeyUpdateCursor = serverKeyUpdateConn.cursor()
                    serverKeyUpdateCursor.execute("UPDATE Info SET key = ? WHERE id = ?", (newRestoreKey, self.targetServerId))
                    serverKeyUpdateConn.commit()
                    serverKeyUpdateConn.close()
                    
                    print(f"키 업데이트 결과: {rowsAffected}행 영향받음 (0은 실패)")
                    if rowsAffected == 0:
                        print(f"키 업데이트 실패: 키 '{self.restoreKey}'를 찾을 수 없습니다.")
                        insertConn = helper.sqlite3.connect(config.DBPath)
                        insertCursor = insertConn.cursor()
                        insertCursor.execute("INSERT INTO Keys (Key, serverId) VALUES (?, ?)", (newRestoreKey, self.targetServerId))
                        insertConn.commit()
                        insertConn.close()
                        print(f"새 키 삽입 시도: {newRestoreKey}")
                    return True
                except Exception as e:
                    print(f"복구 키 업데이트 오류: {str(e)}")
                    return False
            
            await interaction.client.loop.run_in_executor(
                None, updateRestoreKey
            )
            
            await helper.SendOwnerLogWebhook(
                "✅ 복구 프로세스 완료",
                f"### 🎉 **{guild.name}** 서버의 인원 복구가 완료되었습니다.\n\n" +
                f"### 📊 **처리 결과**\n" +
                f"> ✅ 성공: `{successCount}명`\n" +
                f"> ❌ 실패: `{failCount}명`\n" +
                f"> 💫 이미 있음: `{alreadyInServer}명`\n" +
                f"> 📝 총 시도: `{totalCount}명`",
                0x57F287 if successCount > failCount else 0xFF0000,
                [
                    ("📋 복구 서버", f"`{self.serverName}`\n`ID: {self.targetServerId}`"),
                    ("🎯 대상 서버", f"`{guild.name}`\n`ID: {guild.id}`"),
                    ("📊 성공률", f"`{(successCount/totalCount*100) if totalCount > 0 else 0:.1f}%`"),
                    ("🔑 새 복구코드", f"||`{newRestoreKey}`||")
                ],
                [
                    ("👤 실행자", f"<@{interaction.user.id}>"),
                    ("🆔 실행자 ID", f"`{interaction.user.id}`"),
                    ("📝 실행자 이름", f"`{interaction.user.name}`")
                ]
            )
            
            resultEmbed = RestoreResultEmbed.create(
                successCount=successCount,
                failCount=failCount,
                alreadyInServer=alreadyInServer,
                totalCount=totalCount,
                newRestoreKey=newRestoreKey
            )
            
            await interaction.edit_original_response(embed=resultEmbed)
            
        except Exception as e:
            await helper.SendOwnerLogWebhook(
                "🔴 복구 프로세스 오류",
                f"```{traceback.format_exc()}```",
                Color.red()
            )
            
            errorEmbed = discord.Embed(
                title="❌ 복구 중 오류 발생",
                description=f"복구 과정에서 오류가 발생했습니다.\n```{str(e)}```",
                color=Color.red()
            )
            try:
                await interaction.edit_original_response(embed=errorEmbed)
            except discord.errors.NotFound:
                try:
                    await interaction.followup.send(embed=errorEmbed, ephemeral=True)
                except:
                    pass
            
            if apiSession:
                await apiSession.close()

class RestoreResultEmbed:
    @staticmethod
    def create(successCount: int, failCount: int, alreadyInServer: int, totalCount: int, newRestoreKey: str):
        color = Color.green() if successCount > failCount else Color.red()
        description = (
            f"## 📊 **인원 복구 결과 보고서**\n\n"
            f"### 🎯 **처리 현황**\n"
            f"```ini\n"
            f"[✅ 성공] {successCount}명\n"
            f"[❌ 실패] {failCount}명\n"
            f"[💫 이미 있음] {alreadyInServer}명\n"
            f"[📝 총 시도] {totalCount}명\n"
            f"```\n"
            f"### 🔑 **새로운 복구코드**\n"
            f"> 안전하게 보관해주세요!\n"
            f"> ||`{newRestoreKey}`||\n\n"
            f"### ⚠️ **주의사항**\n"
            f"> 🚫 이전 복구코드는 더 이상 사용할 수 없습니다.\n"
            f"> 🔒 새로운 복구코드를 안전한 곳에 보관하세요.\n"
            f"> 📌 문제가 발생한 경우 관리자에게 문의하세요."
        )
        
        return discord.Embed(
            title="✅ 인원 복구 완료",
            description=description,
            color=color,
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )

# V1.3.4