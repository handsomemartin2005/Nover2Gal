# Novel2Gal 架构优化与管理后台

## 本次落地

- 身份与权限：继续使用 HttpOnly Session，登录时明确选择“用户登录 / 管理员登录”；管理员入口会再次校验角色。
- 管理后台：保留用户、项目、样例治理，并新增 30 天 API 调用、Token、图片、语音字符、失败率和逐条调用详情。
- 用户自带 API（BYOK）：每个账号可分别配置文本、生图、语音接口。API Key 加密保存，接口与页面只返回末四位掩码。
- 统一 AI Gateway：文本支持 OpenAI-compatible、Anthropic Messages、Gemini generateContent；生图支持 OpenAI Images-compatible；语音支持 OpenAI Audio-compatible。预设覆盖 DeepSeek、OpenAI、通义百炼、SiliconFlow、Moonshot、Anthropic、Gemini、智谱。
- 创作闭环：文本处理使用当前用户配置；分析出的角色可直接调用用户生图 API 生成专属立绘并写回项目；TTS 提供真实音频合成端点。
- 成本与隐私：平台不再必须承担模型费用；用量账本不保存小说正文、提示词、返回内容或 API Key。
- 网络安全：自定义 Base URL 默认只允许 HTTPS，拒绝 localhost、私网、链路本地和保留地址。

## 当前边界

生产环境现已升级为“FastAPI + Redis worker + PostgreSQL + S3-compatible 对象存储”。SQLite 仅保留身份、Session、BYOK 配置与轻量用量账本；小说原文暂时仍保存在受限本地目录，项目 JSON 元数据已进入 PostgreSQL。

Redis 队列使用 pending/processing 双队列和显式确认，worker 重启时会回收未确认任务。PostgreSQL 启动迁移只导入尚不存在的旧项目，防止历史 JSON 覆盖数据库新状态。生成图片和语音会落入对象存储，再以站内稳定 URL 提供。

## 推荐演进顺序

1. 将 `main.py` 拆成 `auth / account / admin / projects / media` 五组 Router，保持现有 URL 不变。
2. ~~将项目元数据从 JSON 文件迁移到 PostgreSQL。~~ 已完成，保留一次性兼容导入。
3. ~~将后台生成任务迁移到 Redis。~~ 已完成基础持久队列、确认和崩溃回收；后续补用户取消、指数退避和死信队列。
4. API Key 加密迁移到云 KMS/Vault envelope encryption，并加入密钥轮换版本号。
5. 用量账本加入供应商单价快照与预算阈值，支持用户日/月限额、失败熔断和管理员告警。
6. 为角色建立独立资产表，支持多版本立绘、表情差分、审核、删除和对象存储生命周期。

## 生产基础设施

- `novel2gal.service`：FastAPI Web 进程。
- `novel2gal-worker.service`：Redis 队列消费进程。
- PostgreSQL：`projects.payload JSONB` 保存完整项目元数据，并建立所有者/更新时间索引。
- Redis：任务、processing 队列及 7 天任务结果。
- MinIO：部署为仅监听 `127.0.0.1` 的 S3-compatible 服务，媒体通过站内 `/api/media/assets/*` 读取。
- `GET /health/ready`：同时检查 Redis、PostgreSQL 和对象存储。

## 新接口

- `GET/PUT/DELETE /api/account/api-configs/{service_type}`：用户 API 配置。
- `GET /api/account/usage`：当前用户用量。
- `GET /api/admin/usage`：全站用量与用户明细。
- `POST /api/media/image/generate`：统一生图。
- `POST /api/media/tts/synthesize`：统一语音合成。
- `POST /api/projects/{project_id}/characters/{character_id}/generate-image`：根据小说分析结果生成角色立绘。

生产环境必须设置固定的 `API_CONFIG_SECRET`。如需访问内网自部署模型，只在可信网络中显式开启 `ALLOW_PRIVATE_API_URLS=true`。
