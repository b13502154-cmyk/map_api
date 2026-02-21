# Dockerfile for Coding101 Project
# 特別處理 truststore 在 Docker 環境下的 SSL 憑證問題

FROM python:3.12-slim

# 設置工作目錄
WORKDIR /app

# 安裝系統 CA 憑證（重要：確保 SSL 驗證正常工作）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 更新 CA 憑證
RUN update-ca-certificates

# 設置環境變數，標識 Docker 環境
ENV DOCKER_ENV=true
ENV PYTHONUNBUFFERED=1

# 複製依賴檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼（只複製必要的檔案）
COPY app/ ./app/

# 複製成品資料（places.json 必須在建置 Image 時已存在）
COPY data/build/places.json ./data/build/places.json

# 設置 Python 路徑
ENV PYTHONPATH=/app

# 預設命令（可以根據需要修改）
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT


