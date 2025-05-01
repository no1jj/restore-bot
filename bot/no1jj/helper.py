import sqlite3
import os
import random
import requests
from discord import Interaction, Embed, Color
import json
import pytz
from datetime import datetime
from discord.webhook import SyncWebhook

_config_instance = None

def LoadConfig():
    global _config_instance
    if _config_instance is not None:
        return _config_instance
        
    configPath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config.json')
    with open(configPath, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
        class Config: 
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        _config_instance = Config(config_data)
        return _config_instance

config = LoadConfig()

def GenRandom(length: int):
    characters = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ"
    return "".join(random.choice(characters) for _ in range(length))

async def CheckPermission(interaction: Interaction, owner: bool = False):  
    if owner:
        if not str(interaction.user.id) == str(config.ownerId):
            await ErrorEmbed(
                interaction=interaction,
                error_message="이 명령어를 사용할 수 없습니다.."
            )
            return False
    if not interaction.user.guild_permissions.administrator:
        await ErrorEmbed(
            interaction=interaction,
            error_message="이 명령어를 사용하기 위해서는 서버 관리자 권한이 필요합니다."
        )
        return False
    return True


def GenDB():
    config = LoadConfig()
    filePath = config.DBPath

    if not os.path.exists(os.path.dirname(filePath)):
        os.makedirs(os.path.dirname(filePath))

    conn = None
    try:
        conn = sqlite3.connect(filePath)
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS WhiteListUserId (
                            userId TEXT PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS WhiteListIp (
                            ip TEXT PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS WhiteListMail (
                            mail TEXT PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS BlackListUserId (
                            userId TEXT PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS BlackListIp (
                            ip TEXT PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS BlackListMail (
                            mail TEXT PRIMARY KEY
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS Keys (
                            Key TEXT NOT NULL,
                            serverId TEXT NOT NULL
                        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS WebPanel (
                            id TEXT NOT NULL,
                            password TEXT NOT NULL,
                            salt TEXT NOT NULL,
                            serverId TEXT NOT NULL
                        )''')
        conn.commit()
        print(f"DB 생성 완료: {filePath}")
    except Exception as e:
        print(f"DB 생성 중 오류 발생: {e}")
    finally:
        if conn:
            conn.close()

def CheckServerDB(serverId: str):  
    config = LoadConfig()
    filePath = os.path.join(config.DBFolderPath, f"{serverId}.db")
    return os.path.exists(filePath)

def GenServerDB(serverId: str, name: str, date: str, key: str):
    config = LoadConfig()
    if not os.path.exists(config.DBFolderPath):
        os.makedirs(config.DBFolderPath)  
    filePath = os.path.join(config.DBFolderPath, f"{serverId}.db")

    if not os.path.exists(filePath):  
        conn = None
        try:
            conn = sqlite3.connect(filePath)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS Info (
                                name TEXT NOT NULL,
                                id TEXT NOT NULL,
                                date TEXT NOT NULL,
                                key TEXT NOT NULL
                            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS Settings (
                                loggingIp BOOLEAN NOT NULL,
                                loggingMail BOOLEAN NOT NULL,
                                webhookUrl TEXT NOT NULL,
                                roleId TEXT NOT NULL,
                                useCaptcha BOOLEAN NOT NULL,
                                blockVpn BOOLEAN NOT NULL,
                                loggingChannelId INT NOT NULL
                            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS Users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                userId TEXT NOT NULL,
                                refreshToken TEXT,
                                email TEXT,
                                ip TEXT,
                                serviceToken TEXT
                            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS Logs (
                                logId INTEGER PRIMARY KEY AUTOINCREMENT,
                                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                                userId TEXT,
                                content TEXT NOT NULL,
                                ip TEXT,
                                email TEXT,
                                userDetails TEXT
                            )''')
            cursor.execute('''INSERT INTO Info (
                                name, id, date, key) 
                                VALUES (?, ?, ?, ?)''', 
                            (str(name), str(serverId), str(date), str(key)))
                            
            cursor.execute('''INSERT INTO Settings (
                                loggingIp, loggingMail, webhookUrl, roleId, useCaptcha, blockVpn, loggingChannelId) 
                                VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                            (False, False, "", 0, False, False, 0))
            conn.commit()
            
        except Exception as e:
            print(f"[Error] Database creation failed: {e}")
        finally:
            if conn:
                conn.close()

def IsValidIp(ip):
    import re
    pattern = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
    match = pattern.match(ip)
    if not match:
        return False
    
    for i in range(1, 5):
        if int(match.group(i)) > 255:
            return False
    
    return True

async def AddToDB(tableType, field, value):
    config = LoadConfig()
    
    if field == "ip" and not IsValidIp(value):
        raise Exception("유효한 IP 주소를 입력해주세요. (예: 127.0.0.1)")
    
    oppositeTable = None
    if "WhiteList" in tableType:
        oppositeTable = tableType.replace("WhiteList", "BlackList")
    elif "BlackList" in tableType:
        oppositeTable = tableType.replace("BlackList", "WhiteList")
    
    conn = None
    try:
        conn = sqlite3.connect(os.path.join(config.DBPath))
        cursor = conn.cursor()
        
        if oppositeTable:
            query = f"""
                SELECT 
                    (SELECT 1 FROM {tableType} WHERE {field} = ? LIMIT 1) as same_list,
                    (SELECT 1 FROM {oppositeTable} WHERE {field} = ? LIMIT 1) as opposite_list
            """
            cursor.execute(query, (value, value))
            result = cursor.fetchone()
            
            if result[0]:
                listType = "화이트리스트" if "WhiteList" in tableType else "블랙리스트"
                raise Exception(f"이미 {listType}에 등록된 항목입니다.")
            
            if result[1]:
                listType = "화이트리스트" if "BlackList" in tableType else "블랙리스트"
                raise Exception(f"이미 {listType}에 등록된 항목입니다.")
        
        cursor.execute(f"INSERT INTO {tableType} ({field}) VALUES (?)", (value,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        raise Exception(f"이미 등록된 항목입니다.")
    except Exception as e:
        if conn and conn.in_transaction:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

async def DeleteFromDB(tableType, field, value):
    config = LoadConfig()
    conn = None
    try:
        conn = sqlite3.connect(os.path.join(config.DBPath))
        cursor = conn.cursor()
        
        if field == "userId":
            cursor.execute(f"DELETE FROM {tableType} WHERE userId = ?", (value,))
        else:
            cursor.execute(f"DELETE FROM {tableType} WHERE {field} = ?", (value,))
            
        conn.commit()
        if cursor.rowcount == 0:
            raise Exception("삭제할 항목을 찾을 수 없습니다.")
        return True
    except Exception as e:
        raise e
    finally:
        if conn:
            conn.close()

async def GetItemsFromDB(tableType, field, page=0, limit=20):
    config = LoadConfig()
    
    def items_generator(cursor):
        while True:
            batch = cursor.fetchmany(100) 
            if not batch:
                break
            for item in batch:
                yield item
    
    conn = None
    try:
        conn = sqlite3.connect(os.path.join(config.DBPath))
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT COUNT({field}) FROM {tableType}")
        total = cursor.fetchone()[0]
        
        offset = page * limit
        cursor.execute(f"SELECT {field} FROM {tableType} LIMIT {limit} OFFSET {offset}")
        
        items = list(cursor.fetchall())
        
        return items, total
    except Exception as e:
        raise Exception(f"DB 오류: {str(e)[:50]}")
    finally:
        if conn:
            conn.close()

async def SendEmbed(interaction: Interaction, title: str, description: str, color: Color, fields=None, ephemeral=True, view=None):
    embed = Embed(
        title=f"{'🔴' if color == Color.red() else '🟢' if color == Color.green() else '🔵'} {title}",
        description=description,
        color=color,
        timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
    )
    
    if fields:
        for name, value in fields:
            embed.add_field(name=f"**{name}**", value=value, inline=False)
            
    if interaction.response.is_done():
        if view:
            await interaction.followup.send(embed=embed, ephemeral=ephemeral, view=view)
        else:
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.defer(ephemeral=ephemeral)
        if view:
            await interaction.followup.send(embed=embed, ephemeral=ephemeral, view=view)
        else:
            await interaction.followup.send(embed=embed, ephemeral=ephemeral)

async def ErrorEmbed(interaction: Interaction, error_message: str, view=None):
    await SendEmbed(
        interaction=interaction,
        title="오류 발생",
        description=f"⚠️ **{error_message}**",
        color=Color.red(),
        ephemeral=True,
        view=view
    )

async def CheckServerRegistration(interaction: Interaction):
    if not await CheckPermission(interaction): 
        return False
    
    if not CheckServerDB(str(interaction.guild_id)):
        await ErrorEmbed(
            interaction=interaction,
            error_message="등록되지 않은 서버입니다.\n`/등록` 명령어로 서버를 등록해주세요."
        )
        return False
    return True

def UpdateServerSettings(serverId, settingName, value):
    config = LoadConfig()
    filePath = os.path.join(config.DBFolderPath, f"{serverId}.db")
    
    if not os.path.exists(filePath):
        raise Exception("서버 데이터베이스가 존재하지 않습니다.")
    
    conn = None
    try:
        conn = sqlite3.connect(filePath)
        cursor = conn.cursor()
        
        conn.execute("BEGIN")
        
        if isinstance(value, bool):
            cursor.execute(f"UPDATE Settings SET {settingName} = ?", (value,))
        else:
            cursor.execute(f"UPDATE Settings SET {settingName} = ?", (str(value),))
        
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def UpdateMultipleServerSettings(serverId, settingsDict):
    config = LoadConfig()
    filePath = os.path.join(config.DBFolderPath, f"{serverId}.db")
    
    if not os.path.exists(filePath):
        raise Exception("서버 데이터베이스가 존재하지 않습니다.")
    
    conn = None
    try:
        conn = sqlite3.connect(filePath)
        cursor = conn.cursor()
        
        conn.execute("BEGIN")
        
        for settingName, value in settingsDict.items():
            if isinstance(value, bool):
                cursor.execute(f"UPDATE Settings SET {settingName} = ?", (value,))
            else:
                cursor.execute(f"UPDATE Settings SET {settingName} = ?", (str(value),))
        
        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

async def SendOwnerLogWebhook(title, description, color, fields=[], userInfo=None):
    try:
        config = LoadConfig()
        if not hasattr(config, "ownerLogWebhook") or not config.ownerLogWebhook:
            return False

        webhook = SyncWebhook.from_url(config.ownerLogWebhook)
        embed = Embed(
            title=f"{'🔴' if color == 0xFF0000 else '🟢' if color == 0x57F287 else '🔵' if color == 0x3498DB else ''} {title}",
            description=description,
            color=color,
            timestamp=datetime.now(pytz.timezone("Asia/Seoul"))
        )
        
        for name, value in fields:
            embed.add_field(name=f"**{name}**", value=value, inline=False)
            
        if userInfo:
            embed.add_field(name="**📊 관리자 정보**", value="", inline=False)
            for name, value in userInfo:
                embed.add_field(name=name, value=value, inline=True)
                
        webhook.send(embed=embed)
        return True
    except Exception as e:
        print(f"오너 로그 웹훅 전송 실패: {str(e)}")
        return False

def DatabaseConnection(path):
    def decorator(func):
        def wrapper(*args, **kwargs):
            conn = None
            try:
                conn = sqlite3.connect(path)
                kwargs['conn'] = conn
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                if conn and conn.in_transaction:
                    conn.rollback()
                raise e
            finally:
                if conn:
                    conn.close()
        return wrapper
    return decorator

def GetDBPath(serverId=None):
    config = LoadConfig()
    if serverId:
        return os.path.join(config.DBFolderPath, f"{serverId}.db")
    return config.DBPath

@DatabaseConnection(GetDBPath())
def CheckIsWhiteOrBlacklisted(tableType, field, value, conn=None):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {tableType} WHERE {field} = ?", (value,))
    return cursor.fetchone() is not None

async def RefreshToken(refresh_token, session):
    url = "https://discord.com/api/oauth2/token"
    
    config = LoadConfig()
    
    data = {
        "client_id": config.clientId,
        "client_secret": config.clientSecret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        async with session.post(url, data=data, headers=headers) as response:
            if response.status == 200:
                json_response = await response.json()
                new_refresh_token = json_response.get("refresh_token")
                
                if new_refresh_token and new_refresh_token != refresh_token:
                    try:
                        await UpdateRefreshToken(refresh_token, new_refresh_token)
                    except Exception as e:
                        pass
                
                return json_response
            else:
                return {}
    except:
        return {}

async def UpdateRefreshToken(old_token, new_token):
    config = LoadConfig()
    if not os.path.exists(config.DBFolderPath):
        return
    
    db_files = [f for f in os.listdir(config.DBFolderPath) if f.endswith('.db')]
    
    for db_file in db_files:
        db_path = os.path.join(config.DBFolderPath, db_file)
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE Users SET refreshToken = ? WHERE refreshToken = ?", 
                          (new_token, old_token))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"DB {db_file} 업데이트 중 오류: {str(e)}")

# V1.2