@echo off
chcp 65001 >nul
title GeminiTrans - Tự Động Cài Đặt & Khởi Chạy Hệ Thống

echo =====================================================================
echo    🚀 GEMINITRANS - HỆ THỐNG DỊCH THUẬT & PHỤ ĐỀ VIDEO AI
echo       Tự Động Kiểm Tra, Cài Đặt Môi Trường & Khởi Chạy (1-Click)
echo =====================================================================
echo.

:: 1. KIỂM TRA & TỰ CÀI ĐẶT PYTHON
echo [*] Đang kiểm tra Python trên máy của bạn...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Máy tính của bạn chưa có Python!
    echo [*] Đang tự động tải và cài đặt Python 3.11 qua Windows Package Manager (winget)...
    winget install -e --id Python.Python.3.11 --scope currentuser --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo [X] Không thể tự cài Python tự động bằng winget.
        echo [X] Vui lòng tải Python thủ công tại: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo [V] Đã cài đặt Python thành công!
    :: Refresh PATH tạm thời
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
) else (
    echo [V] Đã phát hiện Python có sẵn trên máy.
)

:: 2. KIỂM TRA & TỰ CÀI ĐẶT FFMPEG (HỖ TRỢ XỬ LÝ VIDEO & AUDIO)
echo.
echo [*] Đang kiểm tra FFmpeg (công cụ cắt & ghép video)...
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Máy chưa có FFmpeg. Đang tự động cài FFmpeg qua winget...
    winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
    if %errorlevel% equ 0 (
        echo [V] Đã cài đặt FFmpeg thành công!
    ) else (
        echo [!] Bỏ qua cài FFmpeg qua winget (Hệ thống sẽ chạy ở chế độ Client-Side Burner).
    )
) else (
    echo [V] Đã phát hiện FFmpeg có sẵn trên máy.
)

:: 3. TẠO & KÍCH HOẠT MÔI TRƯỜNG ẢO (VIRTUAL ENVIRONMENT)
echo.
echo [*] Đang thiết lập môi trường ảo Python (.venv)...
if not exist ".venv" (
    python -m venv .venv
    echo [V] Đã tạo môi trường ảo .venv thành công.
)

call .venv\Scripts\activate.bat

:: 4. CÀI ĐẶT CÁC THƯ VIỆN PYTHON CẦN THIẾT
echo.
echo [*] Đang cài đặt các thư viện phụ thuộc (FastAPI, Uvicorn, Google GenAI...)...
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [X] Lỗi cài đặt thư viện! Vui lòng kiểm tra lại kết nối mạng.
    pause
    exit /b 1
)
echo [V] Cài đặt toàn bộ thư viện thành công!

:: 5. KIỂM TRA FILE CẤU HÌNH .ENV
echo.
echo [*] Đang kiểm tra file cấu hình .env (API Keys)...
if not exist ".env" (
    if exist ".env.sample" (
        copy .env.sample .env >nul
        echo [!] Chưa thấy file .env! Đã tự động tạo .env từ mẫu .env.sample.
        echo [!] Vui lòng dán API Key của bạn vào file .env nếu chưa có!
    ) else (
        echo [!] Cảnh báo: Chưa có file .env.
    )
) else (
    echo [V] File .env đã sẵn sàng.
)

:: 6. KHỞI CHẠY ỨNG DỤNG & TỰ MỞ TRÌNH DUYỆT
echo.
echo =====================================================================
echo    🎉 HỆ THỐNG ĐÃ SẴN SÀNG!
echo    🌐 Đang khởi động máy chủ tại: http://localhost:8090
echo    (Đang tự động mở trình duyệt cho bạn...)
echo =====================================================================
echo.

start "" http://localhost:8090
python -m uvicorn app:app --host 0.0.0.0 --port 8090 --reload
pause
