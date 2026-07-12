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

项目仍是适合 MVP 的“FastAPI 单体 + SQLite 身份/用量 + 文件式项目存储”。优点是部署简单，短板是多实例并发与任务可靠性有限：后台任务和部分任务状态仍在进程内，项目 JSON 更新依赖文件锁。

## 推荐演进顺序

1. 将 `main.py` 拆成 `auth / account / admin / projects / media` 五组 Router，保持现有 URL 不变。
2. 将项目元数据从 JSON 文件迁移到 PostgreSQL；大原文、图片、音频放对象存储，数据库只存引用。
3. 将后台生成任务迁移到 Redis + Celery/Dramatiq/Arq，加入幂等键、重试、取消、超时和断点续跑。
4. API Key 加密迁移到云 KMS/Vault envelope encryption，并加入密钥轮换版本号。
5. 用量账本加入供应商单价快照与预算阈值，支持用户日/月限额、失败熔断和管理员告警。
6. 为角色建立独立资产表，支持多版本立绘、表情差分、审核、删除和对象存储生命周期。

## 新接口

- `GET/PUT/DELETE /api/account/api-configs/{service_type}`：用户 API 配置。
- `GET /api/account/usage`：当前用户用量。
- `GET /api/admin/usage`：全站用量与用户明细。
- `POST /api/media/image/generate`：统一生图。
- `POST /api/media/tts/synthesize`：统一语音合成。
- `POST /api/projects/{project_id}/characters/{character_id}/generate-image`：根据小说分析结果生成角色立绘。

生产环境必须设置固定的 `API_CONFIG_SECRET`。如需访问内网自部署模型，只在可信网络中显式开启 `ALLOW_PRIVATE_API_URLS=true`。
