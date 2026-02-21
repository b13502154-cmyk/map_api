-- =============== --
--  PostGIS setup  --
-- =============== --
CREATE EXTENSION IF NOT EXISTS postgis;

-- （可選）如果你想做更進階的字串搜尋再開
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ===================== --
--  Main table: places   --
-- ===================== --
CREATE TABLE IF NOT EXISTS places (
  id         text PRIMARY KEY,          -- 你目前是 name+address hash（最適合 text）
  name       text NOT NULL,
  address    text,
  category   text NOT NULL,              -- 例如 park / public_kindergarten...
  city       text NOT NULL,              -- 例如 taipei
  geom       geometry(Point, 4326) NOT NULL,
  properties jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- ===================== --
--  Basic indexes        --
-- ===================== --

-- 空間索引：附近查詢 / bbox 查詢 都靠這個
CREATE INDEX IF NOT EXISTS places_geom_gix
  ON places USING GIST (geom);

-- 常用篩選：category / city
CREATE INDEX IF NOT EXISTS places_category_idx
  ON places (category);

CREATE INDEX IF NOT EXISTS places_city_idx
  ON places (city);

-- 常見組合：city + category 一起篩
CREATE INDEX IF NOT EXISTS places_city_category_idx
  ON places (city, category);

-- （可選）如果你常做「名稱模糊查」可用 trigram
-- CREATE INDEX IF NOT EXISTS places_name_trgm_idx
--   ON places USING GIN (name gin_trgm_ops);

-- ===================== --
--  JSONB indexes         --
-- ===================== --

-- （可選）如果你會大量用 properties 裡的任意 key 查詢
-- 例如：properties->>'capacity'、properties->>'phone'、properties @> {...}
-- 再打開這個。否則先不要加，避免索引膨脹。
-- CREATE INDEX IF NOT EXISTS places_properties_gin
--   ON places USING GIN (properties);

-- （範例）如果你「確定」會常用某個 key（例如 count）來查：
-- CREATE INDEX IF NOT EXISTS places_properties_count_idx
--   ON places ((properties->>'count'));

-- ===================== --
--  updated_at trigger    --
-- ===================== --
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_places_updated_at ON places;
CREATE TRIGGER trg_places_updated_at
BEFORE UPDATE ON places
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
