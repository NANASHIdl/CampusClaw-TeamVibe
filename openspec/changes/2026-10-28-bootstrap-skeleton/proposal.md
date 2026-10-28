# Proposal · 2026-10-28-bootstrap-skeleton

| 项 | 值 |
| --- | --- |
| 变更名 | `2026-10-28-bootstrap-skeleton` |
| 作者 | TeamVibe |
| 评审人 | 待指派（组内另一人，不与作者同一人） |
| 状态 | 规约已定稿，骨架待 `/opsx-apply` |

## Why

这门课的班级资料与答疑散落在三处：群聊里的截图、网盘里的课件、教师口头补充的「这题别用那个公式」。学期过半后，学生搜不到本班那一份，教师也说不清某个说法出自哪次课。

用通用大模型直接问，问题更糟：它会给出看起来很像的公式与页码，学生无从核对，教师也无从追责。

三件事必须同时成立，缺一件这个产品就不值得做：

1. **只有本班能看到本班的资料**——跨班访问与「不存在」返回完全一致的 404，不给任何探测空间；
2. **每条回答都能落到具体资料的某一段**——出处由服务端按检索命中生成，不采信模型自报；
3. **没有依据时明说没有**——检索未越过阈值就返回「资料中未找到相关内容」，不编造。

## What Changes

本次交付六条能力（编号即 `specs/<能力>/` 目录名）：

| # | 能力 | 一句话 | 优先级 |
| --- | --- | --- | --- |
| 1 | `platform-core` | 配置外置、统一响应与错误码、请求标识、结构化日志、健康检查、优雅停机 | P0（骨架即包含） |
| 2 | `identity` | 邮箱 + 口令登录、会话 Cookie、角色、注销即吊销 | P0 |
| 3 | `classroom` | 教师建班、学生凭 8 位入班码加入、成员列表 | P0 |
| 4 | `materials` | 教师上传资料（≤ 20 MiB / 单批 ≤ 20 个）、解析切片、状态机、原文受控下载、软删 | P0 |
| 5 | `retrieval` | 关键词 / 向量 / 混合三模式检索，只搜本班，结果带 `material_id` + `chunk_index` | P0 |
| 6 | `assistant` | 提问会话、SSE 流式回答、服务端生成出处、无命中固定文案、历史会话只本人可见 | P0 |

本次**骨架**（第 4 组任务）只落地能力 1，外加能力 2–6 的空壳路由与分层目录；业务实现留给后续变更。

## 这次不做的事（边界）

明确不做，避免范围蔓延：

1. **不做多班级切换**——一个账号在同一时刻只有一个「当前班级」（取最近加入的未归档班级）；切换班级留到下一迭代。
2. **不做教师批改与作业**——没有 `homework` / `submission` 表，没有截止时间与评分。
3. **不做文件格式转换**——只解析 `pdf` / `md` / `txt` / `docx` 的纯文本，不处理图片 OCR、不处理 PPT 动画与公式排版。
4. **不做 OCR 与公式识别**——扫描版 PDF 直接置 `failed`，原因写「无可提取文本」。
5. **不做移动端 App**——只有响应式 Web，断点两档。
6. **不做站内通知与邮件**——入班、上传完成都不发通知。
7. **不做跨班检索与全局搜索**——检索强制带 `class_id`，没有「搜全校」的入口。
8. **不做模型微调与自建推理**——只用外部 API，模型名与版本走配置。
9. **不做多轮追问的上下文压缩**——会话内只带最近 6 条消息进上下文，超出直接截断，不做摘要。
10. **不做管理后台**——没有超级管理员角色，班级由教师自建。

## Impact

**新增目录**：`backend/app/{api,services,repositories,models,schemas,core,integrations}`、`backend/{migrations,tests}`、`frontend/src/{views,components,api,stores,router,styles,constants}`、`deploy/`。

**新增依赖**（骨架期）：

| 侧 | 依赖 | 用途 |
| --- | --- | --- |
| 后端 | `fastapi`、`uvicorn[standard]`、`pydantic-settings`、`sqlalchemy[asyncio]`、`asyncpg`、`alembic`、`bcrypt`、`structlog`、`httpx`、`qdrant-client` | 骨架与后续能力 |
| 前端 | `vue`、`vue-router`、`pinia`、`element-plus`、`axios`、`markdown-it`、`vite` | 骨架与后续能力 |
| 测试 | `pytest`、`pytest-asyncio`、`httpx`（AsyncClient）、`vitest`、`@playwright/test` | 门禁 |

**新增配置键**：见 `.env.example`（`SESSION_SECRET`、`DATABASE_URL`、`QDRANT_URL`、`LLM_*`、`EMBEDDING_*`、`SEARCH_*`、`UPLOAD_*`、`SEED_*`）。

**风险与缓解**：

| 风险 | 缓解 |
| --- | --- |
| 向量检索在中文短问句上召回差 | 混合模式默认；`SEARCH_VECTOR_MIN=0.35` 可调；评测集含 10 条必答 |
| 首次上传大文件导致解析超时 | 上传与解析分离（先落库 `pending`，异步处理），单文件 ≤ 20 MiB |
| 教师误删资料 | 软删 + 7 天保留，列表提供「最近删除」入口留到下一迭代，本期先只做软删 |
| 学生把答案当标准答案 | 每条回答带出处卡片；页脚固定提示「回答基于本班资料，请以课堂讲授为准」 |

## 验收

- `/opsx-validate 2026-10-28-bootstrap-skeleton --strict` 通过；
- 每条能力与 Scenario 的对应关系见 `docs/lesson-07/02-capability-scenario-matrix.md`；
- 骨架组完成后：`clone → 填 .env → docker compose up → /health 200`，中间不需要口头补充。
