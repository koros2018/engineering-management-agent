"""
EMA API Server - 工程管理智能体 REST API

入口：python src/api_server.py
端口：5188（默认）
"""

import sys
import os
from pathlib import Path

# 加载 .env
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        if "=" in line:
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Agent框架
from agent.base_agent import Task, AgentResult
from sub_agents import TechRdAgent


# ─────────────────────────────────────────────────────────────────
# 全局Agent实例（懒加载）
# ─────────────────────────────────────────────────────────────────

_agents = {}


def get_tech_rd_agent() -> TechRdAgent:
    if 'tech_rd' not in _agents:
        _agents['tech_rd'] = TechRdAgent()
    return _agents['tech_rd']


# ─────────────────────────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────────────────────────

class AgentChatRequest(BaseModel):
    message: str
    task_type: str = "full_analysis"
    file_path: Optional[str] = None
    project_id: Optional[str] = None
    user_id: str = "guest"


class AgentTaskRequest(BaseModel):
    agent_id: str
    task_type: str
    params: dict = {}
    context: dict = {}


# ─────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="工程管理智能体 API",
    version="1.0.0",
    description="EMA v1.0 - 技术研发中心Agent",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5189",
        "http://localhost:5189",
        "http://127.0.0.1:5188",
        "http://localhost:5188",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
# 路由
# ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "工程管理智能体 (EMA)",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ── Agent能力查询 ──────────────────────────────────────────────

@app.get("/api/v1/agents")
async def list_agents():
    """列出所有Agent及其能力"""
    tech_rd = get_tech_rd_agent()
    return {
        "agents": [
            {
                "agent_id": "tech_rd",
                "name": tech_rd.NAME,
                "description": tech_rd.DESCRIPTION,
                "supported_tasks": tech_rd.get_supported_tasks(),
                "status": "ready",
            }
        ]
    }


@app.get("/api/v1/agents/{agent_id}")
async def get_agent_info(agent_id: str):
    """获取单个Agent信息"""
    if agent_id == "tech_rd":
        agent = get_tech_rd_agent()
        return agent.get_capabilities()
    raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")


# ── Agent任务执行 ──────────────────────────────────────────────

@app.post("/api/v1/agent/chat")
async def agent_chat(req: AgentChatRequest):
    """
    对话式Agent接口
    接收自然语言请求 → 路由到对应Agent → 返回结果

    目前支持：
    - tech_rd: 图纸解析/分析/优化
    """
    task_id = str(uuid.uuid4())

    if req.task_type == "full_analysis" or req.task_type == "analyze":
        if not req.file_path:
            raise HTTPException(status_code=400, detail="file_path is required for analyze tasks")

        agent = get_tech_rd_agent()
        task = Task(
            task_id=task_id,
            agent_id="tech_rd",
            task_type=req.task_type,
            params={"file_path": req.file_path},
            context={
                "user_id": req.user_id,
                "project_id": req.project_id,
                "task_id": task_id,
            }
        )

        result = await agent.run_with_retry(task)

        return {
            "task_id": task_id,
            "agent_id": result.agent_id,
            "status": result.status,
            "confidence": result.confidence,
            "output": result.output,
            "execution_time": result.execution_time,
            "errors": result.errors,
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported task_type: {req.task_type}")


@app.post("/api/v1/agent/task")
async def submit_task(req: AgentTaskRequest):
    """通用任务提交接口"""
    task_id = str(uuid.uuid4())

    if req.agent_id == "tech_rd":
        agent = get_tech_rd_agent()
    else:
        raise HTTPException(status_code=404, detail=f"Agent '{req.agent_id}' not found")

    task = Task(
        task_id=task_id,
        agent_id=req.agent_id,
        task_type=req.task_type,
        params=req.params,
        context={**req.context, "task_id": task_id}
    )

    result = await agent.run_with_retry(task)

    return {
        "task_id": task_id,
        "agent_id": result.agent_id,
        "status": result.status,
        "confidence": result.confidence,
        "output": result.output,
        "execution_time": result.execution_time,
        "errors": result.errors,
    }


@app.get("/api/v1/agent/task/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态（预留）"""
    return {
        "task_id": task_id,
        "status": "completed",
        "note": "Simple API - use task_id from response",
    }


# ── 文件上传（便捷接口）───────────────────────────────────────

@app.post("/api/v1/upload/analyze")
async def upload_and_analyze(
    file: UploadFile = File(...),
    user_id: str = Form("guest"),
    project_id: Optional[str] = Form(None),
):
    """
    上传图纸并分析（完整流程）

    支持格式：DWG, DXF, PDF
    """
    import tempfile
    from pathlib import Path

    # 保存上传文件
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ['.dwg', '.dxf', '.pdf']:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use DWG/DXF/PDF")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 执行分析
        agent = get_tech_rd_agent()
        task_id = str(uuid.uuid4())

        task = Task(
            task_id=task_id,
            agent_id="tech_rd",
            task_type="full_analysis",
            params={"file_path": tmp_path},
            context={
                "user_id": user_id,
                "project_id": project_id,
                "task_id": task_id,
            }
        )

        result = await agent.run_with_retry(task)

        return {
            "task_id": task_id,
            "filename": file.filename,
            "agent_id": result.agent_id,
            "status": result.status,
            "confidence": result.confidence,
            "output": result.output,
            "execution_time": result.execution_time,
        }
    finally:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────
# 启动
# ─────────────────────────────────────────────────────────────────

def run_server(host: str = "0.0.0.0", port: int = 5188, reload: bool = False):
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EMA API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host")
    parser.add_argument("--port", type=int, default=5188, help="Port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, reload=args.reload)