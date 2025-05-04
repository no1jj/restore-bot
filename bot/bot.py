import discord
from discord.ext import commands
from discord import Interaction, Embed, Color
import pytz
from datetime import datetime
import sqlite3
import os
from no1jj.helper import config
from no1jj import discordUI, helper, backup_utils

class Bot(commands.Bot):
    async def on_ready(self):
        await self.wait_until_ready()
        await self.tree.sync()
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="no.1_jj"))
        print(f"{self.user}로 로그인했습니다")
        self.add_view(discordUI.SAuthView("인증", None))

intents = discord.Intents.all()
bot = Bot(command_prefix="!", intents=intents, help_command=None)
timestamp = datetime.now(pytz.timezone("Asia/Seoul"))
botToken = config.botToken

@bot.tree.command(name="등록", description="서버를 등록합니다.")
async def ServerRegister(interaction: Interaction):
    if not await helper.CheckPermission(interaction): 
        return
    
    if helper.CheckServerDB(str(interaction.guild_id)): 
        await helper.ErrorEmbed(interaction, "이미 등록된 서버입니다.")
        return
    
    try:
        view = discordUI.ServerRegisterModal(str(interaction.guild_id))
        await interaction.response.send_modal(view)

    except Exception as e:
        await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")

@bot.tree.command(name="정보", description="등록된 서버의 정보를 확인합니다.")
async def CheckInfo(interaction: Interaction):
    if not await helper.CheckPermission(interaction): 
        return

    if not await helper.CheckServerRegistration(interaction):
        return

    try:
        filePath = os.path.join(config.DBFolderPath, f"{interaction.guild_id}.db")
        conn = sqlite3.connect(filePath)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Info")
        info = cursor.fetchone()
        cursor.execute("SELECT loggingIp, loggingMail, loggingChannelId, roleId, useCaptcha, blockVpn FROM Settings")
        settings = cursor.fetchone()
        
        mainDbPath = os.path.join(config.DBPath)
        mainConn = sqlite3.connect(mainDbPath)
        mainCursor = mainConn.cursor()
        
        mainCursor.execute("""
            SELECT customLink, createdAt, lastUsed, visitCount 
            FROM ServerCustomLinks 
            WHERE serverId = ?
        """, [str(interaction.guild_id)])
        
        linkInfo = mainCursor.fetchone()
        mainConn.close()
        
        conn.close()
        
        channelText = '설정 안됨'
        if settings[2]:
            channel = interaction.guild.get_channel(int(settings[2]))
            channelText = f"#{channel.name}" if channel else '채널을 찾을 수 없음'
            
        roleText = "설정 안됨"
        if settings[3]:
            role = interaction.guild.get_role(int(settings[3]))
            roleText = role.name if role else "역할을 찾을 수 없음"
        
        linkText = "설정되지 않음"
        linkStatText = ""
        if linkInfo:
            domain = config.domain
            linkText = f"{domain}/j/{linkInfo[0]}"
            
            lastUsed = "없음" if not linkInfo[2] else linkInfo[2]
            linkStatText = f"\n🔸 **방문 횟수**: `{linkInfo[3]}회`\n🔸 **생성일**: `{linkInfo[1]}`\n🔸 **마지막 방문**: `{lastUsed}`"
        
        description = f"""
## 🏢 **서버 정보**
🔹 **서버 이름**: `{info[0]}`
🔹 **서버 ID**: `{info[1]}`
🔹 **등록 시간**: `{info[2]}`
🔹 **복구 키**: `{info[3]}`

## 🔗 **고유 링크 정보**
🔹 **링크 주소**: `{linkText}`{linkStatText}

## ⚙️ **설정 정보**
🔸 **IP 기록 여부**: {'✅' if settings[0] else '❌'}
🔸 **이메일 기록 여부**: {'✅' if settings[1] else '❌'}
🔸 **로그 채널**: {channel.mention if settings[2] and channel else f'`{channelText}`'}
🔸 **인증 역할**: {f'<@&{settings[3]}>' if settings[3] else f'`{roleText}`'}
🔸 **캡차 사용 여부**: {'✅' if settings[4] else '❌'}
🔸 **인증시 VPN 사용 차단**: {'✅' if settings[5] else '❌'}
"""
        
        embed = Embed(
            title="🔍 서버 정보",
            description=description,
            color=Color.green(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")

@bot.tree.command(name="설정", description="등록된 서버의 설정을 변경합니다.")
async def Settings(interaction: Interaction):
    if not await helper.CheckPermission(interaction): 
        return
    
    if not await helper.CheckServerRegistration(interaction):
        return
    
    try:
        view = discordUI.SettingsView(str(interaction.guild_id), interaction)
        await interaction.response.send_message(view=view, ephemeral=True)

    except Exception as e:
        await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")

@bot.tree.command(name="인증", description="인증 버튼을 생성합니다.")
async def Auth(interaction: Interaction):
    if not await helper.CheckPermission(interaction): 
        return
    
    if not await helper.CheckServerRegistration(interaction):
        return

    try:
        view = discordUI.AuthMessageModal(str(interaction.guild_id))
        await interaction.response.send_modal(view)

    except Exception as e:
        await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")

@bot.tree.command(name="화이트리스트관리", description="[OWNER] 화이트리스트를 관리합니다.")
async def WhiteList(interaction: Interaction):
    if not await helper.CheckPermission(interaction, owner=True): 
        return
        
    try:
        view = discordUI.AddOrDeleteView("화이트리스트")
        await interaction.response.send_message(view=view, ephemeral=True)

    except Exception as e:
        await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")

@bot.tree.command(name="블랙리스트관리", description="[OWNER] 블랙리스트를 관리합니다.")
async def BlackList(interaction: Interaction):
    if not await helper.CheckPermission(interaction, owner=True): 
        return

    try:
        view = discordUI.AddOrDeleteView("블랙리스트")
        await interaction.response.send_message(view=view, ephemeral=True)

    except Exception as e:
        await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")

@bot.tree.command(name="백업", description="서버를 백업합니다.")
async def BackUp(interaction: Interaction):
    if not await helper.CheckPermission(interaction): 
        return
    
    if not await helper.CheckServerRegistration(interaction):
        return

    try:
        config = helper.LoadConfig()
        timestamp = datetime.now(pytz.timezone("Asia/Seoul")).strftime('%Y%m%d%H%M%S')
        backupDir = os.path.join(config.DBFolderPath, f"backups/{interaction.guild.id}_{timestamp}")
        os.makedirs(backupDir, exist_ok=True)
        
        await interaction.response.defer(ephemeral=True)
        
        creatorInfo = f"{interaction.user.name} (ID: {interaction.user.id})"
        backupData = await backup_utils.CreateServerBackup(interaction.guild, backupDir, creatorInfo)
        
        roleCount = len(backupData["roles_data"])
        categoryCount = len([c for c in backupData["channels_data"] if backup_utils._IsCategory(c)])
        channelCount = len([c for c in backupData["channels_data"] if not backup_utils._IsCategory(c)])
        emojiCount = len(backupData["emojis_data"])
        stickerCount = len(backupData["stickers_data"])
        bannedCount = len(backupData["banned_users"]) if isinstance(backupData["banned_users"], list) else 0
        
        description = f"""
## 📦 **백업 완료**

### 📊 **백업 요약**
```ini
[서버 이름] {interaction.guild.name}
[서버 ID] {interaction.guild.id}
[백업 시간] {backupData["backup_info"]["timestamp"]}
[백업 경로] {backupDir}
```

### 📑 **백업 내용**
```ini
[카테고리] {categoryCount}개
[채널] {channelCount}개
[역할] {roleCount}개
[이모지] {emojiCount}개
[스티커] {stickerCount}개
[차단 목록] {bannedCount}명
```

백업 파일은 서버에 안전하게 저장되었습니다.
"""
        
        embed = Embed(
            title="✅ 백업 완료",
            description=description,
            color=Color.green(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )
        
        userInfo = [
            ("백업 실행자", f"<@{interaction.user.id}>"),
            ("실행자 ID", f"`{interaction.user.id}`"),
            ("실행자 이름", f"`{interaction.user.name}`")
        ]
        
        fields = [
            ("서버 이름", f"`{interaction.guild.name}`"),
            ("서버 ID", f"`{interaction.guild.id}`"),
            ("백업 경로", f"`{backupDir}`"),
            ("백업 내용", f"카테고리: `{categoryCount}개`\n채널: `{channelCount}개`\n역할: `{roleCount}개`\n이모지: `{emojiCount}개`\n스티커: `{stickerCount}개`\n차단 목록: `{bannedCount}명`")
        ]
        
        await helper.SendOwnerLogWebhook(
            "서버 백업 완료",
            f"### 🎉 **{interaction.guild.name}** 서버의 백업이 완료되었습니다.\n\n",
            0x57F287,
            fields,
            userInfo
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        if interaction.user.dm_channel is None:
            await interaction.user.create_dm()
        await interaction.user.dm_channel.send(embed=embed)
        
    except Exception as e:
        await helper.ErrorEmbed(interaction, f"백업 중 오류가 발생했습니다: {str(e)}")

@bot.tree.command(name="복구", description="인원 또는 서버를 복구합니다.")
async def RestoreServer(interaction: Interaction):
    if not await helper.CheckPermission(interaction): 
        return
    
    try:
        view = discordUI.RestoreTypeSelect()
        await interaction.response.send_message("복구 유형을 선택해주세요", view=view, ephemeral=True)
    except Exception as e:
        await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")

@bot.tree.command(name="인원", description="인증한 인원을 확인합니다.")
async def CheckAuthUsers(interaction: Interaction):
    if not await helper.CheckServerRegistration(interaction):
        return
    
    if not await helper.CheckPermission(interaction):
        return
    
    try:
        serverId = str(interaction.guild.id)
        dbPath = os.path.join(config.DBFolderPath, f"{serverId}.db")
        conn = sqlite3.connect(dbPath)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users")
        userCount = cursor.fetchone()[0]
        embed = discord.Embed(
            title="📊 인원 정보",
            description=f"이 서버에 인증된 총 인원 수: **{userCount}명**",
            color=discord.Color.blue(),
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await helper.ErrorEmbed(interaction, f"사용자 정보를 불러오는 중 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    helper.GenDB()
    bot.run(config.botToken)

#V1.5