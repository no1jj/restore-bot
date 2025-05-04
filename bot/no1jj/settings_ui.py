import discord
from discord import Interaction, Embed, Color, SyncWebhook, SelectOption
from discord.ui import View, Button, Select, RoleSelect, ChannelSelect
import pytz
from datetime import datetime
import os
import sqlite3
from . import helper
import re

class SettingsView(View):
    def __init__(self, serverId: str, interaction: Interaction):
        super().__init__(timeout=None)
        self.add_item(SettingsSelect(serverId, interaction))
        self.add_item(WebPanelButton())

class WebPanelButton(Button):
    def __init__(self):
        url = helper.LoadConfig().domain + "/setting"
        super().__init__(label="웹패널", style=discord.ButtonStyle.link, url=url)

class SettingsSelect(Select):
    def __init__(self, serverId: str, interaction: Interaction):
        try:
            conn = sqlite3.connect(os.path.join(helper.LoadConfig().DBFolderPath, f"{serverId}.db"))
            cursor = conn.cursor()
            
            cursor.execute("SELECT loggingIp, loggingMail, webhookUrl, roleId, useCaptcha, blockVpn, loggingChannelId FROM Settings")
            settings = cursor.fetchone()
            
            log_channel_name = "설정되지 않음"
            if settings[6] is not None and str(settings[6]) != '0' and str(settings[6]) != '':
                try:
                    channel = interaction.guild.get_channel(int(settings[6]))
                    if channel is None:
                        log_channel_name = "설정되지 않음"
                    else:
                        log_channel_name = f"#{channel.name}"
                except:
                    log_channel_name = "설정되지 않음"
            
            role_name = "설정되지 않음"
            if settings[3]:
                try:
                    role = interaction.guild.get_role(int(settings[3]))
                    if role is None:
                        role_name = "설정되지 않음"
                    else:
                        role_name = f"@{role.name}"
                except:
                    role_name = "설정되지 않음"
            
            conn.close()
            
            mainDbPath = os.path.join(helper.LoadConfig().DBPath)
            mainConn = sqlite3.connect(mainDbPath)
            mainCursor = mainConn.cursor()
            
            mainCursor.execute("""
                SELECT customLink FROM ServerCustomLinks WHERE serverId = ?
            """, [serverId])
            
            linkInfo = mainCursor.fetchone()
            mainConn.close()
            
            link_status = "설정됨" if linkInfo else "설정되지 않음"
            
            options = [
                SelectOption(
                    label="🌐 IP 기록 여부",
                    value="아이피 기록",
                    description=f"{'활성화' if settings[0] == 1 else '비활성화'}"
                ),
                SelectOption(
                    label="📧 이메일 기록 여부",
                    value="이메일 기록",
                    description=f"{'활성화' if settings[1] == 1 else '비활성화'}"
                ),
                SelectOption(
                    label="📝 로그 채널 설정",
                    value="로그 채널",
                    description=f"{log_channel_name}"
                ),
                SelectOption(
                    label="👑 인증 역할 설정",
                    value="인증 역할",
                    description=f"{role_name}"
                ),
                SelectOption(
                    label="🔒 캡차 사용 여부",
                    value="캡차",
                    description=f"{'활성화' if settings[4] == 1 else '비활성화'}"
                ),
                SelectOption(
                    label="🛡️ VPN 차단 설정",
                    value="vpn차단",
                    description=f"{'활성화' if settings[5] == 1 else '비활성화'}"
                ),
                SelectOption(
                    label="🔗 고유 링크 설정",
                    value="고유 링크",
                    description=f"{link_status}"
                )
            ]
        except Exception as e:
            options = [
                SelectOption(
                    label="🌐 IP 기록 여부",
                    value="아이피 기록",
                    description="설정을 불러올 수 없습니다"
                ),
                SelectOption(
                    label="📧 이메일 기록 여부",
                    value="이메일 기록",
                    description="설정을 불러올 수 없습니다"
                ),
                SelectOption(
                    label="📝 로그 채널 설정",
                    value="로그 채널",
                    description="설정을 불러올 수 없습니다"
                ),
                SelectOption(
                    label="👑 인증 역할 설정",
                    value="인증 역할",
                    description="설정을 불러올 수 없습니다"
                ),
                SelectOption(
                    label="🔒 캡차 사용 여부",
                    value="캡차",
                    description="설정을 불러올 수 없습니다"
                ),
                SelectOption(
                    label="🛡️ VPN 차단 설정",
                    value="vpn차단",
                    description="설정을 불러올 수 없습니다"
                ),
                SelectOption(
                    label="🔗 고유 링크 설정",
                    value="고유 링크",
                    description="설정을 불러올 수 없습니다"
                )
            ]
        
        super().__init__(placeholder="⚙️ 서버 설정", options=options)

    async def callback(self, interaction: Interaction):
        selected = interaction.data['values'][0]
        if selected == "아이피 기록":
            view = OnOffView(interaction.guild_id, selected)
            await interaction.response.edit_message(view=view)
        elif selected == "이메일 기록":
            view = OnOffView(interaction.guild_id, selected)
            await interaction.response.edit_message(view=view)
        elif selected == "로그 채널":
            view = ChannelView(interaction.guild_id)
            await interaction.response.edit_message(view=view)
        elif selected == "인증 역할":
            view = RoleView(interaction.guild_id)
            await interaction.response.edit_message(view=view)
        elif selected == "캡차":
            view = OnOffView(interaction.guild_id, selected)
            await interaction.response.edit_message(view=view)
        elif selected == "vpn차단":
            view = OnOffView(interaction.guild_id, selected)
            await interaction.response.edit_message(view=view)
        elif selected == "고유 링크":
            view = CustomLinkView(interaction.guild_id)
            await interaction.response.edit_message(view=view)

class OnOffView(View):
    def __init__(self, serverId: str, selected):
        super().__init__(timeout=None)
        self.add_item(OnOffSelect(serverId, selected))

class OnOffSelect(Select):
    def __init__(self, serverId: str, selected):
        self.serverId = serverId
        self.selected = selected
        options = [
            SelectOption(label=f"{selected} 활성화", value="on", description=f"{selected}을 활성화합니다."),
            SelectOption(label=f"{selected} 비활성화", value="off", description=f"{selected}을 비활성화합니다."),
            SelectOption(label="뒤로 가기", value="back", description="이전으로 돌아갑니다.")
        ]
        super().__init__(placeholder="ON/OFF 설정", options=options)

    async def callback(self, interaction: Interaction):
        try:
            onOff = interaction.data['values'][0]
            values = {
                "아이피 기록" : "loggingIp",
                "이메일 기록" : "loggingMail",
                "캡차" : "useCaptcha",
                "vpn차단" : "blockVpn"
            }
            if onOff == "on":
                settings = values.get(self.selected)
                helper.UpdateServerSettings(self.serverId, settings, True)
                view = SettingsView(self.serverId, interaction)
                await interaction.response.edit_message(view=view)
                
                await helper.SendEmbed(
                    interaction=interaction, 
                    title="✅ 설정 완료", 
                    description=f"**{self.selected}**을 **활성화**했습니다.", 
                    color=Color.green()
                )
            elif onOff == "off":
                settings = values.get(self.selected)
                helper.UpdateServerSettings(self.serverId, settings, False)
                view = SettingsView(self.serverId, interaction)
                await interaction.response.edit_message(view=view)
                
                await helper.SendEmbed(
                    interaction=interaction, 
                    title="✅ 설정 완료", 
                    description=f"**{self.selected}**을 **비활성화**했습니다.", 
                    color=Color.green()
                )
            elif onOff == "back":
                view = SettingsView(self.serverId, interaction)
                await interaction.response.edit_message(view=view)
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class RoleView(View):
    def __init__(self, serverId: str):
        self.serverId = serverId
        super().__init__(timeout=None)
        self.add_item(VRoleSelect(serverId))
        self.add_item(BackToSettingsButton(serverId))

class VRoleSelect(RoleSelect):
    def __init__(self, serverId: str):
        self.serverId = serverId
        super().__init__(placeholder="인증 역할 설정")

    async def callback(self, interaction: Interaction):
        try:
            roleId = interaction.data['values'][0]
            helper.UpdateServerSettings(self.serverId, "roleId", roleId)
            role = interaction.guild.get_role(int(roleId))
            view = SettingsView(self.serverId, interaction)
            await interaction.response.edit_message(view=view)
            
            await helper.SendEmbed(
                interaction=interaction, 
                title="✅ 설정 완료", 
                description=f"인증 역할을 **{role.name}**({role.mention})으로 설정했습니다.", 
                color=Color.green()
            )
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class ChannelView(View):
    def __init__(self, serverId: str):
        self.serverId = serverId
        super().__init__(timeout=None)
        self.add_item(SChannelSelect(serverId))
        self.add_item(BackToSettingsButton(serverId))

class SChannelSelect(ChannelSelect):
    def __init__(self, serverId: str):
        self.serverId = serverId
        super().__init__(placeholder="로그 채널 설정")

    async def callback(self, interaction: Interaction):
        try:
            channelId = str(interaction.data['values'][0])
            channel = interaction.guild.get_channel(int(channelId))
            
            avatarBytes = await helper.FetchBytesFromUrl("https://cdn.discordapp.com/icons/1337624999380521030/c9d449b5f7d72d82cfc68e3d5e080820.webp?size=1024&format=webp&width=640&height=640")
            webhook = await channel.create_webhook(
                name="RestoreBot",
                avatar=avatarBytes
            )
            webhookUrl = webhook.url
            logWebhook = SyncWebhook.from_url(webhookUrl)
            
            helper.UpdateServerSettings(self.serverId, "loggingChannelId", str(channelId))
            helper.UpdateServerSettings(self.serverId, "webhookUrl", str(webhookUrl))
            
            view = SettingsView(self.serverId, interaction)
            await interaction.response.edit_message(view=view)
            
            await helper.SendEmbed(
                interaction=interaction, 
                title="✅ 설정 완료", 
                description=f"로그 채널을 **{channel.name}**({channel.mention})으로 설정했습니다.", 
                color=Color.green()
            )
            
            embed = Embed(
                title="✅ 설정 완료", 
                description=f"로그 채널이 **{channel.name}**({channel.mention})으로 설정되었습니다.", 
                color=Color.green(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            )
            logWebhook.send(embed=embed)
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class BackToSettingsButton(Button):
    def __init__(self, serverId: str):
        self.serverId = serverId
        super().__init__(label="뒤로 가기", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: Interaction):
        view = SettingsView(self.serverId, interaction)
        await interaction.response.edit_message(view=view)

class CustomLinkView(View):
    def __init__(self, serverId: str):
        super().__init__(timeout=None)
        self.serverId = serverId
        self.add_item(LinkSettingButton(serverId))
        self.add_item(BackToSettingsButton(serverId))

class LinkSettingButton(Button):
    def __init__(self, serverId: str):
        self.serverId = serverId
        super().__init__(label="고유 링크 설정", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: Interaction):
        modal = CustomLinkInput(self.serverId)
        await interaction.response.send_modal(modal)

class CustomLinkInput(discord.ui.Modal, title="고유 링크 설정"):
    def __init__(self, serverId: str):
        super().__init__()
        self.serverId = serverId
        
        try:
            mainDbPath = os.path.join(helper.LoadConfig().DBPath)
            conn = sqlite3.connect(mainDbPath)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT customLink FROM ServerCustomLinks WHERE serverId = ?
            """, [serverId])
            
            linkInfo = cursor.fetchone()
            conn.close()
            
            current_link = linkInfo[0] if linkInfo else ""
        except:
            current_link = ""
        
        self.customLink = discord.ui.TextInput(
            label="고유 링크", 
            placeholder="영문, 숫자, 하이픈, 언더스코어만 사용 가능합니다. (3~30자)",
            min_length=3,
            max_length=30,
            default=current_link
        )
        
        self.add_item(self.customLink)

    async def on_submit(self, interaction: Interaction):
        try:
            customLink = self.customLink.value.strip()
            
            if not customLink:
                await helper.ErrorEmbed(interaction, "고유 링크를 입력해주세요.")
                return
                
            if not re.match(r'^[a-zA-Z0-9\-_]+$', customLink):
                await helper.ErrorEmbed(interaction, "링크는 영문, 숫자, 하이픈, 언더스코어만 사용 가능합니다.")
                return
            
            mainDbPath = os.path.join(helper.LoadConfig().DBPath)
            conn = sqlite3.connect(mainDbPath)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT customLink FROM ServerCustomLinks 
                WHERE customLink = ? AND serverId != ?
            """, [customLink, self.serverId])
            
            existingLink = cursor.fetchone()
            if existingLink:
                conn.close()
                await helper.ErrorEmbed(interaction, "이미 사용 중인 링크입니다.")
                return
            
            cursor.execute("""
                SELECT customLink FROM ServerCustomLinks 
                WHERE serverId = ?
            """, [self.serverId])
            
            myLink = cursor.fetchone()
            
            if myLink:
                cursor.execute("""
                    UPDATE ServerCustomLinks 
                    SET customLink = ?, updatedAt = datetime('now') 
                    WHERE serverId = ?
                """, [customLink, self.serverId])
            else:
                cursor.execute("""
                    INSERT INTO ServerCustomLinks 
                    (serverId, customLink, createdAt, visitCount) 
                    VALUES (?, ?, datetime('now'), 0)
                """, [self.serverId, customLink])
            
            conn.commit()
            conn.close()
            
            domain = helper.LoadConfig().domain
            fullUrl = f"{domain}/j/{customLink}"
            
            await helper.SendEmbed(
                interaction=interaction, 
                title="✅ 고유 링크 설정 완료", 
                description=f"고유 링크가 **{customLink}**로 설정되었습니다.\n**링크:** `{fullUrl}`", 
                color=Color.green()
            )
            
            if not interaction.response.is_done():
                view = SettingsView(self.serverId, interaction)
                await interaction.response.edit_message(view=view)
            else:
                view = SettingsView(self.serverId, interaction)
                await interaction.message.edit(view=view)
            
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

#V1.5