import discord
from discord.ext import commands
from discord import Interaction, Embed, Color
import pytz
from datetime import datetime
import sqlite3
import os
import aiohttp
from no1jj.helper import config
from no1jj import discordUI, helper

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
        conn.close()
        
        channelText = '설정 안됨'
        if settings[2]:
            channel = interaction.guild.get_channel(int(settings[2]))
            channelText = f"#{channel.name}" if channel else '채널을 찾을 수 없음'
            
        roleText = "설정 안됨"
        if settings[3]:
            role = interaction.guild.get_role(int(settings[3]))
            roleText = role.name if role else "역할을 찾을 수 없음"
        
        description = f"""
## 🏢 **서버 정보**
🔹 **서버 이름**: `{info[0]}`
🔹 **서버 ID**: `{info[1]}`
🔹 **등록 시간**: `{info[2]}`
🔹 **복구 키**: `{info[3]}`

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

# @bot.tree.command(name="백업",description="서버를 백업합니다.")
# async def BackUp(interaction: Interaction):
#     if not await helper.CheckPermission(interaction): 
#         return
    
#     if not await helper.CheckServerRegistration(interaction):
#         return

    
#     try:
#         pass
#     except Exception as e:
#         await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")

@bot.tree.command(name="복구", description="복구를 시작합니다.")
async def RestoreServer(interaction: Interaction, restore_key: str):
    if not await helper.CheckPermission(interaction): 
        return
    
    apiSession = None
    
    try:
        config = helper.LoadConfig()
        
        dbConn = sqlite3.connect(config.DBPath)
        dbCursor = dbConn.cursor()
        dbCursor.execute("SELECT serverId FROM Keys WHERE Key = ?", (restore_key,))
        keyResult = dbCursor.fetchone()
        dbConn.close()
        
        if not keyResult:
            await helper.ErrorEmbed(interaction, "유효하지 않은 복구키입니다.")
            return
            
        targetServerId = keyResult[0]
        serverDbPath = os.path.join(config.DBFolderPath, f"{targetServerId}.db")
        
        if not os.path.exists(serverDbPath):
            await helper.ErrorEmbed(interaction, "서버 DB 파일을 찾을 수 없습니다.")
            return
            
        serverConn = sqlite3.connect(serverDbPath)
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
        
        newRestoreKey = helper.GenRandom(16)

        successCount = 0
        failCount = 0
        alreadyInServer = 0
        totalCount = 0
        
        apiSession = aiohttp.ClientSession()

        existingMembers = []
        try:
            membersUrl = f'https://discord.com/api/guilds/{interaction.guild.id}/members?limit=1000'
            apiHeaders = {
                "Authorization": f"Bot {config.botToken}",
                "Content-Type": "application/json"
            }
            
            async with apiSession.get(membersUrl, headers=apiHeaders) as membersResponse:
                if membersResponse.status == 200:
                    membersData = await membersResponse.json()
                    existingMembers = [member["user"]["id"] for member in membersData]
        
        except Exception as e:
            await apiSession.close()  
            await helper.ErrorEmbed(interaction, f"멤버 목록을 가져오는 중 오류가 발생했습니다: {str(e)}")
            return
        
        restoreView = discordUI.RestoreView(
            restore_key=restore_key,
            server_name=serverName,
            target_server_id=targetServerId,
            users_count=len(targetUsers),
            guild_name=interaction.guild.name,
            guild_id=interaction.guild.id
        )
        
        await interaction.response.send_message(embed=restoreView.embed, view=restoreView, ephemeral=True)
        
        await restoreView.wait()
        
        if hasattr(restoreView, 'value') and restoreView.value:
            await helper.SendOwnerLogWebhook(
                "🔄 복구 프로세스 시작",
                f"### 🎯 **{interaction.guild.name}** 서버에서 복구가 시작되었습니다.\n\n" +
                f"복구를 시작한 관리자: <@{interaction.user.id}>",
                0x3498DB,  
                [
                    ("📋 복구 서버", f"`{serverName}`\n`ID: {targetServerId}`"),
                    ("🎯 대상 서버", f"`{interaction.guild.name}`\n`ID: {interaction.guild.id}`"),
                    ("👥 복구 예상 인원", f"`{len(targetUsers)}명`"),
                    ("🔑 복구 코드", f"||`{restore_key}`||")
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
                    
                    addMemberUrl = f'https://discord.com/api/guilds/{interaction.guild.id}/members/{userId}'
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
                except Exception:
                    failCount += 1
            
            await apiSession.close()
            
            await helper.SendOwnerLogWebhook(
                "✅ 복구 프로세스 완료",
                f"### 🎉 **{interaction.guild.name}** 서버의 복구가 완료되었습니다.\n\n" +
                f"### 📊 **처리 결과**\n" +
                f"> ✅ 성공: `{successCount}명`\n" +
                f"> ❌ 실패: `{failCount}명`\n" +
                f"> 💫 이미 있음: `{alreadyInServer}명`\n" +
                f"> 📝 총 시도: `{totalCount}명`",
                0x57F287 if successCount > failCount else 0xFF0000, 
                [
                    ("📋 복구 서버", f"`{serverName}`\n`ID: {targetServerId}`"),
                    ("🎯 대상 서버", f"`{interaction.guild.name}`\n`ID: {interaction.guild.id}`"),
                    ("📊 성공률", f"`{(successCount/totalCount*100) if totalCount > 0 else 0:.1f}%`"),
                    ("🔑 새 복구코드", f"||`{newRestoreKey}`||")
                ],
                [
                    ("👤 실행자", f"<@{interaction.user.id}>"),
                    ("🆔 실행자 ID", f"`{interaction.user.id}`"),
                    ("📝 실행자 이름", f"`{interaction.user.name}`")
                ]
            )
            
            keyUpdateConn = sqlite3.connect(config.DBPath)
            keyUpdateCursor = keyUpdateConn.cursor()
            keyUpdateCursor.execute("UPDATE Keys SET Key = ? WHERE Key = ?", (newRestoreKey, restore_key))
            keyUpdateConn.commit()
            keyUpdateConn.close()

            serverKeyUpdateConn = sqlite3.connect(serverDbPath)
            serverKeyUpdateCursor = serverKeyUpdateConn.cursor()
            serverKeyUpdateCursor.execute("UPDATE Info SET key = ? WHERE id = ?", (newRestoreKey, targetServerId))
            serverKeyUpdateConn.commit()
            serverKeyUpdateConn.close()

            resultEmbed = discordUI.RestoreResultEmbed.create(
                success_count=successCount,
                fail_count=failCount,
                already_in_server=alreadyInServer,
                total_count=totalCount,
                new_restore_key=newRestoreKey
            )
            
            originalMsg = await interaction.original_response()
            await originalMsg.edit(embed=resultEmbed)
        else:
            await helper.SendOwnerLogWebhook(
                "❌ 복구 프로세스 취소",
                f"### ⚠️ **{interaction.guild.name}** 서버에서 복구가 취소되었습니다.",
                0xFF0000, 
                [
                    ("📋 복구 서버", f"`{serverName}`\n`ID: {targetServerId}`"),
                    ("🎯 대상 서버", f"`{interaction.guild.name}`\n`ID: {interaction.guild.id}`")
                ],
                [
                    ("👤 실행자", f"<@{interaction.user.id}>"),
                    ("🆔 실행자 ID", f"`{interaction.user.id}`"),
                    ("📝 실행자 이름", f"`{interaction.user.name}`")
                ]
            )
            
            if apiSession:
                await apiSession.close()
            return
        
    except Exception as e:
        await helper.SendOwnerLogWebhook(
            "🔴 복구 프로세스 오류",
            f"### ⚠️ **{interaction.guild.name}** 서버에서 복구 중 오류가 발생했습니다.\n\n" +
            f"### 📋 **오류 내용**\n" +
            f"```\n{str(e)}\n```",
            0xFF0000,  
            [
                ("📋 복구 서버", f"`{serverName}`\n`ID: {targetServerId}`"),
                ("🎯 대상 서버", f"`{interaction.guild.name}`\n`ID: {interaction.guild.id}`")
            ],
            [
                ("👤 실행자", f"<@{interaction.user.id}>"),
                ("🆔 실행자 ID", f"`{interaction.user.id}`"),
                ("📝 실행자 이름", f"`{interaction.user.name}`")
            ]
        )
        
        if apiSession:
            await apiSession.close()
        await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")
    finally:
        if apiSession:
            await apiSession.close()

if __name__ == "__main__":
    helper.GenDB()
    bot.run(config.botToken)

# V1.3