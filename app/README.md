# Places API - FastAPI 版本

## 專案結構

```
app/
├── __init__.py
├── main.py              # FastAPI 應用程式主程式
├── config.py            # 環境變數配置
├── services/
│   ├── __init__.py
│   └── places_service.py  # 地點資料服務層
└── README.md            # 本檔案
```

## 啟動方式

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 啟動伺服器

```bash
# 開發模式（自動重新載入）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生產模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. 測試 API

- API 文件（Swagger UI）: http://127.0.0.1:8000/docs
- 替代文件（ReDoc）: http://127.0.0.1:8000/redoc
- 健康檢查: http://127.0.0.1:8000/health
- 地點資料: http://127.0.0.1:8000/api/places

## API 端點

### GET /health

健康檢查端點

**回應範例：**
```json
{
  "status": "ok"
}
```

### GET /api/places

取得地點資料

**查詢參數：**
- `category` (可選): 地點分類，可多個（使用重複參數：`?category=park&category=toilet`）
- `city` (可選): 城市代碼
- `bbox` (可選): 地理範圍，格式 `minLng,minLat,maxLng,maxLat`
- `has_diaper_table` (可選): 是否有尿布台，值為 `"1"` 或 `"0"`
- `has_parking` (可選): 是否有停車場，值為 `"1"` 或 `"0"`
- `include_outdated` (可選): 是否包含過期資料，預設為 `false`

**回應範例：**
```json
{
  "items": [
    {
      "id": "0002b5e8fe4d80bb521a2c8a9d86dd41b09a99fa",
      "name": "北投166號綠地",
      "address": "大業路東側",
      "lat": 25.13051033,
      "lng": 121.49687195,
      "category": "park",
      "city": "taipei",
      "properties": {}
    }
  ],
  "count": 1
}
```

**使用範例：**
```bash
# 取得所有地點
curl http://localhost:8000/api/places

# 依單一分類篩選
curl http://localhost:8000/api/places?category=park

# 依多個分類篩選（使用重複參數）
curl "http://localhost:8000/api/places?category=park&category=toilet"

# 依地理範圍篩選（格式: minLng,minLat,maxLng,maxLat）
curl "http://localhost:8000/api/places?bbox=121.50,25.02,121.58,25.10"

# 組合查詢：多個分類 + 地理範圍
curl "http://localhost:8000/api/places?category=park&category=toilet&bbox=121.50,25.02,121.58,25.10"

# 組合查詢
curl "http://localhost:8000/api/places?category=park&bbox=121.50,25.02,121.58,25.10&has_diaper_table=1"
```

## 環境變數

複製 `.env.example` 為 `.env` 並設定：

```bash
cp .env.example .env
```

可設定項目：
- `API_KEY`: API 金鑰（目前未使用）
- `HOST`: 伺服器主機，預設 `0.0.0.0`
- `PORT`: 伺服器埠號，預設 `8000`

## 與舊版 API 的差異

本 FastAPI 版本提供：

1. **自動 API 文件**：Swagger UI 和 ReDoc
2. **型別驗證**：自動驗證查詢參數格式
3. **更好的錯誤處理**：結構化的錯誤回應
4. **CORS 支援**：內建跨域請求支援
5. **非同步支援**：可擴展為非同步處理

## 開發建議

- 使用 `--reload` 參數進行開發，程式碼變更會自動重新載入
- 透過 `/docs` 端點測試 API 功能
- 生產環境建議使用 Gunicorn + Uvicorn workers

