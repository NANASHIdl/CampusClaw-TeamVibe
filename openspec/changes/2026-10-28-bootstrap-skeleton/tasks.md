# Tasks · 2026-10-28-bootstrap-skeleton

规则：**每次 `/opsx-apply` 只跑一组**；一组的 diff ≤ 600 行（不含锁文件与迁移）。每条任务都要能独立判定「做完没有」。
第 1 组是骨架，必须先跑完、先验收、先打标签 `v0.0.1-skeleton`，再动业务代码。

---

## 前置（不写代码，组长完成）

- [ ] 0.1 仓库已建，成员全部加入；`main` 开主干保护：禁止直推、要求 1 名评审人、要求门禁绿
- [ ] 0.2 首次提交只有 `README.md` / `.gitignore` / `LICENSE` / `.env.example`，历史中无密钥明文
- [ ] 0.3 每人 clone 后按 `README.md` 跑通一次（此时预期失败在「骨架未落地」，记录在同一份验证记录里）
- [ ] 0.4 `openspec init --tools <Harness>` 完成，`openspec/changes/` 可见本变更

## 1. 骨架（P0，先跑这一组）

**目标**：clone → 填 `.env` → 一条命令启动 → `/health` 成功。不含任何业务实现。

- [ ] 1.1 建后端分层目录：`app/{api/v1,services,repositories,models,schemas,core,integrations}`
- [ ] 1.2 `core/config.py`：pydantic-settings 读全部键；缺必填键 `SystemExit(1)` 并打印键名
- [ ] 1.3 `core/logging.py`：structlog 单行 JSON，字段 `ts/level/module/request_id/event`；开发环境加 console 渲染
- [ ] 1.4 `core/ids.py`：ULID 生成与校验（26 位）
- [ ] 1.5 `core/errors.py`：`ErrorCode` 枚举（登记 1001–1601 全部已用码）+ 统一响应模型 + 全局异常处理器
- [ ] 1.6 中间件：`X-Request-ID` 继承或生成 → 绑定日志上下文 → 回写响应头 → 计时
- [ ] 1.7 `api/v1/health.py`：`/health`、`/health/live`、`/health/ready`；依赖探测各 2 秒超时；`llm` 只查可达性
- [ ] 1.8 `api/v1/` 其余路由挂空壳，统一返回 501 + `code=1500`，响应体注明「未实现」
- [ ] 1.9 `repositories/base.py`：async session 工厂与依赖；不写任何业务查询
- [ ] 1.10 `main.py`：装配顺序 Settings → 日志 → 中间件 → 异常处理器 → 路由；`SIGTERM` 优雅停机 30 秒
- [ ] 1.11 `frontend/` 骨架：`main.ts` + `router/index.ts`（仅 `/health` 探活页）+ `styles/tokens.scss` + `constants/copy.ts` 占位
- [ ] 1.12 `Dockerfile.api`、`Dockerfile.web`、`docker-compose.yml`、`.dockerignore`；`api`/`db`/`qdrant` 不映射宿主端口
- [ ] 1.13 `Makefile`：14 个门禁子项 + `check` / `check-docs` / `test-api` / `test-web` / `e2e` / `eval` / `seed-test`
- [ ] 1.14 `.githooks/pre-commit`：`gitleaks detect --no-git -v` + `fmt-check`；`git config core.hooksPath .githooks`
- [ ] 1.15 `.github/workflows/check.yml`：push / PR 跑 `make check`
- [ ] 1.16 骨架验收：`docker compose up --build -d` 后 `curl localhost:8080/health` 返回 200，`deps` 三项有值；停掉 qdrant 后返回 503 且 `deps.qdrant=down`、api 容器仍 `Up`
- [ ] 1.17 打标签 `v0.0.1-skeleton`，写 `docs/changes/2026-10-28-bootstrap-skeleton.md`

**完成现象**：新人按 `README.md` 从零操作，中间不需要任何人补充口头说明。

## 2. 身份与会话（identity）

- [ ] 2.1 `users` 表迁移 + 模型（bcrypt cost=12，`email` 唯一）
- [ ] 2.2 `POST /api/v1/auth/login`：失败计数 `(email, IP)` 5 次锁 15 分钟 → 429 `1601`；文案不区分用户不存在与口令错误
- [ ] 2.3 会话写入：Cookie `HttpOnly + Secure + SameSite=Lax`，TTL 720 分钟
- [ ] 2.4 `POST /api/v1/auth/logout`：服务端删会话，旧令牌再用 → 401 `1101`
- [ ] 2.5 `GET /api/v1/me`：返回 `id / display_name / role / classes[]`
- [ ] 2.6 登录页 `/login`：四状态 + 锁定倒计时禁用提交
- [ ] 2.7 路由守卫：未登录 → `/login?next=`；已登录访问 `/login` → `/materials`
- [ ] 2.8 用例：ID-01…ID-07 全覆盖（含锁定边界：第 4 次失败仍可登录）

## 3. 班级与成员（classroom）

- [ ] 3.1 `classes`、`memberships` 迁移 + 模型（`UNIQUE(class_id, user_id)`）
- [ ] 3.2 `POST /api/v1/classes`：教师建班，生成 8 位 `join_code`（唯一）
- [ ] 3.3 `POST /api/v1/classes/join`：幂等（已是成员返回 200 与成员信息）
- [ ] 3.4 `GET /api/v1/classes/{id}/members`：本班可见；跨班 404 与不存在一致
- [ ] 3.5 `GET /api/v1/classes`：当前用户可见班级列表
- [ ] 3.6 教师控制台 `/console`：建班、成员列表、`join_code` 可复制
- [ ] 3.7 用例：CR-01…CR-06

## 4. 资料（materials）

- [ ] 4.1 `materials`、`chunks` 迁移 + 模型（索引 `(class_id, created_at DESC, id DESC)`）
- [ ] 4.2 上传：扩展名 + MIME 双重白名单；≤ 20 MiB；单批 ≤ 20 个；本班总数 ≤ 500 → 超出 409 `1402`
- [ ] 4.3 落盘重命名 `<material_id>.<ext>`；原始名截断 ≤ 200 字符且过滤不可见字符
- [ ] 4.4 `Idempotency-Key` 支持：同键重复请求返回首次结果，不新增行
- [ ] 4.5 解析任务：`pending → processing → ready | failed`；启动时把 `processing` 超 10 分钟的重置为 `pending`
- [ ] 4.6 切片：800 字符 / 重叠 120 / 按段落边界；`UNIQUE(material_id, chunk_index)`
- [ ] 4.7 `GET /api/v1/materials`：`page/page_size`（默认 20，上限 50）+ 排序白名单 + `id` 兜底键
- [ ] 4.8 `GET /api/v1/materials/{id}`：切片按 `chunk_index` 升序
- [ ] 4.9 `GET /api/v1/materials/{id}/file`：先判归属再流式返回；**不提供** `/files/*`、`/static/uploads/*`
- [ ] 4.10 `DELETE /api/v1/materials/{id}`：软删 + 7 天后硬删；异步清理 `chunks` / 向量 / 文件
- [ ] 4.11 前端：`/materials` 列表（四状态 + 分页）、`/materials/:id` 详情、上传组件（即时校验 + 进度条）
- [ ] 4.12 用例：MT-01…MT-12（含 20 MiB 与 20 MiB+1 字节边界）

## 5. 检索（retrieval）

- [ ] 5.1 `GET /api/v1/search`：`mode ∈ {keyword, vector, hybrid}`，非法值 400 `1003`
- [ ] 5.2 关键词：PostgreSQL 全文检索，强制 `class_id` 过滤
- [ ] 5.3 向量：嵌入 + Qdrant `search`，payload 过滤 `class_id`；阈值 `SEARCH_VECTOR_MIN=0.35`
- [ ] 5.4 混合：两路并行 → 融合排序 → 取 `top_k=8`；融合算法写进 `design.md`
- [ ] 5.5 结果字段：`material_id / chunk_index / title / snippet / score`；无命中返回 `hits=[]` + 固定文案
- [ ] 5.6 降级：Qdrant 不可达时 `keyword` 可用，`vector` / `hybrid` → 503 `1502` + 「改用关键词模式」
- [ ] 5.7 前端：`/materials` 顶栏检索框 + 无命中形态（固定文案 + 两个动作）
- [ ] 5.8 用例：RT-01…RT-09（含 0.34 / 0.36 阈值边界）

## 6. 提问与会话（assistant）

- [ ] 6.1 `sessions`、`messages`、`ask_logs` 迁移 + 模型（`messages` 只增不改）
- [ ] 6.2 `POST /api/v1/sessions`：建会话，`title` 取首问前 30 字
- [ ] 6.3 `POST /api/v1/sessions/{id}/messages`：question 2–500 字符；SSE 流式；心跳 15 秒；首字节 30 秒超时
- [ ] 6.4 提示词 `prompts/answer_v1.md` + `cite_v1.md`（文件头四行：version / eval / owner / updated）
- [ ] 6.5 出处由服务端生成：`citations` 只含本次真实命中；`[n]` 与 `citations` 一一对应
- [ ] 6.6 无命中：固定文案「资料中未找到相关内容」，`citations=[]`，正文无编号
- [ ] 6.7 超时 20 秒、重试 1 次、退避 500ms；仍失败 503 `1501`；流式中断追加 `error` 事件
- [ ] 6.8 `GET /api/v1/sessions`、`/sessions/{id}`：只本人可见；他人会话 404 与不存在一致
- [ ] 6.9 前端：`/ask`（输入禁用至流式结束）、`/sessions`、`/sessions/:id` + 出处卡片（可跳资料详情对应切片）
- [ ] 6.10 评测集 `backend/tests/eval/cases.jsonl` 20 条（必答 10 / 必拒 10）+ `make eval`
- [ ] 6.11 用例：AS-01…AS-11

## 7. 归档

- [ ] 7.1 `make check` 全绿（14 项）；任一子项红则不开归档
- [ ] 7.2 `/opsx-validate 2026-10-28-bootstrap-skeleton --strict` 通过
- [ ] 7.3 另起一个不带历史上下文的 Harness 会话，只给仓库路径与变更名，能照本文件实现第 1 组
- [ ] 7.4 交叉评审：组内另一人在自己机器上从零启动成功，记录到 `docs/lesson-07/04-peer-review.md`
- [ ] 7.5 `/opsx-archive` 归档，能力并入 `openspec/specs/`；实现中的调整已回写 `design.md` 与本文件
