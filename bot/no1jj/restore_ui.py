import discord
from discord import Interaction, Embed, Color, Button
from discord.ui import View
import pytz
from datetime import datetime

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

# V1.3.2