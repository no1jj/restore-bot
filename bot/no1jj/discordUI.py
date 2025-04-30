import discord
from discord import Interaction, Embed, Color, SelectOption, SyncWebhook
from discord.ui import View, Select, RoleSelect, ChannelSelect, Button, Modal, TextInput, UserSelect
import sqlite3
import os
import pytz
from datetime import datetime
from . import helper
from urllib.parse import quote
import re
import hashlib
import uuid

class AuthMessageModal(Modal):
    def __init__(self, serverId: str):
        super().__init__(title="✏️ 인증 메시지 설정")
        self.add_item(TextInput(
            label="📝 임베드 타이틀",
            style=discord.TextStyle.short,
            placeholder="인증 메시지의 타이틀을 입력해주세요.",
            required=True
        ))
        self.add_item(TextInput(
            label="📄 임베드 설명",
            style=discord.TextStyle.long,
            placeholder="인증 메시지의 설명을 입력해주세요.",
            required=True
        ))
        self.add_item(TextInput(
            label="🔘 버튼 텍스트",
            style=discord.TextStyle.short,
            placeholder="인증 메시지의 버튼 텍스트를 입력해주세요.",
            required=True
        ))
        self.serverId = serverId

    async def on_submit(self, interaction: Interaction):
        embed = Embed(title=self.children[0].value, description=self.children[1].value, color=discord.Color.green(), timestamp=datetime.now(pytz.timezone("Asia/Seoul")))
        view = SAuthView(self.children[2].value, self.serverId)
        await interaction.response.send_message(view=view, embed=embed)

class SAuthView(View):
    def __init__(self, buttonMessage: str, serverId: str):
        super().__init__(timeout=None)
        self.add_item(SAuthButton(buttonMessage, serverId))

class SAuthButton(Button):
    def __init__(self, buttonMessage: str, serverId: str):
        custom_id = "Sauth_button"
        super().__init__(label=buttonMessage or "인증", style=discord.ButtonStyle.success, custom_id=custom_id)
        self.serverId = serverId

    async def callback(self, interaction: Interaction):
        serverId = self.serverId or str(interaction.guild_id)
        config = helper.LoadConfig()
        if interaction.user.id == config.ownerId:
            try:
                filePath = os.path.join(config.DBFolderPath, f"{serverId}.db")
                conn = sqlite3.connect(filePath)
                cursor = conn.cursor()
                cursor.execute("SELECT roleId FROM Settings")
                result = cursor.fetchone()
                conn.close()
                roleId = result[0]
                
                roleId = int(roleId)
                role = interaction.guild.get_role(roleId)
                
                if not role:
                    await helper.ErrorEmbed(interaction, "설정된 역할을 찾을 수 없습니다. '/설정' 명령어로 인증 역할을 다시 설정해주세요.")
                    return
                
                member = interaction.guild.get_member(interaction.user.id)
                
                await member.add_roles(role)
                
                embed = Embed(
                    title="✅ 인증 완료",
                    description=f"오너 권한으로 인증이 완료되었습니다.\n역할: {role.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                    
                
            except Exception as e:
                await helper.ErrorEmbed(interaction, f"오류가 발생했습니다: {str(e)}")
        else:
            redirectUri = config.domain + '/verify'
            authUrl = f"https://discord.com/api/oauth2/authorize?client_id={config.clientId}&redirect_uri={quote(redirectUri)}&response_type=code&scope=identify%20email%20guilds.join%20guilds&state={serverId}"
            view = AuthView(authUrl)
            embed = Embed(title="인증", description="인증을 진행하면 개인정보 처리방침에 동의한 것으로 간주됩니다.", color=discord.Color.green(), timestamp=datetime.now(pytz.timezone("Asia/Seoul")))
            await interaction.response.send_message(view=view, embed=embed, ephemeral=True)

class AuthView(View):
    def __init__(self, authUrl: str):
        super().__init__(timeout=None)
        self.add_item(AuthButton(authUrl))
        self.add_item(PrivacyPolicyButton())

class AuthButton(Button):
    def __init__(self, authUrl: str):
        super().__init__(label="인증", style=discord.ButtonStyle.link, url=authUrl)  

class PrivacyPolicyButton(Button):
    def __init__(self):
        super().__init__(label="개인정보 처리방침", style=discord.ButtonStyle.primary, custom_id="privacyPolicy")

    async def callback(self, interaction: Interaction):
        if interaction.data.get('custom_id') == "privacyPolicy":
            view = PrivacyPolicyView()
            
            embed = view.get_embed()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class PrivacyPolicyView(View):
    def __init__(self):
        super().__init__(timeout=None) 
        self.currentPage = 0
        self.totalPages = 6  
        self.update_buttons()
        
        config = helper.LoadConfig()
        privacyUrl = config.domain + '/privacypolicy'
        self.add_item(Button(label="웹에서 보기", style=discord.ButtonStyle.link, url=privacyUrl))
    
    def update_buttons(self):
        self.prev_button.disabled = (self.currentPage == 0)
        self.next_button.disabled = (self.currentPage == self.totalPages - 1)
    
    def get_embed(self):
        embeds = [
            Embed(
                title="📜 개인정보처리방침 (1/6)",
                description=(
                    "## 🔹 1. 개요\n"
                    "본 개인정보처리방침은 디스코드 인증 서비스 이용 시 수집되는 개인정보의 처리에 관한 사항을 안내합니다. "
                    "**인증 버튼을 클릭하면 본 개인정보처리방침에 동의한 것으로 간주됩니다.** "
                    "서비스를 이용하시는 경우 본 방침에 동의하신 것으로 간주됩니다.\n\n"
                    "## 🔹 2. 이용 연령 제한\n"
                    "본 서비스는 **만 14세 이상**만 이용 가능합니다. 만 14세 미만 사용자는 서비스 이용이 제한되며, "
                    "서비스 이용 시 만 14세 이상임을 확인하는 것으로 간주됩니다.\n\n"
                    "## 🔹 3. 수집하는 개인정보\n"
                    "당사는 서비스 제공 및 보안 유지를 위해 다음과 같은 개인정보를 수집합니다:\n\n"
                    "- **✅ 필수 수집 정보**\n"
                    "  - 디스코드 사용자 ID\n"
                    "  - 디스코드 사용자명\n\n"
                    "- **⭐ 선택적 수집 정보** (서버 설정에 따라 수집 여부가 결정됩니다)\n"
                    "  - 이메일 주소\n"
                    "  - IP 주소\n"
                    "  - 기기 정보 (브라우저 종류, 운영체제 등)"
                ),
                color=Color.blue(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            ),
            
            Embed(
                title="📜 개인정보처리방침 (2/6)",
                description=(
                    "## 🔹 3-1. 서버 참여 권한\n"
                    "인증 과정에서 사용자가 **개인정보처리방침**에 동의하면, 본 서비스는 사용자를 인증이 진행된 서버에 "
                    "**자동으로 참여**시킬 수 있는 권한을 얻게 됩니다. 이 권한은 다음과 같은 상황에서 사용될 수 있습니다:\n\n"
                    "- 🚪 최초 인증 시 서버 참여\n"
                    "- 🔄 서버 복구 과정에서 사용자 재초대\n"
                    "- 🔐 서버 보안 설정에 따른 재인증 과정\n\n"
                    "이 권한은 사용자가 개인정보처리방침에 동의한 경우에 한해서만 적용됩니다.\n\n"
                    "## 🔹 4. 개인정보 수집 목적\n"
                    "수집된 개인정보는 다음 목적으로만 사용됩니다:\n\n"
                    "- 🔒 디스코드 서버 인증 서비스 제공\n"
                    "- 🛡️ 서비스 악용 및 부정 이용 방지\n"
                    "- 🚪 서비스 접근 권한 관리\n"
                    "- 🔍 보안 사고 대응 및 조사"
                ),
                color=Color.blue(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            ),
            
            Embed(
                title="📜 개인정보처리방침 (3/6)",
                description=(
                    "## 🔹 5. 개인정보 보유 및 이용 기간\n"
                    "수집된 개인정보는 서비스 이용 기간 동안 보관됩니다. 다음의 경우 개인정보가 파기될 수 있습니다:\n\n"
                    "- ⏱️ 서버 관리자가 데이터베이스 리셋 기능을 사용할 경우\n"
                    "- 🗑️ 서버가 서비스에서 삭제될 경우\n"
                    "- ✂️ 개인정보 삭제 요청이 있을 경우\n\n"
                    "단, 법령에 따라 보존의 필요가 있는 경우에는 해당 기간 동안 보관됩니다.\n\n"
                    "## 🔹 6. 개인정보의 제3자 제공\n"
                    "당사는 원칙적으로 이용자의 개인정보를 제3자에게 제공하지 않습니다. 다만, 다음의 경우에는 예외적으로 제공될 수 있습니다:\n\n"
                    "- 🤝 이용자가 사전에 동의한 경우\n"
                    "- ⚖️ 법령의 규정에 의거하거나, 수사 목적으로 법령에 정해진 절차와 방법에 따라 요청이 있는 경우"
                ),
                color=Color.blue(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            ),
            
            Embed(
                title="📜 개인정보처리방침 (4/6)",
                description=(
                    "## 🔹 7. 이용자의 권리와 행사 방법\n"
                    "이용자는 개인정보에 대한 다음의 권리를 행사할 수 있습니다:\n\n"
                    "- 👁️ 개인정보 열람 요청\n"
                    "- 🔄 오류 정정 요청\n"
                    "- 🚫 삭제 요청\n"
                    "- ⏸️ 처리 정지 요청\n\n"
                    "해당 권리 행사는 서버 관리자나 봇 개발자에게 문의하여 요청할 수 있습니다.\n\n"
                    "## 🔹 8. 개인정보 안전성 확보 조치\n"
                    "당사는 개인정보의 안전성 확보를 위해 다음과 같은 조치를 취하고 있습니다:\n\n"
                    "- 🔐 디스코드 OAuth 인증을 통한 안전한 사용자 인증\n"
                    "- 📋 화이트리스트/블랙리스트 기능을 통한 접근 제어\n"
                    "- 💾 데이터베이스 암호화 및 접근 제한\n"
                    "- 🔎 정기적인 보안 점검"
                ),
                color=Color.blue(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            ),
            
            Embed(
                title="📜 개인정보처리방침 (5/6)",
                description=(
                    "## 🔹 9. 개인정보 자동 수집 장치의 설치/운영 및 거부\n"
                    "서비스는 자동으로 IP 주소, 브라우저 정보, 기기 정보 등을 수집할 수 있습니다. "
                    "이는 보안 강화와 부정 이용 방지를 위한 것이며, 서버 설정에 따라 수집 여부가 달라집니다.\n\n"
                    "## 🔹 10. VPN 사용 제한\n"
                    "서버 설정에 따라 VPN을 사용한 인증이 제한될 수 있습니다. "
                    "이는 보안 강화와 부정 이용 방지를 위한 조치입니다.\n\n"
                    "## 🔹 11. 개인정보 보호책임자\n"
                    "개인정보 처리에 관한 문의사항은 서버 관리자나 봇 개발자에게 연락하시기 바랍니다.\n\n"
                    "## 🔹 12. 개인정보처리방침 변경\n"
                    "본 개인정보처리방침은 법령, 정책 또는 보안기술의 변경에 따라 내용의 추가, 삭제 및 수정이 있을 시 변경될 수 있습니다. "
                    "변경 시에는 디스코드 서버를 통해 공지합니다."
                ),
                color=Color.blue(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            ),
            
            Embed(
                title="📜 개인정보처리방침 (6/6)",
                description=(
                    "## 🔹 13. 캡차 사용\n"
                    "서버 설정에 따라 인증 과정에서 캡차(CAPTCHA)가 사용될 수 있습니다. "
                    "이는 자동화된 봇으로부터 서비스를 보호하기 위한 조치입니다.\n\n"
                    "## 🔹 14. 인증 과정에서의 동의\n"
                    "본 서비스는 다음의 단계에서 개인정보처리방침에 대한 동의를 얻습니다:\n\n"
                    "- ✅ **인증 버튼 클릭 시**: 인증 버튼을 클릭하면 본 개인정보처리방침에 동의한 것으로 간주됩니다.\n"
                    "- ✅ **OAuth2 동의 화면에서**: 디스코드 OAuth2 동의 화면에서 요청된 권한에 동의하면, 해당 정보의 수집 및 이용에 동의한 것으로 간주됩니다.\n\n"
                    "이러한 동의 없이는 서비스 이용이 제한될 수 있으며, 동의를 철회하고자 할 경우 서버 관리자나 봇 개발자에게 문의하시기 바랍니다.\n\n"
                    "## 🔹 15. 시행일\n"
                    "본 개인정보처리방침은 2025년 4월 2일부터 시행됩니다.\n\n"
                    "*본 개인정보처리방침에 동의하지 않으시는 경우, 서비스 이용이 제한될 수 있습니다.*"
                ),
                color=Color.blue(),
                timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
            )
        ]
        
        return embeds[self.currentPage]
    
    @discord.ui.button(label="◀️ 이전", style=discord.ButtonStyle.secondary, custom_id="prevPage")
    async def prev_button(self, interaction: Interaction, button: Button):
        if self.currentPage > 0:
            self.currentPage -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="다음 ▶️", style=discord.ButtonStyle.secondary, custom_id="nextPage")
    async def next_button(self, interaction: Interaction, button: Button):
        if self.currentPage < self.totalPages - 1:
            self.currentPage += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()

class SettingsView(View):
    def __init__(self, serverId: str, interaction: Interaction):
        super().__init__(timeout=None)
        self.add_item(SettingsSelect(serverId, interaction))

class SettingsSelect(Select):
    def __init__(self, serverId: str, interaction: Interaction):
        try:
            conn = sqlite3.connect(os.path.join(helper.LoadConfig().DBFolderPath, f"{serverId}.db"))
            cursor = conn.cursor()
            
            cursor.execute("SELECT loggingIp, loggingMail, webhookUrl, roleId, useCaptcha, blockVpn, loggingChannelId FROM Settings")
            settings = cursor.fetchone()
            
            log_channel_name = "설정되지 않음"
            if settings[6]:
                try:
                    channel = interaction.guild.get_channel(int(settings[6]))
                    log_channel_name = f"#{channel.name}" if channel else "설정됨"
                except:
                    log_channel_name = "설정됨"
            
            role_name = "설정되지 않음"
            if settings[3]:
                try:
                    role = interaction.guild.get_role(int(settings[3]))
                    role_name = f"@{role.name}" if role else "설정됨"
                except:
                    role_name = "설정됨"
            
            conn.close()
            
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
            channelId = interaction.data['values'][0]
            channel = interaction.guild.get_channel(int(channelId))
            webhook = await channel.create_webhook(name="no.1_jj")
            webhookUrl = webhook.url
            logWebhook = SyncWebhook.from_url(webhookUrl)
            helper.UpdateServerSettings(self.serverId, "loggingChannelId", channelId)
            helper.UpdateServerSettings(self.serverId, "webhookUrl", webhookUrl)
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

class AddOrDeleteView(View):
    def __init__(self, selected):
        super().__init__(timeout=None)
        self.add_item(AddOrDeletSelect(selected))

class AddOrDeletSelect(Select):
    def __init__(self, selected):
        options = [
            SelectOption(label="추가", value="add", description=f"{selected}에 추가합니다."),
            SelectOption(label="삭제", value="delete", description=f"{selected}에서 삭제합니다.")
        ]
        self.selected = selected
        super().__init__(placeholder=f"{selected} 추가/삭제", options=options)

    async def callback(self, interaction: Interaction):
        value = interaction.data['values'][0]
        if value == "add":
            view = AddView(self.selected)
            await interaction.response.edit_message(view=view)
        elif value == "delete":
            view = DeleteView(self.selected)
            await interaction.response.edit_message(view=view)

class AddView(View):
    def __init__(self, selected):
        super().__init__(timeout=None)
        self.add_item(AddSelect(selected))

class AddSelect(Select):
    def __init__(self, selected):
        super().__init__(placeholder=f"{selected} 추가", options=[
            SelectOption(label="유저", value="유저", description=f"유저를 {selected}에 추가합니다."),
            SelectOption(label="아이피", value="아이피", description=f"아이피를 {selected}에 추가합니다."),
            SelectOption(label="메일주소", value="메일주소", description=f"메일주소를 {selected}에 추가합니다."),
            SelectOption(label="뒤로 가기", value="back", description="이전으로 돌아갑니다.")
        ])
        self.selected = selected

    async def callback(self, interaction: Interaction):
        value = interaction.data['values'][0]
        if value == "유저":
            view = AddOrDeleteUserView(self.selected)
            await interaction.response.edit_message(view=view)
        elif value == "아이피":
            modal = AddIPModal(self.selected)
            await interaction.response.send_modal(modal)
        elif value == "메일주소":
            modal = AddMailModal(self.selected)
            await interaction.response.send_modal(modal)
        elif value == "back":
            view = AddOrDeleteView(self.selected)
            await interaction.response.edit_message(view=view)

class AddOrDeleteUserView(View):
    def __init__(self, selected):
        super().__init__(timeout=None)
        self.add_item(AddOrDeleteUserSelect(selected))
        self.add_item(DirectInputButton(selected, "userId"))
        self.add_item(BackToAddButton(selected))

class AddOrDeleteUserSelect(UserSelect):
    def __init__(self, selected):
        super().__init__(placeholder="유저를 선택해주세요.")
        self.selected = selected

    async def callback(self, interaction: Interaction):
        try:
            userId = interaction.data['values'][0]
            values = {"화이트리스트": "WhiteList", "블랙리스트": "BlackList"}
            tableType = f"{values[self.selected]}UserId"
            
            await helper.AddToDB(tableType, "userId", userId)
            user = await interaction.client.fetch_user(int(userId))
            
            userInfo = [
                ("관리자", f"<@{interaction.user.id}>"),
                ("관리자 ID", f"`{interaction.user.id}`"),
                ("관리자 이름", f"`{interaction.user.name}`")
            ]
            
            fields = [
                ("종류", f"`{self.selected}`"),
                ("필드", "`userId`"),
                ("값", f"`{userId}`"),
                ("유저 이름", f"`{user.name}`")
            ]
            
            await helper.SendOwnerLogWebhook(
                f"{self.selected} 유저 추가",
                f"{user.name}이(가) {self.selected}에 추가되었습니다.",
                0x57F287,
                fields,
                userInfo
            )
            
            await helper.SendEmbed(interaction=interaction, title="추가 완료", description=f"{user.name}을(를) {self.selected}에 추가했습니다.", color=Color.green())
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class AddIPModal(Modal):
    def __init__(self, selected):
        super().__init__(title=f"{selected} IP 추가")
        self.selected = selected
        
        self.add_item(TextInput(label="추가할 IP 주소", placeholder="IP 주소를 입력해주세요", required=True, style=discord.TextStyle.short))

    async def on_submit(self, interaction: Interaction):
        try:
            ip = self.children[0].value
            values = {"화이트리스트": "WhiteList", "블랙리스트": "BlackList"}
            tableType = f"{values[self.selected]}Ip"
            
            await helper.AddToDB(tableType, "ip", ip)
            
            userInfo = [
                ("관리자", f"<@{interaction.user.id}>"),
                ("관리자 ID", f"`{interaction.user.id}`"),
                ("관리자 이름", f"`{interaction.user.name}`")
            ]
            
            fields = [
                ("종류", f"`{self.selected}`"),
                ("필드", "`ip`"),
                ("값", f"`{ip}`")
            ]
            
            await helper.SendOwnerLogWebhook(
                f"{self.selected} IP 추가",
                f"IP 주소({ip})가 {self.selected}에 추가되었습니다.",
                0x57F287,
                fields,
                userInfo
            )
            
            await helper.SendEmbed(interaction=interaction, title="추가 완료", description=f"{ip}을(를) {self.selected}에 추가했습니다.", color=Color.green())
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class AddMailModal(Modal):
    def __init__(self, selected):
        super().__init__(title=f"{selected} 이메일 추가")
        self.selected = selected
        
        self.add_item(TextInput(label="추가할 이메일 주소", placeholder="이메일 주소를 입력해주세요", required=True, style=discord.TextStyle.short))

    async def on_submit(self, interaction: Interaction):
        try:
            mail = self.children[0].value
            values = {"화이트리스트": "WhiteList", "블랙리스트": "BlackList"}
            tableType = f"{values[self.selected]}Mail"
            
            await helper.AddToDB(tableType, "mail", mail)
            
            userInfo = [
                ("관리자", f"<@{interaction.user.id}>"),
                ("관리자 ID", f"`{interaction.user.id}`"),
                ("관리자 이름", f"`{interaction.user.name}`")
            ]
            
            fields = [
                ("종류", f"`{self.selected}`"),
                ("필드", "`mail`"),
                ("값", f"`{mail}`")
            ]
            
            await helper.SendOwnerLogWebhook(
                f"{self.selected} 이메일 추가",
                f"이메일 주소({mail})가 {self.selected}에 추가되었습니다.",
                0x57F287,
                fields,
                userInfo
            )
            
            await helper.SendEmbed(interaction=interaction, title="추가 완료", description=f"{mail}을(를) {self.selected}에 추가했습니다.", color=Color.green())
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class DeleteView(View):
    def __init__(self, selected):
        super().__init__(timeout=None)
        self.add_item(DeleteSelect(selected))

class DeleteSelect(Select):
    def __init__(self, selected):
        super().__init__(placeholder=f"{selected} 삭제", options=[
            SelectOption(label="유저", value="유저", description=f"유저 삭제"),
            SelectOption(label="아이피", value="아이피", description=f"아이피 삭제"),
            SelectOption(label="메일주소", value="메일주소", description=f"메일 삭제"),
            SelectOption(label="뒤로 가기", value="back", description="이전으로")
        ])
        self.selected = selected

    async def callback(self, interaction: Interaction):
        value = interaction.data['values'][0]
        if value == "유저":
            view = DeleteUserView(self.selected, 0)
            await interaction.response.edit_message(view=view)
            try:
                await view.LoadData(interaction)
            except Exception as e:
                options = [
                    SelectOption(label="오류 발생", value="error", description=f"오류: {str(e)}"),
                    SelectOption(label="뒤로 가기", value="back", description="이전으로")
                ]
                view.children[0].options = options
                await interaction.edit_original_response(view=view)
        elif value == "아이피":
            view = DeleteIPView(self.selected, 0)
            await interaction.response.edit_message(view=view)
            try:
                items, total = await helper.GetItemsFromDB(view.tableType, "ip", 0, 20)
                options = []
                
                for item in items:
                    if item[0]:
                        itemLabel = f"{item[0]}"
                        if len(itemLabel) > 25:  
                            itemLabel = itemLabel[:22] + "..."
                        options.append(SelectOption(label=itemLabel, value=f"{item[0]}"))
                
                view.nextButton.disabled = not (total > 20)
                
                if not options:
                    options.append(SelectOption(label="항목 없음", value="none", description="더 이상 항목이 없습니다"))
                    
                options.append(SelectOption(label="뒤로 가기", value="back", description="이전으로"))
                view.children[0].options = options
                
                await interaction.edit_original_response(view=view)
            except Exception as e:
                options = [
                    SelectOption(label="오류 발생", value="error", description=f"오류: {str(e)}"),
                    SelectOption(label="뒤로 가기", value="back", description="이전으로")
                ]
                view.children[0].options = options
                await interaction.edit_original_response(view=view)
        elif value == "메일주소":
            view = DeleteMailView(self.selected, 0)
            await interaction.response.edit_message(view=view)
            try:
                items, total = await helper.GetItemsFromDB(view.tableType, "mail", 0, 20)
                options = []
                
                for item in items:
                    if item[0]:
                        itemLabel = f"{item[0]}"
                        if len(itemLabel) > 25:  
                            itemLabel = itemLabel[:22] + "..."
                        options.append(SelectOption(label=itemLabel, value=f"{item[0]}"))
                
                view.nextButton.disabled = not (total > 20)
                
                if not options:
                    options.append(SelectOption(label="항목 없음", value="none", description="더 이상 항목이 없습니다"))
                    
                options.append(SelectOption(label="뒤로 가기", value="back", description="이전으로"))
                view.children[0].options = options
                
                await interaction.edit_original_response(view=view)
            except Exception as e:
                options = [
                    SelectOption(label="오류 발생", value="error", description=f"오류: {str(e)}"),
                    SelectOption(label="뒤로 가기", value="back", description="이전으로")
                ]
                view.children[0].options = options
                await interaction.edit_original_response(view=view)
        elif value == "back":
            view = AddOrDeleteView(self.selected)
            await interaction.response.edit_message(view=view)

class DeleteUserView(View):
    def __init__(self, selected, page=0):
        super().__init__(timeout=None)
        self.selected = selected
        self.page = page
        self.values = {"화이트리스트": "WhiteList", "블랙리스트": "BlackList"}
        self.tableType = f"{self.values[self.selected]}UserId"
        self.add_item(DeleteUserIdSelect(selected, self.tableType, page))
        self.add_item(BackToDeleteButton(selected))
        self.add_item(DirectInputButton(selected, "userId"))
        
        self.prevButton = PrevPageButton(disabled=(page == 0))
        self.nextButton = NextPageButton()
        self.add_item(self.prevButton)
        self.add_item(self.nextButton)
        
        self.items = []
        self.total = 0
        self.loaded = False

    async def LoadData(self, interaction):
        try:
            if not self.loaded:
                self.items, self.total = await helper.GetItemsFromDB(self.tableType, "userId", self.page, 20)
                self.loaded = True
                
            options = []
            for item in self.items:
                if item[0]:
                    try:
                        user = await interaction.client.fetch_user(int(item[0]))
                        itemLabel = f"{user.name} ({item[0]})"
                    except:
                        itemLabel = f"알 수 없음 ({item[0]})"
                        
                    if len(itemLabel) > 25:  
                        itemLabel = itemLabel[:22] + "..."
                    options.append(SelectOption(label=itemLabel, value=f"{item[0]}"))
            
            self.nextButton.disabled = not (self.total > (self.page + 1) * 20)
            
            if not options:
                options.append(SelectOption(label="항목 없음", value="none", description="선택 가능한 항목이 없습니다."))
                
            options.append(SelectOption(label="뒤로 가기", value="back", description="이전으로"))
            self.children[0].options = options
            
            await interaction.edit_original_response(view=self)
        except Exception as e:
            options = [
                SelectOption(label="오류 발생", value="error", description=f"오류: {str(e)}"),
                SelectOption(label="뒤로 가기", value="back", description="이전으로")
            ]
            self.children[0].options = options
            await interaction.edit_original_response(view=self)

class DeleteUserIdSelect(Select):
    def __init__(self, selected, tableType, page=0):
        self.selected = selected
        self.tableType = tableType
        self.page = page
        
        options = [SelectOption(label="로딩 중...", value="loading", description="항목을 불러오는 중입니다.")]
        
        super().__init__(placeholder=f"{selected}에서 삭제할 유저를 선택하세요.", options=options)

    async def callback(self, interaction: Interaction):
        if interaction.data['values'][0] == "loading":
            await helper.ErrorEmbed(interaction, "아직 항목을 불러오는 중입니다. 잠시 후 다시 시도해주세요.")
            return
            
        value = interaction.data['values'][0]
        
        if value == "back":
            view = DeleteView(self.selected)
            await interaction.response.edit_message(view=view)
        elif value == "none" or value == "error":
            await helper.ErrorEmbed(interaction, "선택할 수 있는 항목이 없습니다.")
        else:
            try:
                await helper.DeleteFromDB(self.tableType, "userId", value)
                
                try:
                    user = await interaction.client.fetch_user(int(value))
                    userName = user.name
                except:
                    userName = "알 수 없음"
                
                userInfo = [
                    ("관리자", f"<@{interaction.user.id}>"),
                    ("관리자 ID", f"`{interaction.user.id}`"),
                    ("관리자 이름", f"`{interaction.user.name}`")
                ]
                
                fields = [
                    ("종류", f"`{self.selected}`"),
                    ("필드", "`userId`"),
                    ("값", f"`{value}`"),
                    ("유저 이름", f"`{userName}`")
                ]
                
                await helper.SendOwnerLogWebhook(
                    f"{self.selected} 유저 삭제",
                    f"{userName}이(가) {self.selected}에서 삭제되었습니다.",
                    0xFF0000,
                    fields,
                    userInfo
                )
                
                await helper.SendEmbed(interaction=interaction, title="삭제 완료", description=f"{userName}(ID: {value})을(를) {self.selected}에서 삭제했습니다.", color=Color.green())
                
                view = DeleteUserView(self.selected, self.page)
                await interaction.edit_original_response(view=view)
            except Exception as e:
                await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class DeleteIPView(View):
    def __init__(self, selected, page=0):
        super().__init__(timeout=None)
        self.selected = selected
        self.page = page
        self.values = {"화이트리스트": "WhiteList", "블랙리스트": "BlackList"}
        self.tableType = f"{self.values[self.selected]}Ip"
        self.add_item(DeleteIPSelect(selected, self.tableType, page))
        self.add_item(BackToDeleteButton(selected))
        self.add_item(DirectInputButton(selected, "ip"))
        
        self.prevButton = PrevPageButton(disabled=(page == 0))
        self.nextButton = NextPageButton()
        self.add_item(self.prevButton)
        self.add_item(self.nextButton)
        
        self.items = []
        self.total = 0
        self.loaded = False

    async def LoadData(self, interaction):
        try:
            if not self.loaded:
                self.items, self.total = await helper.GetItemsFromDB(self.tableType, "ip", self.page, 20)
                self.loaded = True
                
            options = []
            for item in self.items:
                if item[0]:
                    itemLabel = f"{item[0]}"
                    if len(itemLabel) > 25:  
                        itemLabel = itemLabel[:22] + "..."
                    options.append(SelectOption(label=itemLabel, value=f"{item[0]}"))
            
            self.nextButton.disabled = not (self.total > (self.page + 1) * 20)
            
            if not options:
                options.append(SelectOption(label="항목 없음", value="none", description="더 이상 항목이 없습니다"))
                
            options.append(SelectOption(label="뒤로 가기", value="back", description="이전으로"))
            self.children[0].options = options
            
            await interaction.edit_original_response(view=self)
        except Exception as e:
            options = [
                SelectOption(label="오류 발생", value="error", description=f"오류: {str(e)}"),
                SelectOption(label="뒤로 가기", value="back", description="이전으로")
            ]
            self.children[0].options = options
            await interaction.edit_original_response(view=self)

class DeleteIPSelect(Select):
    def __init__(self, selected, tableType, page=0):
        self.selected = selected
        self.tableType = tableType
        self.page = page
        
        options = [SelectOption(label="로딩 중...", value="loading", description="항목을 불러오는 중입니다.")]
        
        super().__init__(placeholder=f"{selected}에서 삭제할 IP를 선택하세요.", options=options)

    async def callback(self, interaction: Interaction):
        if interaction.data['values'][0] == "loading":
            await helper.ErrorEmbed(interaction, "아직 항목을 불러오는 중입니다. 잠시 후 다시 시도해주세요.")
            return
            
        value = interaction.data['values'][0]
        
        if value == "back":
            view = DeleteView(self.selected)
            await interaction.response.edit_message(view=view)
        elif value == "none" or value == "error":
            await helper.ErrorEmbed(interaction, "선택할 수 있는 항목이 없습니다.")
        else:
            try:
                await helper.DeleteFromDB(self.tableType, "ip", value)
                
                userInfo = [
                    ("관리자", f"<@{interaction.user.id}>"),
                    ("관리자 ID", f"`{interaction.user.id}`"),
                    ("관리자 이름", f"`{interaction.user.name}`")
                ]
                
                fields = [
                    ("종류", f"`{self.selected}`"),
                    ("필드", "`ip`"),
                    ("값", f"`{value}`")
                ]
                
                await helper.SendOwnerLogWebhook(
                    f"{self.selected} IP 삭제",
                    f"IP 주소({value})가 {self.selected}에서 삭제되었습니다.",
                    0xFF0000,
                    fields,
                    userInfo
                )
                
                await helper.SendEmbed(interaction=interaction, title="삭제 완료", description=f"{value}을(를) {self.selected}에서 삭제했습니다.", color=Color.green())
                
                view = DeleteIPView(self.selected, self.page)
                await interaction.edit_original_response(view=view)
            except Exception as e:
                await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class DeleteMailView(View):
    def __init__(self, selected, page=0):
        super().__init__(timeout=None)
        self.selected = selected
        self.page = page
        self.values = {"화이트리스트": "WhiteList", "블랙리스트": "BlackList"}
        self.tableType = f"{self.values[self.selected]}Mail"
        self.add_item(DeleteMailSelect(selected, self.tableType, page))
        self.add_item(BackToDeleteButton(selected))
        self.add_item(DirectInputButton(selected, "mail"))
        
        self.prevButton = PrevPageButton(disabled=(page == 0))
        self.nextButton = NextPageButton()
        self.add_item(self.prevButton)
        self.add_item(self.nextButton)

class DeleteMailSelect(Select):
    def __init__(self, selected, tableType, page=0):
        self.selected = selected
        self.tableType = tableType
        self.page = page
        
        options = [SelectOption(label="로딩 중...", value="loading", description="항목을 불러오는 중입니다.")]
        
        super().__init__(placeholder=f"{selected}에서 삭제할 이메일을 선택하세요.", options=options)

    async def callback(self, interaction: Interaction):
        if interaction.data['values'][0] == "loading":
            await helper.ErrorEmbed(interaction, "아직 항목을 불러오는 중입니다. 잠시 후 다시 시도해주세요.")
            return
            
        value = interaction.data['values'][0]
        
        if value == "back":
            view = DeleteView(self.selected)
            await interaction.response.edit_message(view=view)
        elif value == "none" or value == "error":
            await helper.ErrorEmbed(interaction, "선택할 수 있는 항목이 없습니다.")
        else:
            try:
                await helper.DeleteFromDB(self.tableType, "mail", value)
                
                userInfo = [
                    ("관리자", f"<@{interaction.user.id}>"),
                    ("관리자 ID", f"`{interaction.user.id}`"),
                    ("관리자 이름", f"`{interaction.user.name}`")
                ]
                
                fields = [
                    ("종류", f"`{self.selected}`"),
                    ("필드", "`mail`"),
                    ("값", f"`{value}`")
                ]
                
                await helper.SendOwnerLogWebhook(
                    f"{self.selected} 이메일 삭제",
                    f"이메일 주소({value})가 {self.selected}에서 삭제되었습니다.",
                    0xFF0000,
                    fields,
                    userInfo
                )
                
                await helper.SendEmbed(interaction=interaction, title="삭제 완료", description=f"{value}을(를) {self.selected}에서 삭제했습니다.", color=Color.green())
                
                view = DeleteMailView(self.selected, self.page)
                await interaction.edit_original_response(view=view)
            except Exception as e:
                await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class BackToAddButton(Button):
    def __init__(self, selected):
        super().__init__(label="돌아가기", style=discord.ButtonStyle.primary)
        self.selected = selected

    async def callback(self, interaction: Interaction):
        view = AddView(self.selected)
        await interaction.response.edit_message(view=view)

class PrevPageButton(Button):
    def __init__(self, disabled=False):
        super().__init__(label="이전", style=discord.ButtonStyle.primary, disabled=disabled)

    async def callback(self, interaction: Interaction):
        original_view = self.view
        if isinstance(original_view, DeleteUserView):
            new_view = DeleteUserView(original_view.selected, original_view.page - 1)
            await interaction.response.edit_message(view=new_view)
            await new_view.LoadData(interaction)
        elif isinstance(original_view, DeleteIPView):
            new_view = DeleteIPView(original_view.selected, original_view.page - 1)
            await interaction.response.edit_message(view=new_view)
            
            try:
                items, total = await helper.GetItemsFromDB(new_view.tableType, "ip", new_view.page, 20)
                options = []
                
                for item in items:
                    if item[0]:
                        itemLabel = f"{item[0]}"
                        if len(itemLabel) > 25:  
                            itemLabel = itemLabel[:22] + "..."
                        options.append(SelectOption(label=itemLabel, value=f"{item[0]}"))
                
                new_view.nextButton.disabled = not (total > (new_view.page + 1) * 20)
                
                if not options:
                    options.append(SelectOption(label="항목 없음", value="none", description="선택 가능한 항목이 없습니다."))
                    
                options.append(SelectOption(label="뒤로 가기", value="back", description="이전으로 돌아갑니다."))
                new_view.children[0].options = options
                
                await interaction.edit_original_response(view=new_view)
            except Exception as e:
                options = [
                    SelectOption(label="오류 발생", value="error", description=f"오류: {str(e)}"),
                    SelectOption(label="뒤로 가기", value="back", description="이전으로 돌아갑니다.")
                ]
                new_view.children[0].options = options
                await interaction.edit_original_response(view=new_view)
                
        elif isinstance(original_view, DeleteMailView):
            new_view = DeleteMailView(original_view.selected, original_view.page - 1)
            await interaction.response.edit_message(view=new_view)
            
            try:
                items, total = await helper.GetItemsFromDB(new_view.tableType, "mail", new_view.page, 20)
                options = []
                
                for item in items:
                    if item[0]:
                        itemLabel = f"{item[0]}"
                        if len(itemLabel) > 25:  
                            itemLabel = itemLabel[:22] + "..."
                        options.append(SelectOption(label=itemLabel, value=f"{item[0]}"))
                
                new_view.nextButton.disabled = not (total > (new_view.page + 1) * 20)
                new_view.prevButton.disabled = new_view.page == 0
                
                if not options:
                    options.append(SelectOption(label="항목 없음", value="none", description="더 이상 항목이 없습니다."))
                    
                options.append(SelectOption(label="뒤로 가기", value="back", description="이전으로 돌아갑니다."))
                new_view.children[0].options = options
                
                await interaction.edit_original_response(view=new_view)
            except Exception as e:
                options = [
                    SelectOption(label="오류 발생", value="error", description=f"오류: {str(e)}"),
                    SelectOption(label="뒤로 가기", value="back", description="이전으로 돌아갑니다.")
                ]
                new_view.children[0].options = options
                await interaction.edit_original_response(view=new_view)

class NextPageButton(Button):
    def __init__(self):
        super().__init__(label="다음", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: Interaction):
        original_view = self.view
        if isinstance(original_view, DeleteUserView):
            new_view = DeleteUserView(original_view.selected, original_view.page + 1)
            await interaction.response.edit_message(view=new_view)
            await new_view.LoadData(interaction)
        elif isinstance(original_view, DeleteIPView):
            new_view = DeleteIPView(original_view.selected, original_view.page + 1)
            await interaction.response.edit_message(view=new_view)
            
            try:
                items, total = await helper.GetItemsFromDB(new_view.tableType, "ip", new_view.page, 20)
                options = []
                
                for item in items:
                    if item[0]:
                        itemLabel = f"{item[0]}"
                        if len(itemLabel) > 25:  
                            itemLabel = itemLabel[:22] + "..."
                        options.append(SelectOption(label=itemLabel, value=f"{item[0]}"))
                
                new_view.nextButton.disabled = not (total > (new_view.page + 1) * 20)
                new_view.prevButton.disabled = new_view.page == 0
                
                if not options:
                    options.append(SelectOption(label="항목 없음", value="none", description="더 이상 항목이 없습니다."))
                    
                options.append(SelectOption(label="뒤로 가기", value="back", description="이전으로 돌아갑니다."))
                new_view.children[0].options = options
                
                await interaction.edit_original_response(view=new_view)
            except Exception as e:
                options = [
                    SelectOption(label="오류 발생", value="error", description=f"오류: {str(e)}"),
                    SelectOption(label="뒤로 가기", value="back", description="이전으로 돌아갑니다.")
                ]
                new_view.children[0].options = options
                await interaction.edit_original_response(view=new_view)
                
        elif isinstance(original_view, DeleteMailView):
            new_view = DeleteMailView(original_view.selected, original_view.page + 1)
            await interaction.response.edit_message(view=new_view)
            
            try:
                items, total = await helper.GetItemsFromDB(new_view.tableType, "mail", new_view.page, 20)
                options = []
                
                for item in items:
                    if item[0]:
                        itemLabel = f"{item[0]}"
                        if len(itemLabel) > 25:  
                            itemLabel = itemLabel[:22] + "..."
                        options.append(SelectOption(label=itemLabel, value=f"{item[0]}"))
                
                new_view.nextButton.disabled = not (total > (new_view.page + 1) * 20)
                new_view.prevButton.disabled = new_view.page == 0
                
                if not options:
                    options.append(SelectOption(label="항목 없음", value="none", description="더 이상 항목이 없습니다."))
                    
                options.append(SelectOption(label="뒤로 가기", value="back", description="이전으로 돌아갑니다."))
                new_view.children[0].options = options
                
                await interaction.edit_original_response(view=new_view)
            except Exception as e:
                options = [
                    SelectOption(label="오류 발생", value="error", description=f"오류: {str(e)}"),
                    SelectOption(label="뒤로 가기", value="back", description="이전으로 돌아갑니다.")
                ]
                new_view.children[0].options = options
                await interaction.edit_original_response(view=new_view)

class DirectInputButton(Button):
    def __init__(self, selected, inputType):
        super().__init__(label="직접 입력", style=discord.ButtonStyle.primary)
        self.selected = selected
        self.inputType = inputType

    async def callback(self, interaction: Interaction):
        if self.inputType == "userId":
            if self.view.__class__.__name__ == "AddOrDeleteUserView":
                modal = AddUserIdModal(self.selected)
            else:
                modal = DirectInputModal(self.selected, self.inputType)
        else:
            modal = DirectInputModal(self.selected, self.inputType)
        await interaction.response.send_modal(modal)

class AddUserIdModal(Modal):
    def __init__(self, selected):
        super().__init__(title=f"{selected} 유저 추가")
        self.selected = selected
        
        self.add_item(TextInput(label="추가할 유저 ID", placeholder="유저 ID를 입력해주세요", required=True, style=discord.TextStyle.short))

    async def on_submit(self, interaction: Interaction):
        try:
            userId = self.children[0].value
            values = {"화이트리스트": "WhiteList", "블랙리스트": "BlackList"}
            tableType = f"{values[self.selected]}UserId"
            
            await helper.AddToDB(tableType, "userId", userId)
            
            try:
                user = await interaction.client.fetch_user(int(userId))
                userName = user.name
            except:
                userName = "알 수 없음"
            
            userInfo = [
                ("관리자", f"<@{interaction.user.id}>"),
                ("관리자 ID", f"`{interaction.user.id}`"),
                ("관리자 이름", f"`{interaction.user.name}`")
            ]
            
            fields = [
                ("종류", f"`{self.selected}`"),
                ("필드", "`userId`"),
                ("값", f"`{userId}`"),
                ("유저 이름", f"`{userName}`")
            ]
            
            await helper.SendOwnerLogWebhook(
                f"{self.selected} 유저 추가",
                f"{userName}이(가) {self.selected}에 추가되었습니다.",
                0x57F287,
                fields,
                userInfo
            )
            
            await helper.SendEmbed(interaction=interaction, title="추가 완료", description=f"{userName}(ID: {userId})을(를) {self.selected}에 추가했습니다.", color=Color.green())
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class DirectInputModal(Modal):
    def __init__(self, selected, inputType):
        super().__init__(title=f"{selected} 직접 입력")
        self.selected = selected
        self.inputType = inputType
        
        placeholder = "유저 ID를 입력해주세요" if inputType == "userId" else f"{inputType} 주소를 입력해주세요"
        self.add_item(TextInput(label=f"직접 입력할 {inputType}", placeholder=placeholder, required=True, style=discord.TextStyle.short))

    async def on_submit(self, interaction: Interaction):
        try:
            value = self.children[0].value
            values = {"화이트리스트": "WhiteList", "블랙리스트": "BlackList"}
            
            if self.inputType == "userId":
                tableType = f"{values[self.selected]}UserId"
                fieldName = "userId"
            elif self.inputType == "ip":
                tableType = f"{values[self.selected]}Ip"
                fieldName = "ip"
            else: 
                tableType = f"{values[self.selected]}Mail"
                fieldName = "mail"
            
            await helper.DeleteFromDB(tableType, fieldName, value)
            
            userName = "알 수 없음"
            if self.inputType == "userId":
                try:
                    user = await interaction.client.fetch_user(int(value))
                    userName = user.name
                except:
                    pass
            
            userInfo = [
                ("관리자", f"<@{interaction.user.id}>"),
                ("관리자 ID", f"`{interaction.user.id}`"),
                ("관리자 이름", f"`{interaction.user.name}`")
            ]
            
            fields = [
                ("종류", f"`{self.selected}`"),
                ("필드", f"`{self.inputType}`"),
                ("값", f"`{value}`")
            ]
            
            if self.inputType == "userId":
                fields.append(("유저 이름", f"`{userName}`"))
            
            displayValue = f"{userName}(ID: {value})" if self.inputType == "userId" else value
            
            await helper.SendOwnerLogWebhook(
                f"{self.selected} {self.inputType} 삭제 (직접 입력)",
                f"{displayValue}가 {self.selected}에서 삭제되었습니다.",
                0xFF0000,
                fields,
                userInfo
            )
            
            await helper.SendEmbed(interaction=interaction, title="삭제 완료", description=f"{displayValue}을(를) {self.selected}에서 삭제했습니다.", color=Color.green())
        except Exception as e:
            await helper.ErrorEmbed(interaction, f"오류가 발생했습니다.\n\n{str(e)}")

class BackToDeleteButton(Button):
    def __init__(self, selected):
        super().__init__(label="돌아가기", style=discord.ButtonStyle.primary)
        self.selected = selected

    async def callback(self, interaction: Interaction):
        view = DeleteView(self.selected)
        await interaction.response.edit_message(view=view)

class RestoreView(discord.ui.View):
    def __init__(self, restore_key: str, server_name: str, target_server_id: str, users_count: int, guild_name: str, guild_id: int):
        super().__init__(timeout=60.0)
        self.value = None
        self.embedDescription = (
            f"## 🔄 **복구 작업 확인**\n\n"
            f"### 📋 **복구코드 정보**\n"
            f"```ini\n"
            f"[복구코드] {restore_key}\n"
            f"[서버이름] {server_name}\n"
            f"[서버 ID] {target_server_id}\n"
            f"[예상인원] {users_count}명\n"
            f"```\n"
            f"### 🎯 **복구대상 서버**\n"
            f"```ini\n"
            f"[서버이름] {guild_name}\n"
            f"[서버 ID] {guild_id}\n"
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
            title="🔄 복구코드 사용 확인",
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
                f"## 🚀 **복구가 시작되었습니다**\n\n"
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
    def create(success_count: int, fail_count: int, already_in_server: int, total_count: int, new_restore_key: str):
        color = Color.green() if success_count > fail_count else Color.red()
        description = (
            f"## 📊 **복구 결과 보고서**\n\n"
            f"### 🎯 **처리 현황**\n"
            f"```ini\n"
            f"[✅ 성공] {success_count}명\n"
            f"[❌ 실패] {fail_count}명\n"
            f"[💫 이미 있음] {already_in_server}명\n"
            f"[📝 총 시도] {total_count}명\n"
            f"```\n"
            f"### 🔑 **새로운 복구코드**\n"
            f"> 안전하게 보관해주세요!\n"
            f"> ||`{new_restore_key}`||\n\n"
            f"### ⚠️ **주의사항**\n"
            f"> 🚫 이전 복구코드는 더 이상 사용할 수 없습니다.\n"
            f"> 🔒 새로운 복구코드를 안전한 곳에 보관하세요.\n"
            f"> 📌 문제가 발생한 경우 관리자에게 문의하세요."
        )
        
        return discord.Embed(
            title="✅ 복구 완료",
            description=description,
            color=color,
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )

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
            
            common_patterns = ['password', '123456', 'qwerty', 'admin', '1234']
            for pattern in common_patterns:
                if pattern in password.lower():
                    await helper.ErrorEmbed(interaction, "비밀번호에 너무 흔한 패턴이 포함되어 있습니다.")
                    return
            
            config = helper.LoadConfig()
            timestamp = datetime.now(pytz.timezone("Asia/Seoul"))
            
            try:
                db = sqlite3.connect(os.path.join(config.DBFolderPath, f"{self.server_id}.db"))
                cursor = db.cursor()
                cursor.execute("SELECT COUNT(*) FROM WebPanel WHERE id = ?", (id,))
                count = cursor.fetchone()[0]
                db.close()
                
                if count > 0:
                    await helper.ErrorEmbed(interaction, "이미 사용 중인 아이디입니다. 다른 아이디를 선택해주세요.")
                    return
            except Exception as e:
                print(f"아이디 중복 확인 중 오류 발생: {e}")
            
            salt = uuid.uuid4().hex
            hashedPassword = hashlib.sha256(password.encode() + salt.encode()).hexdigest()
            
            await helper.AddToDB("WebPanel", "id", id)
            await helper.AddToDB("WebPanel", "password", hashedPassword)
            await helper.AddToDB("WebPanel", "salt", salt)
            await interaction.user.dm_channel.send(embed=discord.Embed(title="웹패널 정보 입력 완료", description=f"웹패널 정보가 성공적으로 입력되었습니다.\n\n아이디: {id}\n비밀번호: {password}", color=Color.green()))
            
            key = helper.GenRandom(16)
            helper.GenServerDB(str(interaction.guild_id), interaction.guild.name, timestamp.strftime("%Y-%m-%d %H:%M:%S"), key)
            conn = sqlite3.connect(os.path.join(config.DBPath))
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Keys (Key, serverId) VALUES (?, ?)", (key, str(interaction.guild_id)))
            conn.commit()
            conn.close()
            
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