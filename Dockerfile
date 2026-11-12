# ==========================================
# GeminiTrans Multi-Modal Translator Dockerfile
# ==========================================
FROM python:3.12-slim
COPY --from=denoland/deno:bin-2.9.8 /deno /usr/local/bin/deno

# Thiết lập môi trường không đệm stdout và không sinh pyc rác
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Cài đặt ffmpeg cho xử lý luồng âm thanh/video và curl cho healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt uv siêu tốc từ astral-sh
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Sao chép đặc tả dependency
COPY pyproject.toml requirements.txt* ./

# Cài đặt toàn bộ dependencies vào system environment
RUN uv pip install --system --no-cache -r pyproject.toml

# Sao chép toàn bộ mã nguồn
COPY . .

# Mở cổng dịch vụ
EXPOSE 8000

# Healthcheck định kỳ
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/api/pool-status || exit 1

# Khởi chạy ứng dụng với Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
