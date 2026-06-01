#!/bin/bash
# ── EMA 服务管理脚本 ─────────────────────────────────────────
# 工程管理智能体 - 一键启动/停止/状态检查/日志查看
#
# 用法:
#   ./manage.sh start      # 启动所有服务
#   ./manage.sh stop       # 停止所有服务
#   ./manage.sh restart    # 重启所有服务
#   ./manage.sh status     # 查看服务状态
#   ./manage.sh logs       # 查看实时日志
#   ./manage.sh test       # 运行全量测试
#   ./manage.sh open       # 打开浏览器访问UI
#
# 服务:
#   API:  http://127.0.0.1:6188  (FastAPI + Uvicorn)
#   UI:   http://127.0.0.1:6189  (静态文件)
#   Docs: http://127.0.0.1:6188/docs  (Swagger)
# ──────────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

API_PORT=6188
UI_PORT=6189
API_PID_FILE="/tmp/ema_api.pid"
UI_PID_FILE="/tmp/ema_ui.pid"
API_LOG="/tmp/ema_api.log"
UI_LOG="/tmp/ema_ui.log"

# ── 颜色 ────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}ℹ️  $*${NC}"; }
ok()    { echo -e "${GREEN}✅ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; }
fail()  { echo -e "${RED}❌ $*${NC}"; }

# ── 依赖检查 ────────────────────────────────────────────────
check_deps() {
    local missing=()
    command -v python3 &>/dev/null || missing+=("python3")
    command -v curl &>/dev/null || missing+=("curl")

    # 检查Python包
    python3 -c "import fastapi, uvicorn" 2>/dev/null || missing+=("fastapi/uvicorn (pip install fastapi uvicorn)")

    if [ ${#missing[@]} -gt 0 ]; then
        fail "缺少依赖: ${missing[*]}"
        echo "  安装: pip install -r requirements.txt"
        exit 1
    fi
}

# ── 端口检查 ────────────────────────────────────────────────
port_free() {
    ! ss -tlnp 2>/dev/null | grep -q ":${1} " && \
    ! netstat -tlnp 2>/dev/null | grep -q ":${1} "
}

wait_for_port() {
    local port=$1 timeout=${2:-15} elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if curl -sf "http://127.0.0.1:${port}/health" &>/dev/null || \
           curl -sf "http://127.0.0.1:${port}/" &>/dev/null; then
            return 0
        fi
        sleep 1
        ((elapsed++))
    done
    return 1
}

# ── 启动 ────────────────────────────────────────────────────
do_start() {
    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║   工程管理智能体 (EMA) v3.5.0            ║"
    echo "║   从'人管'到'智能体协管'                 ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""

    check_deps

    # ── 启动 API ──
    if curl -sf "http://127.0.0.1:${API_PORT}/health" &>/dev/null; then
        ok "API 已在运行 (PID: $(cat $API_PID_FILE 2>/dev/null || echo '?'))"
    else
        info "启动 API 服务 (端口 ${API_PORT})..."
        nohup python3 -m uvicorn src.api_server:app \
            --host 0.0.0.0 --port ${API_PORT} \
            > "${API_LOG}" 2>&1 &
        echo $! > "${API_PID_FILE}"

        if wait_for_port ${API_PORT} 10; then
            ok "API 就绪 (PID: $(cat ${API_PID_FILE}))"
        else
            fail "API 启动超时，检查日志: tail ${API_LOG}"
            exit 1
        fi
    fi

    # ── 启动 UI ──
    if curl -sf "http://127.0.0.1:${UI_PORT}/" &>/dev/null; then
        ok "UI 已在运行 (PID: $(cat $UI_PID_FILE 2>/dev/null || echo '?'))"
    else
        info "启动 UI 服务 (端口 ${UI_PORT})..."
        nohup python3 -m http.server ${UI_PORT} --directory ui \
            > "${UI_LOG}" 2>&1 &
        echo $! > "${UI_PID_FILE}"

        sleep 2
        if curl -sf "http://127.0.0.1:${UI_PORT}/" &>/dev/null; then
            ok "UI 就绪 (PID: $(cat ${UI_PID_FILE}))"
        else
            warn "UI 启动中，稍后检查: curl http://127.0.0.1:${UI_PORT}/"
        fi
    fi

    # ── 汇总 ──
    echo ""
    echo "═══════════════════════════════════════════"
    ok "所有服务已就绪！"
    echo ""
    echo "  📍 前端UI: http://127.0.0.1:${UI_PORT}"
    echo "  📊 API:    http://127.0.0.1:${API_PORT}"
    echo "  📚 文档:   http://127.0.0.1:${API_PORT}/docs"
    echo "  💚 健康:   http://127.0.0.1:${API_PORT}/health"
    echo ""
    echo "  停止: ./manage.sh stop"
    echo "  日志: ./manage.sh logs"
    echo "═══════════════════════════════════════════"
}

# ── 停止 ────────────────────────────────────────────────────
do_stop() {
    info "停止所有服务..."

    if [ -f "${API_PID_FILE}" ]; then
        local pid=$(cat "${API_PID_FILE}")
        if kill -0 "${pid}" 2>/dev/null; then
            kill "${pid}" 2>/dev/null || true
            # 同时杀掉 uvicorn 子进程
            pkill -f "uvicorn.*${API_PORT}" 2>/dev/null || true
            ok "API 已停止 (PID: ${pid})"
        else
            warn "API 进程不存在"
        fi
        rm -f "${API_PID_FILE}"
    else
        # 尝试按端口杀
        local pid=$(lsof -ti:${API_PORT} 2>/dev/null || true)
        if [ -n "${pid}" ]; then
            kill "${pid}" 2>/dev/null || true
            ok "API 已停止 (PID: ${pid})"
        else
            info "API 未运行"
        fi
    fi

    if [ -f "${UI_PID_FILE}" ]; then
        local pid=$(cat "${UI_PID_FILE}")
        if kill -0 "${pid}" 2>/dev/null; then
            kill "${pid}" 2>/dev/null || true
            pkill -f "http.server.*${UI_PORT}" 2>/dev/null || true
            ok "UI 已停止 (PID: ${pid})"
        else
            warn "UI 进程不存在"
        fi
        rm -f "${UI_PID_FILE}"
    else
        local pid=$(lsof -ti:${UI_PORT} 2>/dev/null || true)
        if [ -n "${pid}" ]; then
            kill "${pid}" 2>/dev/null || true
            ok "UI 已停止 (PID: ${pid})"
        else
            info "UI 未运行"
        fi
    fi

    ok "全部停止"
}

# ── 状态 ────────────────────────────────────────────────────
do_status() {
    echo ""
    echo "═══ EMA 服务状态 ═══"
    echo ""

    # API
    if curl -sf "http://127.0.0.1:${API_PORT}/health" &>/dev/null; then
        local ver=$(curl -sf "http://127.0.0.1:${API_PORT}/" | python3 -c "import sys,json;print(json.load(sys.stdin).get('version','?'))" 2>/dev/null || echo "?")
        ok "API  ${API_PORT}  ✅ 运行中  (v${ver})"
    else
        fail "API  ${API_PORT}  ❌ 未运行"
    fi

    # UI
    if curl -sf "http://127.0.0.1:${UI_PORT}/" &>/dev/null; then
        ok "UI   ${UI_PORT}  ✅ 运行中"
    else
        fail "UI   ${UI_PORT}  ❌ 未运行"
    fi

    # Ollama
    if curl -sf "http://127.0.0.1:11434/api/version" &>/dev/null; then
        ok "Ollama 11434  ✅ 运行中"
    else
        warn "Ollama 11434  ⚠️  未运行（本地AI不可用）"
    fi

    # Supervisor
    if systemctl is-active --quiet ema-supervisor 2>/dev/null; then
        ok "Supervisor  ✅ 运行中"
    else
        warn "Supervisor  ⚠️  未运行"
    fi

    echo ""
    echo "📍 http://127.0.0.1:${UI_PORT}"
}

# ── 日志 ────────────────────────────────────────────────────
do_logs() {
    echo "═══ API 日志 (最后30行) ═══"
    tail -30 "${API_LOG}" 2>/dev/null || echo "无日志"
    echo ""
    echo "═══ UI 日志 (最后10行) ═══"
    tail -10 "${UI_LOG}" 2>/dev/null || echo "无日志"
}

# ── 打开浏览器 ──────────────────────────────────────────────
do_open() {
    local url="http://127.0.0.1:${UI_PORT}"
    info "打开浏览器: ${url}"

    if command -v xdg-open &>/dev/null; then
        xdg-open "${url}"
    elif command -v open &>/dev/null; then
        open "${url}"
    elif command -v wsl-open &>/dev/null; then
        wsl-open "${url}"
    else
        warn "无法自动打开浏览器，请手动访问: ${url}"
    fi
}

# ── 测试 ────────────────────────────────────────────────────
do_test() {
    info "运行全量测试..."
    cd "${PROJECT_DIR}"
    python3 -m pytest tests/ -x -q --tb=short 2>&1
    local rc=$?
    if [ $rc -eq 0 ]; then
        ok "全部通过 ✅"
    else
        fail "有测试失败 ❌"
    fi
    return $rc
}

# ── 主入口 ──────────────────────────────────────────────────
case "${1:-help}" in
    start)    do_start ;;
    stop)     do_stop ;;
    restart)  do_stop; sleep 1; do_start ;;
    status)   do_status ;;
    logs)     do_logs ;;
    open)     do_open ;;
    test)     do_test ;;
    help|*)
        echo "用法: ./manage.sh {start|stop|restart|status|logs|open|test}"
        echo ""
        echo "  start   启动所有服务"
        echo "  stop    停止所有服务"
        echo "  restart 重启所有服务"
        echo "  status  查看服务状态"
        echo "  logs    查看日志"
        echo "  open    打开浏览器"
        echo "  test    运行全量测试"
        ;;
esac
