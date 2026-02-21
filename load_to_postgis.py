#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
將 build 產出的 places.json / places.jsonl 匯入 Postgres+PostGIS 的 places 表。

使用方式：
  export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
  python load_to_postgis.py data/build/places.json

可選參數：
  --batch-size 1000
  --jsonl  （強制當 JSONL 解析）
  --dry-run （只統計不寫入）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

# 優先用 psycopg3（若環境沒有就退回 psycopg2）
try:
    import psycopg  # type: ignore
    PSYCOPG_MAJOR = 3
except Exception:
    psycopg = None  # type: ignore
    PSYCOPG_MAJOR = 0

try:
    import psycopg2  # type: ignore
    import psycopg2.extras  # type: ignore
    PSYCOPG2_AVAILABLE = True
except Exception:
    psycopg2 = None  # type: ignore
    PSYCOPG2_AVAILABLE = False


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def load_json_array(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    raise ValueError("JSON 檔頂層不是陣列（list）。若是 JSONL，請加 --jsonl 或改用 .jsonl")


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as ex:
                raise ValueError(f"JSONL 第 {i} 行解析失敗：{ex}") from ex
            if not isinstance(obj, dict):
                raise ValueError(f"JSONL 第 {i} 行不是物件（dict）")
            rows.append(obj)
    return rows


def coerce_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        v = v.strip()
        if v == "":
            return None
        try:
            return float(v)
        except ValueError:
            return None
    return None


def extract_lat_lng(place: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    # 優先用 location.lat/lng
    loc = place.get("location") or {}
    lat = coerce_float(loc.get("lat"))
    lng = coerce_float(loc.get("lng"))

    # 若缺漏，退回 properties.lat/lng（你的資料有時可能重複放）
    if lat is None or lng is None:
        props = place.get("properties") or {}
        lat2 = coerce_float(props.get("lat"))
        lng2 = coerce_float(props.get("lng"))
        lat = lat if lat is not None else lat2
        lng = lng if lng is not None else lng2

    return lat, lng


def normalize_place(place: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pid = place.get("id")
    name = place.get("name")
    category = place.get("category")
    city = place.get("city")

    if not pid or not isinstance(pid, str):
        return None
    if not name or not isinstance(name, str):
        return None
    if not category or not isinstance(category, str):
        return None
    if not city or not isinstance(city, str):
        return None

    address = place.get("address")
    if address is not None and not isinstance(address, str):
        address = str(address)

    lat, lng = extract_lat_lng(place)
    if lat is None or lng is None:
        # 沒座標就跳過（因為 places.geom NOT NULL）
        return None

    props = place.get("properties")
    if props is None:
        props = {}
    if not isinstance(props, dict):
        # 保底：不是 dict 就包成 {"_raw": ...}
        props = {"_raw": props}

    return {
        "id": pid,
        "name": name,
        "address": address,
        "category": category,
        "city": city,
        "lat": lat,
        "lng": lng,
        "properties": props,
    }


UPSERT_SQL = """
INSERT INTO places (id, name, address, category, city, geom, properties)
VALUES (
  %(id)s,
  %(name)s,
  %(address)s,
  %(category)s,
  %(city)s,
  ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326),
  %(properties)s::jsonb
)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  address = EXCLUDED.address,
  category = EXCLUDED.category,
  city = EXCLUDED.city,
  geom = EXCLUDED.geom,
  properties = EXCLUDED.properties;
"""


def chunked(items: List[Dict[str, Any]], n: int) -> Iterable[List[Dict[str, Any]]]:
    for i in range(0, len(items), n):
        yield items[i : i + n]


def run_import_psycopg2(
    database_url: str,
    rows: List[Dict[str, Any]],
    batch_size: int,
    dry_run: bool,
) -> None:
    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            if dry_run:
                eprint(f"[DRY RUN] 解析後可匯入筆數：{len(rows)}（不寫入 DB）")
                return

            total = 0
            for batch in chunked(rows, batch_size):
                # psycopg2.extras.execute_batch 會比較快
                psycopg2.extras.execute_batch(cur, UPSERT_SQL, batch, page_size=batch_size)
                total += len(batch)
                conn.commit()
                eprint(f"已匯入/更新 {total}/{len(rows)} 筆")

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_import_psycopg3(
    database_url: str,
    rows: List[Dict[str, Any]],
    batch_size: int,
    dry_run: bool,
) -> None:
    # psycopg3
    assert psycopg is not None
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            if dry_run:
                eprint(f"[DRY RUN] 解析後可匯入筆數：{len(rows)}（不寫入 DB）")
                return

            total = 0
            for batch in chunked(rows, batch_size):
                cur.executemany(UPSERT_SQL, batch)
                conn.commit()
                total += len(batch)
                eprint(f"已匯入/更新 {total}/{len(rows)} 筆")


def main() -> int:
    parser = argparse.ArgumentParser(description="匯入 places.json 到 Postgres/PostGIS（UPSERT）")
    parser.add_argument("input", help="places.json 或 places.jsonl 的路徑")
    parser.add_argument("--batch-size", type=int, default=1000, help="每批寫入筆數（預設 1000）")
    parser.add_argument("--jsonl", action="store_true", help="強制用 JSONL 解析")
    parser.add_argument("--dry-run", action="store_true", help="只解析與統計，不寫入資料庫")

    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        eprint("錯誤：找不到環境變數 DATABASE_URL")
        eprint('請先設定，例如：export DATABASE_URL="postgresql://user:pass@host:5432/dbname"')
        return 2

    input_path = args.input
    if not os.path.exists(input_path):
        eprint(f"錯誤：找不到檔案：{input_path}")
        return 2

    # 讀檔
    try:
        if args.jsonl or input_path.lower().endswith(".jsonl"):
            raw = load_jsonl(input_path)
        else:
            raw = load_json_array(input_path)
    except Exception as ex:
        eprint(f"讀檔失敗：{ex}")
        return 2

    # 正規化 / 過濾
    ok: List[Dict[str, Any]] = []
    skipped = 0
    for p in raw:
        if not isinstance(p, dict):
            skipped += 1
            continue
        row = normalize_place(p)
        if row is None:
            skipped += 1
            continue
        # 把 properties dict 轉成 JSON 字串，避免 driver 對 dict 行為不一致
        row["properties"] = json.dumps(row["properties"], ensure_ascii=False)
        ok.append(row)

    eprint(f"讀入 {len(raw)} 筆；可匯入 {len(ok)} 筆；略過 {skipped} 筆（缺 id/name/category/city 或缺座標）")

    # 寫入 DB
    if PSYCOPG_MAJOR == 3:
        run_import_psycopg3(database_url, ok, args.batch_size, args.dry_run)
        return 0

    if PSYCOPG2_AVAILABLE:
        run_import_psycopg2(database_url, ok, args.batch_size, args.dry_run)
        return 0

    eprint("錯誤：找不到 psycopg(3) 或 psycopg2。請安裝其一：")
    eprint("  pip install psycopg[binary]")
    eprint("或")
    eprint("  pip install psycopg2-binary")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
