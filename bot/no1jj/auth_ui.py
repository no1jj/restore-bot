import discord
from discord import Interaction, Embed, Color, SyncWebhook
from discord.ui import View, Button, Modal, TextInput
import pytz
from datetime import datetime
from urllib.parse import quote
import os
import sqlite3
from . import helper

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
        if str(interaction.user.id) == str(config.ownerId):
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

# V1.3.2