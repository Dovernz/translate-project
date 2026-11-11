@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title GeminiTrans

set "CURRENT_DIR=%~dp0"
if "%CURRENT_DIR:~-1%"=="\" set "CURRENT_DIR=%CURRENT_DIR:~0,-1%"
set "CONFIG_PATH_FILE=%CURRENT_DIR%\.install_path"

set "APP_DIR="
if exist "%CONFIG_PATH_FILE%" (
    set /p "APP_DIR="<"%CONFIG_PATH_FILE%"
)
if "!APP_DIR!"=="" (
    if exist "%CURRENT_DIR%\app.py" (
        set "APP_DIR=%CURRENT_DIR%"
    ) else if exist "%USERPROFILE%\GeminiTrans\app.py" (
        set "APP_DIR=%USERPROFILE%\GeminiTrans"
    ) else if exist "D:\Thành\Translate\app.py" (
        set "APP_DIR=D:\Thành\Translate\CODE"
    ) else (
        set "APP_DIR=%CURRENT_DIR%"
    )
)

set "REPO_URL=https://github.com/Dovernz/translate-project.git"
set "REPO_ZIP_URL=https://github.com/Dovernz/translate-project/archive/refs/heads/main.zip"
set "PY_EMBED_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
set "GET_PIP_URL=https://bootstrap.pypa.io/get-pip.py"
set "HOSTS_FILE=%windir%\System32\drivers\etc\hosts"
set "APP_PORT=8090"
set "APP_URL=http://localhost:8090"

if not "%~1"=="" (
    set "choice=%~1"
    goto DISPATCH
)

:MENU
set "choice="
cls
call :CHECK_STATUS_INTERNAL
if "!IS_RUNNING!"=="1" (set "SERVER_STATUS=ĐANG CHẠY") else (set "SERVER_STATUS=ĐÃ TẮT")

echo =======================================================================
echo     GEMINITRANS - HỆ THỐNG DỊCH THUẬT AI
echo     Trạng thái: [!SERVER_STATUS!]  ^|  URL: !APP_URL!
echo     Thư mục app: !APP_DIR!  ^|  CUSTOM_DOMAIN: !CUSTOM_DOMAIN!
echo =======================================================================
echo   [1] Bật web (Mở !APP_URL!)
echo   [2] Tắt web
echo   [3] Cài đặt / Khởi tạo môi trường độc lập
echo   [4] Cập nhật mã nguồn
echo   [5] Xóa cài đặt hoàn toàn
echo   [6] Cấu hình tên miền (Cần quyền Admin)
echo   [0] Thoát
echo =======================================================================
set /p "choice=Nhập lựa chọn (0-6): "

:DISPATCH
if "%choice%"=="1" goto START_APP
if "%choice%"=="2" goto STOP_APP
if "%choice%"=="3" goto INSTALL_APP
if "%choice%"=="4" goto UPDATE_APP
if "%choice%"=="5" goto UNINSTALL_APP
if "%choice%"=="6" goto CONFIG_DOMAIN
if "%choice%"=="0" exit /b 0
goto MENU

:CONFIG_DOMAIN
cls
echo =======================================================================
echo          CẤU HÌNH TÊN MIỀN ẢO (TÙY CHỌN NÂNG CAO)
echo =======================================================================
echo Lưu ý: Ứng dụng đã hoạt động 100%% bình thường tại: http://localhost:8090
echo mà KHÔNG cần bất kỳ quyền Administrator nào trên máy tính.
echo.
echo Vui lòng chọn cách cấu hình tên miền:
echo   [1] Sử dụng tên miền mặc định (translate.local)
echo   [2] Nhập tên miền tùy chỉnh
echo   [3] Hủy và quay lại Menu chính
echo =======================================================================
set "DOMAIN_CHOICE="
set /p "DOMAIN_CHOICE=Nhập lựa chọn (1-3): "

if "!DOMAIN_CHOICE!"=="3" goto MENU

if "!DOMAIN_CHOICE!"=="1" (
    set "CUSTOM_DOMAIN=translate.local"
) else if "!DOMAIN_CHOICE!"=="2" (
    set "CUSTOM_DOMAIN="
    echo.
    set /p "CUSTOM_DOMAIN=Nhập tên miền bạn muốn sử dụng (VD: myapp.local): "
    if "!CUSTOM_DOMAIN!"=="" (
        echo [LỖI] Tên miền không được để trống! Quay lại menu...
        pause
        goto MENU
    )
) else (
    echo [LỖI] Lựa chọn không hợp lệ!
    pause
    goto CONFIG_DOMAIN
)

echo.
echo Bạn sắp cấu hình ứng dụng chạy qua tên miền: http://!CUSTOM_DOMAIN!
echo Thao tác này sẽ yêu cầu quyền Administrator để ghi file hosts và tạo portproxy.
set "CONFIRM_DOMAIN="
set /p "CONFIRM_DOMAIN=Bạn có muốn tiếp tục cấp quyền Admin để cấu hình? (Y/N, mặc định N): "
if /i not "!CONFIRM_DOMAIN!"=="Y" goto MENU

echo.
echo Đang cấu hình tên miền !CUSTOM_DOMAIN! (yêu cầu quyền Admin)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Start-Process cmd -ArgumentList '/c (findstr /C:\"!CUSTOM_DOMAIN!\" \"%HOSTS_FILE%\" >nul 2>&1 || echo 127.0.0.1 !CUSTOM_DOMAIN! >> \"%HOSTS_FILE%\") & (netsh interface portproxy add v4tov4 listenport=80 listenaddress=127.0.0.1 connectport=8090 connectaddress=127.0.0.1 >nul 2>&1)' -Verb RunAs -Wait; Write-Host ' [OK] Cấu hình hoàn tất! Bạn có thể truy cập http://!CUSTOM_DOMAIN!.' -ForegroundColor Green } catch { Write-Host ' [i] Thao tác bị hủy hoặc không có quyền Admin. Bạn vẫn dùng bình thường tại http://localhost:8090.' -ForegroundColor Yellow }"
pause
goto MENU

:FIND_PYTHON
set "PY_RUN="
if exist "!APP_DIR!\runtime\python.exe" (
    "!APP_DIR!\runtime\python.exe" -c "import uvicorn, fastapi" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_RUN=!APP_DIR!\runtime\python.exe"
        exit /b 0
    )
    "!APP_DIR!\runtime\python.exe" -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_RUN=!APP_DIR!\runtime\python.exe"
        echo [INFO] Python Portable dang thieu thu vien, tu dong cai dat...
        call :INSTALL_DEPS
        exit /b 0
    )
)
if exist "!APP_DIR!\.venv\Scripts\python.exe" (
    "!APP_DIR!\.venv\Scripts\python.exe" -c "import uvicorn, fastapi" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_RUN=!APP_DIR!\.venv\Scripts\python.exe"
        exit /b 0
    )
    "!APP_DIR!\.venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_RUN=!APP_DIR!\.venv\Scripts\python.exe"
        echo [INFO] Python .venv dang thieu thu vien, tu dong cai dat...
        call :INSTALL_DEPS
        exit /b 0
    )
)
if exist "!APP_DIR!\venv\Scripts\python.exe" (
    "!APP_DIR!\venv\Scripts\python.exe" -c "import uvicorn, fastapi" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_RUN=!APP_DIR!\venv\Scripts\python.exe"
        exit /b 0
    )
    "!APP_DIR!\venv\Scripts\python.exe" -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_RUN=!APP_DIR!\venv\Scripts\python.exe"
        echo [INFO] Python venv dang thieu thu vien, tu dong cai dat...
        call :INSTALL_DEPS
        exit /b 0
    )
)
exit /b 0

:START_APP
call :CHECK_STATUS_INTERNAL
if "!IS_RUNNING!"=="1" (
    echo GeminiTrans đang chạy sẵn. Đang mở trình duyệt...
    start "" !APP_URL!
    if not "%~1"=="" exit /b 0
    goto MENU
)

if not exist "!APP_DIR!\app.py" (
    echo [INFO] Chưa tìm thấy mã nguồn ứng dụng tại: !APP_DIR!
    echo [INFO] Đang tự động tải và thiết lập môi trường độc lập...
    if not exist "!APP_DIR!" mkdir "!APP_DIR!"
    cd /d "!APP_DIR!"
    call :SYNC_SOURCE_CODE
    call :SETUP_PYTHON_ENV
    call :ENSURE_ENV_CONFIG
)

cd /d "!APP_DIR!"

set "DOCKER_SUCCESS=0"
if exist "docker-compose.yml" (
    docker info >nul 2>&1
    if !errorlevel! equ 0 (
        echo [INFO] Phát hiện Docker daemon đang chạy, đang khởi động container...
        docker compose up -d >nul 2>&1
        if !errorlevel! equ 0 (
            set "DOCKER_SUCCESS=1"
            goto WAIT_READY
        )
    )
)

if "!DOCKER_SUCCESS!"=="0" (
    echo [INFO] Docker Engine không chạy hoặc không có. Khởi chạy bằng Python cục bộ...
)

call :FIND_PYTHON
if "!PY_RUN!"=="" (
    echo [INFO] Chưa tìm thấy môi trường Python của ứng dụng. Đang thiết lập môi trường độc lập...
    call :SETUP_PYTHON_ENV
    call :FIND_PYTHON
)

if "!PY_RUN!"=="" (
    echo [LỖI] Không thể khởi tạo Python. Vui lòng chọn [3] để cài đặt lại môi trường.
    if not "%~1"=="" exit /b 1
    pause
    goto MENU
)

call :ENSURE_ENV_CONFIG

echo Đang khởi động GeminiTrans tại !APP_URL!...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:PYTHONPATH='!APP_DIR!'; Start-Process -FilePath '!PY_RUN!' -ArgumentList '-m uvicorn app:app --host 0.0.0.0 --port !APP_PORT!' -WorkingDirectory '!APP_DIR!' -WindowStyle Hidden -RedirectStandardOutput '!APP_DIR!\server.log' -RedirectStandardError '!APP_DIR!\server_err.log'"

:WAIT_READY
echo Đang kiểm tra kết nối dịch vụ tại cổng !APP_PORT!...
for /l %%i in (1,1,25) do (
    netstat -ano | findstr /R /C:":!APP_PORT! .*LISTENING" >nul 2>&1
    if !errorlevel! equ 0 (
        echo =======================================================================
        echo [OK] GeminiTrans đã khởi động thành công tại !APP_URL!
        echo =======================================================================
        start "" !APP_URL!
        if not "%~1"=="" exit /b 0
        pause
        goto MENU
    )
    ping -n 2 127.0.0.1 >nul
)

echo [CẢNH BÁO] Không thể kết nối tới cổng !APP_PORT! sau thời gian chờ.
if exist "!APP_DIR!\server.log" (
    echo 10 dòng log gần nhất từ server.log:
    echo ---------------------------------------------------------------------
    powershell -NoProfile -Command "Get-Content -Path '!APP_DIR!\server.log' -Tail 10 -ErrorAction SilentlyContinue"
    echo ---------------------------------------------------------------------
)
if exist "!APP_DIR!\server_err.log" (
    echo 10 dòng log gần nhất từ server_err.log:
    echo ---------------------------------------------------------------------
    powershell -NoProfile -Command "Get-Content -Path '!APP_DIR!\server_err.log' -Tail 10 -ErrorAction SilentlyContinue"
    echo ---------------------------------------------------------------------
)
echo Vui lòng kiểm tra lại cấu hình hoặc log lỗi ở trên.
start "" !APP_URL!
if not "%~1"=="" exit /b 0
pause
goto MENU

:STOP_APP
cd /d "!APP_DIR!" 2>nul
if exist "docker-compose.yml" (
    docker info >nul 2>&1
    if !errorlevel! equ 0 (
        docker compose stop >nul 2>&1
    )
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":!APP_PORT! .*LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)

ping -n 2 127.0.0.1 >nul
echo Đã tắt web thành công.
if not "%~1"=="" exit /b 0
ping -n 2 127.0.0.1 >nul
goto MENU

:INSTALL_APP
cls
echo =======================================================================
echo                        CÀI ĐẶT GEMINITRANS
echo =======================================================================
echo Chọn thư mục cài đặt:
echo   [1] Thư mục hiện tại: !CURRENT_DIR!
echo   [2] Nhập đường dẫn tùy chọn (nhập path mới)
echo   Hoặc dán trực tiếp đường dẫn thư mục vào đây (vd: D:\App\Translate)
echo =======================================================================
set "DIR_CHOICE=1"
set /p "DIR_CHOICE=Nhập lựa chọn (1/2 hoặc dán path, Mặc định 1): "
set "DIR_CHOICE=!DIR_CHOICE:"=!"

if "!DIR_CHOICE!"=="1" (
    set "APP_DIR=!CURRENT_DIR!"
) else if "!DIR_CHOICE!"=="2" (
    set "CUSTOM_DIR="
    set /p "CUSTOM_DIR=Nhập đường dẫn thư mục muốn lưu: "
    set "CUSTOM_DIR=!CUSTOM_DIR:"=!"
    if not "!CUSTOM_DIR!"=="" (
        set "APP_DIR=!CUSTOM_DIR!"
    ) else (
        set "APP_DIR=!CURRENT_DIR!"
    )
) else if not "!DIR_CHOICE!"=="" (
    set "APP_DIR=!DIR_CHOICE!"
) else (
    set "APP_DIR=!CURRENT_DIR!"
)

if "!APP_DIR:~-1!"=="\" set "APP_DIR=!APP_DIR:~0,-1!"
if "!APP_DIR:~-1!"=="/" set "APP_DIR=!APP_DIR:~0,-1!"

echo !APP_DIR!>"%CONFIG_PATH_FILE%"
echo Thư mục cài đặt: !APP_DIR!
echo.

if not exist "!APP_DIR!" mkdir "!APP_DIR!"
cd /d "!APP_DIR!"

call :SYNC_SOURCE_CODE
call :SETUP_PYTHON_ENV
call :ENSURE_ENV_CONFIG

echo.
echo Địa chỉ truy cập ứng dụng: !APP_URL! (Hoạt động độc lập 100%%, không cần Admin)
echo Đang tạo phím tắt trên Desktop...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut([System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'GeminiTrans.lnk')); $s.TargetPath = '%~f0'; $s.Arguments = '1'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'GeminiTrans (http://localhost:8090)'; $s.Save()" >nul 2>&1

echo =======================================================================
echo Cài đặt hoàn tất! Bạn có thể bật ứng dụng ngay bây giờ.
echo =======================================================================
pause
goto MENU

:SYNC_SOURCE_CODE
if exist "app.py" (
    echo Đã có sẵn mã nguồn ứng dụng trong thư mục.
    exit /b 0
)

set "USE_GIT=0"
where git >nul 2>&1
if !errorlevel! equ 0 set "USE_GIT=1"

if "!USE_GIT!"=="0" (
    call :DOWNLOAD_ZIP_SOURCE
    exit /b 0
)

if exist ".git" (
    echo Đang cập nhật mã nguồn mới nhất từ Git...
    git pull origin main
    exit /b 0
)

set "IS_EMPTY=1"
for /f "delims=" %%a in ('dir /b /a 2^>nul') do (
    set "IS_EMPTY=0"
    goto PROCEED_GIT_DOWNLOAD
)

:PROCEED_GIT_DOWNLOAD
if "!IS_EMPTY!"=="1" (
    echo Đang tải mã nguồn từ GitHub qua Git...
    git clone "!REPO_URL!" .
) else (
    echo Thư mục đã có tệp tin. Đang khởi tạo và đồng bộ mã nguồn Git...
    git init >nul 2>&1
    git remote add origin "!REPO_URL!" >nul 2>&1
    git remote set-url origin "!REPO_URL!" >nul 2>&1
    git fetch origin main >nul 2>&1
    git checkout -f -B main origin/main >nul 2>&1
    if not exist "app.py" (
        echo Không thể đồng bộ qua Git, chuyển sang tải gói ZIP...
        call :DOWNLOAD_ZIP_SOURCE
    )
)
exit /b 0

:DOWNLOAD_ZIP_SOURCE
echo Đang tải mã nguồn bản nén ZIP từ GitHub...
set "TEMP_ZIP=%TEMP%\geminitrans_main_%RANDOM%.zip"
set "TEMP_EXTRACT=%TEMP%\geminitrans_ext_%RANDOM%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('!REPO_ZIP_URL!', '!TEMP_ZIP!'); Expand-Archive -Path '!TEMP_ZIP!' -DestinationPath '!TEMP_EXTRACT!' -Force; Copy-Item -Path '!TEMP_EXTRACT!\translate-project-main\*' -Destination '!APP_DIR!' -Recurse -Force; Remove-Item -Path '!TEMP_EXTRACT!' -Recurse -Force; Remove-Item -Path '!TEMP_ZIP!' -Force"
exit /b 0

:SETUP_PYTHON_ENV
call :FIND_PYTHON
if not "!PY_RUN!"=="" goto INSTALL_DEPS

set "SYS_PY="
python -c "import sys" >nul 2>&1
if !errorlevel! equ 0 (
    set "SYS_PY=python"
) else (
    py -c "import sys" >nul 2>&1
    if !errorlevel! equ 0 (
        set "SYS_PY=py"
    )
)

if not "!SYS_PY!"=="" (
    echo Phát hiện Python trên hệ thống: !SYS_PY!
    echo Đang khởi tạo môi trường Python virtualenv độc lập cho ứng dụng...
    if not exist "!APP_DIR!\venv\Scripts\python.exe" (
        "!SYS_PY!" -m venv "!APP_DIR!\venv" >nul 2>&1
    )
    if exist "!APP_DIR!\venv\Scripts\python.exe" (
        set "PY_RUN=!APP_DIR!\venv\Scripts\python.exe"
        goto INSTALL_DEPS
    )
)

echo Đang cài đặt môi trường Python Portable (Standalone, 0%% phụ thuộc máy chủ)...
if not exist "!APP_DIR!\runtime" mkdir "!APP_DIR!\runtime"
if not exist "!APP_DIR!\runtime\python.exe" (
    set "PY_ZIP=%TEMP%\py_embed_%RANDOM%.zip"
    echo Đang tải Python 3.11 Embed...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('!PY_EMBED_URL!', '!PY_ZIP!'); Expand-Archive -Path '!PY_ZIP!' -DestinationPath '!APP_DIR!\runtime' -Force; Remove-Item -Path '!PY_ZIP!' -Force"
    echo Đang cấu hình đường dẫn thư viện Python Embed...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '!APP_DIR!\runtime' -Filter '*._pth' | ForEach-Object { $c = Get-Content $_.FullName; $lines = $c -split '`r?`n'; if (-not ($lines -contains '..')) { $lines += '..' }; if (-not ($lines -contains 'Lib\site-packages')) { $lines += 'Lib\site-packages' }; $lines = $lines | ForEach-Object { $_ -replace '#import site', 'import site' }; if (-not ($lines -contains 'import site')) { $lines += 'import site' }; Set-Content -Path $_.FullName -Value ($lines -join \"`r`n\") }"
    set "GET_PIP_FILE=!APP_DIR!\runtime\get-pip.py"
    echo Đang tải bộ cài pip...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; (New-Object System.Net.WebClient).DownloadFile('!GET_PIP_URL!', '!GET_PIP_FILE!')"
    echo Đang cài đặt pip...
    "!APP_DIR!\runtime\python.exe" "!GET_PIP_FILE!" --no-warn-script-location >nul 2>&1
    if exist "!GET_PIP_FILE!" del /f /q "!GET_PIP_FILE!" >nul 2>&1
)
set "PY_RUN=!APP_DIR!\runtime\python.exe"

:INSTALL_DEPS
if not "!PY_RUN!"=="" (
    echo Đang kiểm tra thư viện cần thiết...
    "!PY_RUN!" -m pip install --upgrade pip >nul 2>&1
    if exist "requirements.txt" (
        echo Đang cài đặt các thư viện từ requirements.txt...
        "!PY_RUN!" -m pip install -r requirements.txt --no-warn-script-location
    )
)
exit /b 0

:ENSURE_ENV_CONFIG
if exist ".env" exit /b 0
if exist "%CURRENT_DIR%\.env" (
    copy "%CURRENT_DIR%\.env" .env >nul
    exit /b 0
)

if exist "!APP_DIR!\.env.enc" (
    echo =======================================================================
    echo Ứng dụng đã được khóa key bảo mật. Vui lòng nhập mật khẩu được cấp:
    set "USER_PASS="
    set /p "USER_PASS=Nhập mật khẩu: "
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = '!USER_PASS!'; $f = '!APP_DIR!\.env.enc'; $out = '!APP_DIR!\.env'; try { $b = [System.IO.File]::ReadAllBytes($f); $m = [System.Text.Encoding]::ASCII.GetString($b, 0, 14); if ($m -eq 'GEMINI_DUAL_V1') { $sM = New-Object byte[](16); [System.Array]::Copy($b, 14, $sM, 0, 16); $ckM = New-Object byte[](48); [System.Array]::Copy($b, 30, $ckM, 0, 48); $sU = New-Object byte[](16); [System.Array]::Copy($b, 78, $sU, 0, 16); $ckU = New-Object byte[](48); [System.Array]::Copy($b, 94, $ckU, 0, 48); $dIV = New-Object byte[](16); [System.Array]::Copy($b, 142, $dIV, 0, 16); $pL = $b.Length - 158; $pD = New-Object byte[]($pL); [System.Array]::Copy($b, 158, $pD, 0, $pL); $dk = $null; try { $k = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($p, $sM, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256); $a = [System.Security.Cryptography.Aes]::Create(); $a.Key = $k.GetBytes(32); $a.IV = $k.GetBytes(16); $c = $a.CreateDecryptor().TransformFinalBlock($ckM, 0, 48); if ($c.Length -eq 32) { $dk = $c } } catch {}; if ($dk -eq $null) { try { $k = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($p, $sU, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256); $a = [System.Security.Cryptography.Aes]::Create(); $a.Key = $k.GetBytes(32); $a.IV = $k.GetBytes(16); $c = $a.CreateDecryptor().TransformFinalBlock($ckU, 0, 48); if ($c.Length -eq 32) { $dk = $c } } catch {} }; if ($dk -eq $null) { throw 'Err' }; $af = [System.Security.Cryptography.Aes]::Create(); $af.Key = $dk; $af.IV = $dIV; $dec = $af.CreateDecryptor().TransformFinalBlock($pD, 0, $pL); [System.IO.File]::WriteAllBytes($out, $dec); Write-Host 'Mở khóa thành công.' -ForegroundColor Green } } catch { Write-Host 'Mật khẩu mở khóa không chính xác.' -ForegroundColor Red }"
)

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
    )
)
exit /b 0

:UPDATE_APP
cls
echo =======================================================================
echo                              CẬP NHẬT
echo =======================================================================
cd /d "!APP_DIR!"

if exist ".env" copy /y ".env" "%TEMP%\geminitrans_env_backup.env" >nul

call :SYNC_SOURCE_CODE

if exist "%TEMP%\geminitrans_env_backup.env" (
    copy /y "%TEMP%\geminitrans_env_backup.env" ".env" >nul
    del /f /q "%TEMP%\geminitrans_env_backup.env" >nul
)

call :FIND_PYTHON
if not "!PY_RUN!"=="" (
    if exist "requirements.txt" (
        echo Đang cập nhật các thư viện phụ thuộc...
        "!PY_RUN!" -m pip install -r requirements.txt --no-warn-script-location
    )
)

echo Cập nhật hoàn tất.
pause
goto MENU

:UNINSTALL_APP
cls
echo =====================================================================
echo                            XOA CAI DAT DU AN
echo =====================================================================
echo Thu muc cai dat: !APP_DIR!
echo.
echo Luu y:
echo - Toan bo ma nguon, moi truong venv va du lieu du an se bi xoa sach.
echo - Duy nhat file 'Gemini_Translate.cmd' se duoc giu lai tai thu muc nay
echo   de ban co the cai dat lai bat cu luc nao.
echo =====================================================================
set /p "confirm=Ban co chac chan muon xoa sach cai dat? (Y/N): "
if /i not "!confirm!"=="Y" goto MENU

echo.
echo [*] Dang dung tien trinh dich vu va web server...
call :STOP_APP >nul 2>&1

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$appPath = [System.IO.Path]::GetFullPath('!APP_DIR!').TrimEnd('\'); " ^
  "Get-CimInstance Win32_Process | Where-Object { " ^
  "    $cmd = $_.CommandLine; " ^
  "    $cmd -and ($cmd -like ('*' + $appPath + '*')) -and ($_.ProcessId -ne $PID) " ^
  "} | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1

cd /d "%TEMP%"

if not exist "!APP_DIR!\Gemini_Translate.cmd" (
    if exist "%~f0" copy /y "%~f0" "!APP_DIR!\Gemini_Translate.cmd" >nul 2>&1
)

echo [*] Dang xoa toan bo cac file va thu muc du an (giu lai Gemini_Translate.cmd)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$appDir = [System.IO.Path]::GetFullPath('!APP_DIR!'); " ^
  "if (Test-Path -LiteralPath $appDir) { " ^
  "    Get-ChildItem -LiteralPath $appDir -Force | Where-Object { $_.Name -ne 'Gemini_Translate.cmd' } | ForEach-Object { " ^
  "        try { " ^
  "            $_.Attributes = 'Normal'; " ^
  "            if ($_.PSIsContainer) { Get-ChildItem -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue | ForEach-Object { $_.Attributes = 'Normal' } } " ^
  "            Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction Stop " ^
  "        } catch { " ^
  "            try { Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue } catch {} " ^
  "        } " ^
  "    }; " ^
  "    $leftover = Get-ChildItem -LiteralPath $appDir -Force | Where-Object { $_.Name -ne 'Gemini_Translate.cmd' }; " ^
  "    if ($leftover) { $leftover | ForEach-Object { try { Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue } catch {} } } " ^
  "}"

if exist "%CONFIG_PATH_FILE%" del /f /q "%CONFIG_PATH_FILE%" >nul 2>&1
set "DESKTOP_LNK=%USERPROFILE%\Desktop\GeminiTrans.lnk"
if exist "!DESKTOP_LNK!" del /f /q "!DESKTOP_LNK!" >nul 2>&1

findstr /C:"translate.local" "%HOSTS_FILE%" >nul 2>&1
if !errorlevel! equ 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Start-Process cmd -ArgumentList '/c (powershell -Command \"\"(Get-Content -Path $env:windir\System32\drivers\etc\hosts) | Where-Object { $_ -notmatch ''translate.local'' } | Set-Content -Path $env:windir\System32\drivers\etc\hosts\"\" ) & (netsh interface portproxy delete v4tov4 listenport=80 listenaddress=127.0.0.1 >nul 2>&1)' -Verb RunAs -Wait -ErrorAction Stop } catch {}" >nul 2>&1
)

cd /d "!APP_DIR!" 2>nul
echo.
echo =====================================================================
echo [THANH CONG] Da xoa sach toan bo du an thanh cong!
echo Thu muc hien tai chi con duy nhat file:
echo   !APP_DIR!\Gemini_Translate.cmd
echo Ban co the chay lai file nay de cai dat moi bat cu khi nao.
echo =====================================================================
pause
goto MENU

:CHECK_STATUS_INTERNAL
set "IS_RUNNING=0"
netstat -ano | findstr /R /C:":!APP_PORT! .*LISTENING" >nul 2>&1
if !errorlevel! equ 0 set "IS_RUNNING=1"
exit /b 0
