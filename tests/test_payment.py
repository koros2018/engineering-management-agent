"""
tests/test_payment.py
支付模块单元测试

测试范围:
- 订单创建 (create_order)
- 订单查询 (get_order / list_orders)
- 支付成功回调 (mock_pay_success)
- 微信/支付宝预下单 (wechat_prepay / alipay_prepay)
"""

import pytest
import tempfile
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import payment


@pytest.fixture
def tmp_data_dir():
    """隔离数据目录"""
    d = tempfile.mkdtemp(prefix="ema_test_payment_")
    orig = payment.ORDERS_FILE
    orig2 = payment.PAYMENTS_FILE
    payment.ORDERS_FILE = Path(d) / "orders.json"
    payment.PAYMENTS_FILE = Path(d) / "payments.json"
    yield d
    payment.ORDERS_FILE = orig
    payment.PAYMENTS_FILE = orig2
    shutil.rmtree(d, ignore_errors=True)


class TestCreateOrder:
    """订单创建"""

    def test_create_order_basic(self, tmp_data_dir):
        order = payment.create_order("t-001", "pro", 299.0)
        assert order["tenant_id"] == "t-001"
        assert order["plan_id"] == "pro"
        assert order["amount"] == 299.0
        assert order["payment_method"] == "wechat"  # 默认
        assert order["status"] == "pending"
        assert order["order_id"].startswith("EMA")

    def test_create_order_alipay(self, tmp_data_dir):
        order = payment.create_order("t-002", "enterprise", 999.0, payment_method="alipay")
        assert order["payment_method"] == "alipay"
        assert order["amount"] == 999.0

    def test_create_order_custom_duration(self, tmp_data_dir):
        order = payment.create_order("t-003", "pro", 299.0, duration_months=12)
        assert order["duration_months"] == 12

    def test_order_unique_ids(self, tmp_data_dir):
        o1 = payment.create_order("t-a", "pro", 299.0)
        o2 = payment.create_order("t-b", "pro", 299.0)
        assert o1["order_id"] != o2["order_id"]

    def test_order_2hour_expiry(self, tmp_data_dir):
        from datetime import datetime
        order = payment.create_order("t-004", "pro", 299.0)
        created = datetime.fromisoformat(order["created_at"])
        expires = datetime.fromisoformat(order["expires_at"])
        diff_hours = (expires - created).total_seconds() / 3600
        assert 1.9 <= diff_hours <= 2.1


class TestGetOrders:
    """订单查询"""

    def test_get_order_found(self, tmp_data_dir):
        order = payment.create_order("t-005", "pro", 299.0)
        retrieved = payment.get_order(order["order_id"])
        assert retrieved is not None
        assert retrieved["tenant_id"] == "t-005"

    def test_get_order_not_found(self, tmp_data_dir):
        assert payment.get_order("ema-nonexistent") is None

    def test_list_orders_by_tenant(self, tmp_data_dir):
        payment.create_order("t-006", "pro", 299.0)
        payment.create_order("t-006", "enterprise", 999.0)
        payment.create_order("t-007", "pro", 299.0)

        orders_t6 = payment.list_orders("t-006")
        assert len(orders_t6) == 2

        orders_t7 = payment.list_orders("t-007")
        assert len(orders_t7) == 1

    def test_list_orders_filter_status(self, tmp_data_dir):
        o1 = payment.create_order("t-008", "pro", 299.0)
        payment.mock_pay_success(o1["order_id"])

        pending = payment.list_orders("t-008", status="pending")
        paid = payment.list_orders("t-008", status="paid")

        assert len(paid) == 1
        assert len(pending) == 0

    def test_list_orders_empty(self, tmp_data_dir):
        result = payment.list_orders("tenant-no-orders")
        assert result == []

    def test_list_orders_limit(self, tmp_data_dir):
        for i in range(10):
            payment.create_order("t-009", "pro", 299.0)
        orders = payment.list_orders("t-009", limit=5)
        assert len(orders) == 5

    def test_list_orders_sorted_desc(self, tmp_data_dir):
        o1 = payment.create_order("t-010", "pro", 299.0)
        import time
        time.sleep(0.01)
        o2 = payment.create_order("t-010", "enterprise", 999.0)

        orders = payment.list_orders("t-010")
        assert orders[0]["order_id"] == o2["order_id"]  # 最新的在前


class TestMockPaySuccess:
    """模拟支付"""

    def test_pay_success_basic(self, tmp_data_dir):
        order = payment.create_order("t-pay-001", "pro", 299.0)
        result = payment.mock_pay_success(order["order_id"])
        assert result["status"] == "paid"
        assert result["plan_id"] == "pro"

    def test_pay_success_updates_order(self, tmp_data_dir):
        order = payment.create_order("t-pay-002", "pro", 299.0)
        payment.mock_pay_success(order["order_id"])
        updated = payment.get_order(order["order_id"])
        assert updated["status"] == "paid"
        assert updated["paid_at"] is not None

    def test_pay_nonexistent_order(self, tmp_data_dir):
        with pytest.raises(ValueError, match="订单不存在"):
            payment.mock_pay_success("ema-fake-000")

    def test_pay_already_paid_order(self, tmp_data_dir):
        order = payment.create_order("t-pay-003", "pro", 299.0)
        payment.mock_pay_success(order["order_id"])
        with pytest.raises(ValueError, match="状态异常"):
            payment.mock_pay_success(order["order_id"])


class TestPrepay:
    """微信/支付宝预下单"""

    def test_wechat_prepay_creates_order(self, tmp_data_dir):
        result = payment.wechat_prepay("t-wx-001", "pro", 299.0)
        assert result["amount"] == 299.0
        assert result["prepay_id"].startswith("prepay_")
        assert "appId" in result
        assert "timeStamp" in result
        assert "paySign" in result

    def test_alipay_prepay_creates_order(self, tmp_data_dir):
        result = payment.alipay_prepay("t-ali-001", "enterprise", 999.0)
        assert result["amount"] == 999.0
        assert "order_id" in result


class TestPaymentEdgeCases:
    """边界测试"""

    def test_zero_amount_order(self, tmp_data_dir):
        order = payment.create_order("t-001", "free", 0.0)
        assert order["amount"] == 0.0

    def test_large_amount(self, tmp_data_dir):
        order = payment.create_order("t-large", "private", 99999.0)
        assert order["amount"] == 99999.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
