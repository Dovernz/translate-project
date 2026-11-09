# Hướng Dẫn Tự Động Hóa Dành Cho Antigravity AI Agent (Agent Automation Guide)

Tài liệu này được thiết kế để **bất kỳ Antigravity AI Agent nào** khi tiếp nhận dự án này đều có thể tự động cài đặt môi trường, cấu hình và khởi chạy ứng dụng cho người dùng chỉ với 1 prompt duy nhất.

---

## 🤖 QUY TRÌNH THỰC HIỆN TỰ ĐỘNG CỦA AGENT (RUNBOOK)

Khi người dùng yêu cầu: *"Hãy cài đặt và chạy dự án này trên máy tôi"*, Agent hãy thực hiện tuần tự các bước sau bằng công cụ shell/powershell:

### Bước 1: Kiểm tra Python
Chạy lệnh kiểm tra Python trên máy người dùng:
```powershell
python --version
```
- Nếu đã có Python (>= 3.10): Tiếp tục Bước 2.
- Nếu chưa có Python: Agent hãy tự động cài đặt Python 3.11 bằng lệnh:
  ```powershell
  winget install -e --id Python.Python.3.11 --scope currentuser --accept-package-agreements --accept-source-agreements
  ```
  Sau khi cài xong, nạp lại đường dẫn môi trường:
  ```powershell
  $env:Path = [System.Environment]::GetEnvironmentVariable("Path","User") + ";" + [System.Environment]::GetEnvironmentVariable("Path","Machine")
  ```

### Bước 2: Kiểm tra FFmpeg (Tùy chọn)
Chạy lệnh kiểm tra FFmpeg:
```powershell
ffmpeg -version
```
- Nếu chưa có, Agent có thể cài đặt tự động:
  ```powershell
  winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
  ```
  *(Nếu winget không khả dụng, hệ thống vẫn hoạt động hoàn hảo bằng cơ chế Client-Side Hardsub Burner có sẵn trên trình duyệt).*

### Bước 3: Tạo Virtual Environment & Cài Thư Viện
Tại thư mục gốc của dự án, Agent chạy:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 4: Kiểm tra File `.env`
Kiểm tra xem file `.env` đã tồn tại chưa:
- Nếu chưa có:
  ```powershell
  Copy-Item .env.sample .env
  ```
  Nhắc người dùng dán API Key của họ vào file `.env` (hoặc copy file `.env` từ bạn).

### Bước 5: Khởi Động Server & Mở Trình Duyệt
Agent chạy lệnh khởi động server Uvicorn:
```powershell
python -m uvicorn app:app --host 0.0.0.0 --port 8090 --reload
```
Đồng thời thông báo cho người dùng truy cập tại: **`http://localhost:8090`**.
