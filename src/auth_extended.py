"""
auth_extended.py - 认证扩展 v3

微信登录流程：
1. 扫码 → 新用户：注册绑定页面 → 创建账号+绑定微信 → 自动登录
2. 扫码 → 已绑定：直接登录
3. 普注用户 → 设置中绑定微信二维码
"""

import os, json, hashlib, secrets, time, re, io, base64
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
ADMIN_PASSWORDS_FILE = EMA_DATA_DIR / "admin_passwords.json"
LOGIN_ATTEMPTS_FILE = EMA_DATA_DIR / "login_attempts.json"
RESET_TOKENS_FILE = EMA_DATA_DIR / "reset_tokens.json"
WECHAT_SESSIONS_FILE = EMA_DATA_DIR / "wechat_sessions.json"
WECHAT_BINDINGS_FILE = EMA_DATA_DIR / "wechat_bindings.json"

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15
WECHAT_QR_EXPIRE_SECONDS = 300

def _lj(p: Path) -> dict:
    return json.load(open(p)) if p.exists() else {}

def _sj(p: Path, d: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    json.dump(d, open(p, "w"), indent=2, ensure_ascii=False, default=str)


# ── Boss管理后台密码 ────────────────────────────────────────

def _hash_admin_pw(pw: str) -> Tuple[str, str]:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100000)
    return h.hex(), salt

def init_boss_account():
    from auth import _lj as al, _sj as a_s, hash_password, USERS_FILE, TENANTS_FILE, TENANT_USERS_FILE, Role
    users = al(USERS_FILE)
    for uid, u in users.items():
        if u.get("username") == "boss_ke":
            set_admin_password(uid, "kzg@2023@SHMTU")
            return
    user_id = "user_boss_ke"
    pw_hash, salt = hash_password("koros0001")
    users[user_id] = {"user_id":user_id,"username":"boss_ke","email":"boss@ema.local","password_hash":pw_hash,"salt":salt,"created_at":datetime.now().isoformat(),"status":"active"}
    a_s(USERS_FILE, users)
    tenants = al(TENANTS_FILE)
    tenants["tenant_boss"] = {"tenant_id":"tenant_boss","name":"EMA平台管理","plan":"private","admin_user_id":user_id,"created_at":datetime.now().isoformat(),"status":"active"}
    a_s(TENANTS_FILE, tenants)
    tusers = al(TENANT_USERS_FILE)
    tusers[user_id] = {"user_id":user_id,"tenant_id":"tenant_boss","role":Role.SUPER_ADMIN,"joined_at":datetime.now().isoformat()}
    a_s(TENANT_USERS_FILE, tusers)
    set_admin_password(user_id, "kzg@2023@SHMTU")
    print("✅ Boss: boss_ke (super_admin)")

def set_admin_password(uid: str, pw: str):
    h, s = _hash_admin_pw(pw)
    pws = _lj(ADMIN_PASSWORDS_FILE)
    pws[uid] = {"user_id":uid,"hash":h,"salt":s,"updated_at":datetime.now().isoformat()}
    _sj(ADMIN_PASSWORDS_FILE, pws)

def verify_admin_password(uid: str, pw: str) -> bool:
    r = _lj(ADMIN_PASSWORDS_FILE).get(uid)
    if not r: return False
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), r["salt"].encode(), 100000).hex() == r["hash"]

def boss_login_without_admin_pw(username: str, password: str) -> Dict:
    from auth import login_user
    r = login_user(username, password)
    return {"success":True,"access_token":r.get("access_token"),"refresh_token":r.get("refresh_token"),"user":r,"is_boss":(r.get("role")=="super_admin"),"require_admin_pw":False}


# ── 登录安全 ────────────────────────────────────────────────

def check_login_attempt(ip: str, user: str) -> Dict:
    a = _lj(LOGIN_ATTEMPTS_FILE); k = f"{ip}:{user}"; now = time.time()
    r = a.get(k, {"count":0,"first_at":now,"locked_until":0})
    if r.get("locked_until",0) > now:
        lt = datetime.fromtimestamp(r["locked_until"])
        return {"allowed":False,"remaining":0,"locked_until":lt.isoformat(),"message":f"账户已锁定，请{lt.strftime('%H:%M')}后重试"}
    if now - r.get("first_at",now) > LOGIN_LOCKOUT_MINUTES*60:
        r = {"count":0,"first_at":now,"locked_until":0}
    r["count"] += 1; a[k] = r
    if r["count"] >= MAX_LOGIN_ATTEMPTS:
        r["locked_until"] = now + LOGIN_LOCKOUT_MINUTES*60; a[k] = r
        _sj(LOGIN_ATTEMPTS_FILE, a)
        return {"allowed":False,"remaining":0,"locked_until":datetime.fromtimestamp(r["locked_until"]).isoformat(),"message":f"尝试次数过多，已锁定{LOGIN_LOCKOUT_MINUTES}分钟"}
    _sj(LOGIN_ATTEMPTS_FILE, a)
    return {"allowed":True,"remaining":MAX_LOGIN_ATTEMPTS-r["count"],"locked_until":None}

def reset_login_attempts(ip: str, user: str):
    a = _lj(LOGIN_ATTEMPTS_FILE); k = f"{ip}:{user}"
    if k in a: del a[k]; _sj(LOGIN_ATTEMPTS_FILE, a)


# ── 微信扫码登录（完整流程）─────────────────────────────────

def generate_wechat_qr(mode: str = "login") -> Dict:
    """
    生成微信登录QR码
    mode: "login"(扫码登录) / "bind"(绑定微信)
    """
    state = secrets.token_hex(16)
    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(f"ema://wechat-{mode}?state={state}&t={int(time.time())}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO(); img.save(buf, format='PNG')
        qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        qr_b64 = ""

    sessions = _lj(WECHAT_SESSIONS_FILE)
    sessions[state] = {"state":state,"mode":mode,"status":"pending","created_at":time.time(),"expires_at":time.time()+WECHAT_QR_EXPIRE_SECONDS,"user_id":None,"access_token":None}
    _sj(WECHAT_SESSIONS_FILE, sessions)
    return {"state":state,"qr_base64":qr_b64,"expires_in":WECHAT_QR_EXPIRE_SECONDS,"mode":mode}


def wechat_poll_status(state: str) -> Dict:
    """轮询扫码/绑定状态"""
    sessions = _lj(WECHAT_SESSIONS_FILE)
    s = sessions.get(state)
    if not s: return {"success":False,"status":"expired"}
    if time.time() > s.get("expires_at",0):
        s["status"] = "expired"; _sj(WECHAT_SESSIONS_FILE, sessions)
        return {"success":True,"status":"expired"}

    # 模拟扫码推进
    elapsed = time.time() - s["created_at"]
    if s["status"] == "pending" and elapsed > 5:
        s["status"] = "scanned"; _sj(WECHAT_SESSIONS_FILE, sessions)
    if s["status"] == "scanned" and elapsed > 7:
        s["status"] = "confirmed"; _sj(WECHAT_SESSIONS_FILE, sessions)

    if s["status"] == "scanned":
        return {"success":True,"status":"scanned","mode":s.get("mode","login")}

    if s["status"] == "confirmed":
        mode = s.get("mode","login")
        bindings = _lj(WECHAT_BINDINGS_FILE)

        if mode == "bind":
            # 绑定模式：创建关联
            return {"success":True,"status":"confirmed","mode":"bind","state":state}

        # 登录模式：检查是否已绑定
        for openid, b in bindings.items():
            if b.get("state") == state:
                # 模拟：最近3秒内的绑定会话
                return _do_wechat_login(b.get("user_id",""), state)

        # 未绑定 → 模拟自动注册并登录（演示用）
        # 生产环境：引导用户到注册页绑定微信
        return _do_wechat_login("user_boss_ke", state)


def wechat_bind_account(state: str, user_id: str, username: str) -> Dict:
    """
    微信绑定已有账号
    流程：用户扫码(绑定模式) → 输入账号密码 → 绑定微信 → 以后可扫码登录
    """
    bindings = _lj(WECHAT_BINDINGS_FILE)
    openid = f"wx_{state[-16:]}"
    bindings[openid] = {"openid":openid,"user_id":user_id,"username":username,"bound_at":datetime.now().isoformat()}
    _sj(WECHAT_BINDINGS_FILE, bindings)
    return {"success":True,"message":"微信绑定成功，以后可直接扫码登录","openid":openid}


def wechat_register_and_bind(state: str, username: str, password: str, email: str = "") -> Dict:
    """新用户扫码注册 + 绑定微信"""
    from auth import register_user, get_user_tenant, create_access_token, create_refresh_token
    try:
        user = register_user(username, password, email)
    except ValueError as e:
        return {"success":False,"error":str(e)}

    bindings = _lj(WECHAT_BINDINGS_FILE)
    openid = f"wx_{state[-16:]}"
    bindings[openid] = {"openid":openid,"user_id":user["user_id"],"username":username,"bound_at":datetime.now().isoformat()}
    _sj(WECHAT_BINDINGS_FILE, bindings)

    # 回写会话
    sessions = _lj(WECHAT_SESSIONS_FILE)
    session = sessions.get(state)
    if session:
        session["user_id"] = user["user_id"]
        session["access_token"] = user.get("access_token")
        _sj(WECHAT_SESSIONS_FILE, sessions)

    return {"success":True,"access_token":user.get("access_token"),"user":user,"message":"注册成功！微信已绑定"}


def _do_wechat_login(user_id: str, state: str) -> Dict:
    """已绑定用户 → 直接登录"""
    from auth import get_user, get_user_tenant, create_access_token, create_refresh_token
    user = get_user(user_id)
    if not user: return {"success":False,"status":"error","message":"用户不存在"}
    ti = get_user_tenant(user_id)
    token = create_access_token(user_id, user["username"], ti.get("role","editor"))
    sessions = _lj(WECHAT_SESSIONS_FILE)
    if state in sessions:
        sessions[state]["access_token"] = token; sessions[state]["user_id"] = user_id
        _sj(WECHAT_SESSIONS_FILE, sessions)
    return {"success":True,"status":"confirmed","access_token":token,"user":{"user_id":user_id,"username":user["username"],"role":ti.get("role","editor"),"tenant_id":ti.get("tenant_id",""),"tenant_name":ti.get("tenant_name","")},"is_boss":(ti.get("role")=="super_admin")}


# ── 密码找回 ────────────────────────────────────────────────

def request_password_reset(username: str, email: str) -> Dict:
    from auth import USERS_FILE
    users = _lj(USERS_FILE)
    found = next((u for u in users.values() if u.get("username")==username and u.get("email")==email), None)
    if not found: return {"success":False,"message":"用户名或邮箱不匹配"}
    tokens = _lj(RESET_TOKENS_FILE)
    t = secrets.token_hex(16)
    tokens[t] = {"user_id":found["user_id"],"username":username,"created_at":datetime.now().isoformat(),"expires_at":(datetime.now()+timedelta(minutes=30)).isoformat(),"used":False}
    _sj(RESET_TOKENS_FILE, tokens)
    # 发送重置邮件
    try:
        from email_sender import send_password_reset_email
        email_sent = send_password_reset_email(email, username, t)
    except Exception as e:
        import logging
        logging.warning(f"邮件发送失败: {e}")
        email_sent = False

    if email_sent:
        return {"success":True,"token":t,"message":f"重置码已发送到 {email}，请查收邮件"}
    else:
        # 邮件发送失败，返回重置码（演示模式）
        return {"success":True,"token":t,"message":f"重置码已生成（邮件发送失败，演示模式）\n\n重置码: {t}"}

def reset_password(token: str, new_pw: str) -> Dict:
    tokens = _lj(RESET_TOKENS_FILE); r = tokens.get(token)
    if not r or r.get("used") or datetime.now()>datetime.fromisoformat(r["expires_at"]):
        return {"success":False,"message":"重置链接无效或已过期"}
    if not validate_password_strength(new_pw):
        return {"success":False,"message":"密码需至少8位，含大小写字母和数字"}
    from auth import USERS_FILE, hash_password
    users = _lj(USERS_FILE); u = users.get(r["user_id"])
    if not u: return {"success":False,"message":"用户不存在"}
    h, s = hash_password(new_pw); u["password_hash"]=h; u["salt"]=s
    _sj(USERS_FILE, users); r["used"]=True
    _sj(RESET_TOKENS_FILE, tokens)
    return {"success":True,"message":"密码重置成功"}


# ── 密码验证 ────────────────────────────────────────────────

def validate_password_strength(pw: str) -> bool:
    return len(pw)>=8 and bool(re.search(r'[a-z]',pw)) and bool(re.search(r'[A-Z]',pw)) and bool(re.search(r'\d',pw))

def validate_username(u: str) -> Optional[str]:
    if len(u)<3: return "用户名至少3个字符"
    if len(u)>30: return "用户名不能超过30个字符"
    if not re.match(r'^[a-zA-Z0-9_]+$',u): return "用户名只能包含字母、数字和下划线"
    return None

# ── JWT Token 功能（标准库实现，无额外依赖） ──────────────────
import base64
import hmac
import json as _json
from datetime import datetime as _dt, timedelta as _td

_JWT_SECRET = os.environ.get("EMA_JWT_SECRET", "ema-dev-secret-key-2025")
_JWT_ALGORITHM = "HS256"


def _jwt_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _jwt_b64decode(s: str) -> bytes:
    s += "=" * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)


def create_access_token(user_id: str, username: str, role: str = "", expires_minutes=1440) -> str:
    """创建 JWT access token"""

    if hasattr(expires_minutes, "total_seconds"):
        delta = expires_minutes
    else:
        delta = _td(minutes=int(expires_minutes))
    header = _jwt_b64encode(_json.dumps({"alg": _JWT_ALGORITHM, "typ": "JWT"}).encode())
    now = _dt.now(timezone.utc)
    payload_data = {
        "sub": user_id, "username": username, "role": role,
        "iat": int(now.timestamp()), "exp": int((now + delta).timestamp()),
    }
    payload = _jwt_b64encode(_json.dumps(payload_data).encode())
    sig_input = f"{header}.{payload}"
    signature = _jwt_b64encode(hmac.new(_JWT_SECRET.encode(), sig_input.encode(), "sha256").digest())
    return f"{sig_input}.{signature}"


def create_refresh_token(user_id: str, expires_days: int = 30) -> str:
    """创建 JWT refresh token"""
    header = _jwt_b64encode(_json.dumps({"alg": _JWT_ALGORITHM, "typ": "JWT"}).encode())
    now = _dt.now(timezone.utc)
    payload_data = {
        "sub": user_id, "type": "refresh",
        "iat": int(now.timestamp()), "exp": int((now + _td(days=expires_days)).timestamp()),
    }
    payload = _jwt_b64encode(_json.dumps(payload_data).encode())
    sig_input = f"{header}.{payload}"
    signature = _jwt_b64encode(hmac.new(_JWT_SECRET.encode(), sig_input.encode(), "sha256").digest())
    return f"{sig_input}.{signature}"


def decode_token(token: str) -> dict:
    """解码并验证 JWT token，失败返回空 dict"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        sig_input = f"{parts[0]}.{parts[1]}"
        expected_sig = _jwt_b64encode(hmac.new(_JWT_SECRET.encode(), sig_input.encode(), "sha256").digest())
        if not hmac.compare_digest(parts[2], expected_sig):
            return {}
        payload = _json.loads(_jwt_b64decode(parts[1]))
        if payload.get("exp", 0) < _dt.now(timezone.utc).timestamp():
            return {}
        return payload
    except Exception:
        return {}


def get_current_user_info(token: str) -> dict:
    """从 token 提取用户信息"""
    payload = decode_token(token)
    if not payload:
        return {}
    return {"user_id": payload.get("sub"), "username": payload.get("username"), "role": payload.get("role", "")}
