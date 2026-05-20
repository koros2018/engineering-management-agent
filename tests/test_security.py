"""
tests/test_security.py
安全审计模块单元测试

测试范围:
- JWT 强度检查 (check_jwt_strength)
- 文件上传安全验证 (validate_upload)
- 文件名清洗 (sanitize_filename)
- XSS / SQL注入防护 (sanitize_html / sanitize_sql_input)
- 速率限制 (check_rate_limit)
- 安全事件日志 (log_security_event / get_security_audit)
- 安全基线检查 (run_security_baseline_check)
"""

import pytest
import json
import time
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import security


@pytest.fixture
def tmp_data_dir():
    """隔离数据目录"""
    d = tempfile.mkdtemp(prefix="ema_test_security_")
    orig_audit = security.AUDIT_LOG_FILE
    orig_rate = security.RATE_LIMIT_FILE
    orig_block = security.BLOCKLIST_FILE
    security.AUDIT_LOG_FILE = Path(d) / "security_audit.json"
    security.RATE_LIMIT_FILE = Path(d) / "rate_limit.json"
    security.BLOCKLIST_FILE = Path(d) / "ip_blocklist.json"
    yield d
    security.AUDIT_LOG_FILE = orig_audit
    security.RATE_LIMIT_FILE = orig_rate
    security.BLOCKLIST_FILE = orig_block
    shutil.rmtree(d, ignore_errors=True)


# ── JWT 安全测试 ────────────────────────────────────────────────

class TestJWTCheck:
    """JWT 强度检查"""

    def test_weak_algorithm_hs256(self):
        import base64
        h = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        p = base64.urlsafe_b64encode(json.dumps({"sub": "test", "exp": int(time.time()) + 3600}).encode()).decode().rstrip("=")
        token = f"{h}.{p}.fakesig"

        result = security.check_jwt_strength(token)
        assert result["algorithm"] == "HS256"
        assert result["valid"] is True  # not expired, just weak

    def test_none_algorithm(self):
        import base64
        h = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
        p = base64.urlsafe_b64encode(json.dumps({"sub": "test"}).encode()).decode().rstrip("=")
        token = f"{h}.{p}.fakesig"

        result = security.check_jwt_strength(token)
        assert result["weak_signature"] is True
        assert result["algorithm"] == "none"

    def test_expired_jwt(self):
        import base64
        h = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        p = base64.urlsafe_b64encode(json.dumps({"sub": "test", "exp": int(time.time()) - 3600}).encode()).decode().rstrip("=")
        token = f"{h}.{p}.fakesig"

        result = security.check_jwt_strength(token)
        assert result["expired"] is True

    def test_long_expiry_jwt(self):
        import base64
        h = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        p = base64.urlsafe_b64encode(json.dumps({"sub": "test", "exp": int(time.time()) + 86400 * 30}).encode()).decode().rstrip("=")
        token = f"{h}.{p}.fakesig"

        result = security.check_jwt_strength(token)
        assert any("过长" in r for r in result.get("recommendations", []))

    def test_malformed_jwt(self):
        result = security.check_jwt_strength("not.valid")
        assert "recommendations" in result

    def test_valid_jwt_no_issues(self):
        import base64
        h = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        p = base64.urlsafe_b64encode(json.dumps({"sub": "test", "exp": int(time.time()) + 3600}).encode()).decode().rstrip("=")
        token = f"{h}.{p}.fakesig"

        result = security.check_jwt_strength(token)
        assert result["valid"] is True


# ── 文件上传安全测试 ────────────────────────────────────────────

class TestFileUploadValidation:
    """文件上传安全验证"""

    def test_valid_dxf_upload(self):
        content = b"0\nSECTION\n2\nHEADER"  # DXF 魔术数字
        result = security.validate_upload("test.dxf", content)
        assert result["safe"] is True

    def test_valid_pdf_upload(self):
        content = b"%PDF-1.4\n%..."  # PDF 魔术数字
        result = security.validate_upload("doc.pdf", content)
        assert result["safe"] is True

    def test_invalid_magic_number(self):
        """文件扩展名与魔数不匹配"""
        content = b"THIS IS PLAIN TEXT"  # 不是有效的 DXF 魔术数字
        result = security.validate_upload("fake.dxf", content)
        assert result["safe"] is False
        assert any("魔数" in i for i in result["issues"])

    def test_oversized_file(self):
        large = b"x" * (security.MAX_FILE_SIZE_MB * 1024 * 1024 + 1)
        result = security.validate_upload("large.pdf", large)
        assert result["safe"] is False
        assert any("过大" in i for i in result["issues"])

    def test_unsupported_extension(self):
        result = security.validate_upload("virus.exe", b"")
        assert result["safe"] is False
        assert any("不支持" in i for i in result["issues"])

    def test_path_traversal(self):
        content = b"%PDF-1.4"
        result = security.validate_upload("../etc/passwd.pdf", content)
        assert any("路径遍历" in i or "危险字符" in i for i in result["issues"])

    def test_file_size_reported(self):
        content = b"0\nSECTION\n"
        result = security.validate_upload("test.dxf", content)
        assert "file_size_mb" in result


# ── 文件名清洗测试 ──────────────────────────────────────────────

class TestFilenameSanitization:
    """文件名清洗"""

    def test_path_separator_removed(self):
        result = security.sanitize_filename("a/b\\test.pdf")
        assert "/" not in result
        assert "\\" not in result

    def test_dangerous_chars_replaced(self):
        result = security.sanitize_filename("test<file>.pdf")
        assert "<" not in result
        assert ">" not in result

    def test_trailing_spaces_removed(self):
        result = security.sanitize_filename(" file.pdf ")
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_empty_filename(self):
        result = security.sanitize_filename("")
        assert result == "unnamed"


# ── XSS / 注入防护测试 ──────────────────────────────────────────

class TestXSSSQLInjection:
    """XSS / SQL注入防护"""

    def test_sanitize_html_basic(self):
        assert security.sanitize_html("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"

    def test_sanitize_html_ampersand(self):
        result = security.sanitize_html("price > 0 && price < 100")
        assert "&gt;" in result
        assert "&lt;" in result
        assert "&amp;&amp;" in result

    def test_sanitize_html_safe_text(self):
        result = security.sanitize_html("Hello, 世界")
        assert result == "Hello, 世界"

    def test_sanitize_html_non_string(self):
        result = security.sanitize_html(123)
        assert result == "123"

    def test_sanitize_sql_input_no_crash(self):
        result = security.sanitize_sql_input("SELECT * FROM users; DROP TABLE users;--")
        assert isinstance(result, str)


# ── 速率限制测试 ────────────────────────────────────────────────

class TestRateLimit:
    """速率限制"""

    def test_first_request_allowed(self, tmp_data_dir):
        result = security.check_rate_limit("192.168.1.1")
        assert result["allowed"] is True
        assert result["blocked"] is False

    def test_normal_rate_allowed(self, tmp_data_dir):
        for _ in range(10):
            result = security.check_rate_limit("192.168.1.2")
        assert result["allowed"] is True
        assert result["blocked"] is False

    def test_block_threshold_reached(self, tmp_data_dir):
        # 发送超过 BLOCK_THRESHOLD 的请求
        for _ in range(security.BLOCK_THRESHOLD + 1):
            result = security.check_rate_limit("192.168.1.3")
        assert result["blocked"] is True
        assert result["allowed"] is False

    def test_different_ips_independent(self, tmp_data_dir):
        for _ in range(10):
            security.check_rate_limit("10.0.0.1")

        # 另一个IP不应受影响
        result = security.check_rate_limit("10.0.0.2")
        assert result["blocked"] is False

    def test_returns_remaining_count(self, tmp_data_dir):
        result = security.check_rate_limit("192.168.1.5")
        assert "remaining" in result
        assert "reset_at" in result


# ── 审计日志测试 ────────────────────────────────────────────────

class TestSecurityAudit:
    """安全审计日志"""

    def test_log_event(self, tmp_data_dir):
        event = security.log_security_event(
            "login_failed", "medium", "密码错误", "10.0.0.1", "user-1"
        )
        assert event["event_type"] == "login_failed"
        assert event["severity"] == "medium"

    def test_get_audit_logs(self, tmp_data_dir):
        security.log_security_event("rate_limit", "high", "IP拉黑", "1.2.3.4", None)
        security.log_security_event("upload", "low", "上传成功", "4.3.2.1", "u2")

        logs = security.get_security_audit()
        assert len(logs) == 2

    def test_get_audit_by_severity(self, tmp_data_dir):
        security.log_security_event("test1", "low", "low event", "1.1.1.1")
        security.log_security_event("test2", "high", "high event", "2.2.2.2")

        low_logs = security.get_security_audit(severity="low")
        assert len(low_logs) == 1
        assert low_logs[0]["severity"] == "low"

    def test_get_audit_limit(self, tmp_data_dir):
        for i in range(10):
            security.log_security_event(f"event_{i}", "low", f"detail {i}", "1.1.1.1")
        logs = security.get_security_audit(limit=5)
        assert len(logs) == 5


# ── 安全基线测试 ────────────────────────────────────────────────

class TestSecurityBaseline:
    """安全基线检查"""

    def test_baseline_returns_score(self, tmp_data_dir):
        result = security.run_security_baseline_check()
        assert "score" in result
        assert "checks" in result
        # 应有 JWT / 文件上传 / 速率限制 / CORS 检查
        assert "jwt_config" in result["checks"]
        assert "file_upload" in result["checks"]
        assert "rate_limit" in result["checks"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
