"""
Places 服務層
負責從資料庫載入、篩選和處理地點資料
"""
import json
from typing import Optional, List
import psycopg
from psycopg.rows import dict_row
from app.config import DATABASE_URL


def normalize_place_from_db(row: dict) -> dict:
    """
    從資料庫行資料正規化為 API 格式
    
    參數:
        row: 資料庫查詢結果（使用 psycopg.rows.dict_row）
    
    返回:
        dict: 正規化後的地點資料
    """
    # 從 properties JSONB 取得額外屬性
    properties = row.get("properties", {})
    if isinstance(properties, str):
        properties = json.loads(properties)
    elif properties is None:
        properties = {}
    
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "address": row.get("address"),
        "lat": row.get("lat"),  # 查詢時會使用 ST_Y(geom)
        "lng": row.get("lng"),  # 查詢時會使用 ST_X(geom)
        "category": row.get("category"),
        "city": row.get("city"),
        "properties": properties,
    }


def build_places_query(
    category: Optional[List[str]] = None,
    city: Optional[str] = None,
    bbox: Optional[str] = None,
    has_diaper_table: Optional[str] = None,
    has_parking: Optional[str] = None,
    include_outdated: bool = False,
) -> tuple[str, list]:
    """
    建構 SQL 查詢和參數
    
    返回:
        tuple: (SQL 查詢字串, 參數列表)
    """
    # 基礎查詢：從 places 表選擇資料，並提取座標
    base_query = """
        SELECT 
            id,
            name,
            address,
            category,
            city,
            ST_Y(geom) AS lat,
            ST_X(geom) AS lng,
            properties
        FROM places
        WHERE 1=1
    """
    
    params = []
    conditions = []
    
    # 過濾過期資料
    if not include_outdated:
        conditions.append("(properties->>'data_status' IS NULL OR properties->>'data_status' != 'outdated')")
    
    # 分類篩選
    if category:
        if isinstance(category, list) and len(category) > 0:
            placeholders = ",".join(["%s"] * len(category))
            conditions.append(f"category IN ({placeholders})")
            params.extend(category)
        elif isinstance(category, str):
            conditions.append("category = %s")
            params.append(category)
    
    # 城市篩選
    if city:
        conditions.append("city = %s")
        params.append(city)
    
    # 地理範圍篩選 (bbox)
    if bbox:
        try:
            parts = bbox.split(",")
            if len(parts) == 4:
                min_lng, min_lat, max_lng, max_lat = map(float, parts)
                conditions.append("ST_Within(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))")
                params.extend([min_lng, min_lat, max_lng, max_lat])
            else:
                raise ValueError("bbox 格式錯誤")
        except (ValueError, TypeError) as e:
            raise ValueError(f"bbox 格式錯誤: {bbox}，應為 minLng,minLat,maxLng,maxLat") from e
    
    # 尿布台篩選
    if has_diaper_table:
        if has_diaper_table == "1":
            conditions.append("(properties->>'diaper_table_count')::int > 0")
        elif has_diaper_table == "0":
            conditions.append("((properties->>'diaper_table_count')::int = 0 OR properties->>'diaper_table_count' IS NULL)")
    
    # 停車場篩選
    if has_parking:
        if has_parking == "1":
            conditions.append("""
                (
                    (properties->>'has_parking')::boolean = true
                    OR (properties->>'parking')::boolean = true
                    OR (properties->>'parking_count')::int > 0
                )
            """)
        elif has_parking == "0":
            conditions.append("""
                NOT (
                    (properties->>'has_parking')::boolean = true
                    OR (properties->>'parking')::boolean = true
                    OR (properties->>'parking_count')::int > 0
                )
            """)
    
    # 組合查詢
    if conditions:
        base_query += " AND " + " AND ".join(conditions)
    
    return base_query, params


def get_places(
    category: Optional[List[str]] = None,
    city: Optional[str] = None,
    bbox: Optional[str] = None,
    has_diaper_table: Optional[str] = None,
    has_parking: Optional[str] = None,
    include_outdated: bool = False,
) -> dict:
    """
    取得地點資料（主要入口函數）
    
    參數:
        category: 分類篩選（可多個，列表）
        city: 城市篩選
        bbox: 地理範圍篩選
        has_diaper_table: 是否有尿布台
        has_parking: 是否有停車場
        include_outdated: 是否包含過期資料
    
    返回:
        dict: {"items": [...], "count": int}
    """
    query, params = build_places_query(
        category=category,
        city=city,
        bbox=bbox,
        has_diaper_table=has_diaper_table,
        has_parking=has_parking,
        include_outdated=include_outdated,
    )
    
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            
            # 正規化資料
            places = []
            for row in rows:
                normalized = normalize_place_from_db(row)
                if normalized:
                    places.append(normalized)
            
            return {
                "items": places,
                "count": len(places),
            }


def get_cities(
    category: Optional[List[str]] = None,
    include_outdated: bool = False,
) -> dict:
    """
    取得可用城市列表
    
    參數:
        category: 分類篩選（可多個，列表）- 只返回有指定類別資料的城市
        include_outdated: 是否包含過期資料
    
    返回:
        dict: {
            "cities": [
                {"code": "taipei", "name": "台北", "count": 150},
                ...
            ]
        }
    """
    # 建構查詢
    base_query = """
        SELECT 
            city,
            COUNT(*) as count
        FROM places
        WHERE 1=1
    """
    
    params = []
    conditions = []
    
    # 過濾過期資料
    if not include_outdated:
        conditions.append("(properties->>'data_status' IS NULL OR properties->>'data_status' != 'outdated')")
    
    # 分類篩選
    if category:
        if isinstance(category, list) and len(category) > 0:
            placeholders = ",".join(["%s"] * len(category))
            conditions.append(f"category IN ({placeholders})")
            params.extend(category)
        elif isinstance(category, str):
            conditions.append("category = %s")
            params.append(category)
    
    if conditions:
        base_query += " AND " + " AND ".join(conditions)
    
    base_query += " GROUP BY city ORDER BY city"
    
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(base_query, params)
            rows = cur.fetchall()
            
            cities = []
            for row in rows:
                city_code = row.get("city")
                # 嘗試從資料庫中取得城市名稱（從 properties 中）
                # 這裡簡化處理，使用城市代碼作為名稱
                # 如果需要更精確的名稱，可以從第一個該城市的記錄中取得
                city_name = city_code  # 預設使用代碼
                
                # 嘗試取得城市名稱
                name_query = """
                    SELECT properties->>'city_name' as city_name
                    FROM places
                    WHERE city = %s
                    AND properties->>'city_name' IS NOT NULL
                    LIMIT 1
                """
                cur.execute(name_query, [city_code])
                name_row = cur.fetchone()
                if name_row and name_row.get("city_name"):
                    city_name = name_row.get("city_name")
                
                cities.append({
                    "code": city_code,
                    "name": city_name,
                    "count": row.get("count", 0),
                })
            
            return {
                "cities": cities,
            }


def get_districts(
    city: str,
    category: Optional[List[str]] = None,
    include_outdated: bool = False,
) -> dict:
    """
    取得指定城市的區域列表
    
    參數:
        city: 城市代碼（必需）
        category: 分類篩選（可多個，列表）
        include_outdated: 是否包含過期資料
    
    返回:
        dict: {
            "city": "taipei",
            "districts": [
                {"name": "中正區", "count": 25},
                ...
            ]
        }
    """
    if not city:
        raise ValueError("city 參數必需")
    
    # 建構查詢
    base_query = """
        SELECT 
            properties->>'district' as district,
            COUNT(*) as count
        FROM places
        WHERE city = %s
    """
    
    params = [city]
    conditions = []
    
    # 過濾過期資料
    if not include_outdated:
        conditions.append("(properties->>'data_status' IS NULL OR properties->>'data_status' != 'outdated')")
    
    # 分類篩選
    if category:
        if isinstance(category, list) and len(category) > 0:
            placeholders = ",".join(["%s"] * len(category))
            conditions.append(f"category IN ({placeholders})")
            params.extend(category)
        elif isinstance(category, str):
            conditions.append("category = %s")
            params.append(category)
    
    if conditions:
        base_query += " AND " + " AND ".join(conditions)
    
    base_query += " AND properties->>'district' IS NOT NULL"
    base_query += " GROUP BY properties->>'district' ORDER BY properties->>'district'"
    
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(base_query, params)
            rows = cur.fetchall()
            
            districts = []
            for row in rows:
                district_name = row.get("district")
                if district_name:
                    districts.append({
                        "name": district_name,
                        "count": row.get("count", 0),
                    })
            
            return {
                "city": city,
                "districts": districts,
            }
