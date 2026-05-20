"""
tests/test_auth.py
认证模块单元测试

测试范围:
- 密码哈希/验证 (hash_password / verify_password)
- 用户注册 (register_user)
- 用户登录 (login_user)
- 租户管理 (create_tenant / get_tenant)
- Token刷新 (refresh_access_token)
- 用户查询 (get_user / get_user_tenant)
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from auth import (
    hash_password, verify_password, register_user, login_user,
    create_tenant, get_tenant, get_user, get_user_tenant,
    create_access_token, refresh_access_token, Role,
)


@pytest.fixture
def tmp_data_dir():
    d = tempfile.mkdtemp(prefix="ema_test_auth_")
    # Patch auth data dir
    import auth as auth_mod
    orig = auth_mod.EMA_DATA_DIR
    auth_mod.EMA_DATA_DIR = Path(d)
    auth_mod.USERS_FILE = Path(d) / "users.json"
    auth_mod.TENANTS_FILE = Path(d) / "tenants.json"
    auth_mod.TENANT_USERS_FILE = Path(d) / "tenant_users.json"
    yield d
    auth_mod.EMA_DATA_DIR = orig
    auth_mod.USERS_FILE = orig / "users.json"
    auth_mod.TENANTS_FILE = orig / "tenants.json"
    auth_mod.TENANT_USERS_FILE = orig / "tenant_users.json"
    shutil.rmtree(d, ignore_errors=True)


class TestPasswordHash:
    """密码哈希和验证"""

    def test_hash_and_verify(self):
        pwd_hash, salt = hash_password("MySecureP@ss123")
        assert verify_password("MySecureP@ss123", pwd_hash, salt) is True

    def test_wrong_password(self):
        pwd_hash, salt = hash_password("Correct123")
        assert verify_password("Wrong123", pwd_hash, salt) is False

    def test_case_sensitive(self):
        pwd_hash, salt = hash_password("Abcd1234")
        assert verify_password("abcd1234", pwd_hash, salt) is False

    def test_unique_salts(self):
        _, salt1 = hash_password("same_password")
        _, salt2 = hash_password("same_password")
        assert salt1 != salt2

    def test_hash_length(self):
        # SHA256 produces 64 hex chars
        pwd_hash, _ = hash_password("test")
        assert len(pwd_hash) == 64


class TestRegisterUser:
    """用户注册"""

    def test_register_basic(self, tmp_data_dir):
        result = register_user("newuser", "Abcd1234!", "test@test.com")
        assert result["username"] == "newuser"
        assert "access_token" in result

    def test_register_duplicate(self, tmp_data_dir):
        register_user("dup", "Abcd1234!", "a@a.com")
        with pytest.raises(ValueError, match="已存在"):
            register_user("dup", "Abcd1234!", "b@b.com")

    def test_get_user(self, tmp_data_dir):
        result = register_user("zhangsan", "Abcd1234!", "z@z.com")
        user = get_user(result["user_id"])
        assert user is not None
        assert user["username"] == "zhangsan"

    def test_get_nonexistent_user(self):
        assert get_user("user_fake") is None


class TestLogin:
    """登录功能"""

    def test_login_correct(self, tmp_data_dir):
        register_user("testlogin", "Abcd1234!", "t@t.com")
        result = login_user("testlogin", "Abcd1234!")
        assert "access_token" in result
        assert "refresh_token" in result

    def test_login_wrong_password(self, tmp_data_dir):
        register_user("testlogin2", "Abcd1234!", "t2@t.com")
        with pytest.raises(ValueError, match="用户名或密码错误"):
            login_user("testlogin2", "WrongPassword1!")

    def test_login_nonexistent_user(self, tmp_data_dir):
        with pytest.raises(ValueError, match="用户名或密码错误"):
            login_user("ghost_user", "anything")


class TestTokenRefresh:
    """Token刷新"""

    def test_token_create_and_verify(self):
        token = create_access_token("user_123", "testuser", "editor")
        assert token is not None
        # JWT 是三段式
        assert len(token.split(".")) == 3

    def test_token_with_custom_expiry(self):
        from datetime import timedelta
        token = create_access_token("user_456", "test", "admin", timedelta(minutes=5))
        assert token is not None

    def test_refresh_valid_token(self, tmp_data_dir):
        register_user("refreshtest", "Abcd1234!", "r@r.com")
        login_result = login_user("refreshtest", "Abcd1234!")
        refresh_token = login_result["refresh_token"]

        new_tokens = refresh_access_token(refresh_token)
        assert new_tokens is not None
        assert "access_token" in new_tokens

    def test_refresh_invalid_token(self, tmp_data_dir):
        result = refresh_access_token("invalid_refresh_token_string")
        assert result is None


class TestTenant:
    """多租户"""

    def test_create_tenant(self, tmp_data_dir):
        result = create_tenant("测试企业", "user_admin_1", "pro")
        assert "tenant_id" in result
        assert result["name"] == "测试企业"

    def test_get_tenant(self, tmp_data_dir):
        result = create_tenant("华建集团", "boss", "enterprise")
        tenant = get_tenant(result["tenant_id"])
        assert tenant is not None
        assert tenant["name"] == "华建集团"
        assert tenant["plan"] == "enterprise"

    def test_get_nonexistent_tenant(self):
        assert get_tenant("tenant_not_exist") is None

    def test_tenant_user_association(self, tmp_data_dir):
        result = register_user("tenantuser", "Abcd1234!", "tu@tu.com")
        tenant_info = get_user_tenant(result["user_id"])
        # 注册时自动创建default租户
        assert tenant_info is not None


class TestRoleSystem:
    """角色系统"""

    def test_roles_defined(self):
        assert Role.SUPER_ADMIN == "super_admin"
        assert Role.TENANT_ADMIN == "tenant_admin"
        assert Role.EDITOR == "editor"
        assert Role.VIEWER == "viewer"

    def test_token_contains_role(self):
        token = create_access_token("user_789", "roletest", "super_admin")
        import base64, json
        payload_b64 = token.split(".")[1]
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "==="))
        assert payload["role"] == "super_admin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
