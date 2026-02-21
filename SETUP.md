# 系統啟動指南

## 前置需求
- Docker 和 Docker Compose 已安裝
- Python 3.12+ 已安裝（用於導入數據）

## 啟動步驟

### 1. 創建環境變數文件（可選）

如果需要設置 API Key，創建 `.env` 文件：

```bash
echo "API_KEY=your_api_key_here" > .env
```

如果不設置 API_KEY，API 將在開發模式下運行（不需要驗證）。

### 2. 啟動 Docker 服務

啟動數據庫和 API 服務：

```bash
docker-compose up -d
```

這會：
- 啟動 PostgreSQL + PostGIS 數據庫（端口 5433，避免與本地 PostgreSQL 衝突）
- 自動執行 `schema.sql` 創建表結構
- 啟動 FastAPI 服務（端口 8000）

### 3. 等待服務就緒

檢查服務狀態：

```bash
docker-compose ps
```

等待所有服務顯示為 "healthy" 狀態。

### 4. 導入 JSON 數據到數據庫

在本地環境中（不在 Docker 容器內）執行：

```bash
# 設置數據庫連接 URL（注意使用 5433 端口）
export DATABASE_URL="postgresql://coding101:coding101_password@localhost:5433/coding101"

# 導入數據（先測試，不寫入）
python load_to_postgis.py data/build/places.json --dry-run

# 確認無誤後，正式導入
python load_to_postgis.py data/build/places.json
```

### 5. 驗證系統

#### 檢查 API 健康狀態
```bash
curl http://localhost:8000/health
```

應該返回：
```json
{"status":"ok"}
```

#### 測試 API 端點（如果設置了 API_KEY）
```bash
# 獲取地點列表
curl -H "X-API-Key: your_api_key_here" "http://localhost:8000/api/places?category=park&city=taipei"

# 獲取城市列表
curl -H "X-API-Key: your_api_key_here" "http://localhost:8000/api/cities"

# 獲取區域列表
curl -H "X-API-Key: your_api_key_here" "http://localhost:8000/api/districts?city=taipei"
```

如果沒有設置 API_KEY，可以省略 `-H "X-API-Key: ..."` 部分。

## 常用命令

### 查看日誌
```bash
# 查看所有服務日誌
docker-compose logs -f

# 只查看 API 服務日誌
docker-compose logs -f api

# 只查看數據庫服務日誌
docker-compose logs -f db
```

### 停止服務
```bash
docker-compose down
```

### 停止並刪除數據（注意：會清除所有數據）
```bash
docker-compose down -v
```

### 重新構建 API 服務
```bash
docker-compose build api
docker-compose up -d api
```

### 連接到數據庫（用於調試）
```bash
docker-compose exec db psql -U coding101 -d coding101
```

## 故障排除

### 數據庫連接失敗
- 確認數據庫服務已啟動：`docker-compose ps`
- 檢查數據庫日誌：`docker-compose logs db`
- 確認端口 5432 未被占用

### API 服務無法啟動
- 檢查 API 日誌：`docker-compose logs api`
- 確認數據庫服務已就緒（API 依賴數據庫）
- 檢查環境變數是否正確設置

### 數據導入失敗
- 確認數據庫服務正在運行
- 檢查 DATABASE_URL 環境變數是否正確
- 確認 JSON 文件路徑正確
- 使用 `--dry-run` 先測試

