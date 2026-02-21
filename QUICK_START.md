# 🚀 快速开始指南

## 📚 文档索引

- **DEPLOYMENT.md** - 完整的 Google Cloud VM 部署指南（详细步骤）
- **FILES_CHECKLIST.md** - 部署文件清单和检查方法
- **SETUP.md** - 本地开发环境设置指南
- **deploy.sh** - 自动部署脚本

## 🎯 快速部署到 Google Cloud VM

### 1. 准备文件

确保以下文件已准备好：
- `app/` 目录（应用代码）
- `data/build/places.json`（数据文件）
- `docker-compose.yml`
- `Dockerfile`
- `requirements.txt`
- `schema.sql`
- `load_to_postgis.py`

详细清单见 `FILES_CHECKLIST.md`

### 2. 上传文件到 VM

```bash
# 在本地机器上
cd "/path/to/Coding101(sql ver)"

# 方法 1: 使用 SCP
scp -r app/ data/ docker-compose.yml Dockerfile requirements.txt schema.sql load_to_postgis.py \
  username@VM_IP:/home/username/coding101-api/

# 方法 2: 使用 tar 打包（推荐，更快）
tar -czf coding101-api.tar.gz app/ data/ docker-compose.yml Dockerfile requirements.txt schema.sql load_to_postgis.py
scp coding101-api.tar.gz username@VM_IP:/home/username/
```

### 3. 在 VM 上部署

```bash
# SSH 连接到 VM
ssh username@VM_IP

# 进入项目目录
cd ~/coding101-api

# 如果使用 tar，先解压
tar -xzf coding101-api.tar.gz

# 运行自动部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 4. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 测试 API
curl http://localhost:8000/health

# 查看日志
docker-compose logs -f
```

## 📋 必需文件清单（快速参考）

```
coding101-api/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   └── services/
│       ├── __init__.py
│       └── places_service.py
├── data/
│   └── build/
│       └── places.json          # ⚠️ 必需，可能很大
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── schema.sql
└── load_to_postgis.py
```

## 🔧 手动部署步骤（如果自动脚本失败）

```bash
# 1. 安装 Docker 和 Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 2. 创建 .env 文件（可选）
echo "API_KEY=your_key_here" > .env

# 3. 启动数据库
docker-compose up -d db

# 4. 等待数据库就绪
sleep 15

# 5. 导入数据
export DATABASE_URL="postgresql://coding101:coding101_password@localhost:5433/coding101"
python3 -m pip install 'psycopg[binary]' --quiet
python3 load_to_postgis.py data/build/places.json

# 6. 启动 API
docker-compose up -d api

# 7. 验证
curl http://localhost:8000/health
```

## 🌐 配置域名和 HTTPS（可选）

1. 安装 Nginx
2. 配置反向代理
3. 使用 Let's Encrypt 获取 SSL 证书

详细步骤见 `DEPLOYMENT.md` 的"配置反向代理"部分。

## 🆘 遇到问题？

1. **查看日志**: `docker-compose logs -f`
2. **检查服务状态**: `docker-compose ps`
3. **查看详细部署指南**: `DEPLOYMENT.md`
4. **检查文件完整性**: `FILES_CHECKLIST.md`

## 📞 常用命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f api
docker-compose logs -f db

# 重启服务
docker-compose restart

# 进入数据库
docker-compose exec db psql -U coding101 -d coding101
```

---

**需要更多帮助？查看 `DEPLOYMENT.md` 获取完整文档。**

