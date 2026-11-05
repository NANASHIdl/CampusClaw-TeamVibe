# 2026-11-05 · 第 3、4 课能力落地

## 一句话

在既有骨架上实现「登录 → 班级隔离 → 教师上传入库 → 切片与向量入库 → 三种模式检索」，
并把迁移拆成独立的一次性容器；前端补登录、资料列表/详情、检索三个页面。

## 改了什么

### 数据层

- `backend/app/models/`：`users`、`classes`、`memberships`、`auth_sessions`、`login_attempts`、
  `materials`、`chunks` 七张表；`chunks` 增加 `char_start` / `char_end`（第 4 课要求可回溯到字符区间）。
- `backend/migrations/versions/202611052030_create_core_tables.py`：一次性建表，`downgrade()` 逐表逆序删除。
- `backend/migrations/env.py`：`target_metadata` 接上 `Base.metadata`，`alembic check` 才有比对对象。
- `docs/data-dictionary.md`：补 `auth_sessions`、`login_attempts` 两节与 `chunks` 的两个新列。
- 新增依赖 `python-multipart==0.0.20`：FastAPI 的 `UploadFile` / `File(...)` 必须依赖它，缺了会在导入时直接报错。

### 认证与隔离（第 3 课）

- `core/security.py`：bcrypt cost=12、会话令牌生成、令牌 SHA-256。
- `services/auth.py`：口令比对、`(email, ip)` 失败计数与 5 次锁 15 分钟、会话建立与吊销、
  由令牌还原主体。用户不存在时也做一次等价 bcrypt 比对，避免耗时差被用来枚举账号。
- `core/deps.py`：`class_id` 只从 `auth_sessions.class_id` 读出；角色不足统一 404 `1202`。
- 跨班与不存在走同一个出口（`repositories/materials.py::get_in_class` 把 `id` 与 `class_id`
  写进同一条查询），因此响应除 `request_id` 外逐字节一致。

### 上传与切片（第 3、4 课）

- `services/materials.py`：扩展名 + MIME 双重白名单、20 MiB、单批 20 个、本班 500 条上限；
  服务端命名 `<material_id>.<ext>` 落盘；原始名截断 200 字符并过滤路径与元字符；
  写库失败回滚已落盘文件。
- `services/chunking.py`：800 字符 / 重叠 120，优先段落边界、其次句末标点、最后硬切；
  切片带字符区间。
- `services/ingest.py`：正文提取 → 切分 → 嵌入 → 切片入库 → 向量入库 → 置 `ready`；
  任一步失败置 `failed` 并清理切片与向量；启动时把卡在 `processing` 超 10 分钟的资料退回 `pending`。

### 检索（第 4 课）

- `services/retrieval.py`：三种模式，`class_id` 只来自会话（参数里的 `class_id` 不进入函数签名）。
  - 关键词：PostgreSQL 全文检索 + 子串兜底（中文无空格分词，只靠全文检索会漏）。
  - 向量：Qdrant，payload 过滤 `class_id`，阈值 `SEARCH_VECTOR_MIN=0.35`，召回 `SEARCH_TOP_K=8`。
  - 混合：**RRF（Reciprocal Rank Fusion）**，`score = Σ 1/(60 + rank)`，再按最大值归一化到 0–1。
    选择理由：关键词打分与余弦相似度不同量纲，直接加权相加没有可解释性；RRF 只看名次。
- `integrations/embedding.py`：`EMBEDDING_BASE_URL` 为空时用离线确定性嵌入（字符二元组哈希 + L2 归一化），
  填了则走 OpenAI 兼容接口。离线模式的用途是让判据在没有模型密钥的机器上也能复现。
- `integrations/vectorstore.py`：Qdrant 客户端；不可达一律 `1502`，不返回空结果冒充成功。

### 容器

- `docker-compose.yml`：新增一次性 `migrate` 服务（`alembic upgrade head`），`api` 等它成功退出再启动；
  新增 `uploads` 数据卷，容器删了附件还在。迁移不在应用启动时执行（符合 07 §3）。
- `Dockerfile.api`：预建 `/app/uploads` 并交给 `appuser`。

### 前端

- 新增 `views/LoginView.vue`、`MaterialsView.vue`、`MaterialDetailView.vue`、`SearchView.vue`，
  `stores/auth.ts`、`api/{auth,materials,search}.ts`；路由守卫未登录跳登录页。
- 令牌不进 `localStorage`，全部靠 `credentials: 'include'`；检索无命中显示固定文案与两个动作。
- **视觉重做（同日晚些）**：原来的页面是 Element Plus 默认蓝 + 720px 窄版心 + 时间戳原样输出，
  观感很糙。这一轮把视觉层收到 `styles/tokens.scss` 一处：
  - 色板换成墨青主色（`--cc-brand: #1f6f5c`）+ 冷灰画布，主色/次级文字对白底对比度 5.9:1 / 4.8:1，
    满足 01 §9 的 ≥4.5:1；Element Plus 变量整体映射到本套令牌，组件库跟着走，不再出现默认蓝。
  - 版心 1040px（≥1200px 视口放宽到 1120px），新增 `cc-card` 卡片层、`cc-header` 顶栏，
    页面标题/描述/工具区分层；状态区（加载/错误/空）统一装进卡片，避免裸 `el-empty` 贴在灰底上。
  - 登录页改成左右分栏（左品牌区 + 右表单），窄屏 <768px 自动单列。
  - 新增 `utils/datetime.ts`，上传时间显示为 `2026-11-05 21:11` 而不是原始 ISO 串。
- **登录页测试账号区**：4 个种子账号（1 班/2 班的教师与学生）以可点击卡片列出，点一下邮箱与口令一并填入。
  口令来自构建期注入的 `VITE_DEMO_TEACHER_PASSWORD` / `VITE_DEMO_STUDENT_PASSWORD`，
  开关是 `VITE_SHOW_DEMO_ACCOUNTS`；**三个值默认全空**，此时只显示邮箱、提示去 `.env` 取。
  本机 `.env` 里置 `true` 才显示口令——这与「口令不进前端」的硬约束相反，所以做成显式开关，
  正式部署保持空值即可（`docker-compose.yml` 里三个 `build.args` 会随之为空）。

## 依据哪条规约

- `AGENTS.md` §1.1（跨班一律 404）、§1.2（`class_id` 只取自会话）、§1.3（密钥不入库）
- `docs/specs/02-后端开发规范.md` §1 §3 §4 §5 §8（分层、信封、校验位置、事务、分页）
- `docs/specs/03-安全开发规范.md` §2 §5 §6 §10（逐资源授权、令牌存放、附件读取、口令）
- `docs/specs/07-数据规范.md` §1 §2 §3 §7（命名、审计字段、迁移纪律、跨存储一致性）
- `openspec/.../specs/{identity,classroom,materials,retrieval}/spec.md` 的 Scenario

## 与课件或规约有出入的地方（都已确认或已说明）

1. **学生调用教师端接口返回 404 `1202`，不是课件第 3 课判据三写的 403。**
   已与项目所有者确认按仓库规约执行：`AGENTS.md` §1.1 与 `materials/spec.md` MT-21 明确
   「不使用 403」，理由是跨班与角色不足都必须与「资源不存在」不可区分。若要与课件判据逐字对齐，
   只需把 `core/errors.py` 中 `INSUFFICIENT_ROLE` 的 HTTP 映射改为 403，并同步 `02` §3 的表与 MT-21。
2. **上传白名单收窄为 `.md` / `.txt`。** 第 3 课明确写「仅接受 .txt 与 .md，PDF、Word 与图片解析不在本课范围」，
   因此 `UPLOAD_ALLOWED_EXT` 默认改为 `md,txt`；`materials/spec.md` 里 PDF 相关的 MT-01 / MT-03
   属于后续课次的范围，本轮未实现解析器。
3. **Qdrant 点 ID 用 UUID 写法，与 `chunks.id` 是同一个 128 位值。** Qdrant 只接受无符号整数或 UUID，
   不接受 26 位 ULID 字符串。`core/ids.py::ulid_to_uuid` 做同值换写法（16 字节不变），
   payload 内另存 `chunk_id` 原值，所以「切片 ↔ 向量点」仍是一一对应，只是写法不同。
4. **`Idempotency-Key` 未实现。** 它属于 `materials/spec.md` MT-17，不在第 1–4 课要求内；
   实现它需要给 `materials` 加唯一键列与回放存储，留到需要时按规约补。
5. **融合算法写在本文档而非 `design.md`。** `AGENTS.md` §6.2 禁止自行修改 `openspec/`，
   所以算法选择记录在这里；归档变更时应回写 `design.md` §5.4。

## 怎么才算做完

### 静态检查

- `cd backend && ruff check app tests` → All checks passed
- `cd backend && mypy app` → Success: no issues found in 52 source files
- `cd backend && pytest -q tests/unit` → 19 passed
- `bash scripts/layout-check.sh` → layout: 通过（无反向依赖、SQL 只在仓储层、路由均声明准入）
- `bash scripts/docs-lint.sh` → docs-lint: 通过；`sha256sum -c .gates.sha256` → 全部匹配
- `cd frontend && npx vue-tsc --noEmit` → 无输出；`npx eslint src` → 0 error；`npx vitest run` → 4 passed

### 容器内实测（全部有输出为证）

环境：Docker 守护进程 29.8.2，`docker compose up --build -d`，五服务 `db / migrate / qdrant / api / web`。

| 检查 | 结果 |
| --- | --- |
| `migrate` 建表 | 退出码 0，`api` 随后启动 |
| `curl localhost:8080/health` | 200，`deps={"db":"up","qdrant":"up","llm":"up"}` |
| `curl localhost:8080/` | 200，返回 `index.html`（标题 `CampusClaw · TeamVibe`） |
| 静态资源 | `/assets/index-BR1AoZZH.js` 200，1 123 123 字节 |
| SPA 深链 `/login` | 200（回退到 `index.html`） |
| 未登录 `/api/v1/materials` | 401，`code=1101`，含 `request_id` |
| `scripts/verify_lesson34.py` | **28/28 通过**（第 3 课 3 条、第 4 课 3 条、入参校验与未认证） |
| `scripts/verify_lesson34.py --expect-qdrant-down`（先 `stop qdrant`） | **31/31 通过**，`code=1502`、提示改走关键词模式、关键词模式仍可用 |
| `stop qdrant` 后 `/health` | 503 `status=degraded`、`deps.qdrant=down`，`api` 容器仍 `Up` |
| 知识库状态 | 6 份种子资料全部 `ready`，无卡在 `pending` |
| 上传 → 入库 → 检索 | 教师上传 `.md` → `pending` → 1 秒内 `ready`、`chunk_count=1`；`双黑修正` 关键词命中 `score=1.0`、字符区间 0–98 |
| 混合检索排序 | 「红黑树插入后连续红节点」→ 红黑树 `1.0` 排第一、B 树 `0.4919` 排第二（RRF 起效） |
| 原文下载 | 200，255 字节，与上传内容逐字节一致 |
| `docker compose restart api` 后 | 资料仍 `ready`、原文仍可下载、检索仍命中——三个卷都生效 |
| 软删除 | 200，返回 `deleted_at`；随后同词检索 0 条并回固定文案，列表回到 3 条（切片与向量同步清理） |

复现：

```bash
docker compose up --build -d
curl -s http://localhost:8080/health
backend/.venv/Scripts/python.exe scripts/verify_lesson34.py

docker compose stop qdrant
backend/.venv/Scripts/python.exe scripts/verify_lesson34.py --expect-qdrant-down
docker compose start qdrant
```

脚本逐条打印 PASS / FAIL，任一失败退出码非 0。

## 验证阶段发现并修掉的问题

以下四个缺陷都**只有真跑容器才会暴露**，静态检查与单测都发现不了。

1. **容器里的 `DATABASE_URL` 是 `localhost`，`migrate` 连不上库。**
   报错 `Connect call failed ('127.0.0.1', 5432)`。根因是 `.env` 一份文件承担了两个角色：
   既是 compose 的插值源，又是 `env_file`。写成 `${DATABASE_URL:-...}` 时，插值取到的
   就是给宿主机直跑用的 `localhost`，`environment` 又把这份值覆盖回容器。
   修法：`docker-compose.yml` 里容器内地址一律写字面量（服务名 `db` / `qdrant`），
   因为这两个地址由这份 compose 决定，不是可配置项；`.env.example` 补注说明。

2. **`/health/ready` 永远 503，`api` 容器永远 unhealthy。**
   健康检查把 `llm` 当无条件依赖，但本项目离线确定性嵌入模式下根本没有模型服务，
   于是「选择不用模型」变成了「起不来」。
   修法：`services/health.py` 里 `llm` 改为有条件依赖——`EMBEDDING_BASE_URL` 为空时不探测、
   报 `up`（语义是「当前配置下不构成依赖」），deps 取值仍是 `up`/`down`，符合 `05` §3。

3. **`TypeError: can't compare offset-naive and offset-aware datetimes`。**
   `services/auth.py` 拿 `expires_at` / `locked_until` 直接与 `datetime.now(UTC)` 比。
   PostgreSQL 的 `TIMESTAMPTZ` 读回来是 aware，SQLite 的 `DATETIME` 读回来是 naive，
   于是同一段代码在一个后端能跑、在另一个后端崩。修法：加 `_as_utc()` 统一按 UTC 解释
   并对三处比较全部套用——这类 bug 属于「换个环境才炸」，不能靠「生产是 PG 所以不管」放过。

4. **验收脚本自身在降级模式下的判据不自洽。**
   `--expect-qdrant-down` 时混合模式必然 503，脚本却仍断言 200；判据三也还在用混合模式，
   拿到 `data=null` 后崩在 `.get()` 上。修法：降级模式下把「混合模式 200」标为 SKIP，
   判据三改用关键词模式（它考的是「查不到就明说」，与走哪条检索路径无关）。

## 原文下载的三个缺陷（用户反馈「不能下载」后查出）

先复现：带会话 `GET /api/v1/materials/{id}/file` 返回 `200` + 365 字节正文，
浏览器里点「下载原文」确实落地了 `第三章 贪心与交换论证.md`。**主链路是通的**，
但顺着这条路径查出三处会让人以为「下载坏了」的地方：

1. **列表页根本没有下载入口。** 只有详情页标题右侧一个小链接。用户在列表里找下载，
   找不到就是「不能下载」。修法：表格新增「操作」列，每行都有「下载原文」（教师另有「删除」）。
2. **`Content-Disposition` 只有 `filename*=utf-8''…`，没有 ASCII 兜底名。**
   Starlette 遇非 ASCII 文件名时只输出 RFC 5987 那一段，Chrome / Edge / Firefox 认，
   但下载工具与不解析该字段的客户端会拿到空文件名。修法：`_content_disposition()`
   同时给 `filename="material.md"` 与 `filename*=UTF-8''…`（RFC 6266 允许并存，客户端挑一个）。
3. **会话过期时点下载，浏览器会把一屏 JSON 铺在新标签页上。**
   原来的 `<a href>` 直接跳转，401 的 `{"code":1101,…}` 就成了用户看到的全部内容。
   修法：改成 `downloadMaterialFile()` 抓 blob 再触发保存，失败翻译成
   `ElMessage` 提示「未登录或会话已过期」，页面停在原处不掉走。

顺带补了 **HEAD 支持**：原来只注册了 GET，`HEAD …/file` 回 `405`。
下载管理器、杀毒软件、Office 打开远程文档前都会先探 HEAD，405 会被判成「下载失败」。
`HEAD` 与 `GET` 共用同一套归属判定，未登录仍是 `401`、跨班仍是 `404`，不引入新的旁路。

证据（本轮实测）：

| 场景 | 结果 |
| --- | --- |
| `GET`（带会话） | `200`，`content-disposition: attachment; filename="material.md"; filename*=UTF-8''…`，`Content-Length: 365` |
| `HEAD`（带会话） | `200`，响应头与 GET 一致（原来 `405`） |
| `HEAD` 未登录 / 跨班 | `401` / `404`，与 GET 一致 |
| 浏览器点列表「下载原文」 | `suggestedFilename = 第三章 贪心与交换论证.md` |
| 清掉 Cookie 后再点 | 提示「未登录或会话已过期」，`pathname=/materials` 未跳走 |

## 已知偏差（未在本轮处理）
- **Qdrant 客户端 1.20.0 与服务端 1.12.4 相差 8 个次版本**，官方要求不超过 1，运行时会打一条
  兼容性警告。本轮用到的 `create_collection` / `upsert` / `query_points` / `delete` 都是
  1.10 起稳定的接口，实测写入与检索均正常，因此保留现状并在此记录；对齐时把
  `docker-compose.yml` 里的 `qdrant/qdrant` 升到与客户端同代即可。
- `Idempotency-Key`（MT-17）、PDF/Word 解析（MT-01 / MT-03）、教师控制台页面均未实现，
  理由见上一节第 2、4 条与第 6-1 条已知范围。

## 下一步

第 5 课起：助手会话、提示词、技能开关、SSE 流式、MCP 工具接入与作业批改闭环。
`api/v1/sessions.py` 仍是 501 空壳，第 5 课在原地替换。
