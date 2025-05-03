import discord
from discord import Interaction, Embed, Color
from discord.ui import Modal, TextInput
import pytz
from datetime import datetime
import os
import sqlite3
import re
import hashlib
import uuid
from . import helper

class ServerRegisterModal(Modal):
    def __init__(self, server_id: str):
        super().__init__(title="웹패널 정보 입력")
        self.server_id = server_id
        self.add_item(TextInput(label="아이디", placeholder="웹패널 아이디를 입력해주세요", required=True, style=discord.TextStyle.short, min_length=4, max_length=20))
        self.add_item(TextInput(label="비밀번호", placeholder="웹패널 비밀번호를 입력해주세요", required=True, style=discord.TextStyle.short, min_length=8, max_length=20))

    async def on_submit(self, interaction: Interaction):
        try:
            id = self.children[0].value
            password = self.children[1].value
            
            if not re.match(r'^[a-zA-Z0-9]+$', id):
                await helper.ErrorEmbed(interaction, "아이디는 영문자와 숫자만 포함해야 합니다.")
                return
                
            if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]+$', password):
                await helper.ErrorEmbed(interaction, "비밀번호는 최소 1개의 대문자, 소문자, 숫자, 특수문자(@$!%*?&#)를 포함해야 합니다.")
                return
  
            config = helper.LoadConfig()
            
            try:
                conn = sqlite3.connect(os.path.join(config.DBPath))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM Keys WHERE serverId = ?", (str(interaction.guild_id),))
                
                cursor.execute("SELECT COUNT(*) FROM WebPanel WHERE id = ?", (id,))
                count = cursor.fetchone()[0]
                conn.close()
                
                if count > 0:
                    await helper.ErrorEmbed(interaction, "이미 사용 중인 아이디입니다. 다른 아이디를 선택해주세요.")
                    return
            except Exception as e:
                print(f"데이터베이스 확인 중 오류 발생: {e}")
                await helper.ErrorEmbed(interaction, f"데이터베이스 확인 중 오류가 발생했습니다: {str(e)}")
                return
            
            timestamp = datetime.now(pytz.timezone("Asia/Seoul"))
            
            try:
                key = helper.GenRandom(16)
                helper.GenServerDB(str(interaction.guild_id), interaction.guild.name, timestamp.strftime("%Y-%m-%d %H:%M:%S"), key)
                
                conn = sqlite3.connect(os.path.join(config.DBPath))
                cursor = conn.cursor()
                cursor.execute("INSERT INTO Keys (Key, serverId) VALUES (?, ?)", (key, str(interaction.guild_id)))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"서버 등록 중 오류 발생: {e}")
                await helper.ErrorEmbed(interaction, f"서버 등록 중 오류가 발생했습니다: {str(e)}")
                return
            
            try:
                salt = uuid.uuid4().hex
                hashedPassword = hashlib.sha256(password.encode() + salt.encode()).hexdigest()
                
                try:
                    salt = uuid.uuid4().hex
                    hashedPassword = hashlib.sha256(password.encode() + salt.encode()).hexdigest()
                    
                    conn = sqlite3.connect(os.path.join(config.DBPath))
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO WebPanel (id, password, salt, serverId) 
                        VALUES (?, ?, ?, ?)
                    """, (id, hashedPassword, salt, self.server_id))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"웹패널 정보 저장 중 오류 발생: {e}")
                    await helper.ErrorEmbed(interaction, f"웹패널 정보 저장 중 오류가 발생했습니다: {str(e)}")
                    return
            except Exception as e:
                print(f"웹패널 정보 저장 중 오류 발생: {e}")
                await helper.ErrorEmbed(interaction, f"웹패널 정보 저장 중 오류가 발생했습니다: {str(e)}")
                return
            
            try:
                if interaction.user.dm_channel is None:
                    await interaction.user.create_dm()
                await interaction.user.dm_channel.send(embed=discord.Embed(title="웹패널 정보 입력 완료", description=f"웹패널 정보가 성공적으로 입력되었습니다.\n\n아이디: `{id}`\n비밀번호: `{password}`", color=Color.green()))
            except Exception as e:
                print(f"DM 전송 중 오류 발생: {e}")
            
            fields = [
                ("서버 이름", f"```{interaction.guild.name}```"),
                ("서버 ID", f"```{interaction.guild_id}```"),
                ("등록 시간", f"```{timestamp.strftime('%Y-%m-%d %H:%M:%S')}```"),
                ("복구 키", f"```{key}```")
            ]
            
            userInfo = [
                ("등록자", f"<@{interaction.user.id}>"),
                ("등록자 ID", f"`{interaction.user.id}`"),
                ("등록자 이름", f"`{interaction.user.name}`")
            ]
            
            await helper.SendOwnerLogWebhook(
                "서버 등록",
                f"{interaction.guild.name} 서버가 등록되었습니다.",
                0x57F287,
                fields,
                userInfo
            )
            
            await helper.SendEmbed(
                interaction=interaction,
                title="등록 완료",
                description="서버가 등록되었습니다.",
                color=Color.green(),
                fields=fields
            )
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}") 

# V1.3.2