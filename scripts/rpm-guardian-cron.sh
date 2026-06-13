#!/bin/bash
# rpm-guardian-cron.sh - RPM Guardian Cron Wrapper
# 被 cron 调用，执行 RPM 监控检查
# 用法: ./rpm-guardian-cron.sh [check|recover|probe]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="${OPENCLAW_WORKSPACE:-/mnt/d/OpenClawDataworkspace}"
LOG_FILE="$WORKSPACE/logs/rpm-guardian-cron.log"
GUARDIAN="$SCRIPT_DIR/rpm-guardian.py"

# 确保日志目录存在
mkdir -p "$(dirname "$LOG_FILE")"

# 时间戳
echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⏰ RPM Guardian Cron 启动" >> "$LOG_FILE"

# 命令
CMD="${1:-check}"

case "$CMD" in
    check)
        echo "[$(date '+%H:%M:%S')] 执行健康检查..." >> "$LOG_FILE"
        python3 "$GUARDIAN" check 2>> "$LOG_FILE"
        echo "[$(date '+%H:%M:%S')] 健康检查完成" >> "$LOG_FILE"
        ;;
    recover)
        echo "[$(date '+%H:%M:%S')] 尝试恢复主模型..." >> "$LOG_FILE"
        python3 "$GUARDIAN" recover 2>> "$LOG_FILE"
        echo "[$(date '+%H:%M:%S')] 恢复尝试完成" >> "$LOG_FILE"
        ;;
    probe)
        echo "[$(date '+%H:%M:%S')] 探测主模型..." >> "$LOG_FILE"
        python3 "$GUARDIAN" probe 2>> "$LOG_FILE"
        echo "[$(date '+%H:%M:%S')] 探测完成" >> "$LOG_FILE"
        ;;
    status)
        python3 "$GUARDIAN" status 2>> "$LOG_FILE"
        ;;
    *)
        echo "用法: $0 {check|recover|probe|status}"
        exit 1
        ;;
esac

echo "[$(date '+%H:%M:%S')] ✅ RPM Guardian Cron 完成" >> "$LOG_FILE"
exit 0
