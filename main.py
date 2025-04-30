import subprocess
import sys
import os
import signal
import time
from colorama import Fore, Back, Style, init

init(autoreset=True)

class Logger:
    @staticmethod
    def info(tag, message):
        print(f"{Fore.WHITE}{Style.BRIGHT}[{Fore.BLUE}ℹ {tag}{Fore.WHITE}] {message}")
    
    @staticmethod
    def success(tag, message):
        print(f"{Fore.WHITE}{Style.BRIGHT}[{Fore.GREEN}✔ {tag}{Fore.WHITE}] {message}")
    
    @staticmethod
    def warning(tag, message):
        print(f"{Fore.WHITE}{Style.BRIGHT}[{Fore.YELLOW}⚠ {tag}{Fore.WHITE}] {message}")
    
    @staticmethod
    def error(tag, message):
        print(f"{Fore.WHITE}{Style.BRIGHT}[{Fore.RED}✖ {tag}{Fore.WHITE}] {message}")
    
    @staticmethod
    def system(message):
        print(f"{Fore.WHITE}{Style.BRIGHT}[{Fore.MAGENTA}★ 시스템{Fore.WHITE}] {message}")

loger = Logger()

def RunBot():
    loger.info("🤖 봇", "Discord 봇 시작 중...")
    return subprocess.Popen([sys.executable, "bot/bot.py"], 
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          text=True,
                          encoding='utf-8',
                          errors='replace')

def RunWebServer():
    loger.info("🌐 웹", "웹 서버 시작 중...")
    if os.name == 'nt':
        return subprocess.Popen(["node", "web/app.js"], 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True,
                              encoding='utf-8',
                              errors='replace')
    else:
        return subprocess.Popen(["node", "web/app.js"], 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True,
                              encoding='utf-8',
                              errors='replace')

def MonitorOutput(process, prefix):
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            loger.info(prefix, output.strip())
    return process.poll()

def SignalHandler(sig, frame):
    loger.warning("⚠️ 시스템", "\n\n서비스가 사용자의 요청으로 종료됩니다.\n")
    if 'bot_process' in locals():
        if os.name == 'nt':
            bot_process.terminate()
        else:
            os.kill(bot_process.pid, signal.SIGTERM)
    
    if 'web_process' in locals():
        if os.name == 'nt':
            web_process.terminate()
        else:
            os.kill(web_process.pid, signal.SIGTERM)
    
    sys.exit(0)

def PrintColoredLine(color, text):
    if color == "purple":
        print(f"{Fore.MAGENTA}{Style.BRIGHT}{text}{Style.RESET_ALL}")
    elif color == "blue":
        print(f"{Fore.BLUE}{Style.BRIGHT}{text}{Style.RESET_ALL}")

def PrintBanner(title):
    print("\n")
    PrintColoredLine("purple", "═" * 50)
    print(f"{Fore.MAGENTA}{Style.BRIGHT}▶ {Fore.CYAN}{title} 시작 중...{Style.RESET_ALL}")
    PrintColoredLine("purple", "═" * 50)
    print("\n")

def PrintClosingBanner(title):
    print("\n")
    PrintColoredLine("purple", "═" * 50)
    print(f"{Fore.RED}{Style.BRIGHT}▶ {Fore.CYAN}{title} 종료됨{Style.RESET_ALL}")
    PrintColoredLine("purple", "═" * 50)
    print("\n")

if __name__ == "__main__":
    PrintBanner("RestoreBot")
    
    signal.signal(signal.SIGINT, SignalHandler)
    signal.signal(signal.SIGTERM, SignalHandler)
    
    bot_process = RunBot()
    web_process = RunWebServer()
    
    loger.success("✨ 시스템", "모든 서비스가 시작되었습니다. 종료하려면 Ctrl+C를 누르세요.")
    
    try:
        while True:
            bot_output = bot_process.stdout.readline()
            if bot_output:
                loger.info("🤖 봇", bot_output.strip())

            web_output = web_process.stdout.readline()
            if web_output:
                loger.info("🌐 웹", web_output.strip())
            
            if bot_process.poll() is not None:
                loger.error("⚠️ 시스템", "봇 프로세스가 종료되었습니다. 재시작 중...")
                bot_process = RunBot()
            
            if web_process.poll() is not None:
                loger.error("⚠️ 시스템", "웹 서버 프로세스가 종료되었습니다. 재시작 중...")
                web_process = RunWebServer()
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        loger.warning("⚠️ 시스템", "\n\n서비스가 사용자의 요청으로 종료됩니다.\n\n")
        if 'bot_process' in locals():
            bot_process.terminate()
        if 'web_process' in locals():
            web_process.terminate()
        
        PrintClosingBanner("RestoreBot")

# V1.1