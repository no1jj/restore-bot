import discord
from discord import Interaction, Button, SelectOption
from discord.ui import View, Button, Select
import pytz
from datetime import datetime

class PrevPageButton(Button):
    def __init__(self, disabled=False):
        super().__init__(label="이전", style=discord.ButtonStyle.primary, disabled=disabled)

    async def callback(self, interaction: Interaction):
        await self.view.handle_prev_page(interaction)

class NextPageButton(Button):
    def __init__(self, disabled=False):
        super().__init__(label="다음", style=discord.ButtonStyle.primary, disabled=disabled)

    async def callback(self, interaction: Interaction):
        await self.view.handle_next_page(interaction)

class BackButton(Button):
    def __init__(self, label="돌아가기", style=discord.ButtonStyle.primary, callback_func=None):
        super().__init__(label=label, style=style)
        self.callback_func = callback_func

    async def callback(self, interaction: Interaction):
        if self.callback_func:
            await self.callback_func(interaction)
        else:
            await self.view.handle_back(interaction) 

# V1.3.2