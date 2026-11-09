@echo off
title GeminiTrans - Docker & Local Launcher
echo ========================================================
echo   GEMINITRANS: KHOI CHAY UNG DUNG DICH & PHU DE PHIM
echo ========================================================
echo 1. Chay trong Docker Container (Chuan he thong)
echo 2. Chay truc tiep bang uv / Python tren Host
echo 3. Dung Docker Container
echo ========================================================
set /p choice="Nhap lua chon cua ban (1, 2 hoac 3): "

cd /d "d:\Thành\Translate"

if "%choice%"=="1" (
    echo Dang khoi dong Docker Container...
    docker compose up -d
    echo Ung dung dang chay tai: http://localhost:8090
    start http://localhost:8090
    pause
    exit /b
)

if "%choice%"=="2" (
    echo Dang chay truc tiep qua uv...
    start http://localhost:8000
    "C:\Users\thanhcaotien\.local\bin\uv.exe" run uvicorn app:app --host 127.0.0.1 --port 8000 --reload
    pause
    exit /b
)

if "%choice%"=="3" (
    echo Dang dung Docker Container...
    docker compose down
    pause
    exit /b
)

echo Lua chon khong hop le.
pause
