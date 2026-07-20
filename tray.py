# StockScan Pro — 트레이 앱
# 파일 위치: C:\Users\lllol\stockscan\server\tray.py

import subprocess
import threading
import webbrowser
import time
from PIL import Image, ImageDraw
import pystray

PYTHON32 = r"C:\Users\lllol\AppData\Local\Programs\Python\Python311-32\python.exe"
SERVER_DIR = r"C:\Users\lllol\stockscan\server"
APP_URL = "http://localhost:8000/app"

server_process = None

def is_running():
    return server_process is not None and server_process.poll() is None

def start_server():
    global server_process
    if is_running():
        return
    server_process = subprocess.Popen(
        [PYTHON32, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=SERVER_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

def stop_server():
    global server_process
    if server_process:
        server_process.terminate()
        server_process = None

def make_icon(on):
    color = (0, 200, 80) if on else (120, 120, 120)
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=color)
    draw.text((22, 16), "S", fill=(255, 255, 255))
    return img

tray = None

def monitor():
    while True:
        if tray:
            tray.icon = make_icon(is_running())
            tray.title = "StockScan ● 실행중" if is_running() else "StockScan ○ 꺼짐"
        time.sleep(3)

def open_app(icon, item):
    webbrowser.open(APP_URL)

def quit_app(icon, item):
    stop_server()
    icon.stop()

def main():
    global tray

    start_server()

    menu = pystray.Menu(
        pystray.MenuItem("StockScan 열기", open_app, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("종료", quit_app),
    )

    tray = pystray.Icon("StockScan", make_icon(True), "StockScan ● 실행중", menu)

    t = threading.Thread(target=monitor, daemon=True)
    t.start()

    threading.Timer(2, lambda: webbrowser.open(APP_URL)).start()

    tray.run()

if __name__ == "__main__":
    main()
