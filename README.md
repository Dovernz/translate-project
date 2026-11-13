# 🌐 GeminiTrans: Web Dịch Đa Phương Tiện & Phụ Đề Video Realtime (Docker-First)

Hệ thống dịch thuật siêu tốc khai thác 100% tiềm năng ma trận model Google AI Studio kết hợp Smart Key Pool xoay vòng 7 Cloud Projects để triệt tiêu giới hạn RPM/TPM và đạt hạn mức không giới hạn (Unlimited RPD).

---

## ⚡ 1. Tính Năng Nổi Bật

1. **Dịch Văn Bản & Tài Liệu Siêu Tốc (Streaming Translation):**
   - Hỗ trợ dịch trực tiếp song song qua Server-Sent Events (SSE), từ chạy mượt mà theo thời gian thực.
   - Nạp và dịch trực tiếp các file tài liệu: `.txt`, `.md`, `.srt`, `.vtt`, `.json`, `.csv` giữ nguyên cấu trúc.
   - Tự động định tuyến đa tầng:
     * `bulk` (`gemini-3.5-flash-lite`): 7.000 req/ngày, 210 RPM.
     * `ultra` (`gemma-4-26b-a4b-it`): 100.800 req/ngày, 210 RPM.
     * `standard` (`gemini-3.6-flash`): 420 req/ngày, 105 RPM.
     * `deep` (`gemini-3.8-flash`): 140 req/ngày, 35 RPM.

2. **Dịch Phim & Video Trực Tuyến với Độ Trễ Thấp Nhất (Realtime Video Subtitler):**
   - Dán đường dẫn video từ các extractor yt-dlp (YouTube, Archive.org, Wikimedia và nhiều dịch vụ khác), hoặc link media/stream MP4, HLS, DASH công khai.
   - Streamlink là fallback bổ sung cho một số nguồn stream công khai mà yt-dlp không trích xuất được. Nguồn cần đăng nhập, bị giới hạn truy cập, hoặc dùng DRM không được vượt qua.
   - Với YouTube, hệ thống thử phụ đề công khai trước, sau đó thử Gemini Interactions API cho video công khai; nếu transcript khả dụng, phát qua YouTube IFrame chính thức mà không tải media về server. Đây là best-effort, không đảm bảo transcript có sẵn hoặc tránh được giới hạn API.
   - Trình phát tích hợp kèm **Floating Subtitle Overlay** đè trực tiếp lên khung hình video (phong cách Netflix).
   - Khi không có transcript, người dùng có thể chủ động chia sẻ tab/màn hình kèm audio trên trình duyệt hỗ trợ; audio được gửi theo chunk. Không dùng microphone làm nguồn thay thế và không có cách thu trực tiếp audio của tab khác nếu browser không cấp track.
   - Gemini Key Pool chuyển sang các key khả dụng khi gặp HTTP 429/quota; failover không loại bỏ giới hạn quota hay đảm bảo luôn có key khả dụng.

3. **Ghi Âm & Transcribe Giọng Nói (Speech-to-Text):**
   - Thu âm trực tiếp qua Microphone của trình duyệt hoặc tải lên file âm thanh (`.mp3`, `.wav`, `.m4a`).
   - Tận dụng Gemini Multimodal Audio Model để trích xuất nguyên văn transcript kèm dịch song ngữ sang Tiếng Việt.

4. **Bảng Giám Sát Smart Key Pool (Live HUD):**
   - Theo dõi trạng thái từng key: 🟢 Sẵn sàng, 🟡 Cooldown (nếu gặp 429), tổng số lượt gọi và con trỏ hiện tại.

---

## 🐳 2. Khởi Chạy với Docker (Khuyến Nghị Toàn Hệ Thống)

Dự án tuân thủ chuẩn **Docker-First**, được đóng gói trọn gói kèm `ffmpeg`, `uv`, `fastapi` và healthcheck tự động:

```powershell
cd "d:\Thành\Translate"
docker compose up -d
```

- **Cổng truy cập Web:** [http://localhost:8090](http://localhost:8090)
- **Kiểm tra trạng thái container:**
```powershell
docker compose ps
docker compose logs -f
```
- **Dừng container:**
```powershell
docker compose down
```

Hoặc bấm đúp chuột vào file `run_app.bat` và chọn `1` để khởi chạy tự động.
