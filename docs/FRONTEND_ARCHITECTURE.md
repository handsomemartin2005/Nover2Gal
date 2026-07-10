# Novel2Gal 前端架构与部署指南

## 页面与路由

| 路径 | 职责 |
| --- | --- |
| `/` | 艺术化卷首首页；四封螺旋叠放的功能信纸与最近项目入口 |
| `/create` | Galgame Studio；无参数时恢复最近项目 |
| `/create?new=1` | 创建全新企划，不自动恢复最近项目 |
| `/create?project_id=<id>` | 加载指定项目并恢复剧本、表单与舞台 |
| `/templates` | 作品书架、内置模板和私人样例库 |
| `/projects` | Galgame 存档槽、列表/网格视图、筛选、复制、删除、导出和继续编辑 |

浏览器路由由原生 `history.pushState` 驱动。FastAPI 只为以上四个主路径返回 `index.html`，不会把 `/api/*`、`/static/*` 或未知扫描路径吞入 SPA fallback。

## 前端模块

- `frontend/app.js`：工作台生成与播放逻辑、场景拖拽排序、素材快速替换、演出轨道和页面装配入口。
- `frontend/js/api-client.js`：项目、版本和样例 API。
- `frontend/js/project-session.js`：800ms 自动保存、最近项目、IndexedDB 快照和断网重试。
- `frontend/js/pages/`：首页、模板页和项目页控制器。
- `frontend/js/components/`：Header、Modal、Toast、命令面板、发布样例、版本、资源和导出中心。
- `frontend/js/motion/`：纸张翻页式路由过场和动效等级；不启用环境粒子 Canvas。
- `frontend/css/`：设计变量、基础层、公共组件、Header、首页、内容库、工作台、动效和响应式规则；`editorial.css` 是最终美术指导覆盖层。

工作台采用四区结构：左侧章节/场景导航，中间 16:9 舞台，右侧角色/场景/剧情记忆/生成任务检查器，底部为对白、角色、表情、背景、BGM、音效和转场轨道。原作与生成参数收进项目设置抽屉。

## 项目保存

项目主数据由后端保存：

```text
data/projects/<project_id>/project.json
data/projects/<project_id>/source.txt
```

浏览器只保存：

- `novel2gal.last_project_id`
- `novel2gal.lastProjectTitle`
- `novel2gal.motionLevel`
- `novel2gal.onboarding.complete`
- IndexedDB `novel2gal-studio/project-snapshots` 离线快照

保存状态包括 `idle / dirty / saving / saved / offline / failed / conflict`。服务器恢复失败但本地存在快照时，工作台会明确提示，不会静默覆盖。

## API

在原有 pipeline 和 media API 之外，现已提供：

```text
GET    /api/projects
POST   /api/projects
GET    /api/projects/{id}
PATCH  /api/projects/{id}
DELETE /api/projects/{id}
POST   /api/projects/{id}/duplicate
GET    /api/projects/{id}/versions
POST   /api/projects/{id}/versions/{version_id}/rollback
POST   /api/projects/{id}/samples
GET    /api/samples
GET    /api/samples/{id}
POST   /api/samples/{id}/clone
DELETE /api/samples/{id}
```

公开样例禁止包含原文全文；前端默认私人、不包含原文、包含生成脚本并允许复制。

## 素材

首页插画替换方法见根目录 `ASSETS_GUIDE.md`。素材清单里的远程 URL 仅用于来源记录和下载。背景、立绘和 BGM 使用随部署制品发布的运行时副本：

```text
/static/assets/runtime/<asset-id>.<extension>
```

部署前按许可运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\download_assets.ps1
```

缺少第三方素材时，舞台使用 CSS 渐变、结构化道具和人物剪影降级，不请求远程热链。

## 本地运行

```powershell
cd D:\PyCharmPojects\Novel2Gal\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

访问 `http://127.0.0.1:8001/`。

## Nginx 与 FastAPI

推荐让 FastAPI 继续处理 API，Nginx 代理全部请求：

```nginx
location / {
    proxy_pass http://127.0.0.1:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

如果 Nginx 独立托管前端，只允许 `/`、`/create`、`/templates`、`/projects` fallback 到 `index.html`。`/api/` 必须反向代理，`/static/` 必须真实返回文件或 404，不能统一 fallback。

第三方原始素材目录默认被 Git 忽略；背景、立绘和 BGM 的部署副本位于已跟踪的 `frontend/assets/runtime/`。项目存储目录需要持久卷和写权限，可通过 `PROJECT_STORE_DIR` 与 `SAMPLE_STORE_DIR` 指定。

## 人工验收

1. 直接打开并刷新四个主路由。
2. 检查浏览器返回按钮与带 `project_id` 的工作台恢复。
3. 从模板复制项目，确认舞台、分支和时间线可播放。
4. 修改标题或正文，等待自动保存后刷新。
5. 断网编辑并恢复网络，确认快照提示和自动重试。
6. 保存私人样例；公开样例检查版权二次确认和原文禁用。
7. 在项目页测试搜索、排序、状态筛选、复制、删除、导出。
8. 使用 `Ctrl/Cmd+K`、`Ctrl/Cmd+S`、Space、方向键和 Esc。
9. 在设置中切换到减少动效，确认 Canvas、视差和长过场关闭。
10. 在 390px、768px、1280px 和更宽视口检查布局与键盘焦点。

## 当前边界

- Ren'Py Script、Markdown、JSON 和资源清单可下载；完整 Ren'Py Project ZIP 仍是禁用的预留入口。
- 资源中心展示实际剧本需求，但真实生图、TTS 和资源上传仍取决于后端 provider 的后续实现。
- 版本历史保存脚本结果快照，尚未实现逐字段可视化 diff。
- 当前文件存储适合单机或单实例部署；多实例生产环境应迁移到数据库和对象存储。
