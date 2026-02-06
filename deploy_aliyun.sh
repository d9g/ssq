#!/bin/bash
# 双色球分析系统 - Alibaba Cloud Linux 3 + 宝塔面板 部署脚本
# 在项目根目录以非 root 用户运行: bash deploy_aliyun.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "🚀 SSQ 双色球分析 - 阿里云 Linux 3 部署"
echo "=========================================="

if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ 请勿使用 root 运行，使用将要运行服务的用户（如 www）${NC}"
    exit 1
fi

PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/venv"

# 检测 Python 3.11 / 3.12 / 3.9
PYTHON_CMD=""
for v in python3.11 python3.12 python3.9 python3; do
    if command -v $v &>/dev/null; then
        ver=$($v -c "import sys; print(sys.version_info.major, sys.version_info.minor)" 2>/dev/null || true)
        if [ -n "$ver" ]; then
            maj=${ver% *}; min=${ver#* }
            if [ "$maj" -eq 3 ] && [ "$min" -ge 9 ]; then
                PYTHON_CMD=$v
                break
            fi
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ 未找到 Python 3.9+，请先安装: sudo dnf install python3.11 python3.11-pip${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Python: $($PYTHON_CMD --version)"
echo -e "${GREEN}✓${NC} 项目目录: $PROJECT_DIR"
echo ""

# 虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 创建虚拟环境..."
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓${NC} 虚拟环境已创建"
else
    echo -e "${YELLOW}⚠${NC} 虚拟环境已存在，跳过创建"
fi

source venv/bin/activate

# pip 镜像（可选，国内加速）
if [ ! -f ~/.pip/pip.conf ]; then
    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf << 'PIPEOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
[install]
trusted-host = mirrors.aliyun.com
PIPEOF
    echo -e "${GREEN}✓${NC} 已配置 pip 阿里云镜像"
fi

echo "📦 安装依赖..."
pip install -q --upgrade pip
pip install -q -r requirements.txt gunicorn
echo -e "${GREEN}✓${NC} 依赖安装完成"

mkdir -p logs data reports pics

if [ ! -f "data/lottery_data.json" ]; then
    echo "📊 初始化数据（首次可能较慢）..."
    python main.py
    echo -e "${GREEN}✓${NC} 数据初始化完成"
else
    echo -e "${YELLOW}⚠${NC} 数据已存在，跳过初始化"
fi

if [ ! -f "gunicorn_config.py" ]; then
    echo -e "${YELLOW}⚠${NC} 未找到 gunicorn_config.py，请从仓库获取"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 应用部署完成${NC}"
echo "=========================================="
echo ""
echo "下一步（需 root/sudo）："
echo "  1. 创建 systemd 服务并启动（见 DEPLOY.md「Alibaba Cloud Linux 3 + 宝塔」）"
echo "  2. 宝塔 → 网站 → 添加站点 → 反向代理到 http://127.0.0.1:8000"
echo ""
echo "本地测试："
echo "  source venv/bin/activate && python web_app.py"
echo "  然后访问 http://本机IP:8000"
echo ""
