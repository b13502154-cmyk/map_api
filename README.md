## Places API（FastAPI 伺服器）使用說明

這個專案提供一個以 **FastAPI** 實作的後端服務（`app/main.py`），提供前端地圖應用查詢地點資料的 REST API。

以下說明如何在本機啟動與使用這個伺服器。

---

## 專案結構（重要部分）

```text
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 應用程式主程式（伺服器程式）
│   ├── config.py            # 環境變數 / 設定
│   └── services/
│       ├── __init__.py
│       └── places_service.py  # 地點資料查詢邏輯
├── data/
│   └── build/
│       └── places.json      # 匯入用的地點資料（若有）
├── schema.sql               # 資料庫 schema
├── load_to_postgis.py       # 將資料載入 PostgreSQL / PostGIS 的腳本
├── requirements.txt         # Python 套件清單
├── Dockerfile               # 伺服器 Docker 映像檔設定（可選）
├── docker-compose.yml       # 使用 Docker 啟動 DB + API（可選）
└── README.md                # 本說明文件
```

---

## 環境需求

- **Python**：建議 3.10+（3.11 也可）
- **資料庫**：PostgreSQL（建議搭配 PostGIS，如果要用空間查詢）
- 作業系統：macOS / Linux / WSL 皆可

你可以：

- 直接在本機安裝 PostgreSQL，或
- 使用 `docker-compose.yml` 啟一個 PostgreSQL + API 環境。

---

## 1. 安裝 Python 依賴

在專案根目錄（有 `requirements.txt` 的那層）執行：

```bash
pip install -r requirements.txt
```

建議先建立虛擬環境（可選）：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows 則為 .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2. 設定環境變數

伺服器主要會用到下列環境變數（由 `app/config.py` 讀取）：

- **`DATABASE_URL`**：PostgreSQL 連線字串  
  - 範例：`postgresql://user:password@localhost:5432/places`
- **`API_KEY`**（可選）：若有設定，所有 `/api/...` 相關端點都需要在請求 Header 帶上 `X-API-Key`  
  - 若 **沒設定** `API_KEY`，則視為開發模式，不會檢查 API Key。

你可以在 shell 中直接 export，例如：

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/places"
export API_KEY="my-secret-key"  # 開發階段也可先不設
```

或使用 `.env` 檔（只要 `app/config.py` 有載入 `python-dotenv` 即可）。

---

## 3. 準備資料庫

### 3.1 建立資料庫與表

1. 先在 PostgreSQL 裡建立一個資料庫（例如 `places`）
2. 在該資料庫中執行 `schema.sql`：

```bash
psql -d places -f schema.sql
```

（如果使用 Docker，連線參數請依你的 `docker-compose.yml` 設定調整）

### 3.2 匯入地點資料（若需要）

若你需要將 `data/build/places.json` 載入資料庫，可執行：

```bash
python load_to_postgis.py
```

這支腳本會讀取 JSON 檔，並依 `DATABASE_URL` 寫入 PostgreSQL / PostGIS 中對應的表。

---

## 4. 啟動伺服器

### 4.1 直接用 Uvicorn 啟動

在專案根目錄執行：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- `--reload`：開發模式，程式碼變更會自動重新載入
- 預設會在 `http://127.0.0.1:8000` 提供服務

如果要不用 `--reload`（較接近生產環境）：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
``]

### 4.2 使用 Docker / docker-compose（可選）

若你想用 Docker 來簡化環境設定，可依照自己的 `Dockerfile` / `docker-compose.yml` 內容啟動，例如：

```bash
docker-compose up --build
```

啟動成功後，就可以從對應的埠號存取 API（通常也是 `http://localhost:8000`，視 compose 設定而定）。

---

## 5. 可用 API 端點（來自 `app/main.py`）

### 5.1 健康檢查

- **`GET /health`**  
  - 不需要 API Key  
  - 確認伺服器本身是否正常

範例：

```bash
curl http://127.0.0.1:8000/health
```

回應範例：

```json
{
  "status": "ok"
}
```

### 5.2 資料庫連線檢查

- **`GET /api/db`**  
  - 不需要 API Key  
  - 會實際嘗試連線資料庫並執行 `SELECT 1`

範例：

```bash
curl http://127.0.0.1:8000/api/db
```

---

### 5.3 查詢地點列表

- **`GET /api/places`**  
  - **若設定了 `API_KEY`**：必須在 Header 加上 `X-API-Key: <你的 key>`  
  - 查詢參數（全部皆為可選）：
    - `category`: 地點分類，可重複多個（例如 `?category=park&category=toilet`）
    - `city`: 城市代碼，例如 `taipei`
    - `bbox`: 地理範圍，格式 `minLng,minLat,maxLng,maxLat`
    - `has_diaper_table`: 是否有尿布台，`"1"` 或 `"0"`
    - `has_parking`: 是否有停車場，`"1"` 或 `"0"`
    - `include_outdated`: 是否包含過期資料，布林值

範例：

```bash
# 取得所有地點（未設定 API_KEY 時）
curl "http://127.0.0.1:8000/api/places"

# 有設定 API_KEY 時
curl "http://127.0.0.1:8000/api/places" \
  -H "X-API-Key: my-secret-key"

# 依分類與地理範圍篩選
curl "http://127.0.0.1:8000/api/places?category=park&bbox=121.5,25.02,121.58,25.10"
```

---

### 5.4 取得城市列表

- **`GET /api/cities`**  
  - 需要 API Key（若有設定 `API_KEY`）
  - 查詢參數：
    - `category`（可選，多個）：依分類過濾
    - `include_outdated`（可選，布林）：是否包含過期資料

範例：

```bash
curl "http://127.0.0.1:8000/api/cities" \
  -H "X-API-Key: my-secret-key"
```

---

### 5.5 取得某城市的行政區列表

- **`GET /api/districts`**  
  - 需要 API Key（若有設定 `API_KEY`）
  - 查詢參數：
    - `city`（必填）：城市代碼
    - `category`（可選，多個）：依分類過濾
    - `include_outdated`（可選，布林）：是否包含過期資料

範例：

```bash
curl "http://127.0.0.1:8000/api/districts?city=taipei" \
  -H "X-API-Key: my-secret-key"
```

---

## 6. 開發小提示

- **優先只看 `app/main.py`**：這是主要的伺服器程式，包含所有路由定義與 API Key 驗證邏輯。
- 若要修改查詢邏輯、欄位名稱或篩選條件，請到 `app/services/places_service.py`。
- 新增 API 時，建議：
  1. 在 `app/main.py` 新增 FastAPI 路由
  2. 把實際資料處理邏輯拆到 `app/services/` 內的服務函式

