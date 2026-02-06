#!/bin/bash
# CentOS 7 一键部署脚本
# 双色球分析系统自动部署脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🚀 双色球分析系统 - CentOS 7 部署脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}错误: 请使用 root 用户或 sudo 运行此脚本${NC}"
    exit 1
fi

# 配置变量
PROJECT_USER="ssq"
PROJECT_DIR="/home/${PROJECT_USER}/ssq"
GITHUB_REPO="https://github.com/d9g/ssq.git"
SERVICE_NAME="ssq-webapp"

echo -e "${GREEN}步骤 1/10: 更新系统并安装 EPEL 仓库...${NC}"
yum update -y
yum install epel-release -y

echo -e "${GREEN}步骤 2/10: 安装基础工具...${NC}"
yum install wget curl git -y

echo -e "${GREEN}步骤 3/10: 安装 Python 3.11...${NC}"
# 尝试使用 IUS 仓库安装
if ! command -v python3.11 &> /dev/null; then
    echo "安装 IUS 仓库..."
    yum install https://repo.ius.io/ius-release-el7.rpm -y
    yum install python311 python311-pip python311-devel -y
    
    # 创建软链接
    if [ ! -f /usr/bin/python3.11 ]; then
        alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 2>/dev/null || true
    fi
else
    echo "Python 3.11 已安装"
fi

# 验证 Python 安装
if ! command -v python3.11 &> /dev/null; then
    echo -e "${RED}错误: Python 3.11 安装失败，请检查网络连接或手动安装${NC}"
    exit 1
fi

echo -e "${GREEN}Python 版本: $(python3.11 --version)${NC}"

echo -e "${GREEN}步骤 4/10: 安装系统依赖...${NC}"
yum install nginx gcc openssl-devel libffi-devel -y

echo -e "${GREEN}步骤 5/10: 创建项目用户...${NC}"
if id "$PROJECT_USER" &>/dev/null; then
    echo "用户 $PROJECT_USER 已存在"
else
    useradd -m -s /bin/bash $PROJECT_USER
    echo "用户 $PROJECT_USER 创建成功"
fi

echo -e "${GREEN}步骤 6/10: 克隆项目...${NC}"
if [ -d "$PROJECT_DIR" ]; then
    echo "项目目录已存在，跳过克隆"
    cd $PROJECT_DIR
    git pull || echo "警告: git pull 失败，请手动检查"
else
    sudo -u $PROJECT_USER bash << EOF
cd ~
git clone $GITHUB_REPO ssq
cd ssq
EOF
fi

echo -e "${GREEN}步骤 7/10: 创建虚拟环境并安装依赖...${NC}"
sudo -u $PROJECT_USER bash << EOF
cd $PROJECT_DIR

# 创建虚拟环境
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
fi

# 激活虚拟环境并安装依赖
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# 创建必要的目录
mkdir -p logs data reports pics static templates

# 初始化数据（如果数据文件不存在）
if [ ! -f "data/lottery_data.json" ]; then
    echo "初始化数据..."
    python main.py || echo "警告: 数据初始化可能失败，请稍后手动运行"
fi
EOF

echo -e "${GREEN}步骤 8/10: 配置 Gunicorn...${NC}"
sudo -u $PROJECT_USER bash << 'GUNICORN_EOF'
cd $PROJECT_DIR
cat > gunicorn_config.py << 'EOF'
import multiprocessing
import os

bind = "127.0.0.1:8000"
backlog = 2048
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

proc_name = "ssq_webapp"
daemon = False
EOF
GUNICORN_EOF

echo -e "${GREEN}步骤 9/10: 创建 Systemd 服务...${NC}"
cat > /etc/systemd/system/${SERVICE_NAME}.service << EOF
[Unit]
Description=SSQ Lottery Analysis Web Application
After=network.target

[Service]
Type=notify
User=${PROJECT_USER}
Group=${PROJECT_USER}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${PROJECT_DIR}/venv/bin"
ExecStart=${PROJECT_DIR}/venv/bin/gunicorn \\
    --config gunicorn_config.py \\
    web_app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

echo -e "${GREEN}步骤 10/10: 配置 Nginx...${NC}"
cat > /etc/nginx/conf.d/ssq.conf << EOF
server {
    listen 80;
    server_name _;

    access_log /var/log/nginx/ssq_access.log;
    error_log /var/log/nginx/ssq_error.log;

    client_max_body_size 10M;

    location /static {
        alias ${PROJECT_DIR}/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# 测试 Nginx 配置
nginx -t

# 启动并启用 Nginx
systemctl enable nginx
systemctl restart nginx

# 配置防火墙
echo -e "${GREEN}配置防火墙...${NC}"
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
    echo "防火墙规则已添加"
else
    echo -e "${YELLOW}警告: firewalld 未运行，请手动配置防火墙${NC}"
fi

# 配置 SELinux（如果需要）
if command -v getenforce &> /dev/null; then
    if [ "$(getenforce)" == "Enforcing" ]; then
        echo -e "${GREEN}配置 SELinux...${NC}"
        setsebool -P httpd_can_network_connect 1 || true
        semanage fcontext -a -t httpd_sys_content_t "${PROJECT_DIR}(/.*)?" 2>/dev/null || true
        restorecon -Rv ${PROJECT_DIR} 2>/dev/null || true
    fi
fi

# 检查服务状态
echo ""
echo "=========================================="
echo "📊 部署完成！检查服务状态..."
echo "=========================================="

echo -e "${GREEN}Web 应用服务状态:${NC}"
systemctl status ${SERVICE_NAME} --no-pager -l || true

echo ""
echo -e "${GREEN}Nginx 服务状态:${NC}"
systemctl status nginx --no-pager -l || true

echo ""
echo -e "${GREEN}端口监听情况:${NC}"
netstat -tlnp | grep -E ':(80|8000)' || ss -tlnp | grep -E ':(80|8000)' || true

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "📝 下一步操作："
echo "1. 访问 http://$(hostname -I | awk '{print $1}') 查看 Web 应用"
echo "2. 查看日志: journalctl -u ${SERVICE_NAME} -f"
echo "3. 重启服务: systemctl restart ${SERVICE_NAME}"
echo ""
echo "📚 更多信息请查看 DEPLOY.md 文档"
echo ""
