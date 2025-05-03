import discord
from discord import Interaction, Color, Button, SelectOption
from discord.ui import View, Select
import pytz
from datetime import datetime
import json
import os
from . import helper

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
            
            dbConn = None
            try:
                dbConn = await interaction.client.loop.run_in_executor(
                    None, lambda: helper.sqlite3.connect(config.DBPath)
                )
                dbCursor = dbConn.cursor()
                dbCursor.execute("SELECT serverId FROM Keys WHERE Key = ?", (restoreKey,))
                keyResult = dbCursor.fetchone()
                
                if not keyResult:
                    await helper.ErrorEmbed(interaction, "유효하지 않은 복구키입니다.")
                    return
                    
                targetServerId = keyResult[0]
                serverDbPath = os.path.join(config.DBFolderPath, f"{targetServerId}.db")
                
                if not os.path.exists(serverDbPath):
                    await helper.ErrorEmbed(interaction, "서버 DB 파일을 찾을 수 없습니다.")
                    return
                
                backupDir = None
                backupFile = None
                
                backupsFolder = os.path.join(config.DBFolderPath, "backups")
                if os.path.exists(backupsFolder):
                    for folder in os.listdir(backupsFolder):
                        if folder.startswith(f"{targetServerId}_"):
                            folderPath = os.path.join(backupsFolder, folder)
                            jsonPath = os.path.join(folderPath, "backup.json")
                            if os.path.exists(jsonPath):
                                backupDir = folderPath
                                backupFile = jsonPath
                                break
                
                if self.restoreType == "users":
                    serverConn = await interaction.client.loop.run_in_executor(
                        None, lambda: helper.sqlite3.connect(serverDbPath)
                    )
                    serverCursor = serverConn.cursor()
                    
                    serverCursor.execute("SELECT name FROM Info")
                    serverNameResult = serverCursor.fetchone()
                    serverName = serverNameResult[0] if serverNameResult else "알 수 없음"
                    
                    serverCursor.execute("SELECT userId, refreshToken FROM Users WHERE refreshToken IS NOT NULL")
                    targetUsers = serverCursor.fetchall()
                    serverConn.close()
                    
                    if not targetUsers:
                        await helper.ErrorEmbed(interaction, "복구할 유저 정보가 없습니다.")
                        return
                    
                    restoreView = RestoreView(
                        restoreKey=restoreKey,
                        serverName=serverName,
                        targetServerId=targetServerId,
                        usersCount=len(targetUsers),
                        guildName=interaction.guild.name,
                        guildId=interaction.guild.id
                    )
                    
                    await interaction.response.send_message(embed=restoreView.embed, view=restoreView, ephemeral=True)
                    
                else:
                    if not backupFile:
                        await helper.ErrorEmbed(interaction, "해당 서버의 백업 파일을 찾을 수 없습니다.")
                        return
                    
                    with open(backupFile, 'r', encoding='utf-8') as f:
                        backupData = json.load(f)
                    
                    serverName = backupData["server_info"]["name"]
                    
                    structureRestoreView = StructureRestoreView(
                        restoreKey=restoreKey,
                        serverName=serverName,
                        targetServerId=targetServerId,
                        backupFile=backupFile,
                        backupDir=backupDir,
                        guildName=interaction.guild.name,
                        guildId=interaction.guild.id,
                        backupData=backupData
                    )
                    
                    await interaction.response.send_message(embed=structureRestoreView.embed, view=structureRestoreView, ephemeral=True)
                
            finally:
                if dbConn:
                    dbConn.close()
                    
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")

class StructureRestoreView(discord.ui.View):
    def __init__(self, restoreKey, serverName, targetServerId, backupFile, backupDir, guildName, guildId, backupData):
        super().__init__(timeout=60.0)
        self.restoreKey = restoreKey
        self.serverName = serverName
        self.targetServerId = targetServerId
        self.backupFile = backupFile
        self.backupDir = backupDir
        self.guildName = guildName
        self.guildId = guildId
        self.backupData = backupData
        self.value = None
        
        self.roleCount = len(backupData["roles_data"])
        self.channelCount = len(backupData["channels_data"])
        self.emojiCount = len(backupData["emojis_data"])
        self.stickerCount = len(backupData["stickers_data"])
        
        self.embedDescription = (
            f"## 🔄 **서버 복구 확인**\n\n"
            f"### 📋 **백업 정보**\n"
            f"```ini\n"
            f"[서버이름] {serverName}\n"
            f"[서버 ID] {targetServerId}\n"
            f"[백업시간] {backupData['backup_info']['timestamp']}\n"
            f"```\n"
            f"### 📊 **복구할 항목**\n"
            f"```ini\n"
            f"[역할] {self.roleCount}개\n"
            f"[채널] {self.channelCount}개\n"
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
        await interaction.response.edit_message(embed=startEmbed, view=None)
        self.value = True
        self.stop()
        
        try:
            guild = interaction.guild
            
            channelsCreated = 0
            categoriesCreated = 0
            failedChannels = 0
            
            categoryMap = {}
            
            for channel in self.backupData["channels_data"]:
                if channel["type"] == "category":
                    try:
                        existingCategory = discord.utils.get(guild.categories, name=channel["name"])
                        if existingCategory:
                            categoryMap[channel["name"]] = existingCategory
                        else:
                            overwrites = {}
                            for overwrite in channel["overwrites"]:
                                role = discord.utils.get(guild.roles, name=overwrite["name"])
                                if role:
                                    permissions = discord.PermissionOverwrite()
                                    permissions.update(
                                        **dict(permission for permission in discord.Permissions(overwrite["allow"])))
                                    overwrites[role] = permissions
                            
                            newCategory = await guild.create_category(
                                name=channel["name"],
                                overwrites=overwrites,
                                reason="서버 복구"
                            )
                            categoryMap[channel["name"]] = newCategory
                            categoriesCreated += 1
                    except Exception as e:
                        failedChannels += 1
                        print(f"카테고리 생성 실패: {channel['name']} - {str(e)}")
            
            for channel in self.backupData["channels_data"]:
                if channel["type"] != "category":
                    try:
                        categoryObj = None
                        if "category" in channel and channel["category"]:
                            categoryObj = categoryMap.get(channel["category"])
                        
                        overwrites = {}
                        for overwrite in channel["overwrites"]:
                            role = discord.utils.get(guild.roles, name=overwrite["name"])
                            if role:
                                permissions = discord.PermissionOverwrite()
                                permissions.update(
                                    **dict(permission for permission in discord.Permissions(overwrite["allow"])))
                                overwrites[role] = permissions
                        
                        if "text" in channel["type"].lower():
                            nsfw = channel.get("nsfw", False)
                            slowmode = channel.get("slowmode_delay", 0)
                            
                            await guild.create_text_channel(
                                name=channel["name"],
                                category=categoryObj,
                                overwrites=overwrites,
                                nsfw=nsfw,
                                slowmode_delay=slowmode,
                                reason="서버 복구"
                            )
                            channelsCreated += 1
                            
                        elif "voice" in channel["type"].lower():
                            await guild.create_voice_channel(
                                name=channel["name"],
                                category=categoryObj,
                                overwrites=overwrites,
                                reason="서버 복구"
                            )
                            channelsCreated += 1
                            
                        elif "forum" in channel["type"].lower():
                            try:
                                await guild.create_forum(
                                    name=channel["name"],
                                    category=categoryObj,
                                    overwrites=overwrites,
                                    reason="서버 복구"
                                )
                                channelsCreated += 1
                            except:
                                await guild.create_text_channel(
                                    name=f"{channel['name']} (포럼)",
                                    category=categoryObj,
                                    overwrites=overwrites,
                                    reason="서버 복구"
                                )
                                channelsCreated += 1
                    except Exception as e:
                        failedChannels += 1
                        print(f"채널 생성 실패: {channel['name']} - {str(e)}")
            
            rolesCreated = 0
            failedRoles = 0
            
            for role in reversed(self.backupData["roles_data"]):
                if role["name"] != "@everyone":
                    try:
                        existingRole = discord.utils.get(guild.roles, name=role["name"])
                        if not existingRole:
                            await guild.create_role(
                                name=role["name"],
                                permissions=discord.Permissions(role["permissions"]),
                                colour=discord.Colour(role["colour"]),
                                hoist=role["hoist"],
                                mentionable=role["mentionable"],
                                reason="서버 복구"
                            )
                            rolesCreated += 1
                    except Exception as e:
                        failedRoles += 1
                        print(f"역할 생성 실패: {role['name']} - {str(e)}")
            
            emojisCreated = 0
            failedEmojis = 0
            
            for emoji in self.backupData["emojis_data"]:
                try:
                    emojiPath = os.path.join(self.backupDir, "emojis", f"{emoji['path'].split('/')[-1]}")
                    if os.path.exists(emojiPath):
                        with open(emojiPath, "rb") as img:
                            emojiData = img.read()
                        await guild.create_custom_emoji(
                            name=emoji["name"],
                            image=emojiData,
                            reason="서버 복구"
                        )
                        emojisCreated += 1
                except Exception as e:
                    failedEmojis += 1
                    print(f"이모지 생성 실패: {emoji['name']} - {str(e)}")
            
            stickersCreated = 0
            failedStickers = 0
            
            for sticker in self.backupData["stickers_data"]:
                try:
                    stickerPath = os.path.join(self.backupDir, "stickers", f"{sticker['path'].split('/')[-1]}")
                    if os.path.exists(stickerPath):
                        with open(stickerPath, "rb") as img:
                            stickerData = img.read()
                        await guild.create_sticker(
                            name=sticker["name"],
                            description=sticker.get("description", "복구된 스티커"),
                            emoji=sticker.get("emoji", "⭐"),
                            file=discord.File(stickerPath),
                            reason="서버 복구"
                        )
                        stickersCreated += 1
                except Exception as e:
                    failedStickers += 1
                    print(f"스티커 생성 실패: {sticker['name']} - {str(e)}")
            
            resultEmbed = StructureRestoreResultEmbed.create(
                categoriesCreated=categoriesCreated,
                channelsCreated=channelsCreated,
                rolesCreated=rolesCreated,
                emojisCreated=emojisCreated,
                stickersCreated=stickersCreated,
                failedCategoriesChannels=failedChannels,
                failedRoles=failedRoles,
                failedEmojis=failedEmojis,
                failedStickers=failedStickers
            )
            
            await interaction.edit_original_response(embed=resultEmbed)
            
            userInfo = [
                ("실행자", f"<@{interaction.user.id}>"),
                ("실행자 ID", f"`{interaction.user.id}`"),
                ("실행자 이름", f"`{interaction.user.name}`")
            ]
            
            fields = [
                ("서버 이름", f"`{guild.name}`"),
                ("서버 ID", f"`{guild.id}`"),
                ("백업 서버", f"`{self.serverName}`"),
                ("복구 결과", f"카테고리: {categoriesCreated}개\n채널: {channelsCreated}개\n역할: {rolesCreated}개\n이모지: {emojisCreated}개\n스티커: {stickersCreated}개")
            ]
            
            await helper.SendOwnerLogWebhook(
                "서버 복구 완료",
                f"'{guild.name}' 서버의 구조 복구가 완료되었습니다.",
                0x57F287,
                fields,
                userInfo
            )
            
        except Exception as e:
            errorEmbed = discord.Embed(
                title="❌ 복구 오류",
                description=f"서버 복구 중 오류가 발생했습니다.\n\n```\n{str(e)}\n```",
                color=Color.red(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            )
            await interaction.edit_original_response(embed=errorEmbed)
            
            await helper.SendOwnerLogWebhook(
                "서버 복구 오류",
                f"'{interaction.guild.name}' 서버의 구조 복구 중 오류가 발생했습니다.",
                0xFF0000,
                [
                    ("서버 이름", f"`{interaction.guild.name}`"),
                    ("서버 ID", f"`{interaction.guild.id}`"),
                    ("오류 내용", f"```\n{str(e)}\n```")
                ],
                [
                    ("실행자", f"<@{interaction.user.id}>"),
                    ("실행자 ID", f"`{interaction.user.id}`"),
                    ("실행자 이름", f"`{interaction.user.name}`")
                ]
            )

class StructureRestoreResultEmbed:
    @staticmethod
    def create(categoriesCreated, channelsCreated, rolesCreated, emojisCreated, stickersCreated, 
              failedCategoriesChannels, failedRoles, failedEmojis, failedStickers):
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
            f"[카테고리] {categoriesCreated}개 성공 / {failedCategoriesChannels}개 실패\n"
            f"[채널] {channelsCreated}개 성공 / {failedCategoriesChannels}개 실패\n"
            f"[역할] {rolesCreated}개 성공 / {failedRoles}개 실패\n"
            f"[이모지] {emojisCreated}개 성공 / {failedEmojis}개 실패\n"
            f"[스티커] {stickersCreated}개 성공 / {failedStickers}개 실패\n"
            f"```\n\n"
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
        startEmbed = discord.Embed(
            title="🔄 복구 시작",
            description=(
                f"## 🚀 **인원 복구가 시작되었습니다**\n\n"
                f"### 📋 **진행 상황**\n"
                f"> 🔹 복구가 완료될 때까지 기다려주세요.\n"
                f"> 🔹 진행 상황은 자동으로 업데이트됩니다.\n"
                f"> 🔹 완료 시 결과가 표시됩니다.\n\n"
                f"### ⚠️ **주의사항**\n"
                f"> ⏳ 복구 시간은 인원에 따라 다소 소요될 수 있습니다.\n"
                f"> 🔔 복구가 완료되면 알림을 드립니다."
            ),
            color=Color.green(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )
        await interaction.response.edit_message(embed=startEmbed, view=None)
        self.value = True
        self.stop()

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

# V1.3.3