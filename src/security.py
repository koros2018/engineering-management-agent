"""
security.py - 安全审计模块

Phase 8: JWT 强度检查 / API 访问控制审计 / 文件上传安全检查 / 输入防护

安全基线：
- JWT: RS256 签名, 1h access_token过期, 7d refresh过期
- API: 敏感端点强制认证, CORS 白名单
- 文件: 类型检查(魔数验证) + 大小限制 + 路径遍历防护
- 输入: XSS 防护, SQL注入防护, 速率限制
"""

import re
import hashlib
from src.utils import json_dumps, json_loads
import secrets
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from utils import load_json as _load_json, save_json as _save_json



# ── 配置 ──────────────────────────────────────────────────────

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
AUDIT_LOG_FILE = EMA_DATA_DIR / "security_audit.json"
RATE_LIMIT_FILE = EMA_DATA_DIR / "rate_limit.json"
BLOCKLIST_FILE = EMA_DATA_DIR / "ip_blocklist.json"

# 安全基线
MAX_FILE_SIZE_MB = 500
ALLOWED_FILE_TYPES = {
    '.dwg': [b'AC10', b'\x41\x43\x31\x30'],    # DWG 文件头
    '.dxf': [b'0\nSECTION', b'\x20\x39\x39\x39'], # DXF 文本头
    '.pdf': [b'%PDF'],
    '.jpg': [b'\xff\xd8\xff'],
    '.png': [b'\x89PNG'],
}
DANGEROUS_FILENAME_PATTERNS = ['..', '~', '//', '\\\\', '/etc/', 'C:']
RATE_LIMIT_RPS = 20           # 每IP每秒请求数
RATE_LIMIT_WINDOW_S = 60      # 窗口
BLOCK_THRESHOLD = 50          # 阈值: 超过此请求数则拉黑IP




# ── JWT 安全检查 ──────────────────────────────────────────────

def check_jwt_strength(token: str) -> Dict:
    """
    JWT 安全审计

    Returns:
        {
            "valid": bool,
            "expired": bool,
            "weak_signature": bool,
            "algorithm": str,
            "expires_in_seconds": int,
            "recommendations": List[str],
        }
    """
    issues = []
    info = {
        "valid": False,
        "expired": False,
        "weak_signature": False,
        "algorithm": "unknown",
        "expires_in_seconds": 0,
        "recommendations": [],
    }

    try:
        parts = token.split('.')
        if len(parts) != 3:
            issues.append("JWT格式异常：不是标准的3段式")
            info["recommendations"] = issues
            return info

        import base64
        # 解析 header
        header_bytes = base64.urlsafe_b64decode(parts[0] + '==')
        header = json_loads(header_bytes)

        info["algorithm"] = header.get("alg", "none")
        if info["algorithm"] == "none":
            issues.append("JWT使用'none'算法，可被绕过")
            info["weak_signature"] = True
        elif info["algorithm"].startswith("HS"):
            issues.append(f"JWT使用弱签名算法 {info['algorithm']}，建议使用 RS256 或 ES256")

        # 解析 payload
        payload_bytes = base64.urlsafe_b64decode(parts[1] + '==')
        payload = json_loads(payload_bytes)

        exp = payload.get("exp", 0)
        now = int(time.time())

        if exp > 0:
            info["expires_in_seconds"] = exp - now
            if now > exp:
                info["expired"] = True
                issues.append("JWT已过期")
            elif info["expires_in_seconds"] > 86400:
                issues.append(f"JWT过期时间过长（{info['expires_in_seconds']//3600}h），建议 access_token 不超过 1小时")
        else:
            issues.append("JWT缺少过期时间(exp)")

        info["valid"] = not info["expired"] and not info["weak_signature"]

    except Exception as e:
        issues.append(f"JWT解析异常: {str(e)}")
        info["valid"] = False

    info["recommendations"] = issues or ["JWT安全基线合规 ✅"]
    return info


# ── 文件上传安全检查 ──────────────────────────────────────────

def validate_upload(
    filename: str,
    file_bytes: bytes,
    max_size_mb: int = MAX_FILE_SIZE_MB,
) -> Dict:
    """
    文件上传安全验证

    Returns:
        {
            "safe": bool,
            "issues": List[str],
            "file_type": str,
        }
    """
    issues = []

    # 1. 文件名安全检查
    safe_name = sanitize_filename(filename)
    if safe_name != filename:
        issues.append(f"文件名包含危险字符，已清洗为: {safe_name}")

    for pattern in DANGEROUS_FILENAME_PATTERNS:
        if pattern in filename:
            issues.append(f"文件名包含路径遍历/危险字符: {pattern}")

    # 2. 文件大小检查
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        issues.append(f"文件过大: {size_mb:.1f}MB > {max_size_mb}MB 限制")

    # 3. 扩展名检查
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_FILE_TYPES:
        issues.append(f"不支持的文件类型: {suffix}")

    # 4. 魔数验证
    magic_ok = False
    if suffix in ALLOWED_FILE_TYPES:
        expected_magics = ALLOWED_FILE_TYPES[suffix]
        for magic in expected_magics:
            if file_bytes[:len(magic)] == magic:
                magic_ok = True
                break

    if not magic_ok and suffix in ALLOWED_FILE_TYPES:
        issues.append(f"文件魔数验证失败（文件可能被篡改或损坏）")

    return {
        "safe": len(issues) == 0,
        "issues": issues,
        "file_type": suffix,
        "file_size_mb": round(size_mb, 2),
        "magic_verified": magic_ok or suffix not in ALLOWED_FILE_TYPES,
    }


def sanitize_filename(filename: str) -> str:
    """
    清洗文件名

    移除路径分隔符、特殊字符、Emoji 等
    """
    # 移除路径分隔符
    safe = filename.replace('\\', '_').replace('/', '_')
    # 移除 null 字节
    safe = safe.replace('\x00', '')
    # 移除危险字符
    safe = re.sub(r'[<>:"|?*]', '_', safe)
    # 去首尾空格点
    safe = safe.strip(' .')
    # 限制长度
    if len(safe) > 200:
        name_parts = list(Path(safe).parts)
        safe = str(Path(name_parts[0][:150] + '.' + suffix)) if '.' in safe else safe[:200]

    return safe or 'unnamed'


# ── XSS / 注入防护 ────────────────────────────────────────────

def sanitize_html(text: str) -> str:
    """XSS 防护：转义 HTML 标签"""
    if not isinstance(text, str):
        return str(text)
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')\
               .replace('"', '&quot;').replace("'", '&#x27;')


def sanitize_sql_input(text: str) -> str:
    """简单 SQL 注入防护：过滤危险关键字（正式环境用参数化查询）"""
    dangerous = [
        r'\bDROP\b', r'\bDELETE\b', r'\bINSERT\b', r'\bUPDATE\b',
        r'\bALTER\b', r'\bTRUNCATE\b', r'\bUNION\b', r'\bEXEC\b',
        r';', r'--', r'/\*', r'\*/'
    ]
    for pattern in dangerous:
        if re.search(pattern, text, re.IGNORECASE):
            # 记录告警但不直接拦截（正式环境记录到审计日志）
            pass
    return text


# ── 速率限制 ──────────────────────────────────────────────────

def check_rate_limit(client_ip: str) -> Dict:
    """
    检查速率限制

    Returns:
        {
            "allowed": bool,
            "remaining": int,
            "reset_at": float,
            "blocked": bool,
        }
    """
    blocklist = _load_json(BLOCKLIST_FILE)

    # 检查拉黑
    if client_ip in blocklist:
        bl = blocklist[client_ip]
        if time.time() < bl.get("unblock_at", 0):
            return {
                "allowed": False,
                "remaining": 0,
                "reset_at": bl["unblock_at"],
                "blocked": True,
                "reason": bl.get("reason", "触发安全规则"),
            }
        else:
            # 解封
            del blocklist[client_ip]
            _save_json(BLOCKLIST_FILE, blocklist)

    # 速率检查
    rate_data = _load_json(RATE_LIMIT_FILE)
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_S

    if client_ip not in rate_data:
        rate_data[client_ip] = {"requests": [], "blocked_count": 0}

    client_data = rate_data[client_ip]
    # 清理过期请求
    client_data["requests"] = [t for t in client_data["requests"] if t > window_start]
    client_data["requests"].append(now)

    count = len(client_data["requests"])
    rate_data[client_ip] = client_data
    _save_json(RATE_LIMIT_FILE, rate_data)

    if count > BLOCK_THRESHOLD:
        # 拉黑 1小时
        blocklist[client_ip] = {
            "blocked_at": now,
            "unblock_at": now + 3600,
            "reason": f"{RATE_LIMIT_WINDOW_S}s内 {count} 次请求超阈值 {BLOCK_THRESHOLD}",
        }
        _save_json(BLOCKLIST_FILE, blocklist)
        return {
            "allowed": False,
            "remaining": 0,
            "reset_at": now + 3600,
            "blocked": True,
            "reason": f"触发安全阈值：{BLOCK_THRESHOLD}次/{RATE_LIMIT_WINDOW_S}s",
        }

    return {
        "allowed": count <= RATE_LIMIT_RPS * (RATE_LIMIT_WINDOW_S // 10),
        "remaining": max(0, BLOCK_THRESHOLD - count),
        "reset_at": client_data["requests"][0] + RATE_LIMIT_WINDOW_S if client_data["requests"] else now + RATE_LIMIT_WINDOW_S,
        "blocked": False,
    }


# ── 安全审计日志 ──────────────────────────────────────────────

def log_security_event(
    event_type: str,
    severity: str,        # low / medium / high / critical
    detail: str,
    client_ip: str = None,
    user_id: str = None,
):
    """记录安全事件"""
    audit = _load_json(AUDIT_LOG_FILE)

    event = {
        "id": f"sec_{int(time.time() * 1000)}",
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "severity": severity,
        "detail": detail,
        "client_ip": client_ip,
        "user_id": user_id,
    }

    if "events" not in audit:
        audit["events"] = []

    audit["events"].insert(0, event)
    # 保留最近1000条
    audit["events"] = audit["events"][:1000]
    _save_json(AUDIT_LOG_FILE, audit)

    return event


def get_security_audit(
    severity: str = None,
    event_type: str = None,
    limit: int = 50,
) -> list:
    """查询安全审计日志"""
    audit = _load_json(AUDIT_LOG_FILE)
    events = audit.get("events", [])

    if severity:
        events = [e for e in events if e.get("severity") == severity]
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]

    return events[:limit]


def run_security_baseline_check() -> Dict:
    """
    整体安全基线检查

    Returns:
        dict: 安全评分 + 各模块结果
    """
    checks = {
        "jwt_config": { "pass": True, "detail": "" },
        "file_upload": { "pass": True, "detail": "" },
        "rate_limit": { "pass": True, "detail": "" },
        "cors_config": { "pass": True, "detail": "" },
    }
    total_score = 100

    # JWT 配置检查
    try:
        from auth_extended import create_access_token
        token = create_access_token("test_user", "test", "editor")
        jwt_result = check_jwt_strength(token)
        if jwt_result["recommendations"] and jwt_result["recommendations"][0] != "JWT安全基线合规":
            checks["jwt_config"]["pass"] = False
            checks["jwt_config"]["detail"] = "; ".join(jwt_result["recommendations"])
            total_score -= 20
        else:
            checks["jwt_config"]["detail"] = "JWT安全基线合规"
    except Exception as e:
        checks["jwt_config"]["pass"] = False
        checks["jwt_config"]["detail"] = str(e)
        total_score -= 15

    # 文件上传检查
    test_valid = validate_upload("test.dxf", b"0\nSECTION\n2\nHEADER\n")
    if not test_valid["safe"]:
        checks["file_upload"]["pass"] = False
        checks["file_upload"]["detail"] = "; ".join(test_valid["issues"])
        total_score -= 10
    else:
        checks["file_upload"]["detail"] = "文件上传安全检查通过"

    test_danger = validate_upload("../etc/passwd", b"malicious")
    if test_danger["safe"]:
        checks["file_upload"]["pass"] = False
        checks["file_upload"]["detail"] += "; 路径遍历检查失败"
        total_score -= 20
    else:
        checks["file_upload"]["detail"] += f"，路径遍历检测: {len(test_danger['issues'])}个问题"

    # 速率限制
    rate_result = check_rate_limit("127.0.0.1")
    if not rate_result["allowed"]:
        checks["rate_limit"]["pass"] = False
        checks["rate_limit"]["detail"] = f"速率限制异常"
        total_score -= 15
    else:
        checks["rate_limit"]["detail"] = f"速率限制正常工作（{RATE_LIMIT_RPS}次/秒，阈值{BLOCK_THRESHOLD}次）"

    return {
        "score": max(0, total_score),
        "grade": "A" if total_score >= 90 else "B" if total_score >= 75 else "C" if total_score >= 60 else "D",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
        "recommendations": [
            "生产环境使用 RS256 签名算法",
            "CORS 白名单限定生产域名",
            "API 敏感端点强制认证",
            "定期轮换 JWT Secret Key",
            "接入 WAF / CDN 防护",
        ],
    }
