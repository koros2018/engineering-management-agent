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
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Agent框架
from agent.base_agent import Task, AgentResult
from agent.main_agent import EngineeringManagementAgent
from sub_agents import TechRdAgent


# ─────────────────────────────────────────────────────────────────
# 全局Agent实例（懒加载）
# ─────────────────────────────────────────────────────────────────

_main_agent = None
_agents = {}


def get_main_agent() -> EngineeringManagementAgent:
    global _main_agent
    if _main_agent is None:
        _main_agent = EngineeringManagementAgent()
    return _main_agent


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
    model: Optional[str] = None  # 可选：指定模型（如 "ollama:qwen3.5:9b" 或 "cloud:gpt-4o-mini"）
    model_chain: Optional[List[str]] = None  # 可选：模型链


class AgentTaskRequest(BaseModel):
    agent_id: str
    task_type: str
    params: dict = {}
    context: dict = {}
    model: Optional[str] = None


class LLMModelInfo(BaseModel):
    model_id: str
    name: str
    provider: str  # "ollama" | "cloud"
    status: str  # "available" | "unavailable"
    description: str = ""


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
    main_agent = get_main_agent()
    caps = main_agent.get_capabilities()
    return {
        "agents": [
            {
                "agent_id": "main",
                "name": caps['name'],
                "description": caps['description'],
                "supported_tasks": caps['supported_tasks'],
                "status": "ready",
            },
            *[
                {
                    "agent_id": sa['agent_id'],
                    "name": sa['name'],
                    "description": sa['description'],
                    "supported_tasks": sa.get('supported_tasks', []),
                    "status": "ready",
                }
                for sa in caps.get('sub_agents', [])
            ],
        ]
    }


@app.get("/api/v1/llm/models")
async def list_llm_models():
    """
    列出所有可用的 LLM 模型（本地 Ollama + 云端）
    """
    try:
        from blueprint_parser.llm_service import llm
        available = llm.get_available_models()
        return {
            "success": True,
            "default_chain": llm.default_chain,
            "models": available,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "models": [
                {"model_id": "ollama:qwen3.5:9b", "name": "Qwen 3.5 9B", "provider": "ollama", "status": "unknown", "description": "默认本地模型"},
                {"model_id": "cloud:gpt-4o-mini", "name": "GPT-4o Mini", "provider": "cloud", "status": "unknown", "description": "云端模型（需配置API Key）"},
            ],
            "default_chain": ["ollama:qwen3.5:9b", "cloud:gpt-4o-mini"],
        }


@app.post("/api/v1/llm/test")
async def test_llm_model(model_id: str = Body(...)):
    """
    测试指定模型是否可用
    """
    try:
        from blueprint_parser.llm_service import LLMService, OllamaService
        
        if model_id.startswith("cloud:"):
            model = model_id[6:]
            svc = LLMService(model=model, timeout=30)
        else:
            model = model_id.replace("ollama:", "")
            svc = OllamaService(model=model, timeout=30)
        
        available = svc.is_available()
        return {
            "success": True,
            "model_id": model_id,
            "available": available,
            "error": getattr(svc, 'last_error', None),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "model_id": model_id, "available": False}


@app.get("/api/v1/agents/{agent_id}")
async def get_agent_info(agent_id: str):
    """获取单个Agent信息"""
    main_agent = get_main_agent()
    caps = main_agent.get_capabilities()

    if agent_id == "main":
        return caps

    for sa in caps.get('sub_agents', []):
        if sa['agent_id'] == agent_id:
            return sa

    raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")


# ── Main-Agent 对话入口（主要接口）─────────────────────────────

@app.post("/api/v1/main/chat")
async def main_agent_chat(
    req: AgentChatRequest,
):
    """
    Main-Agent 主对话接口
    接收自然语言 → 意图分类 → 任务规划 → Sub-Agent调度 → 结果整合

    这是 EMA 的核心入口，支持所有 Agent 的自然语言调度。
    """
    main_agent = get_main_agent()

    result = await main_agent._chat(
        params={
            'message': req.message,
            'file_path': req.file_path,
        },
        context={
            'user_id': req.user_id,
            'project_id': req.project_id,
            'task_id': str(uuid.uuid4()),
            'model': req.model,
            'model_chain': req.model_chain,
        }
    )

    return {
        "success": result.get('success', False),
        "task_id": req.project_id or str(uuid.uuid4()),
        "intent": result.get('intent'),
        "plan": result.get('plan'),
        "confidence": result.get('confidence', 0.0),
        "output": result.get('output'),
        "response_text": result.get('response_text'),
        "execution_time": result.get('execution_time', 0.0),
    }


# ── Sub-Agent 路由（原有接口，兼容）────────────────────────────

@app.post("/api/v1/agent/chat")
async def agent_chat(req: AgentChatRequest):
    """
    Sub-Agent 对话接口（兼容模式）
    直接路由到指定 Agent
    """
    task_id = str(uuid.uuid4())
    agent_id = req.task_type if req.task_type in [
        'tech_rd', 'safety_compliance', 'market_sales',
        'engineering_delivery', 'cost_benefit', 'customer_service'
    ] else 'tech_rd'

    main_agent = get_main_agent()
    agent = main_agent.sub_agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    task = Task(
        task_id=task_id,
        agent_id=agent_id,
        task_type=req.task_type,
        params={"file_path": req.file_path, "message": req.message},
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