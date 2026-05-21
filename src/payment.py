"""
payment.py - 支付网关 Stub

Phase 7: 微信支付/支付宝回调接口骨架
生产环境替换为真实的 SDK 调用（wechatpayv3 / alipay-sdk-python）
"""

import json
import hashlib
import time
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional


# ── 配置 ──────────────────────────────────────────────────────

EMA_DATA_DIR = Path(__file__).parent.parent / "data"
PAYMENTS_FILE = EMA_DATA_DIR / "payments.json"
ORDERS_FILE = EMA_DATA_DIR / "orders.json"

# 生产环境从环境变量读取
WECHAT_APP_ID = "wx_mock_app_id"
WECHAT_MCH_ID = "mock_mch_id"
WECHAT_API_KEY = "mock_api_key"
ALIPAY_APP_ID = "mock_alipay_app_id"
ALIPAY_PRIVATE_KEY = "mock_private_key"


def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# ── 订单管理 ──────────────────────────────────────────────────

def create_order(
    tenant_id: str,
    plan_id: str,
    amount: float,
    payment_method: str = "wechat",     # wechat / alipay
    duration_months: int = 1,
) -> Dict:
    """
    创建支付订单

    Args:
        tenant_id: 租户ID
        plan_id: 套餐ID (pro/enterprise/private)
        amount: 金额（元）
        payment_method: 支付方式
        duration_months: 订阅月数

    Returns:
        dict: 订单信息（含支付链接/二维码）
    """
    orders = _load_json(ORDERS_FILE)

    order_id = f"EMA{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now()

    order = {
        "order_id": order_id,
        "tenant_id": tenant_id,
        "plan_id": plan_id,
        "amount": amount,
        "duration_months": duration_months,
        "payment_method": payment_method,
        "status": "pending",            # pending / paid / cancelled / refunded
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=2)).isoformat(),
        "paid_at": None,
        # 生产环境：二维码URL / 支付跳转链接
        "pay_url": f"http://127.0.0.1:6188/api/v1/payment/mock-pay/{order_id}" if payment_method == "wechat" else
                   f"http://127.0.0.1:6188/api/v1/payment/mock-pay/{order_id}",
    }

    orders[order_id] = order
    _save_json(ORDERS_FILE, orders)

    return order


def get_order(order_id: str) -> Optional[Dict]:
    orders = _load_json(ORDERS_FILE)
    return orders.get(order_id)


def list_orders(tenant_id: str, status: str = None, limit: int = 20) -> list:
    """列出租户的订单"""
    orders = _load_json(ORDERS_FILE)
    result = []

    for oid, o in orders.items():
        if o.get("tenant_id") != tenant_id:
            continue
        if status and o.get("status") != status:
            continue
        result.append(o)

    # 按创建时间倒序
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return result[:limit]


# ── 支付回调 ──────────────────────────────────────────────────

def mock_pay_success(order_id: str) -> Dict:
    """
    模拟支付成功（Phase 7 Stub）

    生产环境：由微信/支付宝回调通知触发
    """
    orders = _load_json(ORDERS_FILE)
    order = orders.get(order_id)

    if not order:
        raise ValueError(f"订单不存在: {order_id}")

    if order["status"] != "pending":
        raise ValueError(f"订单状态异常: {order['status']}")

    now = datetime.now()

    # 更新订单状态
    order["status"] = "paid"
    order["paid_at"] = now.isoformat()
    orders[order_id] = order
    _save_json(ORDERS_FILE, orders)

    # 记录支付历史
    payments = _load_json(PAYMENTS_FILE)
    payment_id = f"PAY{now.strftime('%Y%m%d%H%M%S')}"
    payments[payment_id] = {
        "payment_id": payment_id,
        "order_id": order_id,
        "tenant_id": order["tenant_id"],
        "amount": order["amount"],
        "method": order["payment_method"],
        "paid_at": now.isoformat(),
        "status": "success",
    }
    _save_json(PAYMENTS_FILE, payments)

    # 激活订阅
    from subscription import subscribe
    subscribe(order["tenant_id"], order["plan_id"], order["duration_months"])

    # 发送通知
    from notifications import create_notification
    create_notification(
        order["tenant_id"], "subscription_expiring",
        title="✅ 订阅激活成功",
        message=f"您已成功订阅{order['plan_id']}套餐（¥{order['amount']}），有效期{order['duration_months']}个月。",
        severity="info",
        actionable=True,
        action_url="/settings/subscription",
    )

    return {
        "order_id": order_id,
        "status": "paid",
        "plan_id": order["plan_id"],
        "amount": order["amount"],
    }


# ── 微信支付签名（Stub）─────────────────────────────────────

def wechat_prepay(
    tenant_id: str,
    plan_id: str,
    amount: float,
    openid: str = None,
) -> Dict:
    """
    微信支付统一下单（Stub）

    生产环境：调用微信支付 V3 API
    POST https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi

    Returns:
        dict: JSAPI 调起支付所需的参数
    """
    order = create_order(tenant_id, plan_id, amount, "wechat")

    # Mock: 返回前端 JSAPI 参数
    return {
        "order_id": order["order_id"],
        "amount": amount,
        # 生产环境返回真实的 prepay_id / nonceStr / paySign
        "prepay_id": f"prepay_{uuid.uuid4().hex[:12]}",
        "appId": WECHAT_APP_ID,
        "timeStamp": str(int(time.time())),
        "nonceStr": uuid.uuid4().hex[:16],
        "package": f"prepay_id={uuid.uuid4().hex[:12]}",
        "signType": "RSA",
        "paySign": hashlib.sha256(f"{amount}{time.time()}".encode()).hexdigest(),
    }


# ── 支付宝签名（Stub）────────────────────────────────────────

def alipay_prepay(
    tenant_id: str,
    plan_id: str,
    amount: float,
) -> Dict:
    """
    支付宝预下单（Stub）

    生产环境：调用支付宝 API
    POST https://openapi.alipay.com/gateway.do

    Returns:
        dict: 支付参数
    """
    order = create_order(tenant_id, plan_id, amount, "alipay")

    return {
        "order_id": order["order_id"],
        "amount": amount,
        "alipay_trade_no": f"AP{uuid.uuid4().hex[:16].upper()}",
        "sign": hashlib.md5(f"{amount}{time.time()}{ALIPAY_APP_ID}".encode()).hexdigest(),
    }
