#!/bin/bash
# EMA 启动脚本

cd "$(dirname "$0")"

# 检查依赖
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "❌ 缺少依赖，请先安装："
    echo "   pip install -r requirements.txt"
    exit 1
fi

# 启动服务
echo "🚀 启动工程管理智能体..."
python3 src/main.py --host 0.0.0.0 --port 5188 --reload