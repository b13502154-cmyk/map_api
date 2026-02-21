# Google Cloud VM 部署指南

本指南说明如何在 Google Cloud VM 上部署 Coding101 Places API 服务。

## 📋 前置需求

### 服务器要求
- **操作系统**: Ubuntu 20.04 LTS 或更高版本（推荐 Ubuntu 22.04）
- **最低配置**: 
  - 2 CPU 核心
  - 4GB RAM
  - 20GB 磁盘空间
- **网络**: 需要开放端口 80 和 443（用于 HTTP/HTTPS）

### 需要安装的软件
- Docker 和 Docker Compose
- Python 3.12+（用于数据导入脚本）
- Git（可选，用于代码管理）

## 📦 需要的文件清单

部署时需要上传以下文件和目录：

### 必需文件
```
Coding101(sql ver)/
├── app/                          # 应用代码目录
│   ├── __init__.py
│   ├── config.py                 # 配置文件
│   ├── main.py                   # FastAPI 主程序
│   └── services/
│       ├── __init__.py
│       └── places_service.py     # 数据服务层
├── data/
│   └── build/
│       └── places.json           # 地点数据文件（必需）
├── docker-compose.yml            # Docker Compose 配置
├── Dockerfile                    # API 服务 Docker 镜像定义
├── requirements.txt              # Python 依赖
├── schema.sql                    # 数据库表结构定义
└── load_to_postgis.py            # 数据导入脚本
```

### 可选文件
- `.env` - 环境变量文件（包含 API_KEY 等）
- `SETUP.md` - 本地开发设置说明

## 🚀 部署步骤

### 步骤 1: 准备 Google Cloud VM

1. **创建 VM 实例**
   ```bash
   # 在 Google Cloud Console 创建实例，或使用 gcloud CLI
   gcloud compute instances create coding101-api \
     --zone=asia-east1-a \
     --machine-type=e2-standard-2 \
     --image-family=ubuntu-2204-lts \
     --image-project=ubuntu-os-cloud \
     --boot-disk-size=20GB
   ```

2. **配置防火墙规则**
   ```bash
   # 允许 HTTP 流量
   gcloud compute firewall-rules create allow-http \
     --allow tcp:80 \
     --source-ranges 0.0.0.0/0 \
     --target-tags http-server
   
   # 允许 HTTPS 流量
   gcloud compute firewall-rules create allow-https \
     --allow tcp:443 \
     --source-ranges 0.0.0.0/0 \
     --target-tags https-server
   
   # 允许 API 端口（如果直接使用 8000）
   gcloud compute firewall-rules create allow-api \
     --allow tcp:8000 \
     --source-ranges 0.0.0.0/0 \
     --target-tags api-server
   ```

3. **SSH 连接到 VM**
   ```bash
   gcloud compute ssh coding101-api --zone=asia-east1-a
   ```

### 步骤 2: 在 VM 上安装必要软件

```bash
# 更新系统
sudo apt-get update
sudo apt-get upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 安装 Python 3.12+ 和 pip
sudo apt-get install -y python3.12 python3.12-venv python3-pip

# 重新登录以应用 Docker 组权限
exit
# 重新 SSH 连接
```

### 步骤 3: 上传项目文件

#### 方法 1: 使用 SCP（推荐）

在**本地机器**上执行：

```bash
# 从项目根目录上传整个项目
cd "/Users/spectre/Documents/Coding101(diff versions)/Coding101(sql ver)"

# 上传所有必需文件
scp -r app/ data/ docker-compose.yml Dockerfile requirements.txt schema.sql load_to_postgis.py \
  your-username@VM_EXTERNAL_IP:/home/your-username/coding101-api/

# 如果需要 .env 文件
scp .env your-username@VM_EXTERNAL_IP:/home/your-username/coding101-api/
```

#### 方法 2: 使用 Git（如果代码在仓库中）

```bash
# 在 VM 上
cd ~
git clone <your-repo-url> coding101-api
cd coding101-api
```

#### 方法 3: 使用 Google Cloud Storage

```bash
# 在本地打包
tar -czf coding101-api.tar.gz app/ data/ docker-compose.yml Dockerfile requirements.txt schema.sql load_to_postgis.py

# 上传到 GCS
gsutil cp coding101-api.tar.gz gs://your-bucket/

# 在 VM 上下载并解压
gsutil cp gs://your-bucket/coding101-api.tar.gz .
tar -xzf coding101-api.tar.gz
```

### 步骤 4: 在 VM 上配置项目

```bash
# 进入项目目录
cd ~/coding101-api

# 创建 .env 文件（如果还没有）
cat > .env << EOF
API_KEY=your_secure_api_key_here
DATABASE_URL=postgresql://coding101:coding101_password@db:5432/coding101
EOF

# 设置文件权限
chmod 600 .env
```

### 步骤 5: 启动服务

```bash
# 启动数据库和 API 服务
docker-compose up -d

# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 步骤 6: 导入数据到数据库

```bash
# 等待数据库就绪（约 10-30 秒）
sleep 15

# 设置数据库连接
export DATABASE_URL="postgresql://coding101:coding101_password@localhost:5433/coding101"

# 先测试导入（不写入）
python3 load_to_postgis.py data/build/places.json --dry-run

# 正式导入数据
python3 load_to_postgis.py data/build/places.json
```

### 步骤 7: 验证服务

```bash
# 检查 API 健康状态
curl http://localhost:8000/health

# 测试 API 端点（如果设置了 API_KEY）
curl -H "X-API-Key: your_secure_api_key_here" \
  http://localhost:8000/api/cities
```

## 🔧 使用 Systemd 管理服务（推荐）

为了确保服务在系统重启后自动启动，创建 systemd 服务：

```bash
sudo nano /etc/systemd/system/coding101-api.service
```

添加以下内容：

```ini
[Unit]
Description=Coding101 Places API Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/your-username/coding101-api
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=your-username
Group=docker

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable coding101-api
sudo systemctl start coding101-api

# 检查状态
sudo systemctl status coding101-api
```

## 🌐 配置反向代理（可选，推荐）

使用 Nginx 作为反向代理，提供 HTTPS 支持：

### 安装 Nginx

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### 配置 Nginx

```bash
sudo nano /etc/nginx/sites-available/coding101-api
```

添加配置：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或 IP

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/coding101-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 配置 SSL（使用 Let's Encrypt）

```bash
sudo certbot --nginx -d your-domain.com
```

## 📊 监控和维护

### 查看服务日志

```bash
# Docker Compose 日志
docker-compose logs -f api
docker-compose logs -f db

# Systemd 日志
sudo journalctl -u coding101-api -f
```

### 更新服务

```bash
cd ~/coding101-api

# 停止服务
docker-compose down

# 更新代码文件（通过 SCP 或 Git）
# ...

# 重新构建并启动
docker-compose build api
docker-compose up -d
```

### 备份数据库

```bash
# 创建备份脚本
cat > ~/backup-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backups
mkdir -p $BACKUP_DIR
docker-compose exec -T db pg_dump -U coding101 coding101 | gzip > $BACKUP_DIR/coding101-$(date +%Y%m%d-%H%M%S).sql.gz
# 保留最近 7 天的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
EOF

chmod +x ~/backup-db.sh

# 添加到 crontab（每天凌晨 2 点备份）
crontab -e
# 添加：0 2 * * * /home/your-username/backup-db.sh
```

## 🔒 安全建议

1. **更改默认密码**
   - 修改 `docker-compose.yml` 中的数据库密码
   - 使用强密码生成器

2. **配置防火墙**
   - 只开放必要的端口
   - 使用 Google Cloud 防火墙规则限制访问来源

3. **定期更新**
   ```bash
   sudo apt-get update && sudo apt-get upgrade -y
   docker-compose pull
   ```

4. **监控资源使用**
   ```bash
   # 查看容器资源使用
   docker stats
   
   # 查看磁盘使用
   df -h
   ```

## 🐛 故障排除

### 服务无法启动

```bash
# 检查 Docker 服务
sudo systemctl status docker

# 检查端口占用
sudo netstat -tulpn | grep :8000
sudo netstat -tulpn | grep :5433

# 查看详细错误
docker-compose logs
```

### 数据库连接失败

```bash
# 检查数据库容器
docker-compose ps db
docker-compose logs db

# 测试数据库连接
docker-compose exec db psql -U coding101 -d coding101 -c "SELECT 1;"
```

### API 返回错误

```bash
# 查看 API 日志
docker-compose logs api

# 检查环境变量
docker-compose exec api env | grep DATABASE_URL
```

## 📝 快速参考命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 重新构建
docker-compose build --no-cache api

# 进入数据库容器
docker-compose exec db psql -U coding101 -d coding101
```

## 📞 支持

如遇问题，请检查：
1. 服务日志：`docker-compose logs`
2. 系统日志：`sudo journalctl -xe`
3. 网络连接：`curl http://localhost:8000/health`

---

**部署完成后，你的 API 将在 `http://VM_EXTERNAL_IP:8000` 或 `https://your-domain.com` 可用。**

