# 部署文件清单

在部署到 Google Cloud VM 之前，请确认以下文件已准备就绪。

## 📦 必需文件清单

### 核心应用文件

- [ ] `app/` - 应用代码目录
  - [ ] `app/__init__.py`
  - [ ] `app/config.py` - 配置文件
  - [ ] `app/main.py` - FastAPI 主程序
  - [ ] `app/services/__init__.py`
  - [ ] `app/services/places_service.py` - 数据服务层

### 数据文件

- [ ] `data/build/places.json` - **必需**，地点数据文件（可能很大，确保完整上传）

### Docker 配置文件

- [ ] `docker-compose.yml` - Docker Compose 配置
- [ ] `Dockerfile` - API 服务 Docker 镜像定义

### 数据库相关

- [ ] `schema.sql` - 数据库表结构定义
- [ ] `load_to_postgis.py` - 数据导入脚本

### 依赖文件

- [ ] `requirements.txt` - Python 依赖列表

## 🔧 可选文件

- [ ] `.env` - 环境变量文件（包含 API_KEY 等敏感信息）
- [ ] `DEPLOYMENT.md` - 部署指南（本文档）
- [ ] `deploy.sh` - 自动部署脚本
- [ ] `SETUP.md` - 本地开发设置说明

## 📋 文件上传检查清单

### 方法 1: 使用 SCP 上传

在**本地机器**上执行：

```bash
# 进入项目目录
cd "/path/to/Coding101(sql ver)"

# 创建必需文件列表
FILES=(
  "app"
  "data/build/places.json"
  "docker-compose.yml"
  "Dockerfile"
  "requirements.txt"
  "schema.sql"
  "load_to_postgis.py"
)

# 上传文件
for file in "${FILES[@]}"; do
  if [ -e "$file" ]; then
    echo "✅ $file 存在"
  else
    echo "❌ $file 缺失"
  fi
done

# 上传到 VM（替换为你的 VM 信息）
scp -r app/ data/ docker-compose.yml Dockerfile requirements.txt schema.sql load_to_postgis.py \
  username@VM_IP:/home/username/coding101-api/
```

### 方法 2: 使用 tar 打包上传

```bash
# 在本地打包
tar -czf coding101-api.tar.gz \
  app/ \
  data/build/places.json \
  docker-compose.yml \
  Dockerfile \
  requirements.txt \
  schema.sql \
  load_to_postgis.py

# 检查打包文件大小
ls -lh coding101-api.tar.gz

# 上传到 VM
scp coding101-api.tar.gz username@VM_IP:/home/username/

# 在 VM 上解压
ssh username@VM_IP
cd ~
tar -xzf coding101-api.tar.gz
```

## ✅ 上传后验证

在 VM 上执行以下命令验证文件完整性：

```bash
cd ~/coding101-api

# 检查必需文件
echo "检查必需文件..."
[ -d "app" ] && echo "✅ app/ 目录存在" || echo "❌ app/ 目录缺失"
[ -f "data/build/places.json" ] && echo "✅ places.json 存在" || echo "❌ places.json 缺失"
[ -f "docker-compose.yml" ] && echo "✅ docker-compose.yml 存在" || echo "❌ docker-compose.yml 缺失"
[ -f "Dockerfile" ] && echo "✅ Dockerfile 存在" || echo "❌ Dockerfile 缺失"
[ -f "requirements.txt" ] && echo "✅ requirements.txt 存在" || echo "❌ requirements.txt 缺失"
[ -f "schema.sql" ] && echo "✅ schema.sql 存在" || echo "❌ schema.sql 缺失"
[ -f "load_to_postgis.py" ] && echo "✅ load_to_postgis.py 存在" || echo "❌ load_to_postgis.py 缺失"

# 检查数据文件大小（应该很大）
if [ -f "data/build/places.json" ]; then
  SIZE=$(du -h data/build/places.json | cut -f1)
  echo "📊 places.json 文件大小: $SIZE"
fi
```

## 🔍 文件大小参考

- `places.json`: 通常几百 MB 到几 GB（取决于数据量）
- `app/` 目录: 通常 < 1 MB
- 其他配置文件: 每个 < 100 KB

如果 `places.json` 文件很大，上传可能需要较长时间。建议：

1. 使用压缩上传（tar.gz）
2. 使用 `rsync` 支持断点续传
3. 考虑使用 Google Cloud Storage 中转

## 🚨 常见问题

### 问题 1: places.json 文件太大

**解决方案**: 使用压缩或分块上传

```bash
# 压缩上传
tar -czf data.tar.gz data/
scp data.tar.gz username@VM_IP:/home/username/
# 在 VM 上解压
tar -xzf data.tar.gz
```

### 问题 2: 上传中断

**解决方案**: 使用 `rsync` 支持断点续传

```bash
rsync -avz --progress \
  app/ data/ docker-compose.yml Dockerfile requirements.txt schema.sql load_to_postgis.py \
  username@VM_IP:/home/username/coding101-api/
```

### 问题 3: 权限问题

**解决方案**: 确保文件有正确的权限

```bash
# 在 VM 上
chmod +x load_to_postgis.py
chmod 644 docker-compose.yml Dockerfile requirements.txt schema.sql
chmod -R 755 app/
```

## 📝 快速检查脚本

创建 `check_files.sh`:

```bash
#!/bin/bash
echo "检查部署文件..."

REQUIRED=(
  "app"
  "data/build/places.json"
  "docker-compose.yml"
  "Dockerfile"
  "requirements.txt"
  "schema.sql"
  "load_to_postgis.py"
)

ALL_OK=true
for file in "${REQUIRED[@]}"; do
  if [ -e "$file" ]; then
    echo "✅ $file"
  else
    echo "❌ $file - 缺失"
    ALL_OK=false
  fi
done

if [ "$ALL_OK" = true ]; then
  echo ""
  echo "✅ 所有必需文件已就绪！"
else
  echo ""
  echo "❌ 部分文件缺失，请检查"
  exit 1
fi
```

运行: `bash check_files.sh`

