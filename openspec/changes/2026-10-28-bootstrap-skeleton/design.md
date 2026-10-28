# Design · 2026-10-28-bootstrap-skeleton

本文件记录**选型与取舍**：选了什么、放弃了什么、为什么、代价是什么。实现过程中的调整要同步回本文件（任务 4.9）。

---

## 1. 总体形态

```
浏览器（Vue3 + Element Plus）
   │  HTTPS，同源
   ▼
Nginx（web 容器，端口 WEB_PORT=8080）
   ├── /            → 前端静态产物 dist/
   ├── /api/        → api:8000
   └── /health      → api:8000
                     │
                     ▼
              FastAPI（api 容器，8000 不映射宿主）
                 ├── PostgreSQL（db，5432 不映射宿主）
                 ├── Qdrant（qdrant，6333 不映射宿主）
                 └── 外部模型 API（出站白名单）
```

**只暴露一个端口**：`api`、`db`、`qdrant` 都不映射宿主端口。这样做的直接后果是 CORS 不需要配置——前端与接口同源；代价是本地调试接口必须走 `http://localhost:8080/api/v1/...`，不能用 `:8000`。取舍：同源换掉调试便利，值。

## 2. 关键选型

| # | 决策 | 选择了 | 放弃了 | 理由 | 代价 |
| --- | --- | --- | --- | --- | --- |
| D1 | 后端框架 | FastAPI | Django、Flask、Go | 课程要求；Pydantic v2 让「结构校验在入口完成」这条规范可以直接落地成类型声明 | 异步生态不如 Go 简单，必须全链路 async，一处同步阻塞就拖住事件循环 |
| D2 | 前端框架 | Vue3 + Element Plus | React + Ant Design | 课程要求；Element Plus 的 `el-skeleton` / `el-empty` / `el-table` 正好覆盖视图四状态与列表，减少自造样式（对应产品规范 §8 禁止自造样式） | 组件库体积大，首屏需要按需引入 |
| D3 | 认证 | 服务端会话 + HttpOnly Cookie | JWT 放 localStorage | JWT 无法「注销即失效」，且 localStorage 可被 XSS 读取，与安全规范 §5 冲突 | 会话表多一次查询；水平扩展需要共享会话存储（本期单实例，下一迭代接 Redis） |
| D4 | 检索 | 关键词（PG 全文）+ 向量（Qdrant）+ 混合 | 只用向量；只用关键词 | 只用向量在中文短问句上召回不稳；只用关键词对同义表述无能为力。混合模式两者互补，默认 `hybrid` | 两路结果需要融合排序，阈值参数变多（`SEARCH_VECTOR_MIN`） |
| D5 | 切片 | 800 字符 / 重叠 120 字符，按段落边界对齐 | 按固定 token 切；按整篇 | 字符切片不依赖分词器，实现简单可预期；重叠 120 保证跨段问题不被切断 | 长表格会被切散，本期接受（proposal 已声明不做表格结构化） |
| D6 | 流式回答 | SSE（`text/event-stream`） | WebSocket | 单向流足够；SSE 走普通 HTTP，Nginx 只需关 buffering，不需要额外协议升级 | 不能中途客户端发消息打断；断开重连要靠客户端重发 |
| D7 | 主键 | ULID `CHAR(26)` | 自增 BIGINT；UUIDv4 | 有序、可读、不暴露行数（安全规范 §1 的「不泄露资源是否存在」间接受益） | 26 字节字符串索引比 BIGINT 大，本期数据量可忽略 |
| D8 | 迁移 | Alembic，发布时执行 | 启动时 `create_all` | 启动时建表在多副本下会竞争，且不可回滚；与运维规范 §6 冲突 | 多一步发布动作，忘记执行会让新代码打到旧 schema |
| D9 | 错误码 | 分区整数 + 统一外层结构 | 只用 HTTP 状态码；RFC 7807 | 前端要按「业务原因」分支（跨班 / 不存在 / 配额 / 依赖不可达），HTTP 状态码粒度不够 | 需要维护一张登记表，新增码必须登记（后端规范 §3） |
| D10 | 日志 | structlog 输出单行 JSON | 文本日志 + 正则解析 | 结构化字段可直接被 `request_id` 串起来，满足运维规范 §4 | 本地肉眼读起来不如文本舒服，开发环境用 `LOG_LEVEL=debug` 补 `console` 渲染 |
| D11 | 配置 | pydantic-settings + 启动即校验 | 运行时读 `os.environ` | 缺键启动失败（后端规范 §7），把「配置缺失」从运行期故障变成启动期故障 | 本地起服务前必须先填 `.env` |
| D12 | 前端状态 | Pinia，只放会话与当前班级 | Vuex；全局 store 放列表数据 | 列表数据属页面级，放 store 会造成跨页脏数据 | 页面间共享列表需要重新请求 |
| D13 | 向量库 | Qdrant | pgvector | 课程样例链路一致；payload 过滤（`class_id`）在 Qdrant 上表达直接 | 多一个要备份/重建的组件；本期接受「可整表重建」 |

## 3. 后端分层（与后端规范 §1 一致）

```
app/
├── main.py                 装配：Settings → 日志 → 中间件 → 异常处理器 → 路由
├── api/v1/                 路由 + Depends（会话、角色、分页）+ Pydantic 入参
│   ├── auth.py  me.py  classes.py  materials.py  search.py  sessions.py  health.py
├── services/               业务规则与事务边界
│   ├── identity.py  classroom.py  materials.py  retrieval.py  assistant.py
├── repositories/           唯一执行 SQL 的地方
│   ├── users.py  classes.py  materials.py  chunks.py  sessions.py  messages.py
├── models/                 SQLAlchemy 映射（与 docs/data-dictionary.md 一一对应）
├── schemas/                Pydantic 出入参
├── core/                   config / security / logging / errors / deps / ids
└── integrations/           llm / embedding / vectorstore / storage（唯一出站口）
```

依赖方向 `api → services → repositories → models`，`services → integrations`，`core` 全局可用。**反向 import 由 `make check` 的 `layout` 子项阻断**，不靠评审记性。

## 4. 请求生命周期（一次提问）

```
1. Nginx 反代 → api
2. 中间件：生成/继承 X-Request-ID → 绑定日志上下文 → 计时
3. Depends：读会话 Cookie → 载入 user + class_id（不读 query/body）
4. api 层：Pydantic 校验（question 2–500 字符）→ 失败 400/1001
5. services.assistant：
   a. 落 user 消息（事务 1，提交）
   b. 检索：keyword + vector（并行）→ 融合 → 过滤 class_id → 阈值 0.35 → top 8
   c. 未命中 → 固定文案，citations=[]，落 assistant 消息，返回
   d. 命中 → 组装提示词（prompts/answer_v1.md）→ 调模型（超时 20s，重试 1）
   e. 服务端按命中生成 citations → 流式写回
6. 落 assistant 消息 + ask_logs（事务 2）
```

**事务切分的原因**：模型调用是外部调用，不能包在事务里（后端规范 §5）。代价是「用户消息已落库、回答失败」会留下半条会话——由 `outcome=failed` 的 `ask_logs` 记录，前端按错误形态提示重试。

## 5. 数据流与一致性

- `materials` 是事实源，`chunks` 是派生，Qdrant 是 `chunks` 的派生。**派生数据可整表重建**（`deploy/rebuild-index.md`）。
- 上传：落库 `pending` → 投递解析（本期用进程内后台任务，下一迭代换队列）→ `chunks` → 向量 → `ready`。
- 进程内后台任务的代价：api 重启会丢掉未完成的解析任务。缓解：启动时扫 `status=processing` 且 `updated_at` 超过 10 分钟的记录，重置为 `pending` 重跑。

## 6. 前端结构

```
src/
├── main.ts            挂载：router + pinia + Element Plus
├── router/index.ts    路由表 + guards.ts（登录态与角色）
├── api/               axios 实例（withCredentials、X-Request-ID 透传、统一错误映射）
├── stores/session.ts  当前用户与班级
├── views/             与产品规范 §2 的路由一一对应
├── components/        出处卡片、状态标签、空状态、错误块
├── constants/copy.ts  全部中文文案（含视图四状态与无命中文案）
└── styles/tokens.scss 间距/字号/语义色令牌
```

`api/` 层统一把 `{code,message,data}` 拆开：`code !== 0` 抛 `ApiError(code, message)`，视图只处理成功分支与错误块。**页面不直接读 `response.data.data`**。

## 7. 骨架的范围（本次 `/opsx-apply` 只跑这一组）

落地：

- `main.py` + `core/{config,logging,errors,ids}.py`；
- `api/v1/health.py`（三个端点）+ `api/v1/` 其余路由的空壳（返回 501 `1500`，标注「未实现」）；
- `repositories/` 仅建目录与 `base.py`（会话工厂），无业务查询；
- `frontend/` 只建 `main.ts` + `router` + 一个 `/health` 探活页；
- `Dockerfile.api`、`Dockerfile.web`、`docker-compose.yml`、`Makefile`、`.githooks/pre-commit`。

不落地：任何业务表迁移、任何业务接口实现、任何页面视图。

**判据**：骨架完成后 `curl localhost:8080/health` 返回 200 且 `deps` 三项有值；`/api/v1/materials` 返回 501 而不是 404——后者会被误认为路由没挂上。

## 8. 被否决的方案

| 方案 | 否决原因 |
| --- | --- |
| 单体 Django + 模板渲染 | 前端交互（流式回答、出处卡片）需要组件化，模板渲染要写大量 JS，不如直接上 Vue |
| 前端直连模型 API | 密钥会进前端产物，违反安全规范 §4；且无法做服务端出处校验 |
| 用 `pgvector` 替代 Qdrant | 可省一个组件，但课程链路与样例一致更重要，且 Qdrant 的 payload 过滤更直观 |
| 把 `class_id` 放请求头由前端传 | 违反硬约束 2；前端可伪造 |
| 检索失败时回退到「模型自由回答」 | 会编造依据，违反 AI 规范 §5。宁可返回「未找到」 |
| 上传后同步解析再返回 | 20 MiB PDF 解析可能 30 秒以上，接口超时；且事务内夹带外部调用 |

## 9. 待定项（下一迭代）

1. 多班级切换与「最近删除」入口；
2. 解析任务改用独立 worker（替换进程内后台任务）；
3. 会话存储接 Redis，支持多副本；
4. 表格类 PDF 的结构化切片。
