# Novel2Gal 美术素材指南

当前视觉方向为“轻小说编辑部 × 专业 Galgame 制作软件”。运行时只读取本地素材，不使用 CDN 或远程热链。

## 模板封面

`frontend/assets/editorial/` 中包含五张统一美术指导的原创 WebP：

| 文件 | 类型 | 画面方向 |
| --- | --- | --- |
| `campus-rooftop.webp` | 校园恋爱 | 放学后的天台、告白信与樱花 |
| `old-school-recorder.webp` | 悬疑推理 | 黄昏旧校舍、录音笔与半开的门 |
| `rain-convenience.webp` | 日常治愈 | 雨后便利店、暖光与透明伞 |
| `moonlit-forest.webp` | 奇幻冒险 | 月下森林、旧神社、地图与旅伴 |
| `black-rose-hearing.webp` | 黑暗剧情 | 雨天听证室、证言者与黑蔷薇卷宗 |

全部为 1280 × 853，单张约 150–250 KB。模板页从 `frontend/js/pages/templates-page.js` 引用这些文件。

## 统一规范

- 日系轻小说封面插画，细线稿、克制赛璐璐上色、轻微纸张质感。
- 颜色以墨蓝、暖纸白、低饱和场景色为主；樱花粉用于人物/叙事强调，薄荷青用于状态，柔金用于关键细节。
- 禁止霓虹赛博、紫蓝概念拼贴、写实办公摄影、真人头像、发光粒子、UI 截图、文字和水印。
- 保持人物比例、透视、光源与材质统一；类型差异通过构图、环境和局部色彩表达。
- 新增模板封面优先输出 3:2 横图，再由书架组件分别裁切为大横卡或竖版书封。

## 舞台素材

角色立绘和场景背景保存在 `frontend/assets/vendor/`，来源与许可记录位于 `frontend/assets/asset_manifest.json`。远程 URL 仅用于记录和下载；前端运行时解析为：

```text
/static/assets/vendor/<asset-id>.<extension>
```

部署前可按许可运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\download_assets.ps1
```

## 生成提示词骨架

```text
Japanese visual-novel illustration, hand-directed light-novel cover art,
fine clean linework, restrained cel shading, slight watercolor paper texture,
consistent anatomy and perspective, low-saturation ink navy and warm paper palette,
soft sakura pink accent and muted gold detail, readable at thumbnail size,
no text, no logo, no watermark, no neon, no cyberpunk, no collage,
no photorealism, no glossy AI concept-art look
```
