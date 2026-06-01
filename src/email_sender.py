"""
EMA 邮件发送模块
支持 QQ邮箱 / 163邮箱 / Gmail 等 SMTP 服务
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

# ── SMTP 配置（可通过环境变量覆盖）──
SMTP_HOST = "smtp.qq.com"
SMTP_PORT = 465  # SSL
SMTP_USER = "810688745@qq.com"
SMTP_PASSWORD = "azrxstmbxuvpbfbd"  # QQ邮箱授权码
SMTP_FROM = "810688745@qq.com"
SMTP_FROM_NAME = "EMA 工程管理智能体"


def send_email(to: str, subject: str, body: str, html: bool = False) -> bool:
    """
    发送邮件
    :param to: 收件人邮箱
    :param subject: 主题
    :param body: 正文
    :param html: 是否 HTML 格式
    :return: 是否成功
    """
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject

        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type, "utf-8"))

        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to], msg.as_string())

        logger.info(f"邮件发送成功: {to} | {subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP 认证失败：请检查邮箱账号和授权码")
        return False
    except smtplib.SMTPConnectError:
        logger.error(f"SMTP 连接失败：{SMTP_HOST}:{SMTP_PORT}")
        return False
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


def send_password_reset_email(to: str, username: str, reset_code: str) -> bool:
    """
    发送密码重置邮件
    """
    subject = "EMA 工程管理智能体 — 密码重置"
    body = f"""
您好 {username}，

您申请了密码重置，请在 30 分钟内使用以下重置码：

    {reset_code}

如果这不是您的操作，请忽略此邮件。

---
EMA 工程管理智能体
"""
    html_body = f"""
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
  <div style="background:#1a1a2e;color:#fff;padding:20px;border-radius:8px 8px 0 0">
    <h2 style="margin:0">🏗️ EMA 工程管理智能体</h2>
  </div>
  <div style="background:#f8f9fa;padding:30px;border:1px solid #e9ecef;border-top:none">
    <p>您好 <strong>{username}</strong>，</p>
    <p>您申请了密码重置，请在 <strong>30 分钟内</strong>使用以下重置码：</p>
    <div style="background:#1a1a2e;color:#4ade80;padding:15px 20px;border-radius:8px;font-family:monospace;font-size:18px;text-align:center;letter-spacing:2px;margin:20px 0">
      {reset_code}
    </div>
    <p style="color:#6c757d;font-size:13px">如果这不是您的操作，请忽略此邮件。</p>
  </div>
  <div style="background:#e9ecef;padding:15px 20px;border-radius:0 0 8px 8px;font-size:12px;color:#6c757d;text-align:center">
    EMA 工程管理智能体 · 自动发送，请勿回复
  </div>
</body></html>
"""
    return send_email(to, subject, html_body, html=True)


def send_welcome_email(to: str, username: str) -> bool:
    """
    发送欢迎邮件（新用户注册）
    """
    subject = "欢迎加入 EMA 工程管理智能体"
    html_body = f"""
<html><body style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:20px">
  <div style="background:#1a1a2e;color:#fff;padding:20px;border-radius:8px 8px 0 0">
    <h2 style="margin:0">🏗️ 欢迎加入 EMA</h2>
  </div>
  <div style="background:#f8f9fa;padding:30px;border:1px solid #e9ecef;border-top:none">
    <p>您好 <strong>{username}</strong>，</p>
    <p>欢迎加入 EMA 工程管理智能体！您的账号已成功创建。</p>
    <p>立即体验：<a href="http://localhost:6189" style="color:#3b82f6">http://localhost:6189</a></p>
  </div>
</body></html>
"""
    return send_email(to, subject, html_body, html=True)
