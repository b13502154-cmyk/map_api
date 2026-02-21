"""
FastAPI 應用程式主程式
"""
import json
from typing import List
from fastapi import FastAPI, HTTPException, Query, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.services.places_service import get_places, get_cities, get_districts
from app.config import DATA_FILE, API_KEY

app = FastAPI(
    title="Places API",
    description="提供地點資料的 REST API，供前端地圖應用使用",
    version="1.0.0",
)

# CORS 設定（允許跨域請求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開發階段允許所有來源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """
    API Key 驗證依賴項
    
    如果設定了 API_KEY 環境變數，則需要驗證 Header 中的 X-API-Key
    如果未設定 API_KEY，則允許所有請求（開發模式）
    """
    if API_KEY:  # 只有在設定了 API_KEY 時才驗證
        if not x_api_key:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "missing_api_key",
                    "message": "缺少 API Key，請在 Header 中提供 X-API-Key"
                }
            )
        if x_api_key != API_KEY:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "invalid_api_key",
                    "message": "API Key 無效"
                }
            )
    return True


@app.get("/health")
def health():
    """
    健康檢查端點（不需要 API Key）
    """
    return {"status": "ok"}


@app.get("/api/places")
def api_places(
    category: List[str] | None = Query(None, description="地點分類篩選（可多個，例如：?category=park&category=toilet）"),
    city: str | None = Query(None, description="城市代碼篩選"),
    bbox: str | None = Query(
        None,
        description="地理範圍篩選，格式: minLng,minLat,maxLng,maxLat",
        example="121.50,25.02,121.58,25.10"
    ),
    has_diaper_table: str | None = Query(
        None,
        description="是否有尿布台，值為 '1' 或 '0'",
        regex="^[01]$"
    ),
    has_parking: str | None = Query(
        None,
        description="是否有停車場，值為 '1' 或 '0'",
        regex="^[01]$"
    ),
    include_outdated: bool = Query(
        False,
        description="是否包含過期資料"
    ),
    _: bool = Depends(verify_key),  # API Key 驗證
):
    """
    取得地點資料
    
    支援多種查詢參數進行篩選：
    - category: 依分類篩選（可多個，使用重複參數：?category=park&category=toilet）
    - city: 依城市篩選
    - bbox: 依地理範圍篩選（地圖視窗）
    - has_diaper_table: 是否有尿布台
    - has_parking: 是否有停車場
    - include_outdated: 是否包含過期資料
    
    所有參數皆為可選，可單獨或組合使用。
    """
    try:
        # 檢查資料檔案是否存在
        if not DATA_FILE.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "missing_data",
                    "message": f"資料檔案不存在: {DATA_FILE}"
                }
            )

        # 取得並篩選資料
        result = get_places(
            category=category,
            city=city,
            bbox=bbox,
            has_diaper_table=has_diaper_table,
            has_parking=has_parking,
            include_outdated=include_outdated,
        )

        return result

    except ValueError as e:
        # bbox 格式錯誤
        raise HTTPException(
            status_code=400,
            detail={
                "error": "bad_bbox",
                "message": str(e)
            }
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "missing_data",
                "message": str(e)
            }
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "bad_json",
                "message": f"資料檔案 JSON 格式錯誤: {str(e)}"
            }
        )
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "io_error",
                "message": f"讀取資料檔案失敗: {str(e)}"
            }
        )
    except Exception as e:
        # 未預期的錯誤
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"未預期的伺服器錯誤: {str(e)}"
            }
        )


@app.get("/api/cities")
def api_cities(
    category: List[str] | None = Query(None, description="地點分類篩選（可多個，例如：?category=public_kindergarten&category=private_kindergarten）"),
    include_outdated: bool = Query(
        False,
        description="是否包含過期資料"
    ),
    _: bool = Depends(verify_key),  # API Key 驗證
):
    """
    取得可用城市列表
    
    支援以下查詢參數：
    - category: 依分類篩選（可多個）
    - include_outdated: 是否包含過期資料
    
    返回可用城市及各城市的資料數量。
    """
    try:
        # 檢查資料檔案是否存在
        if not DATA_FILE.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "missing_data",
                    "message": f"資料檔案不存在: {DATA_FILE}"
                }
            )

        # 取得城市列表
        result = get_cities(
            category=category,
            include_outdated=include_outdated,
        )

        return result

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "missing_data",
                "message": str(e)
            }
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "bad_json",
                "message": f"資料檔案 JSON 格式錯誤: {str(e)}"
            }
        )
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "io_error",
                "message": f"讀取資料檔案失敗: {str(e)}"
            }
        )
    except Exception as e:
        # 未預期的錯誤
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"未預期的伺服器錯誤: {str(e)}"
            }
        )


@app.get("/api/districts")
def api_districts(
    city: str = Query(..., description="城市代碼（必需），例如：taipei"),
    category: List[str] | None = Query(None, description="地點分類篩選（可多個）"),
    include_outdated: bool = Query(
        False,
        description="是否包含過期資料"
    ),
    _: bool = Depends(verify_key),  # API Key 驗證
):
    """
    取得指定城市的區域列表
    
    支援以下查詢參數：
    - city: 城市代碼（必需，例如 taipei）
    - category: 依分類篩選（可多個）
    - include_outdated: 是否包含過期資料
    
    返回該城市的可用區域及各區域的資料數量。
    """
    try:
        # 檢查資料檔案是否存在
        if not DATA_FILE.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "missing_data",
                    "message": f"資料檔案不存在: {DATA_FILE}"
                }
            )

        # 取得區域列表
        result = get_districts(
            city=city,
            category=category,
            include_outdated=include_outdated,
        )

        return result

    except ValueError as e:
        # 參數驗證錯誤
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_parameter",
                "message": str(e)
            }
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "missing_data",
                "message": str(e)
            }
        )
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "bad_json",
                "message": f"資料檔案 JSON 格式錯誤: {str(e)}"
            }
        )
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "io_error",
                "message": f"讀取資料檔案失敗: {str(e)}"
            }
        )
    except Exception as e:
        # 未預期的錯誤
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"未預期的伺服器錯誤: {str(e)}"
            }
        )

