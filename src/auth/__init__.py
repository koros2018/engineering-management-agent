"""
auth/auth.py - EMA 多租户认证模块

基于 blueprint-ai auth.py 扩展：
- 用户注册/登录 (JWT)
- 租户管理 (企业账号)
- 用户-租户关联
- RBAC 角色权限

数据库表:
- tenants: 租户（企业）
- users: 用户（账号）
- tenant_users: 用户-租户关联（含角色）
"""

import os
import sys
import json
import hashlib
import secrets
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# 复用 blueprint-ai 的 JWT 实现
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "../blueprint-ai" / "src"))
from blueprint_parser.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user_info,
)

# ── 配置 ────────────────────────────────────────────────────────

EMA_DATA_DIR = Path(__file__).parent.parent.parent / "data"
EMA_DATA_DIR.mkdir(parents=True, exist_ok=True)

# 简单 JSON 文件存储（Phase 4 阶段，后续迁移到 PostgreSQL）
USERS_FILE = EMA_DATA_DIR / "users.json"
TENANTS_FILE = EMA_DATA_DIR / "tenants.json"
TENANT_USERS_FILE = EMA_DATA_DIR / "tenant_users.json"

# ── RBAC 角色定义 ────────────────────────────────────────────────

class Role:
    """角色与权限"""
    SUPER_ADMIN = "super_admin"   # 平台管理员（刚哥）
    TENANT_ADMIN = "tenant_admin" # 企业管理员
    EDITOR = "editor"             # 编辑者（正常用户）
    VIEWER = "viewer"             # 只读用户

    PERMISSIONS = {
        SUPER_ADMIN: ["*"],                    # 全部权限
        TENANT_ADMIN: [
            "tenant:read", "tenant:write",
            "project:create", "project:delete",
            "project:read", "project:write",
            "member:invite", "member:remove",
            "analysis:use",
            "billing:read", "billing:manage",
        ],
        EDITOR: [
            "project:create", "project:read", "project:write",
            "analysis:use",
        ],
        VIEWER: [
            "project:read",
            "analysis:use",
        ],
    }

    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        if role == cls.SUPER_ADMIN:
            return True
        return permission in cls.PERMISSIONS.get(role, [])


# ── 数据存储（Phase 4 用 JSON 文件，后续迁移 PostgreSQL）────────────────

def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def _save_json(path: Path, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# 密码哈希

def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    """PBKDF2-SHA256 密码哈希，返回 (hash, salt)"""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return h.hex(), salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """验证密码"""
    computed, _ = hash_password(password, salt)
    return computed == stored_hash


# ── 租户管理 ──────────────────────────────────────────────────

def create_tenant(name: str, admin_user_id: str, plan: str = "free") -> Dict:
    """创建租户（企业账号）"""
    tenants = _load_json(TENANTS_FILE)
    tenant_id = f"tenant_{secrets.token_hex(6)}"

    tenants[tenant_id] = {
        "tenant_id": tenant_id,
        "name": name,
        "plan": plan,
        "admin_user_id": admin_user_id,
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    _save_json(TENANTS_FILE, tenants)
    return tenants[tenant_id]

def get_tenant(tenant_id: str) -> Optional[Dict]:
    tenants = _load_json(TENANTS_FILE)
    return tenants.get(tenant_id)


# ── 用户管理 ──────────────────────────────────────────────────

def register_user(
    username: str,
    password: str,
    email: str = "",
    tenant_name: str = None,
) -> Dict:
    """
    注册用户

    流程：
    1. 检查用户名是否已存在
    2. 创建用户账号（密码哈希）
    3. 如果提供了 tenant_name，自动创建或加入租户
    4. 返回用户信息 + token
    """
    users = _load_json(USERS_FILE)
    tenant_users = _load_json(TENANT_USERS_FILE)

    # 检查用户名
    for uid, u in users.items():
        if u.get("username") == username:
            raise ValueError(f"用户名 '{username}' 已存在")

    # 创建用户
    user_id = f"user_{secrets.token_hex(8)}"
    password_hash, salt = hash_password(password)

    users[user_id] = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "salt": salt,
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    _save_json(USERS_FILE, users)

    # 创建/加入租户
    if tenant_name:
        tenant = create_tenant(tenant_name, user_id)
        tenant_id = tenant["tenant_id"]
        role = Role.TENANT_ADMIN
    else:
        # 默认个人租户
        tenant = create_tenant(f"{username}的个人空间", user_id, plan="free")
        tenant_id = tenant["tenant_id"]
        role = Role.TENANT_ADMIN

    # 用户-租户关联
    tenant_users[user_id] = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "joined_at": datetime.now().isoformat(),
    }
    _save_json(TENANT_USERS_FILE, tenant_users)

    # 生成 tokens
    access_token = create_access_token(user_id, username, role)
    refresh_token = create_refresh_token(user_id)

    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "tenant_id": tenant_id,
        "tenant_name": tenant["name"],
        "role": role,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def login_user(username: str, password: str) -> Dict:
    """用户登录"""
    users = _load_json(USERS_FILE)
    tenant_users = _load_json(TENANT_USERS_FILE)

    # 查找用户
    found_user = None
    for uid, u in users.items():
        if u.get("username") == username:
            found_user = u
            break

    if not found_user:
        raise ValueError("用户名或密码错误")

    # 验证密码
    if not verify_password(password, found_user["password_hash"], found_user["salt"]):
        raise ValueError("用户名或密码错误")

    user_id = found_user["user_id"]

    # 获取租户信息
    tu = tenant_users.get(user_id, {})
    tenant_id = tu.get("tenant_id", "")
    role = tu.get("role", Role.EDITOR)
    tenant = _load_json(TENANTS_FILE).get(tenant_id, {})

    # 生成 tokens
    access_token = create_access_token(user_id, username, role)
    refresh_token = create_refresh_token(user_id)

    return {
        "user_id": user_id,
        "username": username,
        "email": found_user.get("email", ""),
        "tenant_id": tenant_id,
        "tenant_name": tenant.get("name", ""),
        "role": role,
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def get_user(user_id: str) -> Optional[Dict]:
    users = _load_json(USERS_FILE)
    return users.get(user_id)


def get_user_tenant(user_id: str) -> Optional[Dict]:
    """获取用户所属租户信息"""
    tenant_users = _load_json(TENANT_USERS_FILE)
    tu = tenant_users.get(user_id, {})
    tenant = _load_json(TENANTS_FILE).get(tu.get("tenant_id"), {})
    return {
        "user_id": user_id,
        "tenant_id": tu.get("tenant_id", ""),
        "role": tu.get("role", ""),
        "tenant_name": tenant.get("name", ""),
        "plan": tenant.get("plan", "free"),
    }


def refresh_access_token(refresh_token_str: str) -> Optional[Dict]:
    """用 refresh token 获取新的 access token"""
    payload = decode_token(refresh_token_str)
    if not payload or "error" in payload:
        return None
    if payload.get("type") != "refresh":
        return None

    user_id = payload.get("sub", "")
    user = get_user(user_id)
    tenant_info = get_user_tenant(user_id)

    if not user:
        return None

    new_access = create_access_token(user_id, user["username"], tenant_info.get("role", ""))
    return {
        "access_token": new_access,
        "user_id": user_id,
    }


# ── 数据目录隔离 ──────────────────────────────────────────────

def get_tenant_data_dir(tenant_id: str) -> Path:
    """获取租户的数据目录"""
    base = EMA_DATA_DIR / "tenants" / tenant_id
    base.mkdir(parents=True, exist_ok=True)
    return base

def get_user_project_dir(tenant_id: str, project_id: str) -> Path:
    """获取用户项目的数据目录"""
    d = get_tenant_data_dir(tenant_id) / "projects" / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── FastAPI 依赖 ──────────────────────────────────────────────

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> Dict:
    """
    FastAPI 依赖：从 Authorization header 解析当前用户

    用法:
        @app.get("/api/data")
        async def get_data(user: dict = Depends(get_current_user)):
            return {"user": user}
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="请登录后使用")

    token = credentials.credentials
    payload = decode_token(token)

    if not payload or "error" in payload:
        error = payload.get("error", "invalid_token") if payload else "invalid_token"
        if error == "token_expired":
            raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
        raise HTTPException(status_code=401, detail="无效的登录凭据")

    user_id = payload.get("sub", "")
    tenant_info = get_user_tenant(user_id)

    if not tenant_info.get("tenant_id"):
        raise HTTPException(status_code=401, detail="账号未关联租户")

    return {
        "user_id": user_id,
        "username": payload.get("username", ""),
        "role": payload.get("role", ""),
        "tenant_id": tenant_info["tenant_id"],
        "tenant_name": tenant_info.get("tenant_name", ""),
        "plan": tenant_info.get("plan", "free"),
    }


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> Optional[Dict]:
    """可选认证：有 token 返回用户，无则返回 None"""
    if not credentials:
        return None
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    RBAC 检查装饰器依赖

    用法:
        @app.get("/admin/users")
        async def admin_endpoint(user: dict = Depends(require_role("tenant_admin"))):
            ...
    """
    async def role_checker(user: dict = Depends(get_current_user)):
        if not Role.has_permission(user["role"], required_role):
            raise HTTPException(status_code=403, detail="权限不足")
        return user
    return role_checker
