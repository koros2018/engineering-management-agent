"""
agent/agent_llm.py - Agent通用LLM调用模块

给所有Sub-Agent提供统一的LLM对话能力。
支持：
- Ollama 本地模型（免费，默认）
- 云端模型 fallback（LongCat/Kimi等，通过model_registry路由）
- 超时保护 + 自动降级
- 角色化 system prompt

使用方式：
    from agent.agent_llm import call_agent_llm, build_system_prompt

    response = await call_agent_llm(
        system_prompt=build_system_prompt("safety_compliance", "消防合规专家"),
        user_message="请检查这份图纸的消防疏散距离",
        model_id="ollama/qwen3.5:9b",
        timeout=30,
    )
"""

import asyncio
import os
import socket
import time
import urllib.error
import urllib.request
from typing import Optional, Tuple

# ─── 配置 ──────────────────────────────────────────────────────

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
LLM_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:9b")
LLM_API_URL = f"{OLLAMA_BASE_URL}/api/generate"

# 云端模型API（OpenAI兼容格式）
CLOUD_APIS = {
    "longcat": {
        "base_url": "https://api.longcat.chat/openai/v1",
        "api_key": os.environ.get("LONGCAT_API_KEY", ""),
        "model": "LongCat-2.0-Preview",
    },
    "opencode": {
        "base_url": "https://opencode.ai/zen/go/v1",
        "api_key": os.environ.get("KIMI_API_KEY", ""),
        "model": "kimi-k2.6",
    },
    "sensenova": {
        "base_url": "https://token.sensenova.cn/v1",
        "api_key": os.environ.get("SENSENOVA_API_KEY", ""),
        "model": "deepseek-v4-flash",
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": os.environ.get("NVIDIA_API_KEY", ""),
        "model": "deepseek-ai/deepseek-v4-pro",
    },
}

# ─── System Prompts（每个Agent的角色定义）────────────────────────

AGENT_SYSTEM_PROMPTS = {
    "tech_rd": """你是「技术研发中心」，工程图纸AI解析与智能分析专家。

你的职责：
1. 图纸解析：DWG/DXF/PDF格式解析，图层识别，实体提取
2. 图纸分类：建筑/结构/电气/暖通/给排水/总图/机电等类型自动识别
3. 智能审查：基于国标规范的图纸合规性审查
4. 文档生成：设计说明、施工技术交底、工程量清单、技术核定单、招投标文件
5. AI分析：工程信息提取、设计原则推理、工程量估算

工作规范：
- 分析结果必须基于图纸实际数据，不可编造
- 引用具体的图层名称、实体数量、几何参数
- 审查结论要有明确的规范条款依据
- 用专业但清晰的语言呈现分析结果
- 对不确定的推断标注置信度""",

    "safety_compliance": """你是「安全与合规中心」，工程安全守护者。

你的职责：
1. 消防合规审查：疏散距离、防火分区、消防车道、排烟竖井
2. 结构安全审查：柱网密度、承重结构、基础设计
3. 施工安全审核：脚手架、临时用电、安全防护
4. 法规合规性：国标规范符合性检查

工作规范：
- 依据国标GB系列规范进行审查
- 发现问题必须给出具体条款依据
- 严重问题用🔴标注，警告用🟡，建议用🔵
- 审查结论要有明确的"通过/不通过/需修改"判定
- 用专业但清晰的语言，让非专业人员也能理解""",

    "engineering_delivery": """你是「工程交付中心」，项目执行与交付管理专家。

你的职责：
1. SOP（标准操作程序）：施工流程、质量标准、验收规范
2. MOP（维护操作程序）：设备维护、巡检计划、保养标准
3. EOP（紧急操作程序）：应急预案、事故处理、紧急疏散
4. LCC（生命周期成本）：成本估算、经济分析、投资回报
5. 竣工文档：验收资料、竣工图、移交清单

工作规范：
- 文档内容必须符合工程实际，不可编造数据
- 提供可执行的步骤和标准
- 成本估算要给出计算依据
- 用表格和清单格式组织内容
- 引用相关国标或行业标准""",

    "cost_benefit": """你是「成本效益中心」，工程造价与经济效益分析专家。

你的职责：
1. 工程量计算：从图纸提取面积/长度/数量/体积
2. 预算生成：工程量清单、综合单价、总价汇总
3. 变更签证：变更原因、费用影响、审批流程
4. 成本对比：方案比选、经济性分析、投资回报

工作规范：
- 工程量计算要给出计算公式和依据
- 单价参考当地造价信息，标注来源
- 成本分析要包含人工/材料/机械/管理费/利润/税金
- 变更签证要有明确的费用影响分析
- 用表格呈现数据，便于对比""",

    "market_sales": """你是「市场与销售中心」，客户获取与商务推进专家。

你的职责：
1. 市场分析：行业趋势、竞争格局、目标客户画像
2. 商务方案：解决方案设计、价值主张、ROI分析
3. 投标文件：技术标、商务标、资质文件整理
4. 客户需求：需求挖掘、痛点分析、方案匹配

工作规范：
- 方案要突出EMA的核心价值（智能审图/文档生成/AI分析）
- 投标文件格式规范，内容完整
- 报价策略要有竞争力同时保证利润
- 用数据支撑论点，避免空泛描述
- 了解工程建筑行业术语和流程""",

    "customer_service": """你是「客户服务中心」，客户支持与关系维护专家。

你的职责：
1. FAQ解答：产品使用、功能说明、常见问题
2. 工单管理：问题分类、优先级、处理流程
3. 回访计划：客户满意度调查、定期回访安排
4. 培训材料：用户手册、操作指南、视频教程大纲

工作规范：
- 回答要简洁明了，避免技术术语
- 复杂问题要分步骤说明
- 提供操作截图或示例（文字描述）
- 无法解决的问题要引导到人工客服
- 保持友好、专业的服务态度""",
}


def build_system_prompt(agent_id: str, custom_suffix: str = "") -> str:
    """构建Agent的system prompt"""
    base = AGENT_SYSTEM_PROMPTS.get(agent_id, f"你是EMA的{agent_id}助手。请专业、简洁地回答用户问题。")
    if custom_suffix:
        base += f"\n\n附加说明：{custom_suffix}"
    return base


# ─── Ollama 本地调用 ─────────────────────────────────────────────

def _call_ollama(prompt: str, model: str = LLM_MODEL, timeout: float = 30.0) -> str:
    """调用Ollama本地模型"""
    socket_timeout = socket.getdefaulttimeout()
    from src.utils import json_dumps, json_loads
    try:
        socket.setdefaulttimeout(timeout)
        payload = json_dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 2048,
            }
        }).encode()
        req = urllib.request.Request(
            LLM_API_URL, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json_loads(resp.read())
            text = result.get("response", "").strip()
            return text
    except Exception:
        return ""
    finally:
        socket.setdefaulttimeout(socket_timeout)


# ─── 云端模型调用 ────────────────────────────────────────────────

def _call_cloud_openai(base_url: str, api_key: str, model: str,
                        messages: list, timeout: float = 30.0) -> str:
    """调用OpenAI兼容的云端API"""
    socket_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        url = f"{base_url}/chat/completions"
        payload = json_dumps({
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
        }).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json_loads(resp.read())
            text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            return text
    except Exception:
        return ""
    finally:
        socket.setdefaulttimeout(socket_timeout)


# ─── 统一调用入口 ────────────────────────────────────────────────

async def call_agent_llm(
    system_prompt: str,
    user_message: str,
    model_id: str = "",
    timeout: float = 30.0,
    context: str = "",
) -> Tuple[str, str]:
    """
    统一LLM调用入口

    Args:
        system_prompt: 系统提示词（角色定义）
        user_message: 用户消息
        model_id: 模型ID（如 "ollama/qwen3.5:9b"），空则自动路由
        timeout: 超时时间（秒）
        context: 额外上下文（如图纸分析结果）

    Returns:
        (response_text, model_used)
    """
    # 构建完整prompt
    full_prompt = f"{system_prompt}\n\n"
    if context:
        full_prompt += f"## 上下文信息\n{context}\n\n"
    full_prompt += f"## 用户问题\n{user_message}\n\n请给出专业、详细的回答："

    # 确定使用哪个模型
    if not model_id or model_id.startswith("ollama/"):
        # 本地Ollama
        model_name = model_id.split("/")[-1] if "/" in model_id else LLM_MODEL
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, _call_ollama, full_prompt, model_name, timeout
        )
        if response:
            return response, f"ollama/{model_name}"

    # 云端模型 fallback — 优先根据 model_id 前缀匹配 provider
    provider_order = list(CLOUD_APIS.keys())
    prefix = model_id.split("/")[0] if "/" in model_id else ""
    if prefix in CLOUD_APIS:
        provider_order = [prefix] + [p for p in provider_order if p != prefix]
    for provider in provider_order:
        config = CLOUD_APIS[provider]
        if not config["api_key"]:
            continue
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if context:
            messages.append({"role": "user", "content": f"上下文：{context}"})
        messages.append({"role": "user", "content": user_message})

        response = await asyncio.get_event_loop().run_in_executor(
            None, _call_cloud_openai,
            config["base_url"], config["api_key"], config["model"],
            messages, timeout
        )
        if response:
            return response, provider

    # 所有模型都失败，返回fallback
    return (
        "抱歉，当前AI模型服务暂时不可用。请稍后再试，或联系管理员检查模型配置。",
        "none"
    )


# ─── 同步版本（用于非async上下文）───────────────────────────────

def call_agent_llm_sync(
    system_prompt: str,
    user_message: str,
    model_id: str = "",
    timeout: float = 30.0,
    context: str = "",
) -> Tuple[str, str]:
    """同步版本的LLM调用"""
    full_prompt = f"{system_prompt}\n\n"
    if context:
        full_prompt += f"## 上下文信息\n{context}\n\n"
    full_prompt += f"## 用户问题\n{user_message}\n\n请给出专业、详细的回答："

    if not model_id or model_id.startswith("ollama/"):
        model_name = model_id.split("/")[-1] if "/" in model_id else LLM_MODEL
        response = _call_ollama(full_prompt, model_name, timeout)
        if response:
            return response, f"ollama/{model_name}"

    for provider, config in CLOUD_APIS.items():
        if not config["api_key"]:
            continue
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        if context:
            messages.append({"role": "user", "content": f"上下文：{context}"})
        messages.append({"role": "user", "content": user_message})

        response = _call_cloud_openai(
            config["base_url"], config["api_key"], config["model"],
            messages, timeout
        )
        if response:
            return response, provider

    return (
        "抱歉，当前AI模型服务暂时不可用。请稍后再试，或联系管理员检查模型配置。",
        "none"
    )


# ─── 流式调用（SSE/打字机效果）──────────────────────────────────

def _stream_ollama(prompt: str, model: str = LLM_MODEL, timeout: float = 60.0):
    """
    Ollama 流式生成器（逐块 yield token）
    用法: for token in _stream_ollama(prompt): ...
    """
    import urllib.request
    from src.utils import json_dumps

    payload = json_dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 4096,
        }
    }).encode()

    req = urllib.request.Request(
        LLM_API_URL, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            buffer = b""
            while True:
                chunk = resp.read(1024)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if line.strip():
                        try:
                            data = json_loads(line.decode())
                            token = data.get("response", "")
                            done = data.get("done", False)
                            if token:
                                yield token
                            if done:
                                return
                        except Exception:
                            continue
    except Exception as e:
        yield f"\n[Ollama 流式错误: {e}]"


def _stream_cloud_openai(base_url: str, api_key: str, model: str,
                          messages: list, timeout: float = 60.0):
    """
    云端 OpenAI 兼容 API 流式生成器（逐块 yield token）
    """
    import urllib.request
    from src.utils import json_dumps

    url = f"{base_url}/chat/completions"
    payload = json_dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4096,
        "stream": True,
    }).encode()

    req = urllib.request.Request(
        url, data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            buffer = b""
            while True:
                chunk = resp.read(1024)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line_str = line.decode().strip()
                    if not line_str or line_str.startswith(":"):
                        continue
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            return
                        try:
                            data = json_loads(data_str)
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue
    except Exception as e:
        yield f"\n[云端流式错误: {e}]"


def build_stream_prompt(system_prompt: str, user_message: str,
                          context: str = "", history_text: str = "") -> str:
    """构建流式调用的完整 prompt（与同步版本一致）"""
    full = f"{system_prompt}\n\n"
    if history_text:
        full += f"## 对话历史\n{history_text}\n\n"
    if context:
        full += f"## 上下文信息\n{context}\n\n"
    full += f"## 用户问题\n{user_message}\n\n请给出专业、详细的回答："
    return full

def build_history_prompt(history: list) -> str:
    """构建对话历史文本块（用于 Ollama /api/generate 纯文本 prompt 拼接）"""
    if not history:
        return ""
    parts = []
    for h in history:
        role = h.get("role", "user")
        msg = h.get("content", "")
        if role == "user":
            parts.append(f"用户：{msg}")
        else:
            parts.append(f"助手：{msg}")
    return "\n".join(parts)


def build_messages_with_history(system_prompt: str, user_message: str,
                                 history: list = None, context: str = "") -> list:
    """构建带对话历史的 messages 列表（用于云端 chat/completions API）"""
    messages = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append({"role": "user", "content": f"上下文：{context}"})
    if history:
        for h in history:
            messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": user_message})
    return messages


def stream_agent_llm(
    system_prompt: str,
    user_message: str,
    model_id: str = "",
    timeout: float = 60.0,
    context: str = "",
    history: list = None,
):
    """
    LLM 流式生成器入口

    返回一个生成器，逐 token 产出响应文本。
    模型选择逻辑与 call_agent_llm 一致（ollama → cloud fallback）。
    history: 对话历史列表 [{"role": "user"|"assistant", "content": "..."}]

    用法:
        for token in stream_agent_llm(sys_prompt, user_msg):
            print(token, end="", flush=True)
    """
    # 根据模型类型选择 prompt 构建方式
    if not model_id or model_id.startswith("ollama/"):
        history_text = build_history_prompt(history or [])
        full_prompt = build_stream_prompt(system_prompt, user_message, context, history_text)
        model_name = model_id.split("/")[-1] if "/" in model_id else LLM_MODEL
        yield from _stream_ollama(full_prompt, model_name, timeout)
        return

    # 优先根据 model_id 前缀匹配 provider，否则按顺序尝试
    provider_order = list(CLOUD_APIS.keys())
    prefix = model_id.split("/")[0] if "/" in model_id else ""
    if prefix in CLOUD_APIS:
        provider_order = [prefix] + [p for p in provider_order if p != prefix]
    for provider in provider_order:
        config = CLOUD_APIS[provider]
        if not config["api_key"]:
            continue
        messages = build_messages_with_history(system_prompt, user_message, history, context)
        yield from _stream_cloud_openai(
            config["base_url"], config["api_key"], config["model"],
            messages, timeout
        )
        return

    yield "抱歉，当前AI模型服务暂时不可用。请稍后再试，或联系管理员检查模型配置。"
