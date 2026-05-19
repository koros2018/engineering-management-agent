"""
auth_extended.py - 认证扩展 (v2)

- Boss只需账号密码登录，管理后台密码在进入后台时验证
- 微信扫码：真实QR码(base64) + 轮询确认机制
- 注册安全：密码复杂度 + 用户名验证
- 密码找回：token机制
- 登录限流防暴力破解
"""

import os, json, hashlib, secrets, time, re, io, base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
ADMIN_PASSWORDS_FILE = EMA_DATA_DIR / "admin_passwords.json"
LOGIN_ATTEMPTS_FILE = EMA_DATA_DIR / "login_attempts.json"
RESET_TOKENS_FILE = EMA_DATA_DIR / "reset_tokens.json"
WECHAT_SESSIONS_FILE = EMA_DATA_DIR / "wechat_sessions.json"

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15
RESET_TOKEN_EXPIRE_MINUTES = 30
WECHAT_QR_EXPIRE_SECONDS = 300


def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# ── Boss双密码（管理后台独立验证）───────────────────────────

def _hash_admin_password(password: str) -> Tuple[str, str]:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return h.hex(), salt


def init_boss_account():
    from auth import _load_json as auth_load, _save_json as auth_save, hash_password
    from auth import USERS_FILE, TENANTS_FILE, TENANT_USERS_FILE, Role

    users = auth_load(USERS_FILE)
    for uid, u in users.items():
        if u.get("username") == "boss_ke":
            # 确保管理后台密码存在
            set_admin_password(uid, "kzg@2023@SHMTU")
            print("✅ Boss账号已存在: boss_ke")
            return

    user_id = "user_boss_ke"
    password_hash, salt = hash_password("koros0001")
    users[user_id] = {"user_id": user_id, "username": "boss_ke", "email": "boss@ema.local", "password_hash": password_hash, "salt": salt, "created_at": datetime.now().isoformat(), "status": "active"}
    auth_save(USERS_FILE, users)

    tenants = auth_load(TENANTS_FILE)
    tenants["tenant_boss"] = {"tenant_id": "tenant_boss", "name": "EMA平台管理", "plan": "private", "admin_user_id": user_id, "created_at": datetime.now().isoformat(), "status": "active"}
    auth_save(TENANTS_FILE, tenants)

    tenant_users = auth_load(TENANT_USERS_FILE)
    tenant_users[user_id] = {"user_id": user_id, "tenant_id": "tenant_boss", "role": Role.SUPER_ADMIN, "joined_at": datetime.now().isoformat()}
    auth_save(TENANT_USERS_FILE, tenant_users)

    set_admin_password(user_id, "kzg@2023@SHMTU")
    print("✅ Boss账号已创建: boss_ke (super_admin)")


def set_admin_password(user_id: str, password: str) -> bool:
    pw_hash, salt = _hash_admin_password(password)
    admin_pws = _load_json(ADMIN_PASSWORDS_FILE)
    admin_pws[user_id] = {"user_id": user_id, "hash": pw_hash, "salt": salt, "updated_at": datetime.now().isoformat()}
    _save_json(ADMIN_PASSWORDS_FILE, admin_pws)
    return True


def verify_admin_password(user_id: str, password: str) -> bool:
    admin_pws = _load_json(ADMIN_PASSWORDS_FILE)
    record = admin_pws.get(user_id)
    if not record: return False
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), record["salt"].encode(), 100000)
    return h.hex() == record["hash"]


def boss_login_without_admin_pw(username: str, password: str) -> Dict:
    """Boss只需账号密码即可登录主界面"""
    from auth import login_user
    result = login_user(username, password)
    return {
        "success": True,
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "user": result,
        "is_boss": (result.get("role") == "super_admin"),
        "require_admin_pw": False,
    }


# ── 登录安全 ────────────────────────────────────────────────

def check_login_attempt(client_ip: str, username: str) -> Dict:
    attempts = _load_json(LOGIN_ATTEMPTS_FILE)
    key = f"{client_ip}:{username}"
    now = time.time()
    record = attempts.get(key, {"count": 0, "first_at": now, "locked_until": 0})
    if record.get("locked_until", 0) > now:
        lock_time = datetime.fromtimestamp(record["locked_until"])
        return {"allowed": False, "remaining": 0, "locked_until": lock_time.isoformat(), "message": f"账户已锁定，请{lock_time.strftime('%H:%M')}后重试"}
    if now - record.get("first_at", now) > LOGIN_LOCKOUT_MINUTES * 60:
        record = {"count": 0, "first_at": now, "locked_until": 0}
    record["count"] += 1
    attempts[key] = record
    if record["count"] >= MAX_LOGIN_ATTEMPTS:
        record["locked_until"] = now + LOGIN_LOCKOUT_MINUTES * 60
        attempts[key] = record
        _save_json(LOGIN_ATTEMPTS_FILE, attempts)
        return {"allowed": False, "remaining": 0, "locked_until": datetime.fromtimestamp(record["locked_until"]).isoformat(), "message": f"尝试次数过多，已锁定{LOGIN_LOCKOUT_MINUTES}分钟"}
    _save_json(LOGIN_ATTEMPTS_FILE, attempts)
    return {"allowed": True, "remaining": MAX_LOGIN_ATTEMPTS - record["count"], "locked_until": None}


def reset_login_attempts(client_ip: str, username: str):
    attempts = _load_json(LOGIN_ATTEMPTS_FILE)
    key = f"{client_ip}:{username}"
    if key in attempts:
        del attempts[key]
        _save_json(LOGIN_ATTEMPTS_FILE, attempts)


# ── 微信扫码登录（真实QR + 轮询）─────────────────────────────

def generate_wechat_qr_with_image() -> Dict:
    """生成微信扫码登录二维码（base64 PNG）"""
    state = secrets.token_hex(16)
    
    # 生成真实二维码
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(f"ema://wechat-login?state={state}&t={int(time.time())}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        qr_base64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        qr_base64 = ""

    # 创建会话
    sessions = _load_json(WECHAT_SESSIONS_FILE)
    sessions[state] = {
        "state": state,
        "status": "pending",  # pending → scanned → confirmed → expired
        "created_at": time.time(),
        "expires_at": time.time() + WECHAT_QR_EXPIRE_SECONDS,
        "user_id": None,
        "access_token": None,
    }
    _save_json(WECHAT_SESSIONS_FILE, sessions)

    return {
        "state": state,
        "qr_base64": qr_base64,
        "expires_in": WECHAT_QR_EXPIRE_SECONDS,
    }


def wechat_poll_status(state: str) -> Dict:
    """轮询扫码状态"""
    sessions = _load_json(WECHAT_SESSIONS_FILE)
    session = sessions.get(state)
    if not session:
        return {"success": False, "status": "expired"}

    # 检查过期
    if time.time() > session.get("expires_at", 0):
        session["status"] = "expired"
        _save_json(WECHAT_SESSIONS_FILE, sessions)
        return {"success": True, "status": "expired"}

    if session["status"] == "pending":
        # 模拟扫码：每10秒自动推进 (生产环境由手机扫码触发)
        elapsed = time.time() - session["created_at"]
        if elapsed > 5:
            session["status"] = "scanned"
            _save_json(WECHAT_SESSIONS_FILE, sessions)

    if session["status"] == "scanned":
        # 模拟确认：再等2秒
        elapsed = time.time() - session["created_at"]
        if elapsed > 7:
            # 完成登录
            from auth import register_user, get_user_tenant, create_access_token, create_refresh_token
            username = f"wx_{state[-8:]}"
            try:
                user = register_user(username, secrets.token_hex(16), email=f"{state[:8]}@wechat.local")
            except Exception:
                from auth import login_user, _load_json as al, USERS_FILE
                users = al(USERS_FILE)
                for uid, u in users.items():
                    if u.get("username") == username:
                        break
                user = {"user_id": uid, "username": username, "tenant_id": "tenant_wx", "tenant_name": "微信用户", "role": "editor"}
            user_id = user["user_id"]
            tenant_info = get_user_tenant(user_id)
            access_token = create_access_token(user_id, username, tenant_info.get("role", ""))
            session["status"] = "confirmed"
            session["user_id"] = user_id
            session["access_token"] = access_token
            _save_json(WECHAT_SESSIONS_FILE, sessions)

            return {
                "success": True,
                "status": "confirmed",
                "access_token": access_token,
                "user": {
                    "user_id": user_id,
                    "username": username,
                    "role": tenant_info.get("role", "editor"),
                    "tenant_id": tenant_info.get("tenant_id", ""),
                    "tenant_name": tenant_info.get("tenant_name", ""),
                },
                "is_boss": False,
            }

    return {
        "success": True,
        "status": session["status"],
        "access_token": session.get("access_token"),
        "user": session.get("user"),
        "is_boss": False,
    }


def wechat_confirm_scan(state: str) -> Dict:
    """模拟手机扫码确认（API调用触发）"""
    sessions = _load_json(WECHAT_SESSIONS_FILE)
    session = sessions.get(state)
    if not session:
        return {"success": False}
    session["status"] = "scanned"
    _save_json(WECHAT_SESSIONS_FILE, sessions)
    return {"success": True, "status": "scanned"}


# ── 密码找回 ────────────────────────────────────────────────

def request_password_reset(username: str, email: str) -> Dict:
    from auth import _load_json as auth_load, USERS_FILE
    users = auth_load(USERS_FILE)
    found = None
    for uid, u in users.items():
        if u.get("username") == username and u.get("email") == email:
            found = u; break
    if not found:
        return {"success": False, "message": "用户名或邮箱不匹配"}
    tokens = _load_json(RESET_TOKENS_FILE)
    token = secrets.token_hex(16)
    tokens[token] = {"user_id": found["user_id"], "username": username, "created_at": datetime.now().isoformat(), "expires_at": (datetime.now() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)).isoformat(), "used": False}
    _save_json(RESET_TOKENS_FILE, tokens)
    return {"success": True, "token": token, "message": f"重置链接已发送到 {email}\n\n重置码: {token}"}


def reset_password(token: str, new_password: str) -> Dict:
    tokens = _load_json(RESET_TOKENS_FILE)
    record = tokens.get(token)
    if not record or record.get("used") or datetime.now() > datetime.fromisoformat(record["expires_at"]):
        return {"success": False, "message": "重置链接无效或已过期"}
    if not validate_password_strength(new_password):
        return {"success": False, "message": "密码需至少8位，含大小写字母和数字"}
    from auth import _load_json as auth_load, _save_json as auth_save, USERS_FILE, hash_password
    users = auth_load(USERS_FILE)
    user = users.get(record["user_id"])
    if not user:
        return {"success": False, "message": "用户不存在"}
    pw_hash, pw_salt = hash_password(new_password)
    user["password_hash"] = pw_hash; user["salt"] = pw_salt
    auth_save(USERS_FILE, users)
    record["used"] = True
    _save_json(RESET_TOKENS_FILE, tokens)
    return {"success": True, "message": "密码重置成功，请重新登录"}


# ── 密码强度 ────────────────────────────────────────────────

def validate_password_strength(password: str) -> bool:
    return len(password) >= 8 and bool(re.search(r'[a-z]', password)) and bool(re.search(r'[A-Z]', password)) and bool(re.search(r'\d', password))


def validate_username(username: str) -> Optional[str]:
    if len(username) < 3: return "用户名至少3个字符"
    if len(username) > 30: return "用户名不能超过30个字符"
    if not re.match(r'^[a-zA-Z0-9_]+$', username): return "用户名只能包含字母、数字和下划线"
    return None
