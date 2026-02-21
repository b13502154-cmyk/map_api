"""
環境變數配置管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# API 配置
API_KEY = os.getenv("API_KEY", "")

# 資料檔案路徑（保留作為備用或遷移工具使用）
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "build" / "places.json"

# 資料庫配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://coding101:coding101_password@localhost:5433/coding101"  # 使用 5433 端口避免衝突
)

# 伺服器配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

