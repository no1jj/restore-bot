import subprocess
import sys
import os
import signal
import time

def RunBot():
    print("Discord 봇 시작 중...")
    return subprocess.Popen([sys.executable, "bot.py"], 
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          text=True,
                          encoding='utf-8',
                          errors='replace')

def RunWebServer():
    print("웹 서버 시작 중...")
    if os.name == 'nt':
        return subprocess.Popen(["node", "web.js"], 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True,
                              encoding='utf-8',
                              errors='replace')
    else:
        return subprocess.Popen(["node", "web.js"], 
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
            print(f"{prefix}: {output.strip()}")
    return process.poll()

def SignalHandler(sig, frame):
    print("\n프로그램 종료 중...")
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

if __name__ == "__main__":
    signal.signal(signal.SIGINT, SignalHandler)
    signal.signal(signal.SIGTERM, SignalHandler)
    
    bot_process = RunBot()
    web_process = RunWebServer()
    
    print("모든 서비스가 시작되었습니다. 종료하려면 Ctrl+C를 누르세요.")
    
    try:
        while True:
            bot_output = bot_process.stdout.readline()
            if bot_output:
                print(f"[봇]: {bot_output.strip()}")

            web_output = web_process.stdout.readline()
            if web_output:
                print(f"[웹]: {web_output.strip()}")
            
            if bot_process.poll() is not None:
                print("봇 프로세스가 종료되었습니다. 재시작 중...")
                bot_process = RunBot()
            
            if web_process.poll() is not None:
                print("웹 서버 프로세스가 종료되었습니다. 재시작 중...")
                web_process = RunWebServer()
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n프로그램 종료 중...")
        if 'bot_process' in locals():
            bot_process.terminate()
        if 'web_process' in locals():
            web_process.terminate()
