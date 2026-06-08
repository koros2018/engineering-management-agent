#!/usr/bin/env python3
"""
EMA 主入口 - 工程管理智能体

用法：
    python src/main.py                    # 默认启动（API + Agent）
    python src/main.py --agent-only       # 仅Agent（无HTTP服务）
    python src/main.py --port 6188        # 指定端口
"""

import sys
import os
from pathlib import Path

# 加载 .env 环境变量
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

# 将 src 目录加入 path
sys.path.insert(0, str(Path(__file__).parent))

from api_server import run_server
import argparse


def main():
    parser = argparse.ArgumentParser(description="工程管理智能体 (EMA)")
    parser.add_argument("--host", default="0.0.0.0", help="API服务地址")
    parser.add_argument("--port", type=int, default=6188, help="API服务端口")
    parser.add_argument("--reload", action="store_true", help="开发模式热重载")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════╗
║   工程管理智能体 (EMA) v1.0.0            ║
║   Slogan: 工程管理，从"人管"到           ║
║          "智能体协管"                    ║
╠══════════════════════════════════════════╣
║ 状态: 启动中...                          ║
║ 技术标准: Manus Agent 架构                ║
║ 技术研发中心: TechRdAgent (就绪)          ║
╚══════════════════════════════════════════╝
    """)

    run_server(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()