# Blueprint AI API - Supervisor 配置

**用途**: 管理 API 服务器进程，实现自动重启、日志收集、崩溃恢复

---

## 一、安装 Supervisor

```bash
# Ubuntu/Debian
sudo apt-get install supervisor

# 验证安装
supervisord --version
```

---

## 二、配置文件

### 2.1 配置文件位置

```bash
# 全局配置
/etc/supervisor/supervisord.conf

# 项目配置目录
/etc/supervisor/conf.d/
```

### 2.2 创建项目配置

```bash
sudo cp /tmp/supervisor_api.conf /etc/supervisor/conf.d/blueprint-api.conf
```

### 2.3 配置内容

```ini
[program:blueprint-api]
command=python3 src/api_server.py
directory=/mnt/d/OpenClawDataworkspace/Projects/blueprint-ai
autostart=true
autorestart=true
startretries=3
stderr_logfile=/mnt/d/OpenClawDataworkspace/Projects/blueprint-ai/output/logs/api_err.log
stdout_logfile=/mnt/d/OpenClawDataworkspace/Projects/blueprint-ai/output/logs/api_out.log
user=kezhigang
environment=PYTHONPATH="/mnt/d/OpenClawDataworkspace/Projects/blueprint-ai/src"
```

---

## 三、管理命令

### 3.1 重新加载配置

```bash
# 重新加载配置（不重启 supervisor）
sudo supervisorctl reread
sudo supervisorctl update

# 重启服务
sudo supervisorctl restart blueprint-api
```

### 3.2 查看状态

```bash
# 查看所有服务状态
sudo supervisorctl status

# 查看单个服务
sudo supervisorctl status blueprint-api
```

### 3.3 启动/停止

```bash
# 启动
sudo supervisorctl start blueprint-api

# 停止
sudo supervisorctl stop blueprint-api

# 重启
sudo supervisorctl restart blueprint-api
```

---

## 四、日志管理

### 4.1 日志位置

| 日志类型 | 路径 |
|---------|------|
| API 输出 | `output/logs/api_out.log` |
| API 错误 | `output/logs/api_err.log` |
| Supervisor | `/var/log/supervisor/supervisord.log` |

### 4.2 查看日志

```bash
# 实时查看输出日志
tail -f output/logs/api_out.log

# 查看错误日志
tail -f output/logs/api_err.log

# 查看 Supervisor 日志
sudo tail -f /var/log/supervisor/supervisord.log
```

---

## 五、优势对比

| 特性 | nohup | systemd | supervisor |
|------|-------|---------|------------|
| 自动重启 | ❌ | ✅ | ✅ |
| 启动重试 | ❌ | ✅ | ✅ |
| 日志收集 | ⚠️ | ✅ | ✅ |
| 配置简单 | ✅ | ⚠️ | ✅ |
| Python 友好 | ⚠️ | ⚠️ | ✅ |
| 多进程管理 | ❌ | ✅ | ✅ |

**推荐**: Supervisor 更适合 Python 应用管理

---

## 六、故障排查

### 6.1 服务无法启动

```bash
# 检查配置
sudo supervisorctl reread

# 查看详细错误
sudo tail -50 /var/log/supervisor/supervisord.log
sudo tail -50 output/logs/api_err.log
```

### 6.2 频繁重启

```bash
# 增加重试次数
startretries=5

# 查看崩溃原因
tail -f output/logs/api_err.log
```

---

**配置完成时间**: 2026-05-15 09:30 AM
**配置版本**: v1.0
**适用版本**: v0.16.3+
