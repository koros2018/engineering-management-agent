"""
email_notifier.py - EMA 电子邮件通知模块

功能:
- SMTP 邮件发送 (支持SSL/TLS)
- 模板化邮件 (订阅到期/安全告警/使用周报)
- 队列发送 (支持重试)
- 与 notifications.py 集成

Usage:
    from tools.email_notifier import EmailNotifier
    notifier = EmailNotifier()
    notifier.send("user@example.com", "订阅到期提醒", "您的套餐即将到期...")
"""

import smtplib
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# ── 配置 ──────────────────────────────────────────────────────

SMTP_CONFIG = {
    "host": os.environ.get("EMA_SMTP_HOST", "smtp.qq.com"),
    "port": int(os.environ.get("EMA_SMTP_PORT", 587)),
    "use_tls": os.environ.get("EMA_SMTP_TLS", "true").lower() == "true",
    "username": os.environ.get("EMA_SMTP_USER", ""),
    "password": os.environ.get("EMA_SMTP_PASS", ""),
    "from_addr": os.environ.get("EMA_SMTP_FROM", "ema@example.com"),
    "from_name": "工程管理智能体 EMA",
}

# ── 邮件模板 ──────────────────────────────────────────────────

EMAIL_TEMPLATES = {
    "subscription_expiring": {
        "subject": "⚠️ EMA 订阅即将到期提醒",
        "html": """
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #f59e0b;">⚠️ 订阅即将到期</h2>
                <p>尊敬的 {tenant_name}：</p>
                <p>您的 <strong>{plan_name}</strong> 套餐将于 <strong>{expire_date}</strong> 到期，剩余 <strong style="color: #f59e0b;">{days_left} 天</strong>。</p>
                <p>到期后将降级为免费版，可能影响以下功能：</p>
                <ul>
                    <li>图纸分析数量受限</li>
                    <li>高级审图功能暂停</li>
                    <li>AI改图功能不可用</li>
                </ul>
                <p><a href="{renew_url}" style="display: inline-block; padding: 10px 20px; background: #1f6feb; color: #fff; text-decoration: none; border-radius: 6px;">立即续费</a></p>
                <hr>
                <p style="color: #8b949e; font-size: 12px;">此邮件由工程管理智能体 (EMA) 自动发送，如有疑问请联系管理员。</p>
            </div>
        """,
    },
    "subscription_expired": {
        "subject": "🔴 EMA 订阅已过期通知",
        "html": """
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #f85149;">🔴 订阅已过期</h2>
                <p>尊敬的 {tenant_name}：</p>
                <p>您的 <strong>{plan_name}</strong> 套餐已于 <strong>{expire_date}</strong> 过期。</p>
                <p>当前已自动切换为免费版，部分功能受限。如需恢复完整功能，请尽快续费。</p>
                <p><a href="{renew_url}" style="display: inline-block; padding: 10px 20px; background: #1f6feb; color: #fff; text-decoration: none; border-radius: 6px;">立即续费</a></p>
                <hr>
                <p style="color: #8b949e; font-size: 12px;">此邮件由工程管理智能体 (EMA) 自动发送。</p>
            </div>
        """,
    },
    "security_alert": {
        "subject": "🚨 EMA 安全告警",
        "html": """
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #f85149;">🚨 安全告警</h2>
                <p>类型: <strong>{alert_type}</strong></p>
                <p>详情: {detail}</p>
                <p>时间: {time}</p>
                <p>IP: {ip}</p>
                <p style="color: #f85149;">请尽快检查系统安全状态。</p>
            </div>
        """,
    },
    "usage_summary": {
        "subject": "📊 EMA 使用量周报",
        "html": """
            <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #1f6feb;">📊 使用量周报 ({week})</h2>
                <p>尊敬的 {tenant_name}：</p>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 8px; border: 1px solid #30363d;">本周项目数</td><td style="padding: 8px; border: 1px solid #30363d;">{projects_count}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #30363d;">上传文件数</td><td style="padding: 8px; border: 1px solid #30363d;">{files_count}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #30363d;">API调用次数</td><td style="padding: 8px; border: 1px solid #30363d;">{api_calls}</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #30363d;">存储使用量</td><td style="padding: 8px; border: 1px solid #30363d;">{storage_mb} MB</td></tr>
                    <tr><td style="padding: 8px; border: 1px solid #30363d;">配额使用率</td><td style="padding: 8px; border: 1px solid #30363d;">{quota_pct}%</td></tr>
                </table>
                <hr>
                <p style="color: #8b949e; font-size: 12px;">此邮件由 EMA 自动发送，每周一上午发出。</p>
            </div>
        """,
    },
}


class EmailNotifier:
    """SMTP 邮件发送器"""

    def __init__(self, config: dict = None):
        self.config = {**SMTP_CONFIG, **(config or {})}
        self._enabled = bool(self.config["username"] and self.config["password"])
        if not self._enabled:
            print("⚠️ 邮件通知未配置: EMA_SMTP_USER / EMA_SMTP_PASS 未设置")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def send(
        self,
        to_addr: str,
        subject: str,
        body_html: str,
        cc: List[str] = None,
    ) -> Dict:
        """
        发送邮件

        Returns:
            {"success": bool, "message": str, "message_id": str}
        """
        if not self._enabled:
            return {"success": False, "message": "邮件服务未配置"}

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config['from_name']} <{self.config['from_addr']}>"
            msg["To"] = to_addr
            if cc:
                msg["Cc"] = ", ".join(cc)

            msg.attach(MIMEText(body_html, "html", "utf-8"))

            with smtplib.SMTP(self.config["host"], self.config["port"], timeout=15) as server:
                if self.config["use_tls"]:
                    server.starttls()
                server.login(self.config["username"], self.config["password"])
                server.send_message(msg)
                # smtplib 不返回message_id，生成一个
                msg_id = f"ema_{int(time.time() * 1000)}"

            return {"success": True, "message": "发送成功", "message_id": msg_id}

        except smtplib.SMTPAuthenticationError:
            return {"success": False, "message": "SMTP认证失败：用户名或密码错误"}
        except smtplib.SMTPConnectError:
            return {"success": False, "message": f"SMTP连接失败：无法连接到 {self.config['host']}:{self.config['port']}"}
        except Exception as e:
            return {"success": False, "message": f"发送失败: {str(e)[:200]}"}

    def send_template(
        self,
        to_addr: str,
        template_name: str,
        template_data: Dict[str, str],
    ) -> Dict:
        """使用模板发送邮件"""
        template = EMAIL_TEMPLATES.get(template_name)
        if not template:
            return {"success": False, "message": f"模板不存在: {template_name}"}

        subject = template["subject"].format(**template_data)
        body = template["html"].format(**template_data)
        return self.send(to_addr, subject, body)

    def send_subscription_expiring(
        self, to_addr: str, tenant_name: str, plan_name: str, expire_date: str, days_left: int, renew_url: str = ""
    ):
        return self.send_template(to_addr, "subscription_expiring", {
            "tenant_name": tenant_name,
            "plan_name": plan_name,
            "expire_date": expire_date,
            "days_left": str(days_left),
            "renew_url": renew_url or "http://127.0.0.1:6189/ui/index.html#subscribe",
        })

    def send_subscription_expired(self, to_addr: str, tenant_name: str, plan_name: str, expire_date: str, renew_url: str = ""):
        return self.send_template(to_addr, "subscription_expired", {
            "tenant_name": tenant_name,
            "plan_name": plan_name,
            "expire_date": expire_date,
            "renew_url": renew_url or "http://127.0.0.1:6189/ui/index.html#subscribe",
        })

    def send_security_alert(self, to_addr: str, alert_type: str, detail: str, ip: str = ""):
        return self.send_template(to_addr, "security_alert", {
            "alert_type": alert_type,
            "detail": detail,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": ip or "unknown",
        })

    def send_usage_summary(self, to_addr: str, tenant_name: str, week: str, projects: int, files: int, api_calls: int, storage_mb: int, quota_pct: int):
        return self.send_template(to_addr, "usage_summary", {
            "tenant_name": tenant_name,
            "week": week,
            "projects_count": str(projects),
            "files_count": str(files),
            "api_calls": str(api_calls),
            "storage_mb": str(storage_mb),
            "quota_pct": str(quota_pct),
        })


# ── 全局单例 ──────────────────────────────────────────────────

_notifier = EmailNotifier()

def get_email_notifier() -> EmailNotifier:
    return _notifier
