@echo off
chcp 65001 > nul
echo.
echo ========================================
echo    StockScan Pro 서버 시작 중...
echo ========================================
echo.

cd /d C:\Users\lllol\stockscan\server

C:\Users\lllol\AppData\Local\Programs\Python\Python311-32\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
