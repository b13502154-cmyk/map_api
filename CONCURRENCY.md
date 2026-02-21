# 处理并发请求指南

## 🔍 当前实现分析

### 现状

当前代码每次请求都创建新的数据库连接：

```python
# app/services/places_service.py
def get_places(...):
    with psycopg.connect(DATABASE_URL) as conn:  # 每次请求都新建连接
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            ...
```

**问题**：
- ✅ FastAPI 和 Uvicorn 支持异步并发（默认）
- ⚠️ 每次请求创建新连接，连接开销大
- ⚠️ 没有连接池，高并发时可能耗尽数据库连接

## ✅ 好消息：FastAPI 已经支持并发

FastAPI + Uvicorn **默认支持并发请求**：

```python
# 当前配置（Dockerfile）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**默认行为**：
- Uvicorn 使用多个 worker 进程
- 每个请求在独立线程/协程中处理
- **多个请求可以同时处理** ✅

## 🚀 优化方案

### 方案 1: 使用连接池（推荐）

创建数据库连接池，复用连接：

```python
# app/services/db_pool.py (新建文件)
from psycopg_pool import ConnectionPool
from app.config import DATABASE_URL

# 创建连接池
pool = ConnectionPool(
    DATABASE_URL,
    min_size=5,      # 最小连接数
    max_size=20,     # 最大连接数
    max_idle=300,    # 空闲连接超时（秒）
    max_lifetime=3600,  # 连接最大生存时间（秒）
)

def get_db_connection():
    """从连接池获取连接"""
    return pool.getconn()
```

更新 `places_service.py`：

```python
# app/services/places_service.py
from app.services.db_pool import pool

def get_places(...):
    with pool.connection() as conn:  # 从连接池获取连接
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            ...
```

### 方案 2: 使用 psycopg 的连接池（更简单）

psycopg3 内置连接池支持：

```python
# app/services/places_service.py
from psycopg import pool
from app.config import DATABASE_URL

# 全局连接池
_connection_pool = None

def get_pool():
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pool.ConnectionPool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
        )
    return _connection_pool

def get_places(...):
    pool = get_pool()
    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            ...
```

### 方案 3: 使用异步（最佳性能）

使用 FastAPI 的异步支持：

```python
# app/services/places_service.py
import asyncio
from psycopg_pool import AsyncConnectionPool

# 异步连接池
async_pool = AsyncConnectionPool(
    DATABASE_URL,
    min_size=5,
    max_size=20,
)

async def get_places_async(...):
    async with async_pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, params)
            rows = await cur.fetchall()
            ...
```

更新 `main.py`：

```python
@app.get("/api/places")
async def api_places(...):  # 使用 async
    result = await get_places_async(...)  # 异步调用
    return result
```

## 📊 性能对比

| 方案 | 并发能力 | 实现复杂度 | 推荐度 |
|------|---------|-----------|--------|
| 当前实现 | 中等（每次新建连接） | 简单 | ⚠️ |
| 连接池（同步） | 高 | 中等 | ✅ |
| 异步 + 连接池 | 最高 | 较高 | ⭐ |

## 🛠️ 快速实施（推荐：方案 2）

### 步骤 1: 更新 requirements.txt

```txt
psycopg[binary,pool]>=3.1.0
```

### 步骤 2: 创建连接池模块

创建 `app/services/db_pool.py`：

```python
"""
数据库连接池管理
"""
from psycopg import pool
from app.config import DATABASE_URL

_connection_pool = None

def get_pool():
    """获取数据库连接池（单例模式）"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pool.ConnectionPool(
            DATABASE_URL,
            min_size=5,        # 最小连接数
            max_size=20,       # 最大连接数（根据需求调整）
            max_idle=300,     # 空闲连接超时（秒）
            max_lifetime=3600,  # 连接最大生存时间（秒）
        )
    return _connection_pool

def close_pool():
    """关闭连接池（应用关闭时调用）"""
    global _connection_pool
    if _connection_pool:
        _connection_pool.close()
        _connection_pool = None
```

### 步骤 3: 更新 places_service.py

```python
# app/services/places_service.py
from app.services.db_pool import get_pool

def get_places(...):
    pool = get_pool()
    with pool.connection() as conn:  # 从连接池获取
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            ...
```

同样更新 `get_cities()` 和 `get_districts()`。

### 步骤 4: 配置 Uvicorn workers（生产环境）

更新 `docker-compose.yml` 或启动命令：

```yaml
# docker-compose.yml
api:
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

或使用 Gunicorn + Uvicorn workers：

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## 📈 数据库配置优化

### PostgreSQL 连接数配置

在 `docker-compose.yml` 中配置：

```yaml
db:
  environment:
    POSTGRES_USER: coding101
    POSTGRES_PASSWORD: coding101_password
    POSTGRES_DB: coding101
    # 增加最大连接数
    POSTGRES_INITDB_ARGS: "-c max_connections=100"
```

或创建 `postgresql.conf`：

```conf
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
```

## 🧪 测试并发性能

### 使用 Apache Bench (ab) 测试

```bash
# 安装
sudo apt-get install apache2-utils

# 测试 100 个并发请求，总共 1000 个请求
ab -n 1000 -c 100 http://localhost:8000/health
```

### 使用 wrk 测试

```bash
# 安装
sudo apt-get install wrk

# 测试
wrk -t4 -c100 -d30s http://localhost:8000/api/places?city=taipei
```

## ⚠️ 注意事项

### 1. 连接池大小

- **太小**：请求需要等待可用连接
- **太大**：浪费资源，可能超过数据库限制
- **建议**：`max_size = workers * 10`（如果有 4 个 workers，设置 40）

### 2. 数据库连接限制

PostgreSQL 默认最大连接数为 100，确保：
```
连接池大小 × workers ≤ 数据库最大连接数
```

### 3. 监控连接使用

```sql
-- 查看当前连接数
SELECT count(*) FROM pg_stat_activity;

-- 查看连接详情
SELECT pid, usename, application_name, state, query 
FROM pg_stat_activity;
```

## 🎯 推荐配置（生产环境）

```python
# 连接池配置
min_size=5
max_size=40  # 假设 4 个 workers，每个最多 10 个连接

# Uvicorn workers
workers=4

# PostgreSQL
max_connections=100
```

## 📝 总结

**当前状态**：
- ✅ FastAPI 已支持并发
- ⚠️ 需要添加连接池优化

**推荐操作**：
1. 实施连接池（方案 2）
2. 配置多个 Uvicorn workers
3. 调整数据库连接限制
4. 测试并发性能

**预期效果**：
- 支持 100+ 并发请求
- 响应时间稳定
- 资源使用优化

