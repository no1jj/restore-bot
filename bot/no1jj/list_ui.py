import discord
from discord import Interaction, Embed, Color, SelectOption
from discord.ui import View, Select, Button, Modal, TextInput, UserSelect
import pytz
from datetime import datetime
import os
import sqlite3
from . import helper
from .common_ui import PrevPageButton, NextPageButton

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
            SelectOption(label="뒤로 가기", value="back", description="이전으로")
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
    
    async def handle_prev_page(self, interaction):
        new_view = DeleteUserView(self.selected, self.page - 1)
        await interaction.response.edit_message(view=new_view)
        await new_view.LoadData(interaction)
    
    async def handle_next_page(self, interaction):
        new_view = DeleteUserView(self.selected, self.page + 1)
        await interaction.response.edit_message(view=new_view)
        await new_view.LoadData(interaction)

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
    
    async def handle_prev_page(self, interaction):
        new_view = DeleteIPView(self.selected, self.page - 1)
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
    
    async def handle_next_page(self, interaction):
        new_view = DeleteIPView(self.selected, self.page + 1)
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
    
    async def handle_prev_page(self, interaction):
        new_view = DeleteMailView(self.selected, self.page - 1)
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
    
    async def handle_next_page(self, interaction):
        new_view = DeleteMailView(self.selected, self.page + 1)
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

class BackToDeleteButton(Button):
    def __init__(self, selected):
        super().__init__(label="돌아가기", style=discord.ButtonStyle.primary)
        self.selected = selected

    async def callback(self, interaction: Interaction):
        view = DeleteView(self.selected)
        await interaction.response.edit_message(view=view)

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

# V1.3