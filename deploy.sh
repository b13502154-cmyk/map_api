#!/bin/bash
# Coding101 API 快速部署脚本
# 在 Google Cloud VM 上运行此脚本以自动部署服务

set -e  # 遇到错误立即退出

echo "🚀 开始部署 Coding101 API 服务..."

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then 
   echo "❌ 请不要使用 root 用户运行此脚本"
   exit 1
fi

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "📦 安装 Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker 安装完成（需要重新登录以应用权限）"
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "📦 安装 Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose 安装完成"
fi

# 检查必要文件
REQUIRED_FILES=("docker-compose.yml" "Dockerfile" "requirements.txt" "schema.sql" "load_to_postgis.py")
MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        MISSING_FILES+=("$file")
    fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
    echo "❌ 缺少必要文件: ${MISSING_FILES[*]}"
    exit 1
fi

# 检查 app 目录
if [ ! -d "app" ]; then
    echo "❌ 缺少 app 目录"
    exit 1
fi

# 检查数据文件
if [ ! -f "data/build/places.json" ]; then
    echo "⚠️  警告: 未找到 data/build/places.json，数据导入将跳过"
    SKIP_DATA_IMPORT=true
else
    SKIP_DATA_IMPORT=false
fi

# 创建 .env 文件（如果不存在）
if [ ! -f ".env" ]; then
    echo "📝 创建 .env 文件..."
    cat > .env << EOF
API_KEY=
DATABASE_URL=postgresql://coding101:coding101_password@db:5432/coding101
EOF
    echo "✅ .env 文件已创建，请编辑以设置 API_KEY"
fi

# 停止现有服务（如果存在）
echo "🛑 停止现有服务..."
docker-compose down 2>/dev/null || true

# 启动数据库服务
echo "🗄️  启动数据库服务..."
docker-compose up -d db

# 等待数据库就绪
echo "⏳ 等待数据库就绪..."
sleep 15

# 检查数据库健康状态
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U coding101 -d coding101 > /dev/null 2>&1; then
        echo "✅ 数据库已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ 数据库启动超时"
        exit 1
    fi
    sleep 2
done

# 导入数据
if [ "$SKIP_DATA_IMPORT" = false ]; then
    echo "📥 导入数据到数据库..."
    export DATABASE_URL="postgresql://coding101:coding101_password@localhost:5433/coding101"
    
    # 检查 Python 和依赖
    if ! command -v python3 &> /dev/null; then
        echo "❌ 未找到 Python3，请先安装"
        exit 1
    fi
    
    # 安装 psycopg（如果需要）
    python3 -m pip install --quiet 'psycopg[binary]' 2>/dev/null || true
    
    # 导入数据
    python3 load_to_postgis.py data/build/places.json || {
        echo "⚠️  数据导入失败，但服务仍可启动"
    }
else
    echo "⏭️  跳过数据导入"
fi

# 启动 API 服务
echo "🚀 启动 API 服务..."
docker-compose up -d api

# 等待 API 就绪
echo "⏳ 等待 API 服务就绪..."
sleep 10

# 检查 API 健康状态
for i in {1..30}; do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API 服务已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  API 服务可能未正常启动，请检查日志: docker-compose logs api"
    fi
    sleep 2
done

# 显示服务状态
echo ""
echo "📊 服务状态:"
docker-compose ps

echo ""
echo "✅ 部署完成！"
echo ""
echo "📝 下一步:"
echo "  1. 检查服务: docker-compose ps"
echo "  2. 查看日志: docker-compose logs -f"
echo "  3. 测试 API: curl http://localhost:8000/health"
echo "  4. 如果设置了 API_KEY，测试: curl -H 'X-API-Key: YOUR_KEY' http://localhost:8000/api/cities"
echo ""
echo "🌐 API 地址: http://$(curl -s ifconfig.me):8000"
echo ""

