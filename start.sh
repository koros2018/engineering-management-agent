#!/bin/bash
# EMA 一键启动脚本 (Linux/macOS)

cd "$(dirname "$0")"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   工程管理智能体 (EMA) - 一键启动         ║"
echo "╠══════════════════════════════════════════╣"
echo "║  Slogan: 工程管理，从'人管'到            ║"
echo "║         '智能体协管'                     ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装"
    exit 1
fi

# 检查API服务是否已运行
if curl -s http://127.0.0.1:5188/health > /dev/null 2>&1; then
    echo "✅ API 服务已在运行 (端口 5188)"
else
    echo "🚀 启动 API 服务 (端口 5188)..."
    python3 src/main.py --port 5188 &
    API_PID=$!
    echo "   进程 PID: $API_PID"
    sleep 3

    if curl -s http://127.0.0.1:5188/health > /dev/null 2>&1; then
        echo "✅ API 服务已就绪"
    else
        echo "⚠️  服务启动中，请稍后刷新页面"
    fi
fi

# 检测系统并打开浏览器
echo ""
echo "🌐 打开前端UI..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open ui/index.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux - 尝试多种浏览器
    if command -v xdg-open &> /dev/null; then
        xdg-open ui/index.html
    elif command -v gnome-open &> /dev/null; then
        gnome-open ui/index.html
    elif command -v firefox &> /dev/null; then
        firefox ui/index.html
    else
        echo "⚠️  无法自动打开浏览器，请手动访问: file://$(pwd)/ui/index.html"
    fi
else
    echo "⚠️  无法自动打开浏览器，请手动访问: file://$(pwd)/ui/index.html"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "✅ 启动完成！"
echo ""
echo "📍 前端: file://$(pwd)/ui/index.html"
echo "📊 API:  http://127.0.0.1:5188"
echo "📚 文档: http://127.0.0.1:5188/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo "═══════════════════════════════════════════"

# 等待信号，保持前台运行
wait $!