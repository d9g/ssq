# 🚀 Linux 服务器部署指南

本文档详细说明如何将双色球分析系统部署到 Linux 服务器上。

## 📋 目录

1. [Alibaba Cloud Linux 3 + 宝塔面板（推荐）](#alibaba-cloud-linux-3--宝塔面板推荐) ⭐
2. [CentOS 7 快速部署指南](#centos-7-快速部署指南)
3. [服务器环境准备](#服务器环境准备)
4. [项目部署](#项目部署)
5. [使用 Gunicorn + Nginx 部署](#使用-gunicorn--nginx-部署)
6. [使用 Systemd 管理服务](#使用-systemd-管理服务)
7. [定时任务设置](#定时任务设置)
8. [防火墙配置](#防火墙配置)
9. [常见问题](#常见问题)

---

## Alibaba Cloud Linux 3 + 宝塔面板（推荐） ⭐

适用于：**Alibaba Cloud Linux 3.x**（如 3.21.4）、已安装 **宝塔面板**、Node 等由宝塔管理。

### 前置条件

- 操作系统：Alibaba Cloud Linux 3.21.4
- 已安装宝塔面板（Nginx 由宝塔管理，无需手动安装）
- 具备 SSH root 或 sudo 权限

### 零、安装 Git（若无 git 命令）

```bash
# Alibaba Cloud Linux 3 / CentOS / RHEL
sudo dnf install git -y
# 或
sudo yum install git -y

# 验证
git --version
```

### 一、安装 Python 3.11/3.12（系统源）

系统默认带 Python 3.6，请单独安装 3.11 或 3.12，不要替换系统自带的 `python3`：

```bash
# 更新并安装 Python 3.11（推荐）
sudo dnf update -y
sudo dnf install python3.11 python3.11-pip -y

# 若无 3.11，可装 3.12 或 3.9
# sudo dnf install python3.12 python3.12-pip -y

# 验证（使用具体版本命令）
python3.11 --version
```

### 二、配置 pip 镜像（可选，国内加速）

```bash
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
[install]
trusted-host = mirrors.aliyun.com
EOF
```

### 三、部署项目（克隆 + 虚拟环境 + 依赖）

```bash
# 进入计划放置项目的目录（如 www 或 home）
cd /www/wwwroot   # 宝塔常见目录，可按你实际习惯改
sudo mkdir -p ssq && sudo chown $USER:$USER ssq && cd ssq

# 克隆项目
git clone https://github.com/d9g/ssq.git .
# 若 GitHub 慢，可先导入 Gitee 再 clone

# 创建虚拟环境（与上面安装的 Python 版本一致）
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖与 Gunicorn
pip install --upgrade pip
pip install -r requirements.txt gunicorn

# 初始化数据
python main.py
```

### 四、Gunicorn 配置与 systemd 服务

```bash
# 确保项目根目录有 gunicorn 配置（一般仓库已带）
# 创建日志目录
mkdir -p logs

# 用 root 或 sudo 创建 systemd 服务（路径按实际修改）
sudo tee /etc/systemd/system/ssq-webapp.service > /dev/null << 'EOF'
[Unit]
Description=SSQ 双色球分析 Web 应用
After=network.target

[Service]
Type=simple
User=www
Group=www
WorkingDirectory=/www/wwwroot/ssq
Environment="PATH=/www/wwwroot/ssq/venv/bin"
ExecStart=/www/wwwroot/ssq/venv/bin/gunicorn --config gunicorn_config.py web_app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 若项目在 /home/xxx/ssq，将 User/Group 改为对应用户，WorkingDirectory 与 Environment/ExecStart 中的路径改为实际路径

# 重载并启动
sudo systemctl daemon-reload
sudo systemctl enable ssq-webapp
sudo systemctl start ssq-webapp
sudo systemctl status ssq-webapp
```

### 五、宝塔面板：添加网站与反向代理

1. **宝塔 → 网站 → 添加站点**  
   - 域名：填你的域名或留空用 IP 访问  
   - 根目录可随意（例如 `/www/wwwroot/ssq_web`），仅用于“占位”，实际由反向代理到 Python。

2. **该站点 → 设置 → 反向代理**  
   - 代理名称：`ssq`  
   - 目标 URL：`http://127.0.0.1:8000`  
   - 发送域名：`$host`  
   - 保存。

3. **（可选）静态资源**  
   - 在反向代理的“配置文件”里可增加一段，把 `/static` 指到项目里的 `static` 目录，例如：
   ```nginx
   location /static {
       alias /www/wwwroot/ssq/static;
       expires 30d;
   }
   ```
   - 若未配置，应用仍可运行，仅静态走后端。

4. **防火墙**  
   - 宝塔安全/防火墙中放行 80/443；若用云控制台安全组，也需放行 80/443。

### 六、定时更新数据（可选）

```bash
# 创建 systemd 定时任务
sudo tee /etc/systemd/system/ssq-update.service > /dev/null << 'EOF'
[Unit]
Description=SSQ 数据更新
After=network.target

[Service]
Type=oneshot
User=www
Group=www
WorkingDirectory=/www/wwwroot/ssq
Environment="PATH=/www/wwwroot/ssq/venv/bin"
ExecStart=/www/wwwroot/ssq/venv/bin/python main.py
StandardOutput=journal
StandardError=journal
EOF

sudo tee /etc/systemd/system/ssq-update.timer > /dev/null << 'EOF'
[Unit]
Description=SSQ 每日数据更新
Requires=ssq-update.service

[Timer]
OnCalendar=*-*-* 23:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ssq-update.timer --now
sudo systemctl list-timers ssq-update.timer
```

（若服务器非 UTC+8，请把 `23:00:00` 改为你需要的本地时间。）

### 七、一键脚本

项目内提供 `deploy_aliyun.sh`，在 **项目根目录** 以 **非 root 用户** 执行，可自动：创建 venv、安装依赖、初始化数据。systemd 与宝塔反向代理仍需按上面步骤手动配置一次。

```bash
cd /www/wwwroot/ssq   # 或你的项目路径
bash deploy_aliyun.sh
```

### 八、验证与常用命令

```bash
# 服务状态
sudo systemctl status ssq-webapp

# 日志
sudo journalctl -u ssq-webapp -f

# 重启应用
sudo systemctl restart ssq-webapp
```

浏览器访问：`http://你的域名或IP`（需已在宝塔中配置好站点与反向代理）。

---

## CentOS 7 快速部署指南

### 前置要求

- CentOS 7 系统
- root 或 sudo 权限
- 网络连接

### 完整部署步骤

#### 1. 更新系统并安装 EPEL 仓库

```bash
# 更新系统
sudo yum update -y

# 安装 EPEL 仓库（必需）
# 如果无法访问官方源，使用阿里云镜像
sudo yum install epel-release -y

# 如果上面失败，手动配置阿里云 EPEL 镜像
sudo yum install -y wget
sudo wget -O /etc/yum.repos.d/epel.repo http://mirrors.aliyun.com/repo/epel-7.repo

# 安装基础工具
sudo yum install wget curl git -y
```

#### 2. 安装 Python 3.14（CentOS 7 专用方法，适配国内网络）

CentOS 7 默认只有 Python 2.7，需要从源码编译安装 Python 3.14（最新稳定版 3.14.3）：

**方法 A：从源码编译（推荐，适合国内网络环境）**

```bash
# 安装编译依赖
sudo yum groupinstall "Development Tools" -y
sudo yum install openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel xz-devel tk-devel gdbm-devel db4-devel libpcap-devel expat-devel -y

# 下载 Python 3.14.3 源码（使用国内镜像源）
cd /tmp

# 方法 1：使用清华大学镜像（推荐）
wget https://mirrors.tuna.tsinghua.edu.cn/python-release-source/Python-3.14.3/Python-3.14.3.tgz

# 方法 2：如果清华镜像不可用，使用华为云镜像
# wget https://mirrors.huaweicloud.com/python/3.14.3/Python-3.14.3.tgz

# 方法 3：如果都不可用，使用官方源（可能较慢）
# wget https://www.python.org/ftp/python/3.14.3/Python-3.14.3.tgz

# 解压
tar xzf Python-3.14.3.tgz
cd Python-3.14.3

# 编译安装（优化编译，但时间较长）
./configure --enable-optimizations --prefix=/usr/local --with-ssl

# 如果上面编译时间太长，可以使用快速编译方式
# ./configure --prefix=/usr/local --with-ssl

# 编译（使用所有 CPU 核心加速）
# 注意：可能会看到 "stdatomic.h" 警告，这是正常的，不影响安装
make -j$(nproc)

# 如果编译过程中出现警告（如 stdatomic.h），可以安全忽略
# 这些警告不会影响 Python 的正常安装和使用

# 安装
sudo make altinstall

# 创建软链接
sudo ln -sf /usr/local/bin/python3.14 /usr/bin/python3.14
sudo ln -sf /usr/local/bin/pip3.14 /usr/bin/pip3.14

# 验证安装
python3.14 --version
pip3.14 --version

# 配置 pip 使用国内镜像源（重要！）
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com

[install]
trusted-host = mirrors.aliyun.com
EOF

# 升级 pip
pip3.14 install --upgrade pip
```

**注意：** Python 3.14 是较新版本，CentOS 7 的第三方仓库（如 IUS）可能还没有提供预编译包，因此推荐使用源码编译方式。

#### 3. 安装系统依赖

```bash
# 安装 Nginx 和其他必需工具
sudo yum install nginx gcc openssl-devel libffi-devel -y

# 启动并设置 Nginx 开机自启
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### 4. 创建项目用户

```bash
# 创建专用用户
sudo useradd -m -s /bin/bash ssq

# 如果需要 sudo 权限（CentOS 7 使用 wheel 组）
sudo usermod -aG wheel ssq

# 切换到项目用户
sudo su - ssq
```

#### 5. 克隆并部署项目

```bash
# 进入用户目录
cd ~

# 克隆项目（如果 GitHub 访问慢，可以使用镜像或直接上传代码）
git clone https://github.com/d9g/ssq.git
cd ssq

# 如果 GitHub 访问慢，可以使用 Gitee 镜像（需要先 fork 到 Gitee）
# git clone https://gitee.com/your-username/ssq.git
# cd ssq

# 创建虚拟环境（使用 python3.14）
python3.14 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 配置 pip 使用国内镜像源（如果之前没配置）
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com

[install]
trusted-host = mirrors.aliyun.com
EOF

# 升级 pip（使用国内镜像）
pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/

# 安装项目依赖（使用国内镜像，加速下载）
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 如果上面命令失败，可以逐个安装或使用其他镜像源
# 其他可选镜像源：
# 清华大学: https://pypi.tuna.tsinghua.edu.cn/simple/
# 中科大: https://pypi.mirrors.ustc.edu.cn/simple/
# 华为云: https://mirrors.huaweicloud.com/repository/pypi/simple/

# 安装 Gunicorn
pip install gunicorn -i https://mirrors.aliyun.com/pypi/simple/

# 初始化数据
python main.py
```

#### 6. 配置 Gunicorn

```bash
# 创建日志目录
mkdir -p logs

# 创建 Gunicorn 配置文件
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
```

#### 7. 创建 Systemd 服务（CentOS 7）

```bash
# 退出 ssq 用户，回到 root
exit

# 创建 systemd 服务文件
sudo tee /etc/systemd/system/ssq-webapp.service > /dev/null << 'EOF'
[Unit]
Description=SSQ Lottery Analysis Web Application
After=network.target

[Service]
Type=notify
User=ssq
Group=ssq
WorkingDirectory=/home/ssq/ssq
Environment="PATH=/home/ssq/ssq/venv/bin"
ExecStart=/home/ssq/ssq/venv/bin/gunicorn \
    --config gunicorn_config.py \
    web_app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 重新加载 systemd
sudo systemctl daemon-reload

# 启动并设置开机自启
sudo systemctl start ssq-webapp
sudo systemctl enable ssq-webapp

# 查看状态
sudo systemctl status ssq-webapp
```

#### 8. 配置 Nginx（CentOS 7 方式）

CentOS 7 的 Nginx 配置方式不同，需要直接在 `/etc/nginx/conf.d/` 创建配置文件：

```bash
# 创建 Nginx 配置文件
sudo tee /etc/nginx/conf.d/ssq.conf > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;  # 改为你的域名或 IP

    access_log /var/log/nginx/ssq_access.log;
    error_log /var/log/nginx/ssq_error.log;

    client_max_body_size 10M;

    # 静态文件
    location /static {
        alias /home/ssq/ssq/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 代理到 Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# 测试 Nginx 配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

#### 9. 配置防火墙（CentOS 7 使用 firewalld）

```bash
# 允许 HTTP
sudo firewall-cmd --permanent --add-service=http

# 允许 HTTPS（如果使用）
sudo firewall-cmd --permanent --add-service=https

# 重载防火墙
sudo firewall-cmd --reload

# 查看状态
sudo firewall-cmd --list-all
```

#### 10. 设置定时任务（可选）

```bash
# 创建更新数据的服务文件
sudo tee /etc/systemd/system/ssq-update.service > /dev/null << 'EOF'
[Unit]
Description=SSQ Lottery Data Update
After=network.target

[Service]
Type=oneshot
User=ssq
Group=ssq
WorkingDirectory=/home/ssq/ssq
Environment="PATH=/home/ssq/ssq/venv/bin"
ExecStart=/home/ssq/ssq/venv/bin/python /home/ssq/ssq/main.py
StandardOutput=journal
StandardError=journal
EOF

# 创建 Timer 文件
sudo tee /etc/systemd/system/ssq-update.timer > /dev/null << 'EOF'
[Unit]
Description=SSQ Lottery Data Update Timer
Requires=ssq-update.service

[Timer]
# 每天 23:00 (UTC+8) 运行，即 15:00 UTC
OnCalendar=*-*-* 15:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 启用定时器
sudo systemctl daemon-reload
sudo systemctl enable ssq-update.timer
sudo systemctl start ssq-update.timer

# 查看状态
sudo systemctl status ssq-update.timer
```

### 验证部署

```bash
# 检查服务状态
sudo systemctl status ssq-webapp
sudo systemctl status nginx

# 检查端口监听
sudo netstat -tlnp | grep 8000
sudo netstat -tlnp | grep :80

# 查看日志
sudo journalctl -u ssq-webapp -f
```

访问 `http://你的服务器IP` 即可使用 Web 应用！

---

## 服务器环境准备

### 1. 更新系统包

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS 7
sudo yum update -y
sudo yum install epel-release -y

# CentOS 8+/RHEL 8+
sudo dnf update -y
```

### 2. 安装 Python 3.14+

```bash
# Ubuntu/Debian
sudo apt install python3.14 python3.14-venv python3.14-dev python3-pip -y

# CentOS 7 - 从源码编译（推荐，适合国内网络）
sudo yum groupinstall "Development Tools" -y
sudo yum install openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel xz-devel tk-devel gdbm-devel db4-devel libpcap-devel expat-devel -y
cd /tmp
# 使用清华大学镜像下载 Python 3.14.3
wget https://mirrors.tuna.tsinghua.edu.cn/python-release-source/Python-3.14.3/Python-3.14.3.tgz
tar xzf Python-3.14.3.tgz
cd Python-3.14.3
./configure --prefix=/usr/local --with-ssl
make -j$(nproc)
sudo make altinstall
sudo ln -sf /usr/local/bin/python3.14 /usr/bin/python3.14
sudo ln -sf /usr/local/bin/pip3.14 /usr/bin/pip3.14

# 配置 pip 国内镜像源
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
EOF

# CentOS 8+/RHEL 8+ - 可能需要从源码编译（3.14 较新，仓库可能没有）
# 参考 CentOS 7 的源码编译方法

# 验证安装
python3.14 --version
pip3.14 --version
```

### 3. 安装必要的系统依赖

```bash
# Ubuntu/Debian
sudo apt install git nginx build-essential libssl-dev libffi-dev -y

# CentOS 7/RHEL 7
sudo yum install git nginx gcc openssl-devel libffi-devel -y

# CentOS 8+/RHEL 8+
sudo dnf install git nginx gcc openssl-devel libffi-devel -y
```

### 4. 创建项目用户（可选但推荐）

```bash
# 创建专用用户
sudo useradd -m -s /bin/bash ssq

# 如果需要 sudo 权限
# Ubuntu/Debian
sudo usermod -aG sudo ssq

# CentOS 7/RHEL 7（使用 wheel 组）
sudo usermod -aG wheel ssq

# 切换到项目用户
sudo su - ssq
```

---

## 项目部署

### 1. 克隆项目

```bash
# 进入用户目录
cd ~

# 克隆项目
git clone https://github.com/d9g/ssq.git
cd ssq
```

### 2. 创建 Python 虚拟环境

```bash
# 创建虚拟环境
python3.14 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip
```

### 3. 安装项目依赖

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Gunicorn（用于生产环境）
pip install gunicorn
```

### 4. 初始化数据

```bash
# 运行主程序初始化数据
python main.py

# 这会创建必要的目录和数据文件
# - data/lottery_data.json
# - reports/analysis_report.md
# - pics/lottery_frequency_analysis.png
```

### 5. 测试 Web 应用

```bash
# 测试 Flask 应用（开发模式）
python web_app.py

# 在浏览器访问 http://服务器IP:8000 测试
# 按 Ctrl+C 停止
```

---

## 使用 Gunicorn + Nginx 部署

### 1. 配置 Gunicorn

创建 Gunicorn 配置文件：

```bash
# 在项目根目录创建配置文件
cat > gunicorn_config.py << 'EOF'
# Gunicorn 配置文件
import multiprocessing
import os

# 服务器socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker进程
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# 日志
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 进程命名
proc_name = "ssq_webapp"

# 守护进程模式（生产环境建议使用 systemd 管理，这里设为 False）
daemon = False

# 用户和组（如果使用专用用户）
# user = "ssq"
# group = "ssq"

# 临时目录
tmp_upload_dir = None
EOF

# 创建日志目录
mkdir -p logs
```

### 2. 创建 Systemd 服务文件

```bash
# 创建 systemd 服务文件
sudo tee /etc/systemd/system/ssq-webapp.service > /dev/null << 'EOF'
[Unit]
Description=SSQ Lottery Analysis Web Application
After=network.target

[Service]
Type=notify
User=ssq
Group=ssq
WorkingDirectory=/home/ssq/ssq
Environment="PATH=/home/ssq/ssq/venv/bin"
ExecStart=/home/ssq/ssq/venv/bin/gunicorn \
    --config gunicorn_config.py \
    web_app:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 注意：请根据实际路径修改上面的路径
# User/Group: 如果使用专用用户，改为你的用户名
# WorkingDirectory: 改为实际项目路径
# ExecStart 中的路径: 改为实际虚拟环境路径
```

### 3. 配置 Nginx

**Ubuntu/Debian 方式：**

```bash
# 创建 Nginx 配置文件
sudo tee /etc/nginx/sites-available/ssq << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 改为你的域名或 IP

    access_log /var/log/nginx/ssq_access.log;
    error_log /var/log/nginx/ssq_error.log;

    client_max_body_size 10M;

    location /static {
        alias /home/ssq/ssq/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# 启用站点
sudo ln -s /etc/nginx/sites-available/ssq /etc/nginx/sites-enabled/

# 测试 Nginx 配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

**CentOS 7/RHEL 7 方式：**

```bash
# CentOS 7 没有 sites-available/sites-enabled，直接在 conf.d 创建
sudo tee /etc/nginx/conf.d/ssq.conf << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # 改为你的域名或 IP

    access_log /var/log/nginx/ssq_access.log;
    error_log /var/log/nginx/ssq_error.log;

    client_max_body_size 10M;

    location /static {
        alias /home/ssq/ssq/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# 测试 Nginx 配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 4. 启动服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start ssq-webapp

# 设置开机自启
sudo systemctl enable ssq-webapp

# 查看服务状态
sudo systemctl status ssq-webapp

# 查看日志
sudo journalctl -u ssq-webapp -f
```

---

## 使用 Systemd 管理服务

### 常用命令

```bash
# 启动服务
sudo systemctl start ssq-webapp

# 停止服务
sudo systemctl stop ssq-webapp

# 重启服务
sudo systemctl restart ssq-webapp

# 查看状态
sudo systemctl status ssq-webapp

# 查看日志
sudo journalctl -u ssq-webapp -f
sudo journalctl -u ssq-webapp --since today

# 禁用开机自启
sudo systemctl disable ssq-webapp
```

---

## 定时任务设置

### 方案 1: 使用 Systemd Timer（推荐）

创建定时更新数据的服务：

```bash
# 创建更新数据的服务文件
sudo tee /etc/systemd/system/ssq-update.service > /dev/null << 'EOF'
[Unit]
Description=SSQ Lottery Data Update
After=network.target

[Service]
Type=oneshot
User=ssq
Group=ssq
WorkingDirectory=/home/ssq/ssq
Environment="PATH=/home/ssq/ssq/venv/bin"
ExecStart=/home/ssq/ssq/venv/bin/python /home/ssq/ssq/main.py
StandardOutput=journal
StandardError=journal
EOF

# 创建 Timer 文件
sudo tee /etc/systemd/system/ssq-update.timer > /dev/null << 'EOF'
[Unit]
Description=SSQ Lottery Data Update Timer
Requires=ssq-update.service

[Timer]
# 每天 23:00 (UTC+8) 运行，即 15:00 UTC
OnCalendar=*-*-* 15:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 启用并启动定时器
sudo systemctl daemon-reload
sudo systemctl enable ssq-update.timer
sudo systemctl start ssq-update.timer

# 查看定时器状态
sudo systemctl status ssq-update.timer
sudo systemctl list-timers ssq-update.timer
```

### 方案 2: 使用 Cron

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天 23:00 UTC+8 运行）
# 注意：根据服务器时区调整时间
0 23 * * * cd /home/ssq/ssq && /home/ssq/ssq/venv/bin/python main.py >> /home/ssq/ssq/logs/cron.log 2>&1
```

---

## 防火墙配置

### Ubuntu/Debian (UFW)

```bash
# 允许 HTTP
sudo ufw allow 80/tcp

# 允许 HTTPS（如果使用 SSL）
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status
```

### CentOS 7/RHEL 7 (firewalld)

```bash
# 启动并启用 firewalld（如果未启动）
sudo systemctl start firewalld
sudo systemctl enable firewalld

# 允许 HTTP
sudo firewall-cmd --permanent --add-service=http

# 允许 HTTPS
sudo firewall-cmd --permanent --add-service=https

# 重载防火墙
sudo firewall-cmd --reload

# 查看状态
sudo firewall-cmd --list-all
```

**注意：** 如果服务器使用 iptables 而不是 firewalld，可以使用：

```bash
# 允许 HTTP
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 保存规则（CentOS 7）
sudo service iptables save
# 或
sudo /usr/libexec/iptables/iptables.init save
```

---

## SSL/HTTPS 配置（可选但推荐）

### 使用 Let's Encrypt 免费证书

```bash
# 安装 Certbot
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx -y

# CentOS 7/RHEL 7
sudo yum install certbot python2-certbot-nginx -y
# 或使用 EPEL 的 Python 3 版本
sudo yum install certbot python3-certbot-nginx -y

# CentOS 8+/RHEL 8+
sudo dnf install certbot python3-certbot-nginx -y

# 获取证书（需要域名）
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

更新 Nginx 配置以支持 HTTPS：

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # 其他配置同前...
}
```

---

## 常见问题

### 1. 服务无法启动

```bash
# 检查日志
sudo journalctl -u ssq-webapp -n 50

# 检查文件权限
ls -la /home/ssq/ssq

# 检查 Python 环境
/home/ssq/ssq/venv/bin/python --version
```

### 2. 502 Bad Gateway

- 检查 Gunicorn 是否运行：`sudo systemctl status ssq-webapp`
- 检查端口是否正确：
  ```bash
  # CentOS 7
  sudo netstat -tlnp | grep 8000
  # 或使用 ss 命令
  sudo ss -tlnp | grep 8000
  ```
- 检查 Nginx 配置：`sudo nginx -t`
- 检查 SELinux（CentOS 7 常见问题）：
  ```bash
  # 临时允许 Nginx 代理
  sudo setsebool -P httpd_can_network_connect 1
  
  # 或临时禁用 SELinux 测试（不推荐生产环境）
  sudo setenforce 0
  ```

### 3. 数据更新失败

- 检查网络连接
- 检查 API 是否可访问
- 查看更新日志：`sudo journalctl -u ssq-update -n 50`

### 4. 权限问题

```bash
# 确保项目目录权限正确
sudo chown -R ssq:ssq /home/ssq/ssq
sudo chmod -R 755 /home/ssq/ssq

# CentOS 7 SELinux 权限问题（如果遇到）
sudo chcon -R -t httpd_sys_content_t /home/ssq/ssq/static
sudo setsebool -P httpd_read_user_content 1
```

### 6. CentOS 7 特定问题

**问题：Python 3.14 找不到或命令不存在**

```bash
# 检查 Python 3.14 安装位置
which python3.14
# 或
ls -la /usr/bin/python3*

# 如果使用源码编译，检查 /usr/local/bin
ls -la /usr/local/bin/python3*

# 创建软链接
sudo ln -sf /usr/local/bin/python3.14 /usr/bin/python3.14
```

**问题：pip3.14 命令不存在**

```bash
# 使用 python3.14 -m pip 代替
python3.14 -m pip install --upgrade pip

# 或创建软链接
sudo ln -sf /usr/local/bin/pip3.14 /usr/bin/pip3.14
```

**问题：Nginx 无法启动或 403 错误**

```bash
# 检查 SELinux 状态
getenforce

# 如果为 Enforcing，设置 SELinux 上下文
sudo semanage fcontext -a -t httpd_sys_content_t "/home/ssq/ssq(/.*)?"
sudo restorecon -Rv /home/ssq/ssq
```

### 7. 国内网络环境问题（阿里云服务器常见）

**问题：pip 安装包失败或超时**

```bash
# 确保已配置 pip 国内镜像源
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com

[install]
trusted-host = mirrors.aliyun.com
EOF

# 如果阿里云镜像不可用，尝试其他镜像源
# 清华大学镜像
# index-url = https://pypi.tuna.tsinghua.edu.cn/simple/
# trusted-host = pypi.tuna.tsinghua.edu.cn

# 中科大镜像
# index-url = https://pypi.mirrors.ustc.edu.cn/simple/
# trusted-host = pypi.mirrors.ustc.edu.cn

# 华为云镜像
# index-url = https://mirrors.huaweicloud.com/repository/pypi/simple/
# trusted-host = mirrors.huaweicloud.com

# 临时使用镜像源安装
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

**问题：GitHub 访问慢或无法克隆项目**

```bash
# 方法 1：使用 Gitee 镜像（推荐）
# 1. 在 Gitee 上导入 GitHub 仓库
# 2. 使用 Gitee 地址克隆
git clone https://gitee.com/your-username/ssq.git

# 方法 2：使用 GitHub 镜像站
git clone https://github.com.cnpmjs.org/d9g/ssq.git

# 方法 3：配置 Git 代理（如果有代理）
git config --global http.proxy http://proxy.example.com:8080
git config --global https.proxy https://proxy.example.com:8080

# 方法 4：直接上传代码到服务器
# 在本地打包项目，然后上传到服务器解压
# tar -czf ssq.tar.gz ssq/
# scp ssq.tar.gz user@server:/home/ssq/
# ssh user@server
# cd /home/ssq && tar -xzf ssq.tar.gz
```

**问题：Python 源码下载失败**

```bash
# 使用国内镜像源下载 Python 3.14.3 源码
# 清华大学镜像（推荐）
wget https://mirrors.tuna.tsinghua.edu.cn/python-release-source/Python-3.14.3/Python-3.14.3.tgz

# 华为云镜像
wget https://mirrors.huaweicloud.com/python/3.14.3/Python-3.14.3.tgz

# 如果都不可用，可以：
# 1. 在本地下载后上传到服务器
# 2. 使用 scp 命令上传
# scp Python-3.14.3.tgz user@server:/tmp/
```

**问题：yum 安装软件包慢**

```bash
# 配置阿里云 yum 镜像源（CentOS 7）
sudo wget -O /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo

# 清理缓存并更新
sudo yum clean all
sudo yum makecache

# 如果阿里云镜像不可用，尝试其他镜像
# 清华大学镜像
# sudo sed -e 's|^mirrorlist=|#mirrorlist=|g' \
#          -e 's|^#baseurl=http://mirror.centos.org|baseurl=https://mirrors.tuna.tsinghua.edu.cn|g' \
#          -i.bak /etc/yum.repos.d/CentOS-*.repo
```

**问题：编译 Python 时缺少依赖包**

```bash
# 确保安装了所有编译依赖
sudo yum groupinstall "Development Tools" -y
sudo yum install openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel xz-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel expat-devel -y

# 如果某个包找不到，尝试使用 EPEL 仓库
sudo yum install epel-release -y
sudo yum install --enablerepo=epel <package-name> -y
```

**问题：编译时出现 "stdatomic.h" 警告**

```bash
# 警告信息示例：
# Your compiler or platform does have a working C11 stdatomic.h. 
# A future version of Python may require stdatomic.h.

# 这个警告不影响当前安装和使用，可以安全忽略
# Python 3.14 仍然可以正常编译、安装和运行

# 原因：CentOS 7 默认的 GCC 版本（4.8.5）较老，不完全支持 C11 的 stdatomic.h
# 解决方案（可选，如果想消除警告）：

# 方法 1：升级 GCC（推荐，但需要重新编译）
# 安装较新的 GCC 版本
sudo yum install centos-release-scl -y
sudo yum install devtoolset-9-gcc devtoolset-9-gcc-c++ -y

# 启用新版本的 GCC
scl enable devtoolset-9 bash

# 验证 GCC 版本
gcc --version

# 然后重新编译 Python
cd /tmp/Python-3.14.3
make clean
./configure --prefix=/usr/local --with-ssl
make -j$(nproc)
sudo make altinstall

# 方法 2：忽略警告继续安装（推荐，简单快速）
# 这个警告不影响功能，可以直接继续安装
# make -j$(nproc)  # 继续编译
# sudo make altinstall  # 继续安装

# 验证安装是否成功
python3.14 --version
python3.14 -c "import sys; print(sys.version)"
```

**注意：** `stdatomic.h` 警告是 Python 3.14 在较老的编译器上的常见警告，不会影响：
- Python 的正常编译和安装
- Python 的运行和功能
- 第三方包的安装和使用
- 项目的正常运行

只有在未来版本的 Python（如 3.15+）可能会要求 C11 的 `stdatomic.h`，但 Python 3.14 不受影响。

### 5. 内存不足

如果服务器内存较小，可以减少 Gunicorn worker 数量：

```python
# 在 gunicorn_config.py 中
workers = 2  # 改为固定数量
```

### 8. 阿里云服务器优化建议

**优化 yum 源配置**

```bash
# 备份原配置
sudo cp /etc/yum.repos.d/CentOS-Base.repo /etc/yum.repos.d/CentOS-Base.repo.bak

# 使用阿里云镜像源
sudo wget -O /etc/yum.repos.d/CentOS-Base.repo http://mirrors.aliyun.com/repo/Centos-7.repo

# 清理并重建缓存
sudo yum clean all
sudo yum makecache
```

**优化 pip 配置（全局配置）**

```bash
# 为所有用户配置 pip 镜像源
sudo mkdir -p /etc/pip
sudo tee /etc/pip.conf > /dev/null << 'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
EOF
```

**配置 Git 加速（可选）**

```bash
# 配置 Git 使用镜像站
git config --global url."https://github.com.cnpmjs.org/".insteadOf "https://github.com/"
```

---

## 部署检查清单

- [ ] Python 3.14+ 已安装
- [ ] 项目已克隆到服务器
- [ ] 虚拟环境已创建并安装依赖
- [ ] 数据已初始化（运行过 main.py）
- [ ] Gunicorn 配置文件已创建
- [ ] Systemd 服务文件已创建并启用
- [ ] Nginx 配置已完成并重启
- [ ] 防火墙已配置
- [ ] 定时任务已设置
- [ ] Web 应用可以正常访问
- [ ] 日志可以正常查看

---

## 更新部署

当需要更新代码时：

```bash
# 进入项目目录
cd ~/ssq

# 拉取最新代码
git pull

# 激活虚拟环境
source venv/bin/activate

# 更新依赖（如果有变化）
pip install -r requirements.txt

# 重启服务
sudo systemctl restart ssq-webapp
```

---

## 监控和维护

### 查看服务状态

```bash
# Web 应用状态
sudo systemctl status ssq-webapp

# 定时任务状态
sudo systemctl status ssq-update.timer

# Nginx 状态
sudo systemctl status nginx
```

### 查看日志

```bash
# Web 应用日志
sudo journalctl -u ssq-webapp -f

# 数据更新日志
sudo journalctl -u ssq-update -f

# Nginx 访问日志
sudo tail -f /var/log/nginx/ssq_access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/ssq_error.log
```

---

## 备份建议

定期备份重要数据：

```bash
# 创建备份脚本
cat > ~/backup_ssq.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/ssq/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 备份数据文件
tar -czf $BACKUP_DIR/ssq_data_$DATE.tar.gz \
    /home/ssq/ssq/data \
    /home/ssq/ssq/reports \
    /home/ssq/ssq/pics

# 保留最近 7 天的备份
find $BACKUP_DIR -name "ssq_data_*.tar.gz" -mtime +7 -delete
EOF

chmod +x ~/backup_ssq.sh

# 添加到 crontab（每天凌晨 2 点备份）
# crontab -e
# 0 2 * * * /home/ssq/backup_ssq.sh
```

---

**部署完成后，访问 `http://your-server-ip` 即可使用 Web 应用！** 🎉
