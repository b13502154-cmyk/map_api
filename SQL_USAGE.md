# SQL 在 API 中的使用说明

本文档详细说明 SQL 查询在这个 Places API 中是如何构建和使用的。

## 📊 数据库架构

### 数据表结构

API 使用 PostgreSQL + PostGIS 数据库，主要数据表为 `places`：

```sql
CREATE TABLE places (
  id         text PRIMARY KEY,              -- 地点唯一标识（name+address 的 hash）
  name       text NOT NULL,                 -- 地点名称
  address    text,                          -- 地址
  category   text NOT NULL,                 -- 分类（如 park, public_kindergarten）
  city       text NOT NULL,                 -- 城市代码（如 taipei, new_taipei）
  geom       geometry(Point, 4326) NOT NULL, -- 地理位置（PostGIS 几何类型）
  properties jsonb NOT NULL DEFAULT '{}',    -- 额外属性（JSON 格式）
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
```

### 索引

为了提高查询性能，创建了以下索引：

```sql
-- 空间索引：用于地理范围查询（bbox）
CREATE INDEX places_geom_gix ON places USING GIST (geom);

-- 分类索引：用于 category 筛选
CREATE INDEX places_category_idx ON places (category);

-- 城市索引：用于 city 筛选
CREATE INDEX places_city_idx ON places (city);

-- 组合索引：用于 city + category 组合查询
CREATE INDEX places_city_category_idx ON places (city, category);
```

## 🔍 SQL 查询构建流程

### 1. 动态 SQL 构建

API 使用 **参数化查询** 动态构建 SQL，避免 SQL 注入攻击。

#### 基础查询结构

```python
# 从 places_service.py 的 build_places_query() 函数
base_query = """
    SELECT 
        id,
        name,
        address,
        category,
        city,
        ST_Y(geom) AS lat,    -- PostGIS 函数：提取纬度
        ST_X(geom) AS lng,    -- PostGIS 函数：提取经度
        properties
    FROM places
    WHERE 1=1                  -- 方便后续添加 AND 条件
"""
```

#### 条件动态添加

根据 API 请求参数，动态添加 WHERE 条件：

```python
conditions = []
params = []

# 示例：添加分类筛选
if category:
    placeholders = ",".join(["%s"] * len(category))
    conditions.append(f"category IN ({placeholders})")
    params.extend(category)  # 参数化，防止 SQL 注入
```

### 2. 主要 SQL 查询类型

#### A. 获取地点列表 (`get_places`)

**功能**: 根据多个筛选条件查询地点

**SQL 示例**（查询台北市的公园）：

```sql
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
  AND (properties->>'data_status' IS NULL OR properties->>'data_status' != 'outdated')
  AND category = 'park'
  AND city = 'taipei'
```

**关键 SQL 特性**：

1. **PostGIS 空间函数**：
   - `ST_Y(geom)`: 从几何点提取纬度
   - `ST_X(geom)`: 从几何点提取经度
   - `ST_Within(geom, envelope)`: 检查点是否在边界框内

2. **JSONB 查询**：
   - `properties->>'data_status'`: 提取 JSON 字段（返回文本）
   - `properties->>'diaper_table_count'`: 提取嵌套属性

3. **类型转换**：
   - `(properties->>'diaper_table_count')::int`: 将 JSON 文本转换为整数
   - `(properties->>'has_parking')::boolean`: 转换为布尔值

#### B. 地理范围查询 (bbox)

**功能**: 查询指定地理边界框内的地点

**SQL 示例**：

```sql
SELECT ...
FROM places
WHERE ST_Within(geom, ST_MakeEnvelope(121.50, 25.02, 121.58, 25.10, 4326))
```

**说明**：
- `ST_MakeEnvelope(minLng, minLat, maxLng, maxLat, SRID)`: 创建边界框
- `ST_Within(geom, envelope)`: 检查点是否在边界框内
- `4326`: WGS84 坐标系统（GPS 使用的标准）

#### C. JSONB 属性查询

**功能**: 查询 JSONB 字段中的属性

**SQL 示例**（查询有尿布台的地点）：

```sql
SELECT ...
FROM places
WHERE (properties->>'diaper_table_count')::int > 0
```

**SQL 示例**（查询有停车场的的地点）：

```sql
SELECT ...
FROM places
WHERE (
    (properties->>'has_parking')::boolean = true
    OR (properties->>'parking')::boolean = true
    OR (properties->>'parking_count')::int > 0
)
```

#### D. 聚合查询 (`get_cities`)

**功能**: 统计各城市的地点数量

**SQL 示例**：

```sql
SELECT 
    city,
    COUNT(*) as count
FROM places
WHERE 1=1
  AND (properties->>'data_status' IS NULL OR properties->>'data_status' != 'outdated')
  AND category IN ('park', 'toilet')
GROUP BY city
ORDER BY city
```

**关键 SQL 特性**：
- `COUNT(*)`: 聚合函数，统计数量
- `GROUP BY`: 按城市分组
- `ORDER BY`: 排序

#### E. 嵌套查询 (`get_cities` 中的城市名称查询)

**功能**: 从第一个记录中获取城市名称

**SQL 示例**：

```sql
SELECT properties->>'city_name' as city_name
FROM places
WHERE city = 'taipei'
  AND properties->>'city_name' IS NOT NULL
LIMIT 1
```

#### F. 区域统计查询 (`get_districts`)

**功能**: 统计指定城市的各区域地点数量

**SQL 示例**：

```sql
SELECT 
    properties->>'district' as district,
    COUNT(*) as count
FROM places
WHERE city = 'taipei'
  AND (properties->>'data_status' IS NULL OR properties->>'data_status' != 'outdated')
  AND category IN ('park', 'toilet')
  AND properties->>'district' IS NOT NULL
GROUP BY properties->>'district'
ORDER BY properties->>'district'
```

## 🔐 安全特性

### 1. 参数化查询

所有用户输入都通过参数传递，**绝不**直接拼接到 SQL 字符串中：

```python
# ✅ 正确：参数化查询
conditions.append("city = %s")
params.append(city)  # 用户输入作为参数

# ❌ 错误：SQL 注入风险
query = f"SELECT * FROM places WHERE city = '{city}'"  # 危险！
```

### 2. 输入验证

在构建 SQL 之前，API 会验证输入：

```python
# bbox 格式验证
parts = bbox.split(",")
if len(parts) == 4:
    min_lng, min_lat, max_lng, max_lat = map(float, parts)
    # 只有验证通过才添加到 SQL
```

## 📈 性能优化

### 1. 索引使用

查询条件都对应有索引：

- `category` → `places_category_idx`
- `city` → `places_city_idx`
- `city + category` → `places_city_category_idx`
- `geom` → `places_geom_gix` (GIST 空间索引)

### 2. 查询优化

- 使用 `WHERE 1=1` 方便动态添加条件
- 使用 `LIMIT` 限制子查询结果
- 使用 `IS NOT NULL` 过滤空值

## 🔄 完整查询流程示例

### 示例：查询台北市有尿布台的公园

**API 请求**：
```
GET /api/places?city=taipei&category=park&has_diaper_table=1
```

**构建的 SQL**：
```sql
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
  AND (properties->>'data_status' IS NULL OR properties->>'data_status' != 'outdated')
  AND category = 'park'
  AND city = 'taipei'
  AND (properties->>'diaper_table_count')::int > 0
```

**参数列表**：
```python
params = ['park', 'taipei']
```

**执行流程**：

```python
# 1. 构建查询
query, params = build_places_query(
    category=['park'],
    city='taipei',
    has_diaper_table='1'
)

# 2. 连接数据库
with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor(row_factory=dict_row) as cur:
        # 3. 执行参数化查询
        cur.execute(query, params)
        
        # 4. 获取结果
        rows = cur.fetchall()
        
        # 5. 转换为 API 格式
        places = [normalize_place_from_db(row) for row in rows]
```

## 📝 SQL 查询位置

所有 SQL 查询都在以下文件中：

- **`app/services/places_service.py`**:
  - `build_places_query()`: 构建地点查询 SQL
  - `get_places()`: 执行地点查询
  - `get_cities()`: 执行城市统计查询
  - `get_districts()`: 执行区域统计查询

- **`schema.sql`**: 数据库表结构和索引定义

- **`load_to_postgis.py`**: 数据导入脚本中的 UPSERT SQL

## 🎯 关键 SQL 技术总结

1. **PostGIS 空间查询**: `ST_Y()`, `ST_X()`, `ST_Within()`, `ST_MakeEnvelope()`
2. **JSONB 查询**: `properties->>'key'`, 类型转换 `::int`, `::boolean`
3. **参数化查询**: 使用 `%s` 占位符和参数列表
4. **聚合函数**: `COUNT()`, `GROUP BY`
5. **索引优化**: GIST 空间索引、B-tree 索引

## 🔍 调试 SQL 查询

如果需要查看实际执行的 SQL，可以在代码中添加日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 在 execute 之前
logging.debug(f"SQL: {query}")
logging.debug(f"Params: {params}")
```

或者直接在数据库中查看：

```sql
-- 查看慢查询
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

---

**总结**: API 使用动态构建的参数化 SQL 查询，结合 PostGIS 空间函数和 JSONB 查询，实现了高效、安全的地理位置数据查询功能。

