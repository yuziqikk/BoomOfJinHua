#!/bin/bash

echo "=== 炸金花在线游戏 - 环境设置 ==="

cd "$(dirname "$0")"

# Check Python
if command -v python3 &> /dev/null; then
    echo "Python 3: $(python3 --version)"
else
    echo "Python 3 not found. Please install Python 3."
    exit 1
fi

# Install dependencies
echo ""
echo "=== 安装依赖 ==="
pip install -r requirements.txt 2>/dev/null || pip3 install -r requirements.txt

echo ""
echo "=== 环境准备完成 ==="
echo ""
echo "启动游戏服务器:"
echo "  python -c \"from backend.app import run_server; run_server()\""
echo ""
echo "然后在浏览器中打开:"
echo "  http://localhost:5002"
