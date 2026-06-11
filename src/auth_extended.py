"""
auth_extended.py - 认证扩展 v3

微信登录流程：
1. 扫码 → 新用户：注册绑定页面 → 创建账号+绑定微信 → 自动登录
2. 扫码 → 已绑定：直接登录
3. 普注用户 → 设置中绑定微信二维码
"""

import os, json, hashlib, secrets, time, re, io, base64, hmac
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

from utils import load_json, save_json

# ── JWT 配置 ──
_JWT_SECRET = os.environ.get("EMA_JWT_SECRET", "ema-dev-secret-key-2025")
_JWT_ALGORITHM = "HS256"

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
ADMIN_PASSWORDS_FILE = EMA_DATA_DIR / "admin_passwords.json"
LOGIN_ATTEMPTS_FILE = EMA_DATA_DIR / "login_attempts.json"
RESET_TOKENS_FILE = EMA_DATA_DIR / "reset_tokens.json"
WECHAT_SESSIONS_FILE = EMA_DATA_DIR / "wechat_sessions.json"
WECHAT_BINDINGS_FILE = EMA_DATA_DIR / "wechat_bindings.json"

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15
WECHAT_QR_EXPIRE_SECONDS = 300

# _lj/_sj 已统一到 utils.load_json/save_json


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
    pws = load_json(ADMIN_PASSWORDS_FILE)
    pws[uid] = {"user_id":uid,"hash":h,"salt":s,"updated_at":datetime.now().isoformat()}
    save_json(ADMIN_PASSWORDS_FILE, pws)

def verify_admin_password(uid: str, pw: str) -> bool:
    r = load_json(ADMIN_PASSWORDS_FILE).get(uid)
    if not r: return False
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), r["salt"].encode(), 100000).hex() == r["hash"]

def boss_login_without_admin_pw(username: str, password: str) -> Dict:
    from auth import login_user
    r = login_user(username, password)
    return {"success":True,"access_token":r.get("access_token"),"refresh_token":r.get("refresh_token"),"user":r,"is_boss":(r.get("role")=="super_admin"),"require_admin_pw":False}


# ── 登录安全 ────────────────────────────────────────────────

def check_login_attempt(ip: str, user: str) -> Dict:
    a = load_json(LOGIN_ATTEMPTS_FILE); k = f"{ip}:{user}"; now = time.time()
    r = a.get(k, {"count":0,"first_at":now,"locked_until":0})
    if r.get("locked_until",0) > now:
        lt = datetime.fromtimestamp(r["locked_until"])
        return {"allowed":False,"remaining":0,"locked_until":lt.isoformat(),"message":f"账户已锁定，请{lt.strftime('%H:%M')}后重试"}
    if now - r.get("first_at",now) > LOGIN_LOCKOUT_MINUTES*60:
        r = {"count":0,"first_at":now,"locked_until":0}
    r["count"] += 1; a[k] = r
    if r["count"] >= MAX_LOGIN_ATTEMPTS:
        r["locked_until"] = now + LOGIN_LOCKOUT_MINUTES*60; a[k] = r
        save_json(LOGIN_ATTEMPTS_FILE, a)
        return {"allowed":False,"remaining":0,"locked_until":datetime.fromtimestamp(r["locked_until"]).isoformat(),"message":f"尝试次数过多，已锁定{LOGIN_LOCKOUT_MINUTES}分钟"}
    save_json(LOGIN_ATTEMPTS_FILE, a)
    return {"allowed":True,"remaining":MAX_LOGIN_ATTEMPTS-r["count"],"locked_until":None}

def reset_login_attempts(ip: str, user: str):
    a = load_json(LOGIN_ATTEMPTS_FILE); k = f"{ip}:{user}"
    if k in a: del a[k]; save_json(LOGIN_ATTEMPTS_FILE, a)

# ── 微信扫码登录（配置驱动）────────────────────────────────
# 模式切换：设置环境变量 WECHAT_MODE=real 启用真实微信API
# 默认 mock 模式：本地生成二维码 + 自动推进状态（演示用）

import logging as _log
_wechat_log = _log.getLogger("wechat")

# ── 微信配置 ────────────────────────────────────────────────
# 模拟模式（默认）：无需任何配置，本地生成二维码
# 真实模式：需要填写以下配置，并设置 WECHAT_MODE=real
_WECHAT_MODE = os.environ.get("WECHAT_MODE", "mock")  # "mock" | "real"

# 真实微信配置（WECHAT_MODE=real 时必填）
_WECHAT_APP_ID = os.environ.get("WECHAT_APP_ID", "")      # 小程序/公众号 AppID
_WECHAT_APP_SECRET = os.environ.get("WECHAT_APP_SECRET", "")  # 小程序/公众号 AppSecret
_WECHAT_REDIRECT_URI = os.environ.get("WECHAT_REDIRECT_URI", "")  # OAuth 回调地址

# ── 微信 API 常量 ───────────────────────────────────────────
_WECHAT_API_BASE = "https://api.weixin.qq.com"
_WECHAT_OAUTH_URL = "https://open.weixin.qq.com/connect/qrconnect"
_WECHAT_MINIAPP_SESSION_URL = f"{_WECHAT_API_BASE}/sns/jscode2session"


def _wechat_api(endpoint: str, params: dict) -> dict:
    """调用真实微信 API"""
    import urllib.request, urllib.parse
    url = f"{_WECHAT_API_BASE}{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EMA/3.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        _wechat_log.error(f"微信API调用失败: {endpoint} → {e}")
        return {"errcode": -1, "errmsg": str(e)}


def _generate_real_wechat_qr(mode: str, state: str) -> dict:
    """
    生成真实微信二维码（OAuth2.0 网页授权）
    流程：生成微信授权URL → 前端展示二维码 → 用户微信扫码 → 微信回调 → 后端换 openid
    """
    if not _WECHAT_APP_ID:
        return {"state": state, "qr_base64": "", "auth_url": "", "error": "未配置 WECHAT_APP_ID"}

    # 微信 OAuth 授权 URL（网页扫码登录）
    import urllib.parse
    params = {
        "appid": _WECHAT_APP_ID,
        "redirect_uri": _WECHAT_REDIRECT_URI or f"https://{os.environ.get('EMA_HOST', 'localhost:6189')}/api/v1/auth/wechat-callback",
        "response_type": "code",
        "scope": "snsapi_login",  # 扫码登录
        "state": state,
    }
    auth_url = f"{_WECHAT_OAUTH_URL}?{urllib.parse.urlencode(params)}#wechat_redirect"

    # 生成二维码图片
    try:
        import qrcode, io, base64
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(auth_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        qr_b64 = ""

    return {"state": state, "qr_base64": qr_b64, "auth_url": auth_url, "mode": mode}


def _generate_mock_wechat_qr(mode: str, state: str) -> dict:
    """生成模拟微信二维码（演示用，无需微信账号）"""
    try:
        import qrcode, io, base64
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(f"ema://wechat-{mode}?state={state}&t={int(time.time())}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        qr_b64 = ""
    return {"state": state, "qr_base64": qr_b64, "auth_url": "", "mode": mode}


def generate_wechat_qr(mode: str = "login") -> dict:
    """
    生成微信登录二维码
    mode: "login"(扫码登录) / "bind"(绑定微信)
    返回: {state, qr_base64, auth_url, mode, expires_in}
    """
    state = secrets.token_hex(16)

    if _WECHAT_MODE == "real":
        result = _generate_real_wechat_qr(mode, state)
    else:
        result = _generate_mock_wechat_qr(mode, state)

    # 保存会话
    sessions = load_json(WECHAT_SESSIONS_FILE)
    sessions[state] = {
        "state": state,
        "mode": mode,
        "status": "pending",
        "created_at": time.time(),
        "expires_at": time.time() + WECHAT_QR_EXPIRE_SECONDS,
        "user_id": None,
        "access_token": None,
        "openid": None,
        "wx_code": None,  # 微信回调的 code（真实模式）
    }
    save_json(WECHAT_SESSIONS_FILE, sessions)

    result["expires_in"] = WECHAT_QR_EXPIRE_SECONDS
    _wechat_log.info(f"生成微信二维码: mode={mode}, state={state[:8]}..., mode_config={_WECHAT_MODE}")
    return result


def wechat_poll_status(state: str) -> dict:
    """
    轮询扫码状态
    模拟模式：5秒自动 scanned → 7秒自动 confirmed
    真实模式：等待微信回调后状态变为 confirmed
    """
    sessions = load_json(WECHAT_SESSIONS_FILE)
    s = sessions.get(state)
    if not s:
        return {"success": False, "status": "expired", "message": "会话不存在"}

    if time.time() > s.get("expires_at", 0):
        s["status"] = "expired"
        save_json(WECHAT_SESSIONS_FILE, sessions)
        return {"success": True, "status": "expired", "message": "二维码已过期"}

    # 模拟模式：自动推进状态
    if _WECHAT_MODE == "mock":
        elapsed = time.time() - s["created_at"]
        if s["status"] == "pending" and elapsed > 5:
            s["status"] = "scanned"
            save_json(WECHAT_SESSIONS_FILE, sessions)
            _wechat_log.info(f"模拟扫码: state={state[:8]}... → scanned")
        if s["status"] == "scanned" and elapsed > 7:
            s["status"] = "confirmed"
            save_json(WECHAT_SESSIONS_FILE, sessions)
            _wechat_log.info(f"模拟确认: state={state[:8]}... → confirmed")

    # 已扫描
    if s["status"] == "scanned":
        return {"success": True, "status": "scanned", "mode": s.get("mode", "login")}

    # 已确认 → 执行登录
    if s["status"] == "confirmed":
        mode = s.get("mode", "login")

        # 绑定模式
        if mode == "bind":
            return {"success": True, "status": "confirmed", "mode": "bind", "state": state}

        # 登录模式：检查是否已绑定微信
        bindings = load_json(WECHAT_BINDINGS_FILE)
        # 模拟模式：用固定测试 openid（真实模式从微信API获取）
        openid = s.get("openid") or ("wx_mock_user_001" if _WECHAT_MODE == "mock" else f"wx_{state[-16:]}")

        # 查找已绑定的用户
        for oid, b in bindings.items():
            if oid == openid or b.get("state") == state:
                return _do_wechat_login(b.get("user_id", ""), state)

        # 未绑定 → 返回 need_register（前端引导注册）
        return {"success": True, "status": "need_register", "openid": openid, "state": state}

    # 等待中
    return {"success": True, "status": "pending", "message": "等待扫码..."}


def wechat_callback(code: str, state: str) -> dict:
    """
    微信 OAuth 回调处理（真实模式）
    微信用户扫码确认后，微信服务器会回调此接口
    参数：
      code: 微信授权码（用于换 openid）
      state: 会话 state
    返回：{success, openid, access_token, user}
    """
    sessions = load_json(WECHAT_SESSIONS_FILE)
    s = sessions.get(state)
    if not s:
        return {"success": False, "error": "会话不存在或已过期"}

    if _WECHAT_MODE != "real":
        return {"success": False, "error": "当前为模拟模式，不支持微信回调"}

    # 用 code 换 access_token + openid
    resp = _wechat_api("/sns/oauth2/access_token", {
        "appid": _WECHAT_APP_ID,
        "secret": _WECHAT_APP_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    })

    if "errcode" in resp:
        _wechat_log.error(f"微信换票失败: {resp}")
        return {"success": False, "error": resp.get("errmsg", "微信授权失败")}

    openid = resp.get("openid")
    if not openid:
        return {"success": False, "error": "未获取到 openid"}

    # 更新会话
    s["status"] = "confirmed"
    s["openid"] = openid
    s["wx_code"] = code
    save_json(WECHAT_SESSIONS_FILE, sessions)

    # 检查是否已绑定
    bindings = load_json(WECHAT_BINDINGS_FILE)
    if openid in bindings:
        # 已绑定 → 直接登录
        b = bindings[openid]
        return _do_wechat_login(b["user_id"], state)

    # 未绑定 → 返回 need_register
    return {"success": True, "status": "need_register", "openid": openid, "state": state}


def wechat_bind_account(state: str, user_id: str, username: str) -> dict:
    """
    微信绑定已有账号
    流程：用户扫码(绑定模式) → 输入账号密码 → 验证 → 绑定
    """
    bindings = load_json(WECHAT_BINDINGS_FILE)
    sessions = load_json(WECHAT_SESSIONS_FILE)
    s = sessions.get(state, {})
    openid = s.get("openid") or ("wx_mock_user_001" if _WECHAT_MODE == "mock" else f"wx_{state[-16:]}")

    bindings[openid] = {
        "openid": openid,
        "user_id": user_id,
        "username": username,
        "bound_at": datetime.now().isoformat(),
    }
    save_json(WECHAT_BINDINGS_FILE, bindings)
    _wechat_log.info(f"微信绑定: openid={openid[:12]}... → user={username}")

    return {
        "success": True,
        "message": "微信绑定成功，以后可直接扫码登录",
        "openid": openid,
    }


def wechat_register_and_bind(state: str, username: str, password: str, email: str = "") -> dict:
    """
    新用户扫码注册 + 绑定微信
    流程：扫码 → 填写注册信息 → 创建账号 → 绑定微信 → 自动登录
    """
    from auth import register_user, get_user_tenant, create_access_token

    try:
        user = register_user(username, password, email)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    bindings = load_json(WECHAT_BINDINGS_FILE)
    sessions = load_json(WECHAT_SESSIONS_FILE)
    s = sessions.get(state, {})
    openid = s.get("openid") or ("wx_mock_user_001" if _WECHAT_MODE == "mock" else f"wx_{state[-16:]}")

    bindings[openid] = {
        "openid": openid,
        "user_id": user["user_id"],
        "username": username,
        "bound_at": datetime.now().isoformat(),
    }
    save_json(WECHAT_BINDINGS_FILE, bindings)

    # 回写会话
    if state in sessions:
        sessions[state]["user_id"] = user["user_id"]
        sessions[state]["access_token"] = user.get("access_token")
        save_json(WECHAT_SESSIONS_FILE, sessions)

    _wechat_log.info(f"微信注册+绑定: openid={openid[:12]}... → user={username}")

    return {
        "success": True,
        "access_token": user.get("access_token"),
        "user": user,
        "message": "注册成功！微信已绑定",
    }


def _do_wechat_login(user_id: str, state: str) -> Dict:
    """已绑定用户 → 直接登录"""
    from auth import get_user, get_user_tenant, create_access_token, create_refresh_token
    user = get_user(user_id)
    if not user: return {"success":False,"status":"error","message":"用户不存在"}
    ti = get_user_tenant(user_id)
    token = create_access_token(user_id, user["username"], ti.get("role","editor"))
    sessions = load_json(WECHAT_SESSIONS_FILE)
    if state in sessions:
        sessions[state]["access_token"] = token; sessions[state]["user_id"] = user_id
        save_json(WECHAT_SESSIONS_FILE, sessions)
    return {"success":True,"status":"confirmed","access_token":token,"user":{"user_id":user_id,"username":user["username"],"role":ti.get("role","editor"),"tenant_id":ti.get("tenant_id",""),"tenant_name":ti.get("tenant_name","")},"is_boss":(ti.get("role")=="super_admin")}


# ── 密码找回 ────────────────────────────────────────────────

def request_password_reset(username: str, email: str) -> Dict:
    from auth import USERS_FILE
    users = load_json(USERS_FILE)
    found = next((u for u in users.values() if u.get("username")==username and u.get("email")==email), None)
    if not found: return {"success":False,"message":"用户名或邮箱不匹配"}
    tokens = load_json(RESET_TOKENS_FILE)
    t = secrets.token_hex(16)
    tokens[t] = {"user_id":found["user_id"],"username":username,"created_at":datetime.now().isoformat(),"expires_at":(datetime.now()+timedelta(minutes=30)).isoformat(),"used":False}
    save_json(RESET_TOKENS_FILE, tokens)
    # 发送重置邮件
    try:
        from email_sender import send_password_reset_email
        email_sent = send_password_reset_email(email, username, t)
        import logging
        logging.info(f"邮件发送结果: {email_sent}")
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
    tokens = load_json(RESET_TOKENS_FILE); r = tokens.get(token)
    if not r or r.get("used") or datetime.now()>datetime.fromisoformat(r["expires_at"]):
        return {"success":False,"message":"重置链接无效或已过期"}
    if not validate_password_strength(new_pw):
        return {"success":False,"message":"密码需至少8位，含大小写字母和数字"}
    from auth import USERS_FILE, hash_password
    users = load_json(USERS_FILE); u = users.get(r["user_id"])
    if not u: return {"success":False,"message":"用户不存在"}
    h, s = hash_password(new_pw); u["password_hash"]=h; u["salt"]=s
    save_json(USERS_FILE, users); r["used"]=True
    save_json(RESET_TOKENS_FILE, tokens)
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
        delta = timedelta(minutes=int(expires_minutes))
    header = _jwt_b64encode(json.dumps({"alg": _JWT_ALGORITHM, "typ": "JWT"}).encode())
    now = datetime.now(timezone.utc)
    payload_data = {
        "sub": user_id, "username": username, "role": role,
        "iat": int(now.timestamp()), "exp": int((now + delta).timestamp()),
    }
    payload = _jwt_b64encode(json.dumps(payload_data).encode())
    sig_input = f"{header}.{payload}"
    signature = _jwt_b64encode(hmac.new(_JWT_SECRET.encode(), sig_input.encode(), "sha256").digest())
    return f"{sig_input}.{signature}"


def create_refresh_token(user_id: str, expires_days: int = 30) -> str:
    """创建 JWT refresh token"""
    header = _jwt_b64encode(json.dumps({"alg": _JWT_ALGORITHM, "typ": "JWT"}).encode())
    now = datetime.now(timezone.utc)
    payload_data = {
        "sub": user_id, "type": "refresh",
        "iat": int(now.timestamp()), "exp": int((now + timedelta(days=expires_days)).timestamp()),
    }
    payload = _jwt_b64encode(json.dumps(payload_data).encode())
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
        payload = json.loads(_jwt_b64decode(parts[1]))
        if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
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
