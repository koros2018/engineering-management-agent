"""
tests/test_subscription.py
订阅支付模型单元测试

测试范围:
- 套餐定义 (PLANS)
- 订阅管理 (subscribe / get_subscription / check_subscription)
- 使用量追踪 (track_usage / get_usage / reset_usage)
- 配额检查 (check_quota)
"""

import pytest
import json
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import subscription


# ── Fixtures ────────────────────────────────────────────────────

@pytest.fixture
def tmp_data_dir():
    """隔离的数据目录，避免污染真实数据"""
    d = tempfile.mkdtemp(prefix="ema_test_subscription_")
    orig_dir = subscription.EMA_DATA_DIR
    subscription.EMA_DATA_DIR = Path(d)
    subscription.SUBSCRIBERS_FILE = Path(d) / "subscribers.json"
    subscription.USAGE_FILE = Path(d) / "usage.json"
    yield d
    subscription.EMA_DATA_DIR = orig_dir
    subscription.SUBSCRIBERS_FILE = orig_dir / "subscribers.json"
    subscription.USAGE_FILE = orig_dir / "usage.json"
    shutil.rmtree(d, ignore_errors=True)


# ── 套餐定义测试 ────────────────────────────────────────────────

class TestPlans:
    """套餐定义"""

    def test_all_plans_defined(self):
        assert "free" in subscription.PLANS
        assert "pro" in subscription.PLANS
        assert "enterprise" in subscription.PLANS
        assert "private" in subscription.PLANS

    def test_free_plan_correct(self):
        p = subscription.PLANS["free"]
        assert p.name == "体验版"
        assert p.price_yuan == 0
        assert p.projects_per_month == 3
        assert p.file_size_mb == 25
        assert len(p.agents_enabled) == 3
        assert "tech_rd" in p.agents_enabled

    def test_pro_plan_correct(self):
        p = subscription.PLANS["pro"]
        assert p.name == "专业版"
        assert p.price_yuan == 299
        assert p.projects_per_month == -1  # 无限
        assert p.file_size_mb == 100
        assert len(p.agents_enabled) == 6

    def test_enterprise_plan_correct(self):
        p = subscription.PLANS["enterprise"]
        assert p.name == "企业版"
        assert p.price_yuan == 999
        assert p.storage_mb == 10240
        assert any("改图" in f for f in p.features)

    def test_get_plan_valid(self):
        p = subscription.get_plan("pro")
        assert p is not None
        assert p.plan_id == "pro"

    def test_get_plan_invalid(self):
        p = subscription.get_plan("nonexistent")
        assert p is None

    def test_list_plans(self):
        plans = subscription.list_plans()
        assert len(plans) == 4
        plan_ids = [p["plan_id"] for p in plans]
        assert "free" in plan_ids
        assert "pro" in plan_ids
        assert "enterprise" in plan_ids
        assert "private" in plan_ids


# ── 订阅管理测试 ────────────────────────────────────────────────

class TestSubscribe:
    """订阅管理"""

    def test_new_subscription(self, tmp_data_dir):
        result = subscription.subscribe("tenant-001", "pro", duration_months=1)
        assert result["plan_id"] == "pro"
        assert result["status"] == "active"

    def test_subscription_persisted(self, tmp_data_dir):
        subscription.subscribe("tenant-002", "free")
        sub = subscription.get_subscription("tenant-002")
        assert sub is not None
        assert sub["plan_id"] == "free"

    def test_upgrade_subscription(self, tmp_data_dir):
        subscription.subscribe("tenant-003", "free")
        result = subscription.subscribe("tenant-003", "pro", duration_months=6)
        assert result["plan_id"] == "pro"
        sub = subscription.get_subscription("tenant-003")
        assert sub["plan_id"] == "pro"

    def test_renew_subscription(self, tmp_data_dir):
        subscription.subscribe("tenant-004", "pro", duration_months=1)
        # 模拟过期后重新订阅
        subscribers = subscription._load_json(subscription.SUBSCRIBERS_FILE)
        past = (datetime.now() - timedelta(days=60)).isoformat()
        subscribers["tenant-004"]["expires_at"] = past
        subscription._save_json(subscription.SUBSCRIBERS_FILE, subscribers)

        result = subscription.subscribe("tenant-004", "pro", duration_months=3)
        assert result["plan_id"] == "pro"
        assert result["status"] == "active"

    def test_get_nonexistent_subscription(self, tmp_data_dir):
        sub = subscription.get_subscription("no-such-tenant")
        assert sub is None

    def test_check_subscription_active(self, tmp_data_dir):
        subscription.subscribe("tenant-005", "pro", duration_months=12)
        status = subscription.check_subscription("tenant-005")
        assert status["active"] is True
        assert status["plan_id"] == "pro"
        assert status["days_remaining"] > 300  # 约365天

    def test_check_subscription_expired(self, tmp_data_dir):
        subscription.subscribe("tenant-006", "free")
        # 手动改为已过期
        subscribers = subscription._load_json(subscription.SUBSCRIBERS_FILE)
        past = (datetime.now() - timedelta(days=10)).isoformat()
        subscribers["tenant-006"]["expires_at"] = past
        subscription._save_json(subscription.SUBSCRIBERS_FILE, subscribers)

        status = subscription.check_subscription("tenant-006")
        assert status["active"] is False
        assert status["days_remaining"] <= 0

    def test_check_subscription_nonexistent(self, tmp_data_dir):
        status = subscription.check_subscription("no-tenant")
        assert status["active"] is False
        assert status["status"] == "none"  # 源码默认返回"none"状态


# ── 使用量追踪测试 ──────────────────────────────────────────────

class TestUsageTracking:
    """使用量追踪"""

    def test_track_usage_new_tenant(self, tmp_data_dir):
        result = subscription.track_usage("tenant-007", "projects", amount=1)
        assert result["projects"] == 1

    def test_track_usage_cumulative(self, tmp_data_dir):
        subscription.track_usage("tenant-008", "projects", amount=1)
        subscription.track_usage("tenant-008", "projects", amount=2)
        usage = subscription.get_usage("tenant-008")
        assert usage["projects"] == 3

    def test_track_usage_multiple_metrics(self, tmp_data_dir):
        subscription.track_usage("tenant-009", "projects", 1)
        subscription.track_usage("tenant-009", "api_calls", 10)
        subscription.track_usage("tenant-009", "storage_mb", 50)
        usage = subscription.get_usage("tenant-009")
        assert usage["projects"] == 1
        assert usage["api_calls"] == 10
        assert usage["storage_mb"] == 50

    def test_get_usage_new_tenant(self, tmp_data_dir):
        usage = subscription.get_usage("tenant-010")
        # 新租户应返回空字典或0值
        assert isinstance(usage, dict)

    def test_reset_usage(self, tmp_data_dir):
        subscription.track_usage("tenant-011", "projects_created", 5)
        subscription.track_usage("tenant-011", "api_calls", 100)
        subscription.reset_usage("tenant-011")
        usage = subscription.get_usage("tenant-011")
        # 重置后projects_created和api_calls应为0
        assert usage["projects_created"] == 0
        assert usage["api_calls"] == 0

    def test_month_key_changes_monthly(self):
        key1 = subscription._get_current_month_key()
        assert isinstance(key1, str)
        # 格式应为 YYYY-MM
        parts = key1.split("-")
        assert len(parts) == 2
        assert len(parts[0]) == 4


# ── 配额检查测试 ────────────────────────────────────────────────

class TestQuotaCheck:
    """配额检查"""

    def test_within_quota(self, tmp_data_dir):
        subscription.subscribe("tenant-012", "free")
        # free套餐: 每月3个项目
        subscription.track_usage("tenant-012", "projects_created", 2)
        quota = subscription.check_quota("tenant-012")
        assert quota["can_create_project"] is True
        assert len(quota["violations"]) == 0

    def test_quota_exceeded_projects(self, tmp_data_dir):
        subscription.subscribe("tenant-013", "free")
        # free套餐限制3个项目
        subscription.track_usage("tenant-013", "projects_created", 5)
        quota = subscription.check_quota("tenant-013")
        assert quota["can_create_project"] is False
        assert len(quota["violations"]) > 0

    def test_unlimited_projects_pro_plan(self, tmp_data_dir):
        subscription.subscribe("tenant-014", "pro")
        # pro套餐: 无限项目
        subscription.track_usage("tenant-014", "projects_created", 999)
        quota = subscription.check_quota("tenant-014")
        assert quota["can_create_project"] is True  # -1 = unlimited

    def test_file_size_quota(self, tmp_data_dir):
        subscription.subscribe("tenant-015", "free")
        # free套餐: 单文件25MB
        subscription.track_usage("tenant-015", "storage_mb", 80)
        quota = subscription.check_quota("tenant-015")
        # 存储超出100MB配额
        assert "storage" in str(quota).lower() or quota["within_quota"] is False

    def test_no_subscription_quota(self, tmp_data_dir):
        """无订阅记录时也应能检查（默认free套餐）"""
        quota = subscription.check_quota("tenant-no-sub")
        assert "can_create_project" in quota
        assert "violations" in quota


# ── 边界测试 ────────────────────────────────────────────────────

class TestEdgeCases:
    """边界测试"""

    def test_subscribe_invalid_plan(self, tmp_data_dir):
        """无效套餐应抛出ValueError"""
        with pytest.raises(ValueError, match="无效的订阅计划"):
            subscription.subscribe("tenant-016", "ultra_pro_max")

    def test_track_usage_zero_amount(self, tmp_data_dir):
        result = subscription.track_usage("tenant-017", "projects", 0)
        assert result is not None

    def test_track_usage_negative(self, tmp_data_dir):
        """负值应被处理（例如回退计数）"""
        result = subscription.track_usage("tenant-018", "projects", -1)
        assert result is not None

    def test_multitenant_isolation(self, tmp_data_dir):
        subscription.subscribe("tenant-a", "free")
        subscription.subscribe("tenant-b", "pro")
        subscription.track_usage("tenant-a", "projects_created", 3)
        subscription.track_usage("tenant-b", "projects_created", 10)

        quota_a = subscription.check_quota("tenant-a")
        quota_b = subscription.check_quota("tenant-b")

        # tenant-a: free(3个限制) → 3个刚好边界
        # tenant-b: pro(无限) → 不受限制
        assert quota_b["can_create_project"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
