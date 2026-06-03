# EMA 客户试用部署指南 (Quick Start)

> **版本：** v3.8.0 | **更新：** 2026-06-03
> **适用：** 勘察设计院 / 住建局 / 审图单位 / 施工单位 等工程参与方

---

## 一、前置要求

| 项目 | 最低要求 | 推荐 |
|------|----------|------|
| 操作系统 | Linux / macOS / Windows WSL2 | Ubuntu 22.04+ |
| Docker | 24.0+ | 最新版 |
| Docker Compose | v2.20+ | 最新版 |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 10GB 可用 | 20GB+ (含模型) |
| Ollama (可选) | 本地AI分析需要 | — |

---

## 二、一键部署（推荐）

```bash
# 1. 克隆项目
git clone <repo-url> ema
cd ema

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，至少修改 JWT_SECRET
nano .env

# 3. 启动服务
docker compose up -d

# 4. 验证
curl http://localhost:6188/health
# 返回 {"status":"ok"} 即成功

# 5. 访问
# API 文档: http://localhost:6188/docs
# 管理后台: http://localhost:6189/admin.html
# 用户界面: http://localhost:6189
```

---

## 三、生产部署（含 Nginx + SSL）

```bash
# 配置 SSL 证书
mkdir -p ssl
# 将证书放入 ssl/fullchain.pem 和 ssl/privkey.pem

# 编辑 nginx.conf 中的域名

# 启动生产模式
docker compose --profile prod up -d
```

---

## 四、功能模块

| 模块 | 说明 | 访问方式 |
|------|------|----------|
| 图纸分析 | DWG/DXF/PDF 解析 + 图层识别 | 上传文件即可 |
| 智能审查 | 15条国标规则自动审查 | 分析后点击"审查" |
| 文档生成 | 设计说明/技术交底/工程量清单等 | 分析后一键生成 |
| 全生命周期 | SOP/MOP/EOP/LCC | 生命周期页面 |
| 大模型对话 | 工程知识问答 | 聊天界面 |
| 性能监控 | 实时指标+告警 | 侧边栏"性能监控" |

---

## 五、配置本地 AI（可选，提升分析能力）

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 下载模型（二选一）
ollama pull qwen3.5:9b      # 通义千问 9B，推荐
ollama pull deepseek-r1:7b  # DeepSeek R1 7B

# 验证
ollama run qwen3.5:9b "你好"
```

---

## 六、常用命令

```bash
# 查看日志
docker compose logs -f api

# 重启服务
docker compose restart

# 停止服务
docker compose down

# 更新到最新版
git pull && docker compose build --no-cache && docker compose up -d

# 备份数据
tar -czf ema-backup-$(date +%Y%m%d).tar.gz data/

# 测试
docker compose exec api python3 -m pytest tests/ -q
```

---

## 七、默认账号

| 角色 | 用户名 | 密码 | 权限 |
|------|--------|------|------|
| 管理员 | boss_ke | （首次登录后修改） | 全部 |
| 演示用户 | demo | demo123 | 基础功能 |

> ⚠️ 生产环境请立即修改默认密码！

---

## 八、常见问题

**Q: 端口被占用？**
```bash
# 修改 docker-compose.yml 中的端口映射，或修改 .env 中的 EMA_PORT
```

**Q: Ollama 连接失败？**
```bash
# 检查 .env 中 OLLAMA_HOST 配置
# Docker 内访问宿主机：http://host.docker.internal:11434
# 宿主机直接运行：http://localhost:11434
```

**Q: 图纸分析无结果？**
- 确认文件格式为 DWG/DXF/PDF
- 检查文件是否损坏
- 查看日志：`docker compose logs api | grep -i error`

**Q: 如何对接微信小程序？**
- 在 .env 中填入 WECHAT_APPID + WECHAT_SECRET
- 设置 WECHAT_MODE=real
- 参考 `docs/04-项目进展/wechat-miniapp-guide.md`

---

## 九、技术支持

- 项目文档：`docs/`
- API 文档：http://localhost:6188/docs
- 状态报告：`docs/04-项目进展/`
