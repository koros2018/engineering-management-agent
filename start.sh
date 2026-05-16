#!/bin/bash
# EMA 一键启动脚本 (Linux/macOS/WSL)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

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

# 启动UI静态文件服务（端口5189，从项目根目录serve）
if curl -s http://127.0.0.1:5189/health > /dev/null 2>&1; then
    echo "✅ UI 服务已在运行 (端口 5189)"
else
    echo "🚀 启动 UI 文件服务 (端口 5189)..."
    python3 -m http.server 5189 --directory . > /dev/null 2>&1 &
    UI_PID=$!
    echo "   进程 PID: $UI_PID"
    sleep 2
    if curl -s http://127.0.0.1:5189/ > /dev/null 2>&1; then
        echo "✅ UI 文件服务已就绪"
    fi
    echo "   访问地址: http://127.0.0.1:5189/ui/index.html"
fi

# 检测系统并打开浏览器
echo ""
echo "🌐 打开前端UI..."
UI_URL="http://127.0.0.1:5189/ui/index.html"
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "$UI_URL"
elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "linux"* ]]; then
    if command -v xdg-open &> /dev/null; then
        xdg-open "$UI_URL"
    elif command -v gnome-open &> /dev/null; then
        gnome-open "$UI_URL"
    elif command -v wsl-open &> /dev/null; then
        wsl-open "$UI_URL"
    elif command -v firefox &> /dev/null; then
        firefox "$UI_URL"
    else
        echo "⚠️  无法自动打开浏览器，请手动访问: $UI_URL"
    fi
else
    echo "⚠️  无法自动打开浏览器，请手动访问: $UI_URL"
fi

echo ""
echo "═══════════════════════════════════════════"
echo "✅ 启动完成！"
echo ""
echo "📍 前端UI: http://127.0.0.1:5189/ui/index.html"
echo "📊 API:    http://127.0.0.1:5188"
echo "📚 文档:   http://127.0.0.1:5188/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "═══════════════════════════════════════════"

# 保持前台运行
wait