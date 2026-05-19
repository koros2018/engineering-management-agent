"""
auth_extended.py - 认证扩展模块

新增：
- Boss双密码（账号密码 + 管理后台密码）
- 微信扫码登录（OAuth2 Stub）
- 密码找回（邮件验证码）
- 注册安全（密码复杂度/验证码）
- 登录限流防暴力破解
"""

import os
import json
import hashlib
import secrets
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple


# ── 配置 ──────────────────────────────────────────────────────

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
ADMIN_PASSWORDS_FILE = EMA_DATA_DIR / "admin_passwords.json"
LOGIN_ATTEMPTS_FILE = EMA_DATA_DIR / "login_attempts.json"
WECHAT_USERS_FILE = EMA_DATA_DIR / "wechat_users.json"
RESET_TOKENS_FILE = EMA_DATA_DIR / "reset_tokens.json"

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15
RESET_TOKEN_EXPIRE_MINUTES = 30


def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# ── Boss双密码 ────────────────────────────────────────────────

def _hash_admin_password(password: str) -> Tuple[str, str]:
    """PBKDF2-SHA256，返回 (hash, salt)"""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return h.hex(), salt


def init_boss_account():
    """
    初始化boss账号（首次启动时调用）
    - boss_ke / koros0001（账号登录）
    - kzg@2023@SHMTU（管理后台密码）
    """
    from auth import _load_json as auth_load, _save_json as auth_save, hash_password
    from auth import USERS_FILE, TENANTS_FILE, TENANT_USERS_FILE, Role

    users = auth_load(USERS_FILE)

    # 检查是否已存在
    for uid, u in users.items():
        if u.get("username") == "boss_ke":
            print("✅ Boss账号已存在: boss_ke")
            return

    # 创建boss用户
    user_id = "user_boss_ke"
    password_hash, salt = hash_password("koros0001")

    users[user_id] = {
        "user_id": user_id,
        "username": "boss_ke",
        "email": "boss@ema.local",
        "password_hash": password_hash,
        "salt": salt,
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    auth_save(USERS_FILE, users)

    # 创建boss租户
    tenants = auth_load(TENANTS_FILE)
    tenants["tenant_boss"] = {
        "tenant_id": "tenant_boss",
        "name": "EMA平台管理",
        "plan": "private",
        "admin_user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }
    auth_save(TENANTS_FILE, tenants)

    # 租户关联
    tenant_users = auth_load(TENANT_USERS_FILE)
    tenant_users[user_id] = {
        "user_id": user_id,
        "tenant_id": "tenant_boss",
        "role": Role.SUPER_ADMIN,
        "joined_at": datetime.now().isoformat(),
    }
    auth_save(TENANT_USERS_FILE, tenant_users)

    # 设置管理后台密码
    set_admin_password(user_id, "kzg@2023@SHMTU")

    print("✅ Boss账号已创建: boss_ke (super_admin)")


def set_admin_password(user_id: str, password: str) -> bool:
    """设置管理后台密码"""
    pw_hash, salt = _hash_admin_password(password)
    admin_pws = _load_json(ADMIN_PASSWORDS_FILE)
    admin_pws[user_id] = {
        "user_id": user_id,
        "hash": pw_hash,
        "salt": salt,
        "updated_at": datetime.now().isoformat(),
    }
    _save_json(ADMIN_PASSWORDS_FILE, admin_pws)
    return True


def verify_admin_password(user_id: str, password: str) -> bool:
    """验证管理后台密码"""
    admin_pws = _load_json(ADMIN_PASSWORDS_FILE)
    record = admin_pws.get(user_id)
    if not record:
        return False
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), record["salt"].encode(), 100000)
    return h.hex() == record["hash"]


def boss_login(username: str, password: str, admin_password: str = None) -> Dict:
    """
    Boss登录（双密码）

    返回:
        {
            "success": bool,
            "access_token": str,
            "user": dict,
            "is_boss": bool,
            "require_admin_pw": bool,  # 需要管理后台密码
        }
    """
    from auth import login_user
    result = login_user(username, password)

    if result.get("role") != "super_admin":
        return {
            "success": True,
            "access_token": result.get("access_token"),
            "refresh_token": result.get("refresh_token"),
            "user": result,
            "is_boss": False,
            "require_admin_pw": False,
        }

    # Boss账号：检查是否需要管理后台密码
    if admin_password:
        # 验证管理后台密码
        if verify_admin_password(result["user_id"], admin_password):
            return {
                "success": True,
                "access_token": result.get("access_token"),
                "refresh_token": result.get("refresh_token"),
                "user": result,
                "is_boss": True,
                "require_admin_pw": False,
                "admin_verified": True,
            }
        else:
            return {
                "success": False,
                "error": "管理后台密码错误",
            }
    else:
        # 需要管理后台密码
        return {
            "success": True,
            "access_token": result.get("access_token"),
            "refresh_token": result.get("refresh_token"),
            "user": result,
            "is_boss": True,
            "require_admin_pw": True,
            "admin_verified": False,
        }


# ── 登录安全 ──────────────────────────────────────────────────

def check_login_attempt(client_ip: str, username: str) -> Dict:
    """
    检查登录尝试次数

    Returns:
        {"allowed": bool, "remaining": int, "locked_until": str or None}
    """
    attempts = _load_json(LOGIN_ATTEMPTS_FILE)
    key = f"{client_ip}:{username}"
    now = time.time()

    record = attempts.get(key, {"count": 0, "first_at": now, "locked_until": 0})

    # 检查锁定
    if record.get("locked_until", 0) > now:
        lock_time = datetime.fromtimestamp(record["locked_until"])
        return {
            "allowed": False,
            "remaining": 0,
            "locked_until": lock_time.isoformat(),
            "message": f"账户已锁定，请{lock_time.strftime('%H:%M')}后重试",
        }

    # 重置过期记录
    if now - record.get("first_at", now) > LOGIN_LOCKOUT_MINUTES * 60:
        record = {"count": 0, "first_at": now, "locked_until": 0}

    record["count"] += 1
    attempts[key] = record

    if record["count"] >= MAX_LOGIN_ATTEMPTS:
        record["locked_until"] = now + LOGIN_LOCKOUT_MINUTES * 60
        attempts[key] = record
        _save_json(LOGIN_ATTEMPTS_FILE, attempts)
        return {
            "allowed": False,
            "remaining": 0,
            "locked_until": datetime.fromtimestamp(record["locked_until"]).isoformat(),
            "message": f"尝试次数过多，已锁定{LOGIN_LOCKOUT_MINUTES}分钟",
        }

    _save_json(LOGIN_ATTEMPTS_FILE, attempts)
    return {
        "allowed": True,
        "remaining": MAX_LOGIN_ATTEMPTS - record["count"],
        "locked_until": None,
    }


def reset_login_attempts(client_ip: str, username: str):
    """登录成功后重置尝试次数"""
    attempts = _load_json(LOGIN_ATTEMPTS_FILE)
    key = f"{client_ip}:{username}"
    if key in attempts:
        del attempts[key]
        _save_json(LOGIN_ATTEMPTS_FILE, attempts)


# ── 密码找回 ──────────────────────────────────────────────────

def request_password_reset(username: str, email: str) -> Dict:
    """
    请求密码重置

    Returns:
        {"success": bool, "token": str, "message": str}
    """
    from auth import _load_json as auth_load, USERS_FILE

    users = auth_load(USERS_FILE)
    found = None
    for uid, u in users.items():
        if u.get("username") == username and u.get("email") == email:
            found = u
            break

    if not found:
        return {"success": False, "message": "用户名或邮箱不匹配"}

    # 生成重置token
    tokens = _load_json(RESET_TOKENS_FILE)
    token = secrets.token_hex(16)

    tokens[token] = {
        "user_id": found["user_id"],
        "username": username,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)).isoformat(),
        "used": False,
    }
    _save_json(RESET_TOKENS_FILE, tokens)

    return {
        "success": True,
        "token": token,
        "message": f"重置链接已发送到 {email}（模拟）\n重置码: {token}",
    }


def verify_reset_token(token: str) -> Optional[str]:
    """验证重置token，返回user_id"""
    tokens = _load_json(RESET_TOKENS_FILE)
    record = tokens.get(token)

    if not record or record.get("used"):
        return None

    expires = datetime.fromisoformat(record["expires_at"])
    if datetime.now() > expires:
        return None

    return record["user_id"]


def reset_password(token: str, new_password: str) -> Dict:
    """
    重置密码

    Returns:
        {"success": bool, "message": str}
    """
    user_id = verify_reset_token(token)
    if not user_id:
        return {"success": False, "message": "重置链接无效或已过期"}

    # 密码复杂度
    if not validate_password_strength(new_password):
        return {"success": False, "message": "密码需至少8位，含大小写字母和数字"}

    from auth import _load_json as auth_load, _save_json as auth_save
    from auth import USERS_FILE, hash_password

    users = auth_load(USERS_FILE)
    user = users.get(user_id)
    if not user:
        return {"success": False, "message": "用户不存在"}

    pw_hash, pw_salt = hash_password(new_password)
    user["password_hash"] = pw_hash
    user["salt"] = pw_salt
    auth_save(USERS_FILE, users)

    # 标记token已使用
    tokens = _load_json(RESET_TOKENS_FILE)
    tokens[token]["used"] = True
    _save_json(RESET_TOKENS_FILE, tokens)

    return {"success": True, "message": "密码重置成功，请重新登录"}


# ── 微信扫码登录 ──────────────────────────────────────────────

def generate_wechat_qr() -> Dict:
    """
    生成微信登录二维码（Stub）

    生产环境：调用微信开放平台 /connect/qrconnect
    """
    state = secrets.token_hex(16)
    qr_url = f"weixin://dl/business/?state={state}&appid=wx_mock_app"

    return {
        "state": state,
        "qr_url": qr_url,
        "expires_in": 300,  # 5分钟
    }


def wechat_callback(code: str, state: str) -> Dict:
    """
    微信扫码回调（Stub）

    生产环境：
    1. 用 code 换取 access_token
    2. 用 access_token 获取用户信息
    3. 创建/关联本地用户
    4. 返回 JWT
    """
    wechat_users = _load_json(WECHAT_USERS_FILE)

    # 模拟微信用户
    mock_openid = f"wx_openid_{secrets.token_hex(6)}"
    mock_nickname = f"微信用户{secrets.token_hex(3)}"

    # 检查是否已关联
    wechat_user = wechat_users.get(mock_openid)
    if wechat_user:
        user_id = wechat_user["user_id"]
    else:
        # 创建新用户
        from auth import register_user
        username = f"wx_{mock_openid[-8:]}"
        user = register_user(username, secrets.token_hex(16), email=f"{mock_openid}@wechat.local")
        user_id = user["user_id"]
        wechat_users[mock_openid] = {"user_id": user_id, "nickname": mock_nickname}
        _save_json(WECHAT_USERS_FILE, wechat_users)

    # 获取用户信息
    from auth import get_user, get_user_tenant
    from auth import create_access_token, create_refresh_token

    user = get_user(user_id)
    if not user:
        return {"success": False, "error": "用户创建失败"}

    tenant_info = get_user_tenant(user_id)
    access = create_access_token(user_id, user["username"], tenant_info.get("role", ""))
    refresh = create_refresh_token(user_id)

    return {
        "success": True,
        "access_token": access,
        "refresh_token": refresh,
        "user": {
            "user_id": user_id,
            "username": user["username"],
            "role": tenant_info.get("role", ""),
            "tenant_id": tenant_info.get("tenant_id", ""),
            "tenant_name": tenant_info.get("tenant_name", ""),
            "wechat_nickname": mock_nickname,
        },
    }


# ── 密码强度验证 ──────────────────────────────────────────────

def validate_password_strength(password: str) -> bool:
    """密码强度：至少8位，含大小写字母和数字"""
    if len(password) < 8:
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True


def validate_username(username: str) -> Optional[str]:
    """验证用户名规则，返回None表示通过，否则返回错误信息"""
    if len(username) < 3:
        return "用户名至少3个字符"
    if len(username) > 30:
        return "用户名不能超过30个字符"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return "用户名只能包含字母、数字和下划线"
    return None
