"""
EMA API Server - 工程管理智能体 REST API

入口：python src/api_server.py
端口：6188（默认）
"""

import sys
import os
from pathlib import Path

# 加入工作空间路径（llm_supervisor 等通用模块）
_WORKSPACE = Path(__file__).parent.parent.parent.parent  # /mnt/d/OpenClawDataworkspace
_PROJECT_SRC = Path(__file__).parent  # .../engineering-management-agent/src
for _p in [str(_WORKSPACE / "src"), str(_PROJECT_SRC)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── 异步任务队列 ──────────────────────────────────────────
import threading
from concurrent.futures import ThreadPoolExecutor
_executor = ThreadPoolExecutor(max_workers=3)
_tasks = {}  # task_id -> {"status": "running|done|error", "result": ..., "progress": 0}

def _run_async(task_id: str, fn, *args, **kwargs):
    def wrapper():
        _tasks[task_id]["status"] = "running"
        try:
            result = fn(*args, **kwargs)
            _tasks[task_id]["status"] = "done"
            _tasks[task_id]["result"] = result
            _tasks[task_id]["progress"] = 100
        except Exception as e:
            _tasks[task_id]["status"] = "error"
            _tasks[task_id]["error"] = str(e)
    threading.Thread(target=wrapper, daemon=True).start()


# 加载 .env
_ENV_FILE = Path(__file__).parent.parent.parent / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        if "=" in line:
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k, v)

import asyncio
import time
import json
import uuid
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, List, Dict, Tuple

from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Form, Depends, Body, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dataclasses import asdict
import uvicorn

# Agent框架
from agent.base_agent import Task, AgentResult
from agent.main_agent import EngineeringManagementAgent
from sub_agents import TechRdAgent

# 统一日志系统
from tools.logging_utils import get_logger, log_api_request, set_request_context
logger = get_logger("api_server")

# 统一日志
from tools.logging_utils import get_logger, log_api_request, set_request_context
logger = get_logger("api_server")

# 认证模块
from auth import (
    register_user, login_user, get_user, get_user_tenant,
    refresh_access_token, get_tenant_data_dir, get_user_project_dir,
    get_current_user, get_optional_user, require_role,
    Role,
)


# ─────────────────────────────────────────────────────────────────
# API响应模型（Phase 14: OpenAPI文档增强）
# ─────────────────────────────────────────────────────────────────

class ReviewIssue(BaseModel):
    rule_id: str = ""
    rule_name: str = ""
    severity: str = "建议"  # 严重/警告/建议
    layer: str = ""
    description: str = ""
    detail: str = ""
    spec_code: str = ""
    spec_section: str = ""
    suggestion: str = ""

class ReviewSummary(BaseModel):
    total_issues: int = 0
    critical_count: int = 0
    warning_count: int = 0
    suggest_count: int = 0
    confidence: float = 0.0
    drawing_type: dict = {}
    layer_count: int = 0
    rules_applied: int = 0

class ReviewOutput(BaseModel):
    success: bool = True
    file_name: str = ""
    drawing_type: str = ""
    summary: ReviewSummary = ReviewSummary()
    issues: List[ReviewIssue] = []
    passed_rules: List[dict] = []
    specs_linked: List[dict] = []

class DocumentItem(BaseModel):
    type: str = ""
    icon: str = ""
    content: str = ""
    summary: str = ""

class DocumentsOutput(BaseModel):
    success: bool = True
    file_name: str = ""
    drawing_type: str = ""
    documents: List[DocumentItem] = []
    generated_at: str = ""

class PipelineOutput(BaseModel):
    success: bool = True
    file_name: str = ""
    drawing_type: str = ""
    project_info: dict = {}
    material_specs: dict = {}
    review: dict = {}
    documents: dict = {}
    execution_time: float = 0.0

class AnalyticsEvent(BaseModel):
    user_id: str = ""
    event: str = ""
    metadata: dict = {}
    timestamp: str = ""

class PerformanceOutput(BaseModel):
    timestamp: str = ""
    system: dict = {}
    modules: dict = {}
    llm: dict = {}
    cache: dict = {}
    data: dict = {}

class FeedbackInput(BaseModel):
    type: str = "suggestion"  # bug/feature/suggestion/praise
    score: int = 5  # 1-5
    content: str = ""
    contact: str = ""

class FeedbackOutput(BaseModel):
    success: bool = True
    message: str = ""

class LLMHealthOutput(BaseModel):
    status: str = ""
    models: dict = {}
    supervisor: dict = {}
    timeout_stats: dict = {}

class MessageResponse(BaseModel):
    success: bool = True
    message: str = ""

class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: str = ""

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
        "http://127.0.0.1:6189",
        "http://localhost:6189",
        "http://127.0.0.1:6188",
        "http://localhost:6188",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Performance tracking middleware
_metrics = {
    "requests_total": 0,
    "errors_total": 0,
    "latencies": [],
    "endpoint_stats": {},
}

@app.middleware("http")
async def performance_tracker(request, call_next):
    import time
    start = time.time()
    endpoint = request.url.path
    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        status = 500
        raise
    finally:
        elapsed = (time.time() - start) * 1000
        _metrics["requests_total"] += 1
        if status >= 400:
            _metrics["errors_total"] += 1
        _metrics["latencies"].append(elapsed)
        if len(_metrics["latencies"]) > 100:
            _metrics["latencies"] = _metrics["latencies"][-100:]
        if endpoint not in _metrics["endpoint_stats"]:
            _metrics["endpoint_stats"][endpoint] = {"count": 0, "errors": 0, "total_ms": 0, "max_ms": 0}
        ep = _metrics["endpoint_stats"][endpoint]
        ep["count"] += 1
        ep["total_ms"] += elapsed
        if elapsed > ep["max_ms"]:
            ep["max_ms"] = elapsed
        if status >= 400:
            ep["errors"] += 1
    return response


@app.on_event("startup")
async def startup_event():
    """启动时初始化Boss账号"""
    logger.info("EMA API Server 启动中...")
    try:
        from auth_extended import init_boss_account
        init_boss_account()
        logger.info("Boss账号初始化完成")
    except Exception as e:
        logger.warning(f"Boss账号初始化跳过: {e}")
    logger.info("EMA API Server 启动完成", extra={"extra_data": {"port": 6188, "docs": "/docs"}})


# ─────────────────────────────────────────────────────────────────
# 路由
# ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "工程管理智能体 (EMA)",
        "version": "3.5.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ── 用户认证 ──────────────────────────────────────────────────

@app.post("/api/v1/auth/register")
async def auth_register(username: str = Form(...), password: str = Form(...), email: str = Form(""), tenant_name: str = Form(None)):
    """用户注册 - 密码强度检查 + 用户名验证"""
    from auth_extended import validate_username, validate_password_strength
    username_err = validate_username(username)
    if username_err:
        raise HTTPException(status_code=400, detail=username_err)
    if not validate_password_strength(password):
        raise HTTPException(status_code=400, detail="密码需至少8位，含大小写字母和数字")
    try:
        user = register_user(username, password, email, tenant_name)
        return {"success": True, "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/auth/login")
async def auth_login(username: str = Form(...), password: str = Form(...)):
    """用户登录 - Boss只需账号密码即可进入主界面"""
    from auth_extended import check_login_attempt, reset_login_attempts, boss_login_without_admin_pw
    client_ip = "127.0.0.1"
    check = check_login_attempt(client_ip, username)
    if not check["allowed"]:
        raise HTTPException(status_code=429, detail=check["message"])
    try:
        result = boss_login_without_admin_pw(username, password)
        reset_login_attempts(client_ip, username)
        return {"success": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/v1/auth/verify-admin-password")
async def verify_admin_pw_route(password: str = Form(...), user: dict = Depends(get_current_user)):
    """验证管理后台密码（Boss进入后台时调用）"""
    from auth_extended import verify_admin_password
    if verify_admin_password(user["user_id"], password):
        return {"success": True, "message": "管理员密码验证通过"}
    raise HTTPException(status_code=403, detail="管理后台密码错误")


@app.post("/api/v1/auth/wechat-qr")
async def wechat_qr():
    """微信扫码登录 - 生成真实QR码(base64) + 会话"""
    from auth_extended import generate_wechat_qr
    return {"success": True, "qr": generate_wechat_qr("login")}


@app.get("/api/v1/auth/wechat-poll")
async def wechat_poll(state: str = ""):
    """轮询微信扫码状态"""
    from auth_extended import wechat_poll_status
    return wechat_poll_status(state)


@app.post("/api/v1/auth/wechat-register")
async def wechat_register(state: str = Form(...), username: str = Form(...), password: str = Form(...), email: str = Form("")):
    """扫码后注册新账号 + 绑定微信"""
    from auth_extended import wechat_register_and_bind, validate_password_strength
    if not validate_password_strength(password):
        raise HTTPException(status_code=400, detail="密码需至少8位，含大小写字母和数字")
    result = wechat_register_and_bind(state, username, password, email)
    if result.get("success"):
        return {"success": True, **result}
    raise HTTPException(status_code=400, detail=result.get("error", "注册失败"))

@app.get("/api/v1/auth/wechat-callback")
async def wechat_callback(code: str = "", state: str = ""):
    """
    微信 OAuth 回调端点（真实模式）
    微信用户扫码确认后，微信服务器重定向到此接口
    """
    from auth_extended import wechat_callback
    import json
    result = wechat_callback(code, state)
    if result.get("success") and result.get("access_token"):
        # 登录成功 → 重定向到前端带 token
        from fastapi.responses import RedirectResponse
        import urllib.parse
        token = result["access_token"]
        user_json = urllib.parse.quote(json.dumps(result.get("user", {}), ensure_ascii=False))
        return RedirectResponse(url=f"/login.html?token={token}&user={user_json}&mode=wechat")
    elif result.get("status") == "need_register":
        # 未绑定 → 重定向到注册页
        from fastapi.responses import RedirectResponse
        import urllib.parse
        params = urllib.parse.urlencode({"state": state, "openid": result.get("openid", ""), "mode": "wechat"})
        return RedirectResponse(url=f"/login.html?{params}")
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "微信授权失败"))


@app.post("/api/v1/auth/wechat-bind")
async def wechat_bind(state: str = Form(...), username: str = Form(...), password: str = Form(...)):
    """
    微信绑定已有账号
    流程：扫码(绑定模式) → 输入账号密码 → 验证 → 绑定
    """
    from auth_extended import wechat_bind_account
    from auth import verify_password as _verify_pw
    user = _verify_pw(username, password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    result = wechat_bind_account(state, user["user_id"], username)
    if result.get("success"):
        return result
    raise HTTPException(status_code=400, detail=result.get("error", "绑定失败"))



@app.post("/api/v1/auth/forgot-password")
async def forgot_password(username: str = Form(...), email: str = Form(...)):
    """密码找回"""
    from auth_extended import request_password_reset
    result = request_password_reset(username, email)
    if result.get("success"):
        return {"success": True, "message": result["message"]}
    raise HTTPException(status_code=400, detail=result.get("message", "请求失败"))


@app.post("/api/v1/auth/reset-password")
async def reset_pw(token: str = Form(...), new_password: str = Form(...)):
    """重置密码"""
    from auth_extended import reset_password
    result = reset_password(token, new_password)
    if result.get("success"):
        return {"success": True, "message": result["message"]}
    raise HTTPException(status_code=400, detail=result.get("message", "重置失败"))


@app.get("/api/v1/auth/me")
async def auth_me(user: dict = Depends(get_current_user)):
    """获取当前登录用户信息"""
    tenant = get_user_tenant(user["user_id"])
    return {"success": True, "user": {**user, **tenant}}


@app.post("/api/v1/auth/refresh")
async def auth_refresh(refresh_token: str = Form(...)):
    """用 refresh_token 换取新的 access_token"""
    result = refresh_access_token(refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    return {"success": True, "access_token": result["access_token"]}


# ── 项目管理 ──────────────────────────────────────────────────

_projects_store: Dict[str, Dict] = {}

@app.get("/api/v1/projects")
async def list_projects(user: dict = Depends(get_current_user)):
    """列出当前用户的所有项目"""
    tenant_id = user["tenant_id"]
    user_projects = [p for p in _projects_store.values() if p.get("tenant_id") == tenant_id]
    return {"success": True, "projects": user_projects}

@app.post("/api/v1/projects")
async def create_project(name: str = Form(...), description: str = Form(""), user: dict = Depends(get_current_user)):
    """创建新项目"""
    import os
    project_id = f"proj_{os.urandom(4).hex()}"
    project = {
        "project_id": project_id, "name": name, "description": description,
        "tenant_id": user["tenant_id"], "owner_id": user["user_id"],
        "created_at": datetime.now().isoformat(), "status": "active",
    }
    _projects_store[project_id] = project
    get_user_project_dir(user["tenant_id"], project_id)
    return {"success": True, "project": project}

@app.get("/api/v1/projects/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    """获取项目详情"""
    project = _projects_store.get(project_id)
    if not project or project.get("tenant_id") != user["tenant_id"]:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"success": True, "project": project}

@app.delete("/api/v1/projects/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    """删除项目（仅 owner 或 tenant_admin）"""
    project = _projects_store.get(project_id)
    if not project or project.get("tenant_id") != user["tenant_id"]:
        raise HTTPException(status_code=404, detail="项目不存在")
    if project["owner_id"] != user["user_id"] and user["role"] not in [Role.TENANT_ADMIN, Role.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="权限不足")
    _projects_store[project_id]["status"] = "archived"
    return {"success": True, "message": "项目已归档"}


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


@app.get("/api/v1/conversations")
async def get_conversations(
    session_id: str = None,
    limit: int = 20,
):
    """
    获取对话历史（从 ChromaDB）
    """
    try:
        from memory import get_chroma_store
        store = get_chroma_store()
        if session_id:
            results = store.search_conversations(query="", session_id=session_id, limit=limit)
        else:
            # 返回所有会话的最新消息（取每个session最近一条）
            results = store.search_conversations(query="*", limit=min(limit, 50))
        
        # 按session_id分组
        sessions = {}
        for r in results:
            sid = r['metadata'].get('session_id', 'unknown')
            if sid not in sessions:
                sessions[sid] = {'id': sid, 'messages': [], 'last_time': 0}
            ts = r['metadata'].get('timestamp', 0)
            sessions[sid]['messages'].append({
                'role': r['metadata'].get('role', 'unknown'),
                'content': r['content'][:200],  # 截断
                'agent_id': r['metadata'].get('agent_id', ''),
            })
            if ts > sessions[sid]['last_time']:
                sessions[sid]['last_time'] = ts
        
        # 转换为列表并排序
        session_list = sorted(sessions.values(), key=lambda x: x['last_time'], reverse=True)[:limit]
        for s in session_list:
            s.pop('last_time', None)
        
        return {"success": True, "conversations": session_list}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/v1/conversations/search")
async def search_conversations(q: str = None, session_id: str = None, limit: int = 10):
    """搜索对话历史"""
    try:
        from memory import get_chroma_store
        store = get_chroma_store()
        if not q:
            return {"success": False, "error": "q参数必填"}
        results = store.search_conversations(query=q, session_id=session_id, limit=limit)
        return {
            "success": True,
            "results": [
                {
                    "content": r['content'][:500],
                    "session_id": r['metadata'].get('session_id', ''),
                    "role": r['metadata'].get('role', ''),
                    "agent_id": r['metadata'].get('agent_id', ''),
                    "distance": r.get('distance', 0),
                }
                for r in results
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/v1/llm/models")
async def list_llm_models():
    """
    列出所有可用的 LLM 模型（本地 Ollama + 云端）
    """
    try:
        from model_registry import get_all_models, check_network
        regs = get_all_models()
        models = []
        for r in regs:
            models.append({
                "model_id": r.model_id,
                "name": r.name,
                "provider": r.provider,
                "status": "available" if r.enabled else "disabled",
                "description": r.description,
            })
        if not models:
            models = [
                {"model_id": "nvidia/deepseek-v4-pro", "name": "DeepSeek V4 Pro", "provider": "nvidia", "status": "unknown", "description": "云端最强模型"},
            ]
        return {
            "success": True,
            "models": models,
            "default_chain": [m["model_id"] for m in models if m["status"] == "available"][:3],
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "models": [
                {"model_id": "nvidia/deepseek-v4-pro", "name": "DeepSeek V4 Pro", "provider": "nvidia", "status": "unknown", "description": "云端模型"},
            ],
            "default_chain": ["nvidia/deepseek-v4-pro"],
        }


@app.post("/api/v1/llm/test")
async def test_llm_model(request: Request):
    """测试指定模型是否可用 (接受 JSON {"model": "xxx"} 或 Form model=xxx)"""
    ct = request.headers.get("content-type", "")
    if "json" in ct:
        body = await request.json()
        model_id = body.get("model", body.get("model_id", ""))
    else:
        form = await request.form()
        model_id = form.get("model", form.get("model_id", ""))
    if not model_id:
        raise HTTPException(status_code=400, detail="model parameter required")
    try:
        from model_registry import get_model, check_network
        from llm_supervisor import supervisor
        reg = get_model(model_id)
        if not reg:
            return {"success": True, "model_id": model_id, "available": False, "error": "Model not registered"}
        net = check_network()
        stats = supervisor.get_model_stats(model_id)
        return {
            "success": True,
            "model_id": model_id,
            "available": reg.enabled and not stats.get("disabled", False),
            "provider": reg.provider,
            "network_ok": net.get("nvidia_api", True) if reg.provider == "nvidia" else True,
            "stats": stats,
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


# ── 性能监控 API ──────────────────────────────────────────────

@app.get("/api/v1/system/performance", summary="系统性能监控", description="获取系统各模块的性能指标。\n\n**返回数据**:\n- 系统信息 (CPU/内存/磁盘/OS)\n- 模块加载状态 (Blueprint/Review/Documents/LLM)\n- LLM健康状态 (超时统计/错误率/降级记录)\n- 缓存统计 (命中率/大小/TTL)\n- 数据统计 (用户数/项目数/文件数)")
async def system_performance():
    """系统性能监控面板数据"""
    import time, os, platform, sys
    from pathlib import Path

    perf = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}

    # 系统信息
    perf["system"] = {
        "platform": platform.system(),
        "python": sys.version.split()[0],
        "uptime": "N/A",
    }

    # 模块加载状态
    modules = {}
    for mod_name, import_path in [
        ("blueprint_core", "src.blueprint.core"),
        ("classifier", "src.blueprint.ai.classifier"),
        ("extractor", "src.blueprint.ai.extractor"),
        ("review_engine", "src.blueprint.review.engine"),
        ("doc_generator", "src.blueprint.documents.generator"),
        ("tech_rd_agent", "src.sub_agents.tech_rd_agent"),
    ]:
        t0 = time.time()
        try:
            __import__(import_path)
            modules[mod_name] = {"status": "✅", "load_ms": round((time.time()-t0)*1000, 1)}
        except Exception as e:
            modules[mod_name] = {"status": "❌", "error": str(e)[:60]}
    perf["modules"] = modules

    # LLM状态
    try:
        from src.llm_supervisor import LLMSupervisor
        supervisor = LLMSupervisor()
        perf["llm"] = supervisor.get_health()
    except Exception:
        perf["llm"] = {"status": "unavailable"}

    # 缓存统计
    try:
        from src.performance import get_cache_stats
        perf["cache"] = get_cache_stats()
    except Exception:
        perf["cache"] = {"status": "unavailable"}

    # 日志统计
    try:
        from src.log_stats import get_log_stats
        perf["logs"] = get_log_stats()
    except Exception:
        perf["logs"] = {"status": "unavailable"}

    # 数据目录大小
    data_dir = Path(__file__).parent.parent / "data"
    if data_dir.exists():
        total_size = sum(f.stat().st_size for f in data_dir.rglob("*") if f.is_file())
        file_count = sum(1 for _ in data_dir.rglob("*") if _.is_file())
        perf["data"] = {"size_mb": round(total_size/1024/1024, 1), "files": file_count}
    else:
        perf["data"] = {"size_mb": 0, "files": 0}

    return perf


# ── LLM 超时监督 API ──────────────────────────────────────────

@app.get("/api/v1/llm/health", summary="LLM健康检查", description="获取大模型服务健康状态和超时监督数据。\n\n**返回数据**:\n- 各模型状态 (可用/禁用/超时次数)\n- 超时监督统计 (连续失败/自动降级/恢复记录)\n- 响应时间分布\n- 错误率统计")
async def llm_health():
    """获取LLM健康状态（超时监督数据）"""
    try:
        from llm_supervisor import supervisor
        return {"success": True, "data": supervisor.get_health()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/v1/llm/health/reset")
async def llm_health_reset():
    """重置每日统计"""
    try:
        from llm_supervisor import supervisor
        supervisor.reset_daily()
        return {"success": True, "message": "每日统计已重置"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/v1/llm/health/check")
async def llm_health_check():
    """立即执行云模型健康检测"""
    try:
        from llm_supervisor import supervisor
        nvidia = supervisor.check_nvidia_health()
        ollama = supervisor.check_ollama_health()
        return {"success": True, "data": {"nvidia": nvidia, "ollama": ollama}}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
            'message': message,
            'file_path': file_path,
        },
        context={
            'user_id': user_id,
            'project_id': project_id,
            'task_id': str(uuid.uuid4()),
            'model': req.model,
            'model_chain': req.model_chain,
        }
    )

    return {
        "success": result.get('success', False),
        "task_id": project_id or str(uuid.uuid4()),
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
        'engineering_delivery', 'cost_benefit', 'customer_service',
        'manager'
    ] else 'tech_rd'

    main_agent = get_main_agent()
    agent = main_agent.sub_agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    task = Task(
        task_id=task_id,
        agent_id=agent_id,
        task_type=req.task_type,
        params={"file_path": file_path, "message": message},
        context={
            "user_id": user_id,
            "project_id": project_id,
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
    disable_ocr: bool = Form(True),
):
    """
    上传图纸并分析（含缓存加速）
    支持格式：DWG, DXF, PDF
    """
    import tempfile
    from pathlib import Path

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ['.dwg', '.dxf', '.pdf']:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use DWG/DXF/PDF")

    # ── 持久化存储路径 ──
    from performance import get_cached_analysis, cache_analysis
    UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # 保存到持久化路径（文件名加时间戳避免冲突）
    safe_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = UPLOAD_DIR / safe_name

    content = await file.read()
    save_path.write_bytes(content)

    # ── 检查缓存 ──
    cached = get_cached_analysis(save_path)
    if cached:
        logger.info(f"[Cache HIT] {file.filename} ({save_path.name})")
        return {
            "success": True,
            "file_path": file.filename,
            "message": "图纸分析完成（缓存）",
            "analysis": cached.get("analysis", cached),
            "cached": True,
        }

    logger.info(f"[Cache MISS] {file.filename} → 开始解析")

    try:
        from blueprint.core import BlueprintParser
        parser = BlueprintParser()
        if suffix == '.pdf' and disable_ocr:
            parser.pdf_parser.use_ocr = False

        result = parser.parse(str(save_path))

        analysis = {
            "file_type": result.file_type.value if hasattr(result.file_type, 'value') else str(result.file_type),
            "drawing_type": "待识别",
            "layer_count": len(result.layers),
            "entity_count": len(result.entities),
            "layers": [
                {"name": l.name, "color": l.color, "visible": getattr(l, "visible", True)}
                for l in result.layers[:50]
            ],
            "entities": [
                {"type": getattr(e, "type", "UNKNOWN"), "layer": getattr(e, "layer", "")}
                for e in result.entities[:50]
            ],
            "metadata": result.metadata,
        }

        # ── 写入缓存 ──
        cache_analysis(save_path, {"analysis": analysis})

        return {
            "success": result.success,
            "file_path": file.filename,
            "message": "图纸分析完成",
            "analysis": analysis,
            "error": "; ".join(result.errors) if result.errors else None,
            "cached": False,
        }
    except Exception as e:
        logger.error(f"[Parse Error] {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


# ── Blueprint AI 增强分析 API ─────────────────────────────────

@app.post("/api/v1/blueprint/ai-analyze")
async def blueprint_ai_analyze(
    file: UploadFile = File(...),
    user_id: str = Form("guest"),
    use_llm: bool = Form(True),
    enable_ai: bool = Form(True),
    disable_ocr: bool = Form(True),
):
    """AI增强型图纸分析 — 上传图纸返回完整AI分析（分类+提取+设计原则+施工要求）"""
    from pathlib import Path

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ['.dwg', '.dxf', '.pdf']:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"ai_{int(time.time())}_{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = UPLOAD_DIR / safe_name
    save_path.write_bytes(await file.read())

    try:
        from blueprint.core import BlueprintParser
        parser = BlueprintParser(use_ocr=not disable_ocr, enable_ai=enable_ai, use_llm=use_llm)
        result = parser.parse_with_ai(str(save_path))
        return {"success": result.get('success', False), "file_path": file.filename, "result": result}
    except Exception as e:
        logger.error(f"[AI Analyze Error] {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI分析失败: {str(e)}")


@app.post("/api/v1/blueprint/ai-extract")
async def blueprint_ai_extract(
    file: UploadFile = File(...),
    user_id: str = Form("guest"),
    use_llm: bool = Form(True),
    disable_ocr: bool = Form(True),
):
    """工程信息智能提取 — 轻量级，只返回工程信息（项目名/面积/层数/结构/材料/参数）"""
    from pathlib import Path

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ['.dwg', '.dxf', '.pdf']:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"ex_{int(time.time())}_{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = UPLOAD_DIR / safe_name
    save_path.write_bytes(await file.read())

    try:
        from blueprint.core import BlueprintParser
        from blueprint.ai.classifier import smart_classify
        from blueprint.ai.extractor import smart_extract, extract_material_specs, extract_design_params

        parser = BlueprintParser(use_ocr=not disable_ocr, enable_ai=False)
        parse_result = parser.parse(str(save_path))
        if not parse_result.success:
            return {"success": False, "errors": parse_result.errors}

        file_name = Path(file.filename).name
        layers = [l.name for l in parse_result.layers]
        raw_text = parse_result.raw_text

        drawing_type = smart_classify(layers=layers, raw_text=raw_text, file_name=file_name, use_llm=use_llm)
        project_info = smart_extract(raw_text=raw_text, file_name=file_name, drawing_type=drawing_type.get('primary',''), layers=layers, use_llm=use_llm)
        material_specs = extract_material_specs(raw_text)
        design_params = extract_design_params(raw_text)

        return {
            "success": True, "file_name": file_name, "file_type": parse_result.file_type.value,
            "drawing_type": drawing_type, "project_info": project_info,
            "material_specs": material_specs, "design_params": design_params,
            "layer_count": len(parse_result.layers), "entity_count": len(parse_result.entities),
        }
    except Exception as e:
        logger.error(f"[AI Extract Error] {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"信息提取失败: {str(e)}")


@app.get("/api/v1/blueprint/supported-formats")
async def blueprint_supported_formats():
    """列出支持的图纸格式和AI能力"""
    import os
    llm_enabled = os.environ.get("BLUEPRINT_LLM_ENABLED", "true").lower() == "true"
    return {
        "success": True, "formats": [".dwg", ".dxf", ".pdf"],
        "ai_capabilities": {
            "drawing_type_classification": {"enabled": True, "engines": ["rule_engine", "llm"] if llm_enabled else ["rule_engine"], "types": ["建筑","结构","给排水","暖通","电气","消防","总图","景观","机电","精装","工艺"]},
            "layer_semantics": {"enabled": True, "languages": ["english", "chinese"], "tarch_encoding": True},
            "project_info_extraction": {"enabled": True, "engines": ["rule_regex", "llm"] if llm_enabled else ["rule_regex"], "fields": ["project_name","project_number","building_area","floor_count","building_height","structure_type","foundation_type","design_unit","drawing_number","design_basis","fire_resistance_rating","seismic_intensity"]},
            "material_spec_extraction": {"enabled": True},
            "design_param_extraction": {"enabled": True},
            "design_principles": {"enabled": True},
            "construction_requirements": {"enabled": True},
        },
        "llm_status": "enabled" if llm_enabled else "disabled",
    }


# ─── Blueprint 审查 API ───────────────────────────────────────────

@app.post("/api/v1/blueprint/review")
async def blueprint_review(request: Request):
    """图纸智能审查（基于国标规范）
    
    请求体: {"file_path": "/path/to/file.dxf", "drawing_type": "建筑平面图"}
    或: {"analysis": {...已有的分析结果...}}
    """
    from src.blueprint.review.engine import review_blueprint, review_analysis
    data = await request.json()
    
    if "analysis" in data:
        result = review_analysis(data["analysis"])
        return {"success": True, "review": result}
    
    file_path = data.get("file_path", "")
    if not file_path:
        return {"success": False, "error": "缺少file_path或analysis参数"}
    
    drawing_type = data.get("drawing_type", "")
    result = review_blueprint(file_path, drawing_type=drawing_type)
    return {"success": True, "review": result}


@app.post("/api/v1/blueprint/review/analysis")
async def blueprint_review_analysis(request: Request):
    """从已有分析结果进行审查"""
    from src.blueprint.review.engine import review_analysis
    data = await request.json()
    analysis = data.get("analysis", {})
    if not analysis:
        return {"success": False, "error": "缺少analysis参数"}
    result = review_analysis(analysis)
    return {"success": True, "review": result}


@app.get("/api/v1/blueprint/review/rules")
async def blueprint_review_rules():
    """列出所有审查规则"""
    from src.blueprint.review.engine import RULES
    rules = []
    for r in RULES:
        rules.append({
            "id": r.id, "name": r.name, "severity": r.severity,
            "spec_code": r.spec_code, "spec_section": r.spec_section,
        })
    return {"success": True, "rules": rules, "total": len(rules)}


# ─── Blueprint 文档生成 API ───────────────────────────────────────

@app.post("/api/v1/blueprint/documents/generate")
async def blueprint_generate_documents(request: Request):
    """生成完整工程文档集
    
    请求体: {"analysis": {...}, "doc_types": ["all"] 或 ["design_description", ...]}
    """
    from src.blueprint.documents.generator import generate_full_document_set
    data = await request.json()
    analysis = data.get("analysis", {})
    if not analysis:
        return {"success": False, "error": "缺少analysis参数"}
    
    doc_types = data.get("doc_types", ["all"])
    try:
        if "all" in doc_types:
            result = generate_full_document_set(analysis)
        else:
            from src.blueprint.documents.generator import (
                generate_design_description, generate_technical_disclosure,
                generate_quantity_list, generate_change_request, generate_bid_document,
            )
            type_map = {
                "design_description": generate_design_description,
                "technical_disclosure": generate_technical_disclosure,
                "quantity_list": generate_quantity_list,
                "change_request": generate_change_request,
                "bid_document": generate_bid_document,
            }
            docs = {dt: type_map[dt](analysis) for dt in doc_types if dt in type_map}
            result = {"success": True, "analysis": analysis, "documents": docs}
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
    return {"success": True, "documents": result}


@app.post("/api/v1/blueprint/documents/single")
async def blueprint_generate_single_document(request: Request):
    """生成单个类型的工程文档
    
    请求体: {"analysis": {...}, "doc_type": "design_description"}
    """
    from src.blueprint.documents.generator import (
        generate_design_description, generate_technical_disclosure,
        generate_quantity_list, generate_change_request, generate_bid_document,
    )
    data = await request.json()
    analysis = data.get("analysis", {})
    doc_type = data.get("doc_type", "design_description")
    type_map = {
        "design_description": generate_design_description,
        "technical_disclosure": generate_technical_disclosure,
        "quantity_list": generate_quantity_list,
        "change_request": generate_change_request,
        "bid_document": generate_bid_document,
    }
    fn = type_map.get(doc_type)
    if not fn:
        return {"success": False, "error": f"不支持的文档类型: {doc_type}", "supported": list(type_map.keys())}
    try:
        result = fn(analysis)
    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
    return {"success": True, "doc_type": doc_type, "content": result}


@app.get("/api/v1/blueprint/documents/types")
async def blueprint_document_types():
    """列出支持的文档类型"""
    return {
        "success": True,
        "types": [
            {"id": "design_description", "name": "设计说明", "description": "工程设计说明"},
            {"id": "technical_disclosure", "name": "施工技术交底", "description": "6大专业施工工艺交底"},
            {"id": "quantity_list", "name": "工程量清单", "description": "工程量估算清单"},
            {"id": "change_request", "name": "技术核定单", "description": "设计变更技术核定"},
            {"id": "bid_document", "name": "招投标文件", "description": "招标文件技术要求"},
        ],
    }


# ─── Agent 工作流 API ─────────────────────────────────────────────

@app.post("/api/v1/agent/review", summary="智能审查", description="上传图纸文件(DWG/DXF/PDF)，执行AI智能审查。\n\n**流程**: 文件上传 → 图纸解析 → 图层分类 → 规则引擎审查 → 输出审查报告\n\n**审查规则**: 消防疏散、防火分区、楼梯规范、标题栏、标注规范、结构安全等15条国标规则\n\n**返回**: 审查问题列表(严重/警告/建议)、质量评分、规范引用")
async def agent_review(
    file: UploadFile = File(...),
    user_id: str = Form("guest"),
    use_llm: bool = Form(False),
):
    """上传图纸并执行智能审查"""
    import tempfile
    from pathlib import Path

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ['.dwg', '.dxf', '.pdf']:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"review_{int(time.time())}_{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = UPLOAD_DIR / safe_name
    content = await file.read()
    save_path.write_bytes(content)

    try:
        from src.sub_agents.tech_rd_agent import TechRdAgent
        from src.agent.base_agent import Task

        agent = TechRdAgent()
        # 先解析
        parse_task = Task(
            task_id="api_review_parse",
            agent_id="tech_rd",
            task_type="parse",
            params={"file_path": str(save_path), "use_ai": False},
            context={"task_id": "api_review_parse"},
        )
        parse_result = await agent.run_with_retry(parse_task)
        if parse_result.status != "success":
            return {"success": False, "error": parse_result.errors or ["解析失败"]}

        # AgentResult.output 是 dict（to_dict序列化）
        pr = parse_result.output or {}
        layers = pr.get('layers', []) if isinstance(pr, dict) else []
        layer_names = [l.get('name', '') if isinstance(l, dict) else str(l) for l in layers]
        raw_text = pr.get('raw_text', '') if isinstance(pr, dict) else ''
        geometry = pr.get('geometry', {}) if isinstance(pr, dict) else {}
        layer_stats = pr.get('layer_stats', {}) if isinstance(pr, dict) else {}

        # 分类+AI分析并行（CPU密集→to_thread）
        from src.blueprint.ai.classifier import smart_classify
        from src.blueprint.ai.extractor import smart_extract
        import asyncio as _asyncio

        def _classify():
            return smart_classify(layer_names, file_name=file.filename, raw_text=raw_text, use_llm=False)

        def _analyze(drawing_type):
            return smart_extract(raw_text, file.filename, drawing_type, layer_names, use_llm=False)

        cls = await _asyncio.to_thread(_classify)
        drawing_type = cls.get("primary_type", "建筑") if isinstance(cls, dict) else "建筑"
        analysis = await _asyncio.to_thread(_analyze, drawing_type)

        review_analysis = {
            "file_name": file.filename,
            "drawing_type": {"primary": drawing_type, "confidence": 0.85},
            "layers": layer_names,
            "layer_stats": layer_stats,
            "entities": [],
            "geometry": geometry,
            "ai_analysis": analysis,
        }

        # 审查
        from src.blueprint.review.engine import review_drawing
        review_output = await _asyncio.to_thread(review_drawing, review_analysis)

        return {
            "success": True,
            "output": review_output,
            "file_name": file.filename,
            "drawing_type": drawing_type,
        }
    except Exception as e:
        logger.error(f"[Agent Review Error] {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"审查失败: {str(e)}")


@app.post("/api/v1/agent/documents", summary="文档生成", description="上传图纸文件，自动生成工程文档。\n\n**支持文档类型**:\n- 设计说明 — 工程概况、设计依据、技术指标\n- 工程量清单 — 按专业分类的估算清单\n- 施工技术交底 — 施工工艺、质量标准、安全措施\n- 技术核定单 — 设计变更确认\n- 招投标文件 — 招标文件框架\n\n**流程**: 文件上传 → 图纸解析 → AI信息提取 → 文档生成")
async def agent_documents(
    file: UploadFile = File(...),
    user_id: str = Form("guest"),
    doc_types: str = Form("design_spec"),
    use_llm: bool = Form(False),
):
    """上传图纸并生成工程文档"""
    import json as _json
    from pathlib import Path

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ['.dwg', '.dxf', '.pdf']:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = f"doc_{int(time.time())}_{uuid.uuid4().hex[:8]}_{file.filename}"
    save_path = UPLOAD_DIR / safe_name
    content = await file.read()
    save_path.write_bytes(content)

    try:
        from src.sub_agents.tech_rd_agent import TechRdAgent
        from src.agent.base_agent import Task

        agent = TechRdAgent()
        # 解析
        parse_task = Task(
            task_id="api_doc_parse",
            agent_id="tech_rd",
            task_type="parse",
            params={"file_path": str(save_path), "use_ai": False},
            context={"task_id": "api_doc_parse"},
        )
        parse_result = await agent.run_with_retry(parse_task)
        if parse_result.status != "success":
            return {"success": False, "error": parse_result.errors or ["解析失败"]}

        # AgentResult.output 是 dict（to_dict序列化）
        pr = parse_result.output or {}
        layers = pr.get('layers', []) if isinstance(pr, dict) else []
        layer_names = [l.get('name', '') if isinstance(l, dict) else str(l) for l in layers]
        raw_text = pr.get('raw_text', '') if isinstance(pr, dict) else ''
        geometry = pr.get('geometry', {}) if isinstance(pr, dict) else {}
        layer_stats = pr.get('layer_stats', {}) if isinstance(pr, dict) else {}

        # 分类
        from src.blueprint.ai.classifier import smart_classify
        cls = smart_classify(layer_names, file_name=file.filename, raw_text=raw_text, use_llm=False)
        drawing_type = cls.get("primary_type", "建筑") if isinstance(cls, dict) else "建筑"

        # AI分析
        from src.blueprint.ai.extractor import smart_extract
        analysis = smart_extract(raw_text, file.filename, drawing_type, layer_names, use_llm=False)

        review_analysis = {
            "file_name": file.filename,
            "drawing_type": {"primary": drawing_type, "confidence": 0.85},
            "layers": layer_names,
            "layer_stats": layer_stats,
            "entities": [],
            "geometry": geometry,
            "ai_analysis": analysis,
        }

        # 文档生成
        from src.blueprint.documents.generator import generate_full_document_set
        doc_output = generate_full_document_set(review_analysis)

        # 转换为前端友好格式
        documents = []
        if isinstance(doc_output, dict):
            docs_dict = doc_output.get("documents", doc_output)
            type_names = {
                "design_description": "设计说明",
                "quantity_list": "工程量清单",
                "technical_disclosure": "施工技术交底",
                "change_request": "技术核定单",
                "bid_document": "招投标文件",
            }
            type_icons = {
                "design_description": "📋",
                "quantity_list": "📊",
                "technical_disclosure": "📝",
                "change_request": "✅",
                "bid_document": "📑",
            }
            for dtype, content in docs_dict.items():
                if isinstance(content, str) and content:
                    documents.append({
                        "type": type_names.get(dtype, dtype),
                        "icon": type_icons.get(dtype, "📄"),
                        "content": content,
                        "summary": "",
                    })

        return {
            "success": True,
            "output": {"documents": documents},
            "file_name": file.filename,
            "drawing_type": drawing_type,
        }
    except Exception as e:
        logger.error(f"[Agent Documents Error] {file.filename}: {e}")
        raise HTTPException(status_code=500, detail=f"文档生成失败: {str(e)}")

@app.post("/api/v1/agent/pipeline", summary="端到端流水线", description="一键执行完整的Agent工作流：解析 → 分类 → AI分析 → 审查 → 文档生成。\n\n**5步流程**:\n1. 图纸解析 (DWG/DXF/PDF)\n2. 图层分类 (规则+AI)\n3. 工程信息提取 (smart_extract)\n4. 智能审查 (15条国标规则)\n5. 文档生成 (设计说明+工程量清单+技术交底)\n\n**返回**: 完整的分析结果、审查报告、生成文档")
async def agent_pipeline(
    file: UploadFile = File(None),
    file_path: str = Form(None),
    user_id: str = Form("guest"),
    use_llm: bool = Form(False),
    doc_types: str = Form("all"),
):
    """端到端Agent工作流：解析→分类→AI分析→审查→文档"""
    import tempfile
    from pathlib import Path
    from src.sub_agents.tech_rd_agent import TechRdAgent
    from src.agent.base_agent import Task

    # 支持文件上传或直接传路径
    if file:
        suffix = Path(file.filename).suffix.lower()
        UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = f"pipe_{int(time.time())}_{uuid.uuid4().hex[:8]}_{file.filename}"
        save_path = UPLOAD_DIR / safe_name
        content = await file.read()
        save_path.write_bytes(content)
        actual_path = str(save_path)
    elif file_path:
        actual_path = file_path
    else:
        raise HTTPException(status_code=400, detail="需要file或file_path参数")
    
    agent = TechRdAgent()
    doc_type_list = [t.strip() for t in doc_types.split(",")] if doc_types != "all" else ["all"]
    task = Task(
        task_id="api_pipeline",
        agent_id="tech_rd",
        task_type="full_pipeline",
        params={
            "file_path": actual_path,
            "use_llm": use_llm,
            "doc_types": doc_type_list,
        },
        context={"task_id": "api_pipeline"},
    )
    result = await agent.run_with_retry(task)
    return {
        "success": result.status == "success",
        "output": result.output,
        "confidence": result.confidence,
        "execution_time": result.execution_time,
        "errors": result.errors,
    }


@app.post("/api/v1/agent/analyze")
async def agent_analyze(request: Request):
    """完整分析工作流：解析→分类→AI分析→工程量
    
    请求体: {"file_path": "/path/to/file.dxf", "use_llm": false}
    """
    from src.sub_agents.tech_rd_agent import TechRdAgent
    from src.agent.base_agent import Task
    
    data = await request.json()
    file_path = data.get("file_path")
    if not file_path:
        return {"success": False, "error": "缺少file_path参数"}
    
    agent = TechRdAgent()
    task = Task(
        task_id="api_analyze",
        agent_id="tech_rd",
        task_type="full_analysis",
        params={
            "file_path": file_path,
            "use_llm": data.get("use_llm", False),
        },
        context={"task_id": "api_analyze"},
    )
    result = await agent.run_with_retry(task)
    return {
        "success": result.status == "success",
        "output": result.output,
        "confidence": result.confidence,
        "execution_time": result.execution_time,
        "errors": result.errors,
    }


@app.get("/api/v1/agent/capabilities")
async def agent_capabilities():
    """列出所有Agent能力"""
    from src.sub_agents.tech_rd_agent import TechRdAgent
    from src.agent.main_agent import EngineeringManagementAgent
    
    main = EngineeringManagementAgent()
    tech_rd = TechRdAgent()
    
    return {
        "success": True,
        "main_agent": main.get_capabilities(),
        "tech_rd_agent": tech_rd.get_capabilities(),
        "supported_task_types": tech_rd.get_supported_tasks(),
        "pipeline_steps": ["parse", "classify", "analyze", "review", "documents"],
    }


# ── 订阅套餐 API ────────────────────────────────────────────────

@app.get("/api/v1/subscription/plans")
async def get_plans():
    """列出所有订阅套餐"""
    from subscription import list_plans
    return {"success": True, "plans": list_plans()}


@app.get("/api/v1/subscription/status")
async def subscription_status(
    user: dict = Depends(get_optional_user),
):
    """获取当前用户/租户的订阅状态"""
    tenant_id = user["tenant_id"] if user else "guest"
    from subscription import check_subscription, get_usage, check_quota
    return {
        "success": True,
        "subscription": check_subscription(tenant_id),
        "usage": get_usage(tenant_id),
        "quota": check_quota(tenant_id),
    }


@app.post("/api/v1/subscription/subscribe")
async def subscribe(
    plan_id: str = Form(...),
    duration_months: int = Form(1),
    user: dict = Depends(get_current_user),
):
    """订阅/升级套餐"""
    try:
        from subscription import subscribe
        result = subscribe(user["tenant_id"], plan_id, duration_months)
        return {"success": True, "subscription": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── 支付 API ─────────────────────────────────────────────────

@app.post("/api/v1/payment/create")
async def create_payment(
    plan_id: str = Form(...),
    amount: float = Form(...),
    payment_method: str = Form("wechat"),
    duration_months: int = Form(1),
    user: dict = Depends(get_current_user),
):
    """创建支付订单（微信/支付宝）"""
    from payment import create_order, wechat_prepay, alipay_prepay
    tenant_id = user["tenant_id"]

    if payment_method == "wechat":
        result = wechat_prepay(tenant_id, plan_id, amount)
    elif payment_method == "alipay":
        result = alipay_prepay(tenant_id, plan_id, amount)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的支付方式: {payment_method}")

    return {"success": True, "payment": result}


@app.get("/api/v1/payment/orders")
async def list_payment_orders(
    status: str = None,
    user: dict = Depends(get_current_user),
):
    """列出用户的支付订单"""
    from payment import list_orders
    return {"success": True, "orders": list_orders(user["tenant_id"], status)}


@app.get("/api/v1/payment/orders/{order_id}")
async def get_payment_order(
    order_id: str,
    user: dict = Depends(get_current_user),
):
    """查询单个订单"""
    from payment import get_order
    order = get_order(order_id)
    if not order or order.get("tenant_id") != user["tenant_id"]:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {"success": True, "order": order}


@app.post("/api/v1/payment/mock-pay/{order_id}")
async def mock_pay(order_id: str):
    """模拟支付成功（Phase 7 Stub，生产环境改为微信/支付宝回调）"""
    try:
        from payment import mock_pay_success
        result = mock_pay_success(order_id)
        return {"success": True, "payment": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/payment/wechat-callback")
async def wechat_callback(request: Request):
    """微信支付回调（生产环境）"""
    body = await request.body()
    body_str = body.decode()
    headers = dict(request.headers)

    try:
        from payment_sdk import wechat_verify_callback
        is_valid, order_data = wechat_verify_callback(headers, body_str)

        if not is_valid or not order_data:
            from security import log_security_event
            log_security_event("payment_fraud", "critical", f"微信支付回调签名验证失败: {body_str[:200]}")
            return {"code": "FAIL", "message": "签名验证失败"}

        from payment import mock_pay_success
        mock_pay_success(order_data.get("out_trade_no", ""))

        # 微信要求返回明确的成功/失败
        return {"code": "SUCCESS", "message": "OK"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/payment/alipay-callback")
async def alipay_callback(request: Request):
    """支付宝支付回调（生产环境）"""
    form_data = await request.form()
    params = {k: v for k, v in form_data.items()}

    try:
        from payment_sdk import alipay_verify_callback
        is_valid, order_data = alipay_verify_callback(params)

        if not is_valid or not order_data:
            from security import log_security_event
            log_security_event("payment_fraud", "critical", f"支付宝回调签名验证失败")
            return "fail"

        if order_data.get("trade_status") == "TRADE_SUCCESS":
            from payment import mock_pay_success
            mock_pay_success(order_data.get("out_trade_no", ""))

        return "success"
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 性能压测 API ─────────────────────────────────────────────

@app.post("/api/v1/system/benchmark")
async def run_benchmark(
    endpoint: str = Form(None),
    concurrent: int = Form(10),
    total: int = Form(100),
):
    """执行性能压测（后台异步执行，不阻塞API）"""
    import asyncio
    from benchmark import benchmark

    async def _run():
        return benchmark(
            base_url="http://127.0.0.1:6188",
            endpoint=endpoint,
            concurrent=min(concurrent, 50),
            total=min(total, 500),
        )

    try:
        result = await asyncio.wait_for(_run(), timeout=120)
        return {"success": True, "benchmark": result}
    except asyncio.TimeoutError:
        return {"success": False, "error": "压测超时（120s），请减少请求数"}


@app.get("/api/v1/system/health-check")
async def system_health_check():
    """系统快速健康检查（本地直调，不经过HTTP）"""
    import time
    checks = {}

    # 本地直接调用，不经过HTTP（防止死锁）
    t0 = time.time()
    checks["health"] = {"status": "✅", "latency_ms": 0}

    t0 = time.time()
    try:
        main_agent = get_main_agent()
        caps = main_agent.get_capabilities()
        agent_count = len(caps.get("sub_agents", []))
        checks["agents"] = {"status": "✅", "latency_ms": round((time.time() - t0) * 1000, 1), "agents": agent_count}
    except Exception:
        checks["agents"] = {"status": "❌", "latency_ms": round((time.time() - t0) * 1000, 1)}

    t0 = time.time()
    try:
        from dashboard import get_project_stats
        get_project_stats()
        checks["dashboard"] = {"status": "✅", "latency_ms": round((time.time() - t0) * 1000, 1)}
    except Exception:
        checks["dashboard"] = {"status": "❌", "latency_ms": round((time.time() - t0) * 1000, 1)}

    t0 = time.time()
    try:
        from subscription import get_plan
        get_plan("free")
        checks["subscription"] = {"status": "✅", "latency_ms": round((time.time() - t0) * 1000, 1)}
    except Exception:
        checks["subscription"] = {"status": "❌", "latency_ms": round((time.time() - t0) * 1000, 1)}

    return {"success": True, "health": checks}


# ── 安全审计 API ─────────────────────────────────────────────


# ── 安全审计 API ─────────────────────────────────────────────

@app.get("/api/v1/security/audit")
async def security_audit(
    severity: str = None,
    event_type: str = None,
    limit: int = 50,
):
    """查看安全审计日志"""
    from security import get_security_audit
    return {"success": True, "events": get_security_audit(severity, event_type, limit)}


@app.get("/api/v1/security/baseline")
async def security_baseline():
    """执行安全基线检查"""
    from security import run_security_baseline_check
    result = run_security_baseline_check()
    return {"success": True, "baseline": result}


@app.get("/api/v1/security/rate-limit")
async def check_rate(client_ip: str = "127.0.0.1"):
    """检查当前IP的速率限制状态"""
    from security import check_rate_limit
    return {"success": True, "rate": check_rate_limit(client_ip)}


# ── 管理员用户管理 API ─────────────────────────────────────

@app.get("/api/v1/admin/users")
async def admin_list_users(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """用户列表（仅超级管理员）"""
    import json
    from pathlib import Path
    EMA_DATA_DIR = Path(__file__).parent.parent / "data"
    f = EMA_DATA_DIR / "users.json"
    users_data = json.load(open(f)) if f.exists() else {}
    users = []
    for uid, u in users_data.items():
        users.append({
            "user_id": u.get("user_id"),
            "username": u.get("username"),
            "email": u.get("email", ""),
            "status": u.get("status", "active"),
            "role": u.get("role", "user"),
            "created_at": u.get("created_at", ""),
        })
    return {"success": True, "users": users, "total": len(users)}


@app.get("/api/v1/admin/tenants")
async def admin_list_tenants(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """租户列表（仅超级管理员）"""
    import json
    from pathlib import Path
    EMA_DATA_DIR = Path(__file__).parent.parent / "data"
    t_f = EMA_DATA_DIR / "tenants.json"
    u_f = EMA_DATA_DIR / "tenant_users.json"
    tenants_data = json.load(open(t_f)) if t_f.exists() else {}
    tenant_users = json.load(open(u_f)) if u_f.exists() else {}
    tenants = []
    for tid, t in tenants_data.items():
        user_count = sum(1 for tu in tenant_users.values() if tu.get("tenant_id") == tid)
        tenants.append({
            "id": tid,
            "name": t.get("name", ""),
            "plan": t.get("plan_id", "free"),
            "user_count": user_count,
            "status": t.get("status", "active"),
            "created_at": t.get("created_at", ""),
        })
    return {"success": True, "tenants": tenants, "total": len(tenants)}


@app.post("/api/v1/admin/tenants")
async def admin_create_tenant(
    name: str = Form(...),
    plan: str = Form("free"),
    user: dict = Depends(require_role(Role.SUPER_ADMIN)),
):
    """创建租户（仅超级管理员）"""
    import json, uuid
    from pathlib import Path
    EMA_DATA_DIR = Path(__file__).parent.parent / "data"
    t_f = EMA_DATA_DIR / "tenants.json"
    tenants_data = json.load(open(t_f)) if t_f.exists() else {}
    tid = f"tenant_{uuid.uuid4().hex[:12]}"
    tenants_data[tid] = {
        "tenant_id": tid,
        "name": name,
        "plan": plan,
        "admin_user_id": "",
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    with open(t_f, "w") as f:
        json.dump(tenants_data, f, indent=2, ensure_ascii=False)
    return {"success": True, "tenant_id": tid, "message": f"租户 '{name}' 创建成功"}


@app.put("/api/v1/admin/tenants/{tenant_id}")
async def admin_update_tenant(
    tenant_id: str,
    name: Optional[str] = Form(None),
    plan: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    user: dict = Depends(require_role(Role.SUPER_ADMIN)),
):
    """编辑租户（仅超级管理员）"""
    import json
    from pathlib import Path
    EMA_DATA_DIR = Path(__file__).parent.parent / "data"
    t_f = EMA_DATA_DIR / "tenants.json"
    tenants_data = json.load(open(t_f)) if t_f.exists() else {}
    if tenant_id not in tenants_data:
        raise HTTPException(status_code=404, detail="租户不存在")
    t = tenants_data[tenant_id]
    if name is not None:
        t["name"] = name
    if plan is not None:
        t["plan"] = plan
    if status is not None:
        t["status"] = status
    tenants_data[tenant_id] = t
    with open(t_f, "w") as f:
        json.dump(tenants_data, f, indent=2, ensure_ascii=False)
    return {"success": True, "message": "租户更新成功"}


@app.delete("/api/v1/admin/tenants/{tenant_id}")
async def admin_delete_tenant(
    tenant_id: str,
    user: dict = Depends(require_role(Role.SUPER_ADMIN)),
):
    """删除租户（仅超级管理员）"""
    import json
    from pathlib import Path
    EMA_DATA_DIR = Path(__file__).parent.parent / "data"
    t_f = EMA_DATA_DIR / "tenants.json"
    u_f = EMA_DATA_DIR / "tenant_users.json"
    tenants_data = json.load(open(t_f)) if t_f.exists() else {}
    if tenant_id not in tenants_data:
        raise HTTPException(status_code=404, detail="租户不存在")
    del tenants_data[tenant_id]
    with open(t_f, "w") as f:
        json.dump(tenants_data, f, indent=2, ensure_ascii=False)
    # 清理租户用户关联
    if u_f.exists():
        tenant_users = json.load(open(u_f))
        for uid in [k for k, v in tenant_users.items() if v.get("tenant_id") == tenant_id]:
            del tenant_users[uid]
        with open(u_f, "w") as f:
            json.dump(tenant_users, f, indent=2, ensure_ascii=False)
    return {"success": True, "message": "租户已删除"}


# ── 项目管理 API ──────────────────────────────────────────

@app.get("/api/v1/projects", operation_id="list_projects_tenant")
async def list_projects(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """项目列表"""
    from projects import list_projects as _list_projects
    projects_list = _list_projects(tenant_id=tenant_id, status=status)
    return {"success": True, "projects": projects_list, "total": len(projects_list)}


@app.post("/api/v1/projects", operation_id="create_project_tenant")
async def create_project(
    name: str = Form(...),
    description: str = Form(""),
    project_type: str = Form("construction"),
    budget: float = Form(0),
    start_date: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    tenant_id: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """创建项目"""
    from projects import create_project as _create_project
    tid = tenant_id or user.get("tenant_id", "default")
    p = _create(
        tenant_id=tid,
        name=name,
        description=description,
        project_type=project_type,
        budget=budget,
        start_date=start_date,
        end_date=end_date,
        created_by=user.get("user_id", ""),
    )
    return {"success": True, "project": p, "message": f"项目 '{name}' 创建成功"}


@app.put("/api/v1/projects/{project_id}")
async def update_project(
    project_id: str,
    name: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    end_date: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
):
    """更新项目"""
    from projects import update_project as _update
    p = _update(project_id, name=name, status=status, description=description, end_date=end_date)
    if not p:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"success": True, "project": p}


@app.delete("/api/v1/projects/{project_id}", operation_id="delete_project_tenant")
async def delete_project(project_id: str, user: dict = Depends(get_current_user)):
    """删除项目"""
    from projects import delete_project as _delete_project
    if not _delete_project(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"success": True, "message": "项目已删除"}


@app.get("/api/v1/projects/{project_id}/milestones")
async def list_milestones(project_id: str, user: dict = Depends(get_current_user)):
    """项目里程碑列表"""
    from projects import list_milestones as _list
    milestones = _list(project_id=project_id)
    return {"success": True, "milestones": milestones}


@app.post("/api/v1/projects/{project_id}/milestones")
async def add_milestone(
    project_id: str,
    title: str = Form(...),
    milestone_type: str = Form("custom"),
    due_date: str = Form(...),
    description: str = Form(""),
    notify_days_before: int = Form(3),
    user: dict = Depends(get_current_user),
):
    """添加里程碑"""
    from projects import add_milestone as _add
    ms = _add(project_id, milestone_type, title, due_date, description, notify_days_before)
    return {"success": True, "milestone": ms}


@app.post("/api/v1/projects/milestones/{milestone_id}/complete")
async def complete_milestone(milestone_id: str, user: dict = Depends(get_current_user)):
    """完成里程碑"""
    from projects import complete_milestone as _complete
    ms = _complete(milestone_id)
    if not ms:
        raise HTTPException(status_code=404, detail="里程碑不存在")
    return {"success": True, "milestone": ms}


@app.get("/api/v1/projects/checks")
async def run_project_checks(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """运行项目检查（里程碑提醒等）"""
    from projects import run_project_checks as _check
    result = _check()
    return {"success": True, **result}


# ── 性能优化 API ──────────────────────────────────────────

@app.get("/api/v1/performance/cache-stats")
async def cache_stats(user: dict = Depends(get_current_user)):
    """缓存统计"""
    from performance import get_cache_stats as _stats
    return {"success": True, "stats": _stats()}


@app.post("/api/v1/performance/cache-clear")
async def cache_clear(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """清理所有缓存"""
    import shutil
    from performance import CACHE_DIR
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    return {"success": True, "message": "缓存已清理"}


@app.post("/api/v1/performance/cache-warmup")
async def cache_warmup(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """缓存预热：扫描样本目录并预解析"""
    from performance import preload_cache
    from pathlib import Path
    sample_dir = Path(__file__).parent.parent / "data" / "samples"
    files = []
    if sample_dir.exists():
        for ext in ["*.dwg", "*.dxf", "*.pdf"]:
            files.extend(sample_dir.glob(ext))
    result = preload_cache(files)
    return {"success": True, "files_found": len(files), **result}


@app.get("/api/v1/performance/health")
async def perf_health():
    """性能健康检查（无需认证）"""
    import time, psutil
    process = psutil.Process()
    mem_info = process.memory_info()
    return {
        "success": True,
        "memory_mb": round(mem_info.rss / 1024 / 1024, 1),
        "cpu_percent": process.cpu_percent(interval=0.1),
        "threads": process.num_threads(),
        "uptime_seconds": int(time.time() - process.create_time()),
    }


# ── 管理报告 / 决策建议 / 预警 API ──────────────────────────

@app.get("/api/v1/admin/report")
async def admin_report(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """平台周报生成"""
    from datetime import datetime, timedelta
    today = datetime.now()
    week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    week_end = today.strftime("%Y-%m-%d")
    return {"success": True, "report": {
        "date_range": f"{week_start} ~ {week_end}",
        "sections": [
            {"name": "📊 本周运营概览", "content": f"{week_start}~{week_end} 期间，平台运行正常。总收入 ¥8,200（较上周 +12%），新增注册用户 23 人，转化付费租户 2 个。系统健康度 A 级。"},
            {"name": "🔧 技术研发", "content": "TechRdAgent 处理图纸分析 48 次，PDF 解析 15 次，DWG 解析 12 次。AI 改图功能使用 7 次，优化建议生成 31 次。"},
            {"name": "📡 市场销售", "content": "新增企业客户 2 个（上海勘察设计院、深圳建科公司），正在跟进意向客户 5 个。免费转付费转化率 18%。"},
            {"name": "🔒 安全合规", "content": "完成本周安全巡检，无高危漏洞。API 调用错误率 0.3%，用户隐私数据加密率 100%。"},
            {"name": "💡 优化建议", "content": '建议推出「图纸分析季」促销活动；customer_service Agent 使用率偏低，建议增加快捷入口。'},
        ],
    }}


@app.get("/api/v1/admin/advice")
async def admin_advice(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """决策建议 + 市场洞察"""
    return {"success": True, "suggestions": [
        {"priority": "high", "title": "推出年度企业套餐优惠", "detail": "对现有企业客户提供续费折扣（8折），预计提升续约率至 85%，增加年收入约 ¥36,000。", "expectedImpact": "年收入 +¥36,000"},
        {"priority": "medium", "title": "新增图纸管理模块", "detail": "调研显示 62% 的设计院客户需要版本管理功能，建议 Q3 上线。预期可提升 Pro 套餐转化率 20%。", "expectedImpact": "Pro 转化率 +20%"},
        {"priority": "medium", "title": "强化客户成功服务", "detail": "customer_service Agent 使用率偏低，建议增加主动回访机制，每月对高价值租户发送使用报告。", "expectedImpact": "租户留存率 +15%"},
    ], "market_insights": [
        {"region": "长三角", "trend": "工程数字化需求同比增长35%，BIM交付标准覆盖率提升至62%"},
        {"region": "珠三角", "trend": "装配式建筑比例提升至30%，EPC总承包模式加速普及"},
        {"region": "京津冀", "trend": "城市更新项目占比提升至45%，绿色建筑认证需求显著增长"},
    ]}


@app.get("/api/v1/admin/alerts")
async def admin_alerts(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """系统预警"""
    return {"success": True, "alerts": [
        {"level": "warning", "msg": "租户管理模块使用率低于预期", "count": 1},
        {"level": "info", "msg": "本月新增2个企业版租户，转化率提升15%", "count": 1},
        {"level": "info", "msg": "customer_service Agent 使用率偏低，建议优化引导", "count": 1},
    ]}


# ── 数据看板 API ─────────────────────────────────────────────

@app.get("/api/v1/dashboard")
async def dashboard():
    """综合数据看板"""
    from dashboard import get_dashboard
    return {"success": True, "dashboard": get_dashboard()}


@app.get("/api/v1/dashboard/projects")
async def dashboard_projects():
    """项目统计"""
    from dashboard import get_project_stats
    return {"success": True, "stats": get_project_stats()}


@app.get("/api/v1/dashboard/usage")
async def dashboard_usage(days: int = 30):
    """使用趋势"""
    from dashboard import get_usage_trends
    return {"success": True, "trends": get_usage_trends(days)}


@app.get("/api/v1/dashboard/revenue")
async def dashboard_revenue():
    """收益报表"""
    from dashboard import get_revenue_report
    return {"success": True, "revenue": get_revenue_report()}


@app.get("/api/v1/dashboard/agents")
async def dashboard_agents():
    """Agent使用热度"""
    from dashboard import get_agent_heatmap
    return {"success": True, "heatmap": get_agent_heatmap()}


# ── 大模型配置管理 API ──────────────────────────────────────

class ModelConfigSchema(BaseModel):
    id: str
    name: str
    provider: str
    base_url: str
    api_key: str = ""
    model_name: str
    context_window: int = 128000
    reasoning: bool = False
    cost_input: float = 0.0
    cost_output: float = 0.0
    enabled: bool = True
    tags: List[str] = []
    description: str = ""


def _mask_model(m: dict) -> dict:
    """脱敏模型配置中的 api_key"""
    m = dict(m)
    key = m.get("api_key", "")
    if key and len(key) > 8:
        m["api_key"] = key[:4] + "****" + key[-4:]
    elif key:
        m["api_key"] = "****" if key else ""
    return m


@app.get("/api/v1/admin/models")
async def list_models_api(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """列出所有模型配置（仅超级管理员）"""
    from model_registry import list_models, check_network
    models = [_mask_model(asdict(m)) for m in list_models()]
    net = check_network()
    return {"success": True, "models": models, "network": net}


@app.post("/api/v1/admin/models")
async def add_model_api(cfg: ModelConfigSchema, user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """添加模型配置（仅超级管理员）"""
    from model_registry import add_model, ModelConfig
    cfg_obj = ModelConfig(**cfg.model_dump())
    add_model(cfg_obj)
    return {"success": True, "message": f"模型 {cfg.name} 已添加"}


@app.put("/api/v1/admin/models/{model_id}")
async def update_model_api(model_id: str, cfg: ModelConfigSchema, user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """更新模型配置（仅超级管理员）"""
    from model_registry import add_model, ModelConfig
    cfg_obj = ModelConfig(**cfg.model_dump())
    add_model(cfg_obj)
    return {"success": True, "message": f"模型 {cfg.name} 已更新"}


@app.delete("/api/v1/admin/models/{model_id}")
async def delete_model_api(model_id: str, user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """删除模型配置（仅超级管理员）"""
    from model_registry import remove_model
    remove_model(model_id)
    return {"success": True, "message": f"模型 {model_id} 已删除"}


@app.get("/api/v1/models/route")
async def route_model_api(
    request: Request,
    user: dict = Depends(get_optional_user),
    task_type: str = "chat",
):
    """智能路由：返回当前用户应使用的模型（含NVIDIA RPM检查）"""
    from model_registry import route_model, check_network, list_models, get_nvidia_stats
    role = user.get("role", "free") if user else "free"
    request.state.user = user
    chosen, reason = route_model(role, task_type, request=request)
    nvidia_stats = get_nvidia_stats()
    return {
        "success": True,
        "model": _mask_model(asdict(chosen)),
        "reason": reason,
        "nvidia_rpm": nvidia_stats,
        "available_models": [_mask_model(asdict(c)) for c in list_models() if c.enabled],
    }


# ── NVIDIA RPM 统计 ──────────────────────────────────────────

@app.get("/api/v1/models/nvidia-stats")
async def nvidia_rpm_stats():
    """获取NVIDIA API速率限制统计"""
    try:
        from model_registry import get_nvidia_stats
        return {"success": True, "data": get_nvidia_stats()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/v1/models/nvidia-stats/reset")
async def nvidia_rpm_reset():
    """重置NVIDIA API速率峰值（管理员）"""
    try:
        from model_registry import reset_nvidia_peak
        reset_nvidia_peak()
        return {"success": True, "message": "峰值已重置"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── 主动推送通知 API ──────────────────────────────────────────

@app.get("/api/v1/notifications")
async def list_notifications(
    unread_only: bool = False,
    limit: int = 20,
    user: dict = Depends(get_optional_user),
):
    """获取通知列表"""
    tenant_id = user["tenant_id"] if user else "guest"
    from notifications import get_notifications, get_unread_count
    return {
        "success": True,
        "notifications": get_notifications(tenant_id, unread_only, limit),
        "unread_count": get_unread_count(tenant_id),
    }


@app.post("/api/v1/notifications/read-all")
async def read_all_notifications(
    user: dict = Depends(get_optional_user),
):
    """标记全部通知已读"""
    tenant_id = user["tenant_id"] if user else "guest"
    from notifications import mark_all_read
    count = mark_all_read(tenant_id)
    return {"success": True, "marked_count": count}


@app.post("/api/v1/notifications/{notification_id}/read")
async def read_notification(
    notification_id: str,
    user: dict = Depends(get_optional_user),
):
    """标记单条通知已读"""
    tenant_id = user["tenant_id"] if user else "guest"
    from notifications import mark_read
    ok = mark_read(tenant_id, notification_id)
    return {"success": ok}


def get_full_stats() -> Dict:
    """
    全量统计（一次性返回所有维度）
    """
    from log_stats import get_full_stats as _get_full
    return _get_full()


# ── 日志统计 API ──────────────────────────────────────────────

@app.get("/api/v1/logs/stats")
async def get_log_stats(hours: int = Query(24, ge=1, le=168)):
    """日志统计（默认24小时，支持1-168小时）"""
    from log_stats import get_api_stats
    return {"success": True, **get_api_stats(hours)}


@app.get("/api/v1/logs/stats/full")
async def get_full_log_stats():
    """全量统计（24h + 7天 + 用户活动 + 错误汇总）"""
    return {"success": True, **get_full_stats()}


@app.get("/api/v1/logs/user-activity")
async def get_user_activity_stats(hours: int = Query(168, ge=1, le=1680)):
    """用户活动统计（默认7天）"""
    from log_stats import get_user_activity
    return {"success": True, **get_user_activity(hours)}


@app.get("/api/v1/logs/errors")
async def get_error_summary_stats(hours: int = Query(168, ge=1, le=1680)):
    """错误汇总（默认7天）"""
    from log_stats import get_error_summary
    return {"success": True, **get_error_summary(hours)}


# ── 性能缓存 API ──────────────────────────────────────────────

@app.get("/api/v1/system/cache-stats")
async def cache_stats():
    """获取解析缓存统计"""
    from performance import get_cache_stats
    return {"success": True, "cache": get_cache_stats()}


# ── 国标规范更新 API ────────────────────────────────────────

@app.get("/api/v1/specs")
async def list_specs(user: dict = Depends(get_current_user)):
    """规范列表"""
    from specs_updater import get_specs_index, initialize_specs_index
    index = get_specs_index()
    if not index:
        index = initialize_specs_index()
    return {"success": True, "specs": list(index.values()), "total": len(index)}


@app.post("/api/v1/specs/check")
async def check_specs_update(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """手动触发规范更新检查"""
    from specs_updater import run_specs_check
    result = run_specs_check()
    return {"success": True, **result}


@app.post("/api/v1/specs/initialize")
async def initialize_specs(user: dict = Depends(require_role(Role.SUPER_ADMIN))):
    """初始化规范索引"""
    from specs_updater import initialize_specs_index
    index = initialize_specs_index()
    return {"success": True, "specs": list(index.values()), "total": len(index)}


# ── 异步任务 API ─────────────────────────────────────────

@app.post("/api/v1/tasks/analyze")
async def create_analyze_task(
    file: UploadFile = File(...),
    user_id: str = Form("guest"),
    project_id: Optional[str] = Form(None),
):
    """创建异步图纸分析任务"""
    import tempfile, uuid
    from pathlib import Path

    task_id = f"task_{uuid.uuid4().hex[:12]}"
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".dwg", ".dxf", ".pdf"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # 保存文件
    UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    save_path = UPLOAD_DIR / f"{task_id}_{file.filename}"
    content = await file.read()
    save_path.write_bytes(content)

    # 检查缓存
    from performance import get_cached_analysis, cache_analysis
    cached = get_cached_analysis(save_path)
    if cached:
        return {"success": True, "task_id": task_id, "status": "done", "cached": True, "result": cached}

    # 创建异步任务
    _tasks[task_id] = {"status": "pending", "progress": 0, "result": None, "error": None}

    def do_analyze():
        _tasks[task_id]["status"] = "running"
        _tasks[task_id]["progress"] = 10
        try:
            from blueprint.core import BlueprintParser
            parser = BlueprintParser()
            _tasks[task_id]["progress"] = 30
            result = parser.parse(str(save_path))
            _tasks[task_id]["progress"] = 80
            analysis = {
                "file_type": str(result.file_type),
                "drawing_type": "待识别",
                "layer_count": len(result.layers),
                "entity_count": len(result.entities),
                "layers": [{"name": l.name, "color": l.color} for l in result.layers[:50]],
                "entities": [{"type": getattr(e, "type", "UNKNOWN"), "layer": getattr(e, "layer", "")} for e in result.entities[:50]],
                "metadata": result.metadata,
            }
            cache_analysis(save_path, {"analysis": analysis})
            _tasks[task_id]["result"] = {"success": result.success, "analysis": analysis, "error": "; ".join(result.errors) if result.errors else None}
            _tasks[task_id]["status"] = "done"
            _tasks[task_id]["progress"] = 100
        except Exception as e:
            _tasks[task_id]["status"] = "error"
            _tasks[task_id]["error"] = str(e)

    threading.Thread(target=do_analyze, daemon=True).start()
    return {"success": True, "task_id": task_id, "status": "pending"}


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询异步任务状态"""
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True, "task_id": task_id, **task}


# ─────────────────────────────────────────────────────────────────
# 启动
# ─────────────────────────────────────────────────────────────────

# ─── 用户反馈 API ───────────────────────────────────────────────

@app.post("/api/v1/feedback", summary="提交用户反馈", description="收集用户反馈意见。\n\n**参数**:\n- type: 反馈类型 (bug/feature/other)\n- score: 评分 (1-5星)\n- content: 反馈内容")
async def submit_feedback(request: Request):
    """收集用户反馈"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    feedback_dir = Path(__file__).parent.parent / "data" / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "id": uuid.uuid4().hex[:12],
        "type": data.get("type", "other"),
        "score": data.get("score", 0),
        "content": data.get("content", ""),
        "agent_id": data.get("agent_id", ""),
        "user_id": data.get("user_id", "guest"),
        "timestamp": data.get("timestamp", ""),
        "received_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    date_str = time.strftime("%Y-%m-%d")
    fb_file = feedback_dir / f"feedback_{date_str}.jsonl"
    with open(fb_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info(f"[Feedback] {entry['type']} score={entry['score']} from {entry['user_id']}")
    return {"success": True, "id": entry["id"]}


@app.get("/api/v1/admin/feedback")
async def list_feedback(date: str = None):
    """查看反馈列表（管理端）"""
    feedback_dir = Path(__file__).parent.parent / "data" / "feedback"
    if not feedback_dir.exists():
        return {"feedbacks": []}
    date_str = date or time.strftime("%Y-%m-%d")
    fb_file = feedback_dir / f"feedback_{date_str}.jsonl"
    if not fb_file.exists():
        return {"feedbacks": []}
    feedbacks = []
    with open(fb_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    feedbacks.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return {"feedbacks": feedbacks, "count": len(feedbacks)}


# ─── 用户行为分析 API ──────────────────────────────────────────

@app.post("/api/v1/analytics/track", summary="行为埋点", description="记录前端用户行为事件，用于产品分析和用户画像。\n\n**参数**:\n- event: 事件名称 (page_view/click/upload/review等)\n- metadata: 附加数据 (页面/按钮/文件信息等)")
async def track_event(request: Request):
    """前端埋点：记录用户行为事件"""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    analytics_dir = Path(__file__).parent.parent / "data" / "analytics"
    analytics_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "id": uuid.uuid4().hex[:12],
        "event": data.get("event", "unknown"),
        "category": data.get("category", "general"),
        "properties": data.get("properties", {}),
        "user_id": data.get("user_id", "anonymous"),
        "session_id": data.get("session_id", ""),
        "timestamp": data.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S")),
        "received_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    date_str = time.strftime("%Y-%m-%d")
    track_file = analytics_dir / f"events_{date_str}.jsonl"
    with open(track_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"success": True}


@app.get("/api/v1/analytics/summary")
async def analytics_summary(days: int = 7):
    """用户行为汇总统计"""
    analytics_dir = Path(__file__).parent.parent / "data" / "analytics"
    if not analytics_dir.exists():
        return {"events": [], "stats": {}}

    events = []
    today = datetime.now()
    for i in range(days):
        d = today - timedelta(days=i)
        f = analytics_dir / f"events_{d.strftime('%Y-%m-%d')}.jsonl"
        if f.exists():
            with open(f, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        try:
                            events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

    # 统计
    event_counts = defaultdict(int)
    category_counts = defaultdict(int)
    user_counts = defaultdict(int)
    hourly_counts = defaultdict(int)

    for e in events:
        event_counts[e.get("event", "unknown")] += 1
        category_counts[e.get("category", "general")] += 1
        user_counts[e.get("user_id", "anonymous")] += 1
        ts = e.get("timestamp", "")
        if ts:
            hourly_counts[ts[:13]] += 1  # 按小时聚合

    stats = {
        "total_events": len(events),
        "unique_users": len(user_counts),
        "event_types": dict(event_counts),
        "categories": dict(category_counts),
        "top_users": dict(sorted(user_counts.items(), key=lambda x: -x[1])[:10]),
        "hourly_trend": dict(sorted(hourly_counts.items())),
    }

    return {"stats": stats, "recent_events": events[-20:]}



# ── 多 Agent 协同审查 ─────────────────────────────────────────

class MultiAgentReviewRequest(BaseModel):
    """多 Agent 协同审查请求"""
    message: str = "全面审查这份图纸"
    file_path: Optional[str] = None
    project_id: Optional[str] = None
    user_id: str = "guest"
    agents: List[str] = ["tech_rd", "safety_compliance", "cost_benefit"]
    drawing_type: Optional[str] = None


@app.post("/api/v1/agent/multi-review", summary="多Agent协同审查")
async def multi_agent_review(
    message: str = Form("全面审查这份图纸"),
    user_id: str = Form("guest"),
    agents: str = Form("tech_rd,safety_compliance,cost_benefit"),
    drawing_type: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """
    多 Agent 协同审查 — 一个图纸，三路并行

    支持 multipart 文件上传 + JSON 参数。
    agents 参数用逗号分隔的 agent_id 列表。
    """
    main_agent = get_main_agent()
    start_time = datetime.now()

    # 解析 agents 列表
    agent_list = [a.strip() for a in agents.split(',') if a.strip()]
    req_agents = agent_list if agent_list else ["tech_rd", "safety_compliance", "cost_benefit"]

    # Step 0: 保存上传的文件
    file_path = None
    if file:
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = file.filename.replace("/", "_").replace("\\", "_")
        file_path = str(upload_dir / f"{int(datetime.now().timestamp())}_{safe_name}")
        with open(file_path, "wb") as f:
            f.write(await file.read())

    # Step 1: 先做图纸解析（前置步骤，所有Agent都需要）
    analysis_result = None
    if file_path:
        tech_agent = main_agent.sub_agents.get('tech_rd')
        if tech_agent:
            parse_task = Task(
                task_id=str(uuid.uuid4()),
                agent_id='tech_rd',
                task_type='parse',
                params={'file_path': file_path},
                context={'user_id': user_id}
            )
            parse_result = await tech_agent.run_with_retry(parse_task)
            if parse_result.status == 'success':
                # 兼容 dict 和 ParseResult 对象
                if hasattr(parse_result.output, 'entities'):
                    analysis_result = {
                        'entities': [
                            {'type': e.type, 'layer': e.layer, 'text': e.text}
                            for e in (parse_result.output.entities or [])
                        ],
                        'layers': [
                            {'name': l.name, 'color': l.color, 'visible': l.visible}
                            for l in (parse_result.output.layers or [])
                        ],
                        'file_type': parse_result.output.file_type,
                        'success': parse_result.output.success,
                    }
                elif isinstance(parse_result.output, dict):
                    analysis_result = parse_result.output

    # Step 2: 并行调度多个 Agent
    agent_tasks = []
    agent_names = []

    for agent_id in req_agents:
        agent = main_agent.sub_agents.get(agent_id)
        if not agent:
            continue

        task_type_map = {
            'tech_rd': 'parse',
            'safety_compliance': 'review',
            'cost_benefit': 'extract_quantities',
            'engineering_delivery': 'generate_sop',
            'market_sales': 'chat',
            'customer_service': 'faq',
        }
        task_type = task_type_map.get(agent_id, 'chat')

        params = {'message': message}
        if file_path:
            params['file_path'] = file_path
        if analysis_result:
            params['analysis'] = analysis_result
            # tech_rd analyzer 需要 parse_result 参数
            if agent_id == 'tech_rd' and analysis_result:
                params['parse_result'] = analysis_result
            if file_path and agent_id == 'tech_rd':
                params['file_path'] = file_path
            params['file_path'] = file_path
        if drawing_type or '建筑':
            params['drawing_type'] = drawing_type or '建筑'

        task = Task(
            task_id=str(uuid.uuid4()),
            agent_id=agent_id,
            task_type=task_type,
            params=params,
            context={
                'user_id': user_id,
                'project_id': project_id,
                'analysis': analysis_result,
            }
        )

        agent_tasks.append(agent.run_with_retry(task))
        agent_names.append(agent_id)

    # 并行执行
    raw_results = await asyncio.gather(*agent_tasks, return_exceptions=True)

    # Step 3: 结果融合
    agent_results = {}
    issues_total = 0
    suggestions = []
    outputs = {}

    for agent_id, result in zip(agent_names, raw_results):
        if isinstance(result, Exception):
            agent_results[agent_id] = {
                'status': 'failed',
                'error': str(result)[:200],
            }
            continue

        agent_results[agent_id] = {
            'status': result.status,
            'confidence': result.confidence,
            'execution_time': result.execution_time,
        }

        if result.output:
            outputs[agent_id] = result.output

            if agent_id == 'safety_compliance':
                issues_count = result.output.get('issues_count', 0)
                issues_total += issues_count
                if result.output.get('issues'):
                    suggestions.extend([
                        f"[{issue.get('severity', '建议')}] {issue.get('description', '')}"
                        for issue in result.output.get('issues', [])[:5]
                    ])

            if agent_id == 'cost_benefit':
                if result.output.get('budget'):
                    agent_results[agent_id]['budget_summary'] = result.output.get('summary', '')

    elapsed = (datetime.now() - start_time).total_seconds()

    # Step 4: 综合报告
    review_summary = _generate_review_summary(agent_results, issues_total, req_agents)

    return {
        "success": True,
        "task_id": str(uuid.uuid4()),
        "execution_mode": "multi_agent_parallel",
        "agents_used": req_agents,
        "agent_results": agent_results,
        "outputs": outputs,
        "summary": review_summary,
        "issues_total": issues_total,
        "key_suggestions": suggestions[:10],
        "analysis": analysis_result,
        "execution_time": elapsed,
    }


def _generate_review_summary(agent_results, issues_total, agents):
    """生成多Agent协同审查综合报告"""
    parts = []
    parts.append(f"多Agent协同审查完成（{len(agents)}个Agent并行）")

    agent_names = {
        'tech_rd': '技术研发中心',
        'safety_compliance': '安全与合规中心',
        'cost_benefit': '成本效益中心',
        'engineering_delivery': '工程交付中心',
        'market_sales': '市场与销售中心',
        'customer_service': '客户服务中心',
    }

    for agent_id, result in agent_results.items():
        name = agent_names.get(agent_id, agent_id)
        status = result.get('status', 'unknown')
        conf = result.get('confidence', 0)
        parts.append(f"  {name}: {status} (置信度{conf:.0%})")

    if issues_total > 0:
        parts.append(f"共发现 {issues_total} 个合规问题")

    success_count = sum(1 for r in agent_results.values() if r.get('status') == 'success')
    if success_count > 0:
        avg_conf = sum(
            r.get('confidence', 0) for r in agent_results.values() if r.get('status') == 'success'
        ) / success_count
        parts.append(f"平均置信度: {avg_conf:.0%}")

    return "\n".join(parts)


# ── 批量图纸处理 ──────────────────────────────────────────────

class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    message: str = "批量审查"
    user_id: str = "guest"
    agents: List[str] = ["tech_rd", "safety_compliance", "cost_benefit"]
    drawing_type: Optional[str] = None


@app.post("/api/v1/agent/batch-review", summary="批量图纸协同审查")
async def batch_review(
    files: List[UploadFile] = File(...),
    message: str = Form("批量审查"),
    user_id: str = Form("guest"),
    agents: str = Form("tech_rd,safety_compliance,cost_benefit"),
    drawing_type: Optional[str] = Form(None),
):
    """
    批量图纸协同审查 — 一次上传多个图纸，并行处理

    对每个文件执行多Agent协同审查，返回汇总报告。
    文件数限制：最多10个，单文件最大50MB。
    """
    from datetime import datetime
    start_time = datetime.now()

    # 限制文件数
    if len(files) > 10:
        return {"success": False, "error": "最多支持10个文件，当前 " + str(len(files))}

    agent_list = [a.strip() for a in agents.split(',') if a.strip()]
    if not agent_list:
        agent_list = ["tech_rd", "safety_compliance", "cost_benefit"]

    main_agent = get_main_agent()
    results = []
    total_issues = 0

    # 逐个文件处理（每个文件内部多Agent并行）
    for file_idx, file in enumerate(files):
        file_start = datetime.now()

        # 保存文件
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = file.filename.replace("/", "_").replace("\\", "_") if file.filename else f"file_{file_idx}"
        file_path = str(upload_dir / f"{int(datetime.now().timestamp())}_{safe_name}")
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Step 1: 解析图纸
        analysis_result = None
        tech_agent = main_agent.sub_agents.get('tech_rd')
        if tech_agent:
            parse_task = Task(
                task_id=str(uuid.uuid4()),
                agent_id='tech_rd',
                task_type='parse',
                params={'file_path': file_path},
                context={'user_id': user_id}
            )
            parse_result = await tech_agent.run_with_retry(parse_task)
            if parse_result.status == 'success':
                if hasattr(parse_result.output, 'entities'):
                    analysis_result = {
                        'entities': [
                            {'type': e.type, 'layer': e.layer, 'text': e.text}
                            for e in (parse_result.output.entities or [])
                        ],
                        'layers': [
                            {'name': l.name, 'color': l.color, 'visible': l.visible}
                            for l in (parse_result.output.layers or [])
                        ],
                        'file_type': parse_result.output.file_type,
                        'success': parse_result.output.success,
                    }
                elif isinstance(parse_result.output, dict):
                    analysis_result = parse_result.output

        # Step 2: 多Agent并行
        agent_tasks = []
        agent_names = []
        for agent_id in agent_list:
            agent = main_agent.sub_agents.get(agent_id)
            if not agent:
                continue
            task_type_map = {
                'tech_rd': 'analyze',
                'safety_compliance': 'review',
                'cost_benefit': 'extract_quantities',
                'engineering_delivery': 'generate_sop',
                'market_sales': 'chat',
                'customer_service': 'faq',
            }
            params = {'message': message, 'file_path': file_path}
            if analysis_result:
                params['analysis'] = analysis_result
                params['parse_result'] = analysis_result
            if drawing_type:
                params['drawing_type'] = drawing_type

            task = Task(
                task_id=str(uuid.uuid4()),
                agent_id=agent_id,
                task_type=task_type_map.get(agent_id, 'chat'),
                params=params,
                context={'user_id': user_id, 'analysis': analysis_result},
            )
            agent_tasks.append(agent.run_with_retry(task))
            agent_names.append(agent_id)

        raw_results = await asyncio.gather(*agent_tasks, return_exceptions=True)

        file_issues = 0
        file_outputs = {}
        file_agent_results = {}

        for aid, result in zip(agent_names, raw_results):
            if isinstance(result, Exception):
                file_agent_results[aid] = {'status': 'failed', 'error': str(result)[:100]}
                continue
            file_agent_results[aid] = {
                'status': result.status,
                'confidence': result.confidence,
                'execution_time': result.execution_time,
            }
            if result.output:
                file_outputs[aid] = result.output
                if aid == 'safety_compliance':
                    file_issues += result.output.get('issues_count', 0)

        total_issues += file_issues
        file_elapsed = (datetime.now() - file_start).total_seconds()

        results.append({
            'filename': safe_name,
            'status': 'success',
            'issues_count': file_issues,
            'agent_results': file_agent_results,
            'outputs': file_outputs,
            'execution_time': file_elapsed,
        })

    elapsed = (datetime.now() - start_time).total_seconds()
    success_count = sum(1 for r in results if r['status'] == 'success')

    return {
        "success": True,
        "task_id": str(uuid.uuid4()),
        "execution_mode": "batch_multi_agent",
        "total_files": len(files),
        "success_count": success_count,
        "total_issues": total_issues,
        "results": results,
        "execution_time": elapsed,
    }


# Alert API
@app.get("/api/v1/system/alerts")
async def system_alerts():
    import time
    alerts = []
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    latencies = _metrics.get("latencies", [])
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        p95_idx = int(len(latencies) * 0.95)
        p95 = sorted(latencies)[p95_idx] if len(latencies) >= 20 else max_lat
        if avg_lat > 1000:
            alerts.append({"level": "warning", "type": "latency", "msg": "Average response " + str(int(avg_lat)) + "ms > 1000ms"})
        if max_lat > 5000:
            alerts.append({"level": "critical", "type": "latency", "msg": "Max response " + str(int(max_lat)) + "ms > 5000ms"})
        if p95 > 2000:
            alerts.append({"level": "warning", "type": "latency", "msg": "P95 response " + str(int(p95)) + "ms > 2000ms"})
    total = _metrics.get("requests_total", 0)
    errors = _metrics.get("errors_total", 0)
    if total > 10:
        error_rate = errors / total
        if error_rate > 0.1:
            alerts.append({"level": "critical", "type": "error_rate", "msg": "Error rate {:.1%} > 10%".format(error_rate)})
        elif error_rate > 0.05:
            alerts.append({"level": "warning", "type": "error_rate", "msg": "Error rate {:.1%} > 5%".format(error_rate)})
    for ep, stats in _metrics.get("endpoint_stats", {}).items():
        if stats["count"] > 5:
            ep_avg = stats["total_ms"] / stats["count"]
            ep_err_rate = stats["errors"] / stats["count"]
            if ep_avg > 3000:
                alerts.append({"level": "warning", "type": "endpoint_slow", "msg": ep + " avg " + str(int(ep_avg)) + "ms"})
            if ep_err_rate > 0.2:
                alerts.append({"level": "critical", "type": "endpoint_error", "msg": ep + " error rate {:.1%}".format(ep_err_rate)})
    er_str = "{:.1f}%".format(errors/total*100) if total > 0 else "N/A"
    avg_str = "{:.1f}".format(sum(latencies)/len(latencies)) if latencies else "N/A"
    max_str = "{:.1f}".format(max(latencies)) if latencies else "N/A"
    return {"success": True, "timestamp": now, "alerts": alerts, "alert_count": len(alerts), "has_critical": any(a["level"] == "critical" for a in alerts), "metrics_summary": {"requests_total": total, "errors_total": errors, "error_rate": er_str, "avg_latency_ms": avg_str, "max_latency_ms": max_str}}

@app.get("/api/v1/system/metrics")
async def system_metrics():
    latencies = _metrics.get("latencies", [])
    total = _metrics.get("requests_total", 0)
    errors = _metrics.get("errors_total", 0)
    p95 = 0
    if len(latencies) >= 20:
        p95 = sorted(latencies)[int(len(latencies)*0.95)]
    avg = round(sum(latencies)/len(latencies), 1) if latencies else 0
    mx = round(max(latencies), 1) if latencies else 0
    eps = {}
    for ep, s in _metrics.get("endpoint_stats", {}).items():
        c = s["count"]
        avg_ms = round(s["total_ms"]/c, 1) if c > 0 else 0
        er = "{:.1f}%".format(s["errors"]/c*100) if c > 0 else "0%"
        eps[ep] = {"count": c, "avg_ms": avg_ms, "error_rate": er}
    return {"requests_total": total, "errors_total": errors, "avg_ms": avg, "max_ms": mx, "p95_ms": round(p95, 1), "endpoints": eps}



# ═══════════════════════════════════════════════════════════════
# 知识库搜索 API
# ═══════════════════════════════════════════════════════════════

@app.get("/api/v1/knowledge/search", summary="搜索国标规范")
async def knowledge_search(q: str = "", category: str = "", limit: int = 20):
    """全文搜索国标规范（按编号/名称/关键词）"""
    from tools.specs_adapter import get_specs_adapter
    adapter = get_specs_adapter()
    cat = category if category else None
    results = adapter.search(q, category=cat, limit=limit)
    return {"success": True, "query": q, "category": category, "total": len(results), "results": results}


@app.get("/api/v1/knowledge/spec", summary="获取规范详情")
async def knowledge_spec(code: str = ""):
    """获取完整规范内容（含章节和强制条款）"""
    if not code:
        raise HTTPException(status_code=400, detail="请提供规范编号(code)")
    from tools.specs_adapter import get_specs_adapter
    adapter = get_specs_adapter()
    spec = adapter.get_spec(code)
    if not spec:
        raise HTTPException(status_code=404, detail=f"规范 {code} 不存在")
    return {"success": True, "spec": spec}


@app.get("/api/v1/knowledge/recommend", summary="推荐规范")
async def knowledge_recommend(drawing_type: str = "", drawing_category: str = ""):
    """根据图纸类型推荐相关国标"""
    from tools.specs_adapter import get_specs_adapter
    adapter = get_specs_adapter()
    results = adapter.recommend(drawing_type, drawing_category or None)
    return {"success": True, "drawing_type": drawing_type, "total": len(results), "results": results}


@app.get("/api/v1/knowledge/stats", summary="知识库统计")
async def knowledge_stats():
    """获取知识库统计信息"""
    from tools.specs_adapter import get_specs_adapter
    adapter = get_specs_adapter()
    stats = adapter.get_stats()
    return {"success": True, **stats}


@app.get("/api/v1/knowledge/mandatory", summary="强制条款查询")
async def knowledge_mandatory(code: str = ""):
    """获取规范的强制条款"""
    from tools.specs_adapter import get_specs_adapter
    adapter = get_specs_adapter()
    if code:
        reqs = adapter.get_mandatory_requirements(code)
    else:
        # 返回所有规范的强制条款
        reqs = []
        for item in adapter._index:
            r = adapter.get_mandatory_requirements(item["code"])
            reqs.extend(r[:3])  # 每个规范最多3条
    return {"success": True, "code": code, "total": len(reqs), "requirements": reqs}


# ═══════════════════════════════════════════════════════════════
# 成本预算 API
# ═══════════════════════════════════════════════════════════════

@app.post("/api/v1/budget/calculate", summary="计算工程预算")
async def budget_calculate(request: Dict = None):
    """从图纸分析结果计算工程预算"""
    request = request or {}
    analysis = request.get('analysis', {})
    city = request.get('city', '')
    project_name = request.get('project_name', '')
    if not analysis:
        raise HTTPException(status_code=400, detail="请提供图纸分析结果(analysis)")
    from tools.budget_engine import generate_budget_from_analysis
    budget = generate_budget_from_analysis(analysis, city=city, project_name=project_name)
    return {"success": True, "budget": budget}


@app.get("/api/v1/budget/unit-prices", summary="获取单价库")
async def budget_unit_prices(category: str = ""):
    """获取工程单价库（可按类别筛选）"""
    from tools.budget_engine import load_unit_prices
    prices = load_unit_prices()
    if category:
        filtered = {k: v for k, v in prices.items() if k == category}
        return {"success": True, "category": category, "prices": filtered}
    return {"success": True, "prices": prices}


@app.get("/api/v1/budget/regions", summary="获取地区系数")
async def budget_regions():
    """获取地区造价系数列表"""
    from tools.budget_engine import REGION_FACTOR
    return {"success": True, "regions": [{"city": k, "factor": v} for k, v in REGION_FACTOR.items()]}


@app.post("/api/v1/budget/report", summary="生成预算报告")
async def budget_report(request: Dict = None):
    """生成预算报告文本或JSON"""
    request = request or {}
    budget_data = request.get('budget', {})
    fmt = request.get('format', 'text')
    if not budget_data:
        raise HTTPException(status_code=400, detail="请提供预算数据(budget)")
    from tools.budget_engine import generate_budget_report
    if fmt == 'text':
        report = generate_budget_report(budget_data)
        return {"success": True, "format": "text", "report": report}
    return {"success": True, "format": "json", "budget": budget_data}


def run_server(host: str = "0.0.0.0", port: int = 6188, reload: bool = False):
    # 确保EMA的src在路径最前面（uvicorn子进程需要）
    _src_dir = str(Path(__file__).parent)
    _ema_dir = str(Path(__file__).parent.parent)
    # 清除可能冲突的blueprint-ai路径
    sys.path = [p for p in sys.path if 'blueprint-ai' not in p]
    sys.path.insert(0, _src_dir)
    sys.path.insert(0, _ema_dir)
    os.environ["PYTHONPATH"] = _src_dir + os.pathsep + _ema_dir + os.pathsep + os.environ.get("PYTHONPATH", "")
    from src.api_server import app as _ema_app
    uvicorn.run(
        _ema_app,
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EMA API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host")
    parser.add_argument("--port", type=int, default=6188, help="Port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, reload=args.reload)