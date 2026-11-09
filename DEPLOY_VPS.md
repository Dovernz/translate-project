# Hướng Dẫn Triển Khai GeminiTrans Lên VPS & Quy Trình Dev Song Song

Tài liệu này hướng dẫn cách đưa ứng dụng GeminiTrans lên máy chủ VPS để công khai cho người khác sử dụng, đồng thời giữ nguyên môi trường máy công ty (`localhost:8090`) để tiếp tục lập trình và thử nghiệm an toàn.

---

## 🏗️ 1. Mô Hình Tách Biệt: Local Dev & Production VPS

```
┌─────────────────────────────────┐           ┌──────────────────────────────────┐
│        MÁY TÍNH CÔNG TY         │           │             MÁY CHỦ VPS          │
│   (Không cần mở IP, mạng nội bộ)│           │   (IP tĩnh công khai / Tên miền) │
├─────────────────────────────────┤           ├──────────────────────────────────┤
│ 1. Code & Test: localhost:8090  │           │ 1. Chạy dịch vụ cho người ngoài  │
│ 2. Docker container nội bộ      │           │ 2. Nginx Reverse Proxy + SSL     │
│ 3. Git push cập nhật tính năng  │──Git Push─▶ 3. Git pull cập nhật tức thì     │
└─────────────────────────────────┘           └──────────────────────────────────┘
```

---

## 🚀 2. Các Bước Cài Đặt Trên VPS (Lần Đầu Tiên)

### Bước 2.1: Cài đặt Docker & Nginx trên VPS (Ubuntu 22.04 / 24.04)
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-v2 nginx certbot python3-certbot-nginx git curl
sudo systemctl enable --now docker nginx
```

### Bước 2.2: Clone mã nguồn & Cấu hình biến môi trường
```bash
git clone https://github.com/Dovernz/translate-project.git /opt/translate-project
cd /opt/translate-project
```
Tạo file `.env` bằng cách copy nội dung từ file `.env` trên máy của bạn (chứa 7 Gemini API Keys):
```bash
nano .env
# Dán toàn bộ nội dung file .env của bạn vào đây rồi bấm Ctrl+O -> Enter -> Ctrl+X
```

### Bước 2.3: Khởi chạy ứng dụng qua Docker
```bash
docker compose up -d --build
```
Kiểm tra container đang chạy:
```bash
docker ps
# Thấy geminitrans_app ở trạng thái Up (0.0.0.0:8090->8000/tcp)
```

### Bước 2.4: Cấu hình Nginx làm Reverse Proxy
```bash
sudo cp nginx/geminitrans.conf /etc/nginx/sites-available/geminitrans
sudo nano /etc/nginx/sites-available/geminitrans
# Sửa 'your-domain.com' thành tên miền của bạn (hoặc địa chỉ IP VPS)

# Kích hoạt cấu hình
sudo ln -s /etc/nginx/sites-available/geminitrans /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Bước 2.5: Cài đặt chứng chỉ SSL HTTPS miễn phí (Let's Encrypt)
*(Bắt buộc nếu muốn dùng tính năng ghi âm giọng nói Microphone qua mạng ngoài)*:
```bash
sudo certbot --nginx -d your-domain.com
```

---

## 🔄 3. Quy Trình Cập Nhật (Khi Bạn Sửa Code Ở Máy Công Ty)

Khi bạn code xong tính năng mới trên máy công ty:
1. **Tại máy công ty:**
   ```bash
   git add .
   git commit -m "feat: mo ta tinh nang moi"
   git push origin main
   ```
2. **Tại VPS (Chỉ cần 1 lệnh duy nhất):**
   ```bash
   cd /opt/translate-project && git pull && docker compose restart
   ```
   *Mọi tính năng mới sẽ được áp dụng ngay lập tức cho tất cả người dùng trên VPS mà không làm gián đoạn hệ thống.*

---

## 💡 4. Giải Pháp Test Nhanh Từ Máy Công Ty (Không Cần VPS)

Nếu bạn chưa kịp mua VPS nhưng muốn **gửi link cho sếp hoặc đồng nghiệp dùng thử ngay từ máy công ty** mà không thể mở IP/port mạng công ty:
- Hãy sử dụng **Cloudflare Tunnel (Hoàn toàn miễn phí & Bảo mật)**:
  1. Tải `cloudflared` về máy.
  2. Gõ lệnh:
     ```bash
     cloudflared tunnel --url http://localhost:8090
     ```
  3. Cloudflare sẽ cấp cho bạn một đường link HTTPS công khai (ví dụ: `https://random-words.trycloudflare.com`). Bạn gửi link này cho bất kỳ ai trên internet đều vào dùng được mà mạng công ty hoàn toàn không bị chặn!
