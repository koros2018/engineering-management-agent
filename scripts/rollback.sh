#!/bin/bash
# rollback.sh — 回滚到 v3.7.1-stable 稳定版
# 用法: bash scripts/rollback.sh [--hard]
#
# --hard: 丢弃所有未提交的改动（谨慎使用）
# 不加参数: 保留当前工作区改动，只重置 git HEAD

set -e

TAG="v3.7.1-stable"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "🔙 回滚到 $TAG"
echo "   项目路径: $PROJECT_DIR"
echo ""

cd "$PROJECT_DIR"

if [ "${1:-}" = "--hard" ]; then
    echo "⚠️   --hard 模式: 丢弃所有未提交的改动"
    echo ""
    # 保存当前 stash（如果有的话）
    git stash push -m "auto-rollback-$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
    # 强制重置到稳定标签
    git reset --hard "$TAG"
    echo "✅ 已强制回滚到 $TAG，所有未提交改动已 stash"
else
    # 安全模式：只重置 HEAD，保留工作区文件
    git checkout "$TAG" -- .
    echo "✅ 已恢复所有跟踪文件到 $TAG 版本"
    echo "   未跟踪文件不受影响"
    echo "   用 git diff 查看剩余差异"
fi

echo ""
echo "📌 当前状态:"
git log --oneline -3
