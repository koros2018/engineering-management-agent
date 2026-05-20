"""
tests/test_notifications.py
通知模块单元测试

测试范围:
- 创建通知 (create_notification)
- 查询通知 (get_notifications)
- 已读/全部已读 (mark_read / mark_all_read)
- 未读计数 (get_unread_count)
- 订阅到期检查 (run_subscription_check)
- 配额检查 (run_quota_check)
"""

import pytest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import notifications


@pytest.fixture
def tmp_data_dir():
    """隔离数据目录"""
    d = tempfile.mkdtemp(prefix="ema_test_notif_")
    orig_n = notifications.NOTIFICATIONS_FILE
    orig_a = notifications.ALERTS_FILE
    orig_c = notifications.CHECKPOINTS_FILE
    notifications.NOTIFICATIONS_FILE = Path(d) / "notifications.json"
    notifications.ALERTS_FILE = Path(d) / "alerts.json"
    notifications.CHECKPOINTS_FILE = Path(d) / "checkpoints.json"
    yield d
    notifications.NOTIFICATIONS_FILE = orig_n
    notifications.ALERTS_FILE = orig_a
    notifications.CHECKPOINTS_FILE = orig_c
    shutil.rmtree(d, ignore_errors=True)


class TestCreateNotification:
    """创建通知"""

    def test_create_basic(self, tmp_data_dir):
        result = notifications.create_notification(
            "t-001", "system_update", "系统升级", "v2.1 已发布"
        )
        # create_notification 返回 notification dict
        assert result["id"].startswith("notif_")
        assert result["type"] == "system_update"
        assert result["read"] is False

    def test_create_with_severity(self, tmp_data_dir):
        notifications.create_notification(
            "t-002", "security_alert", "异常登录", "检测到异常IP登录",
            severity="critical", actionable=True
        )
        notifs = notifications.get_notifications("t-002")
        assert len(notifs) == 1
        assert notifs[0]["severity"] == "critical"
        assert notifs[0]["actionable"] is True

    def test_create_with_action_url(self, tmp_data_dir):
        notifications.create_notification(
            "t-003", "subscription_expiring", "即将到期",
            "您的套餐3天后到期", action_url="/subscribe"
        )
        notifs = notifications.get_notifications("t-003")
        assert notifs[0]["action_url"] == "/subscribe"

    def test_multiple_notifications(self, tmp_data_dir):
        for i in range(5):
            notifications.create_notification(
                "t-004", f"type_{i}", f"title {i}", f"message {i}"
            )
        notifs = notifications.get_notifications("t-004")
        assert len(notifs) == 5

    def test_tenant_isolation(self, tmp_data_dir):
        notifications.create_notification("t-a", "test", "A", "msg A")
        notifications.create_notification("t-b", "test", "B", "msg B")

        a_notifs = notifications.get_notifications("t-a")
        b_notifs = notifications.get_notifications("t-b")
        assert len(a_notifs) == 1
        assert len(b_notifs) == 1
        assert a_notifs[0]["title"] != b_notifs[0]["title"]


class TestMarkRead:
    """已读标记"""

    def test_mark_single_read(self, tmp_data_dir):
        n = notifications.create_notification("t-005", "test", "T1", "M1")
        result = notifications.mark_read("t-005", n["id"])
        assert result is True

    def test_mark_all_read(self, tmp_data_dir):
        for _ in range(3):
            notifications.create_notification("t-006", "test", "T", "M")
        count = notifications.mark_all_read("t-006")
        assert count == 3

    def test_unread_count_after_read(self, tmp_data_dir):
        for _ in range(5):
            notifications.create_notification("t-007", "test", "T", "M")

        assert notifications.get_unread_count("t-007") == 5
        notifications.mark_all_read("t-007")
        assert notifications.get_unread_count("t-007") == 0

    def test_mark_nonexistent(self, tmp_data_dir):
        result = notifications.mark_read("t-none", "fake-id")
        assert result is False


class TestUnreadCount:
    """未读计数"""

    def test_new_tenant_zero(self, tmp_data_dir):
        count = notifications.get_unread_count("new-tenant")
        assert count == 0

    def test_only_unread_counted(self, tmp_data_dir):
        n1 = notifications.create_notification("t-008", "test", "T1", "M1")
        import time
        time.sleep(0.01)  # 确保ID不同(基于毫秒时间戳)
        n2 = notifications.create_notification("t-008", "test", "T2", "M2")
        notifications.mark_read("t-008", n1["id"])

        unread = notifications.get_notifications("t-008", unread_only=True)
        assert len(unread) == 1
        assert unread[0]["title"] == "T2"


class TestScheduledChecks:
    """定时检查"""

    def test_subscription_check_runs(self, tmp_data_dir):
        result = notifications.run_subscription_check("t-check-001")
        assert isinstance(result, list)

    def test_quota_check_runs(self, tmp_data_dir):
        result = notifications.run_quota_check("t-check-002")
        assert isinstance(result, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
