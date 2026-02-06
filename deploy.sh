#!/bin/bash
# 快速部署脚本 - 双色球分析系统
# 使用方法: bash deploy.sh

set -e  # 遇到错误立即退出

echo "🚀 开始部署双色球分析系统..."

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root 用户
if [ "$EUID" -eq 0 ]; then 
   echo -e "${RED}❌ 请不要使用 root 用户运行此脚本${NC}"
   echo "建议创建专用用户: sudo useradd -m -s /bin/bash ssq"
   exit 1
fi

# 获取当前用户和项目路径
CURRENT_USER=$(whoami)
PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/venv"

echo -e "${GREEN}✓${NC} 当前用户: $CURRENT_USER"
echo -e "${GREEN}✓${NC} 项目目录: $PROJECT_DIR"

# 检查 Python 版本
echo ""
echo "📦 检查 Python 环境..."
if ! command -v python3.11 &> /dev/null; then
    echo -e "${YELLOW}⚠${NC} 未找到 Python 3.11，尝试使用 python3..."
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python3.11"
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo -e "${GREEN}✓${NC} $PYTHON_VERSION"

# 创建虚拟环境
echo ""
echo "🔧 创建虚拟环境..."
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}✓${NC} 虚拟环境创建成功"
else
    echo -e "${YELLOW}⚠${NC} 虚拟环境已存在，跳过创建"
fi

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
echo ""
echo "📦 升级 pip..."
pip install --upgrade pip -q

# 安装依赖
echo ""
echo "📦 安装项目依赖..."
pip install -r requirements.txt -q
pip install gunicorn -q
echo -e "${GREEN}✓${NC} 依赖安装完成"

# 创建必要的目录
echo ""
echo "📁 创建必要的目录..."
mkdir -p logs data reports pics static templates
echo -e "${GREEN}✓${NC} 目录创建完成"

# 初始化数据（如果数据文件不存在）
echo ""
if [ ! -f "data/lottery_data.json" ]; then
    echo "📊 初始化数据（这可能需要几分钟）..."
    python main.py
    echo -e "${GREEN}✓${NC} 数据初始化完成"
else
    echo -e "${YELLOW}⚠${NC} 数据文件已存在，跳过初始化"
fi

# 检查 Gunicorn 配置
echo ""
if [ ! -f "gunicorn_config.py" ]; then
    echo -e "${YELLOW}⚠${NC} 未找到 gunicorn_config.py，请确保配置文件存在"
else
    echo -e "${GREEN}✓${NC} Gunicorn 配置文件已存在"
fi

echo ""
echo -e "${GREEN}✅ 部署完成！${NC}"
echo ""
echo "下一步操作："
echo "1. 测试运行: python web_app.py"
echo "2. 使用 Gunicorn: gunicorn --config gunicorn_config.py web_app:app"
echo "3. 配置 systemd 服务（参考 DEPLOY.md）"
echo "4. 配置 Nginx（参考 DEPLOY.md）"
echo ""
echo "详细部署说明请查看: DEPLOY.md"
