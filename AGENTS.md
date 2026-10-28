# AGENTS.md · CampusClaw · TeamVibe

本文件是**常驻约束**：每次会话开始、每次改代码都会被读到。按 glob 才生效的细则在 `.cursor/rules/`；只走一遍的流程在 `skills/`。**没落进这两处的规范，等于没有规范。**

---

## 0. 项目事实（改任何代码前先确认这几行）

| 项 | 事实 |
| --- | --- |
| 一句话 | 按班级隔离的课程知识库与解题助手；教师上传本班资料，学生只检索本班资料提问，回答必须带出处。 |
| 部署链路 | 浏览器 → Nginx（`web`）→ FastAPI（`api`）→ PostgreSQL（`db`）与 Qdrant（`qdrant`） |
| 后端入口 | `backend/app/main.py`；分层 `app/{api,services,repositories,models,schemas,core,integrations}` |
| 前端入口 | `frontend/src/main.ts`；目录 `frontend/src/{views,components,api,stores,router}` |
| 技术栈 | 后端 FastAPI + SQLAlchemy 2.x(async) + Alembic + Pydantic v2；前端 Vue3 + Element Plus + Vite + Pinia |
| 接口测试 | `backend/tests/api/<URL 路径>/test_<方法>.py`，报告落 `backend/tests/reports/` |
| 本机入口 | `http://localhost:8080`（端口取自 `.env` 的 `WEB_PORT`） |
| 启动 | `cp .env.example .env` → 填必填键 → `docker compose up --build -d` |
| 门禁 | `make check`，任一子项非零退出码即未通过 |
| 变更命名 | `YYYY-MM-DD-短横小写英文名`，例如 `2026-10-28-bootstrap-skeleton` |

---

## 1. 三条硬约束（违反即回退，不接受例外口头豁免）

### 1.1 跨班一律 404

按 ID 取单条资源时，**归属条件写进查询**：`WHERE id = :id AND class_id = :session_class_id`，取不到即 1301。这就是 fetch-then-check 在本项目的落地形式——不是「先查出来再在业务层判断」，而是查询本身就不返回他人资源。这一步落在 `repositories/`，`services/` 只接收「拿到 / 没拿到」。

「不存在」与「非本班」返回逐字节一致的响应体：

```json
{ "code": 1301, "message": "资源不存在", "data": null, "request_id": "01HQ..." }
```

不得用 403、不得用 200 空对象泄露资源是否存在。

**判据**：A / B 两班各放一条资料，互换 `material_id` 重放请求，两次响应除 `request_id` 外逐字节相同。

### 1.2 班级标识只取自会话

`class_id` 只从服务端会话（HttpOnly Cookie）读取，**不从 query、body、请求头、表单取得**。角色判定不采信客户端声明的 header；前端隐藏入口不是授权手段。

**判据**：手构造 `GET /api/v1/materials?class_id=<他人班级>`，该参数应被忽略（返回本班会话所属班级的数据），而不是被使用。

### 1.3 密钥不入库、不进镜像、不进前端

明文值只出现在各人本机 `.env`；`.env.example` 只写键名。密钥不写进提示词、不进日志、不进响应体、不进前端产物、不进镜像层。

**判据**：在全部提交历史与镜像层中检索 `SESSION_SECRET`、`LLM_API_KEY`、`EMBEDDING_API_KEY` 的原值；命中即为事故，处置方式是**轮换（rotate）**，不是删文件。

---

## 2. 门禁

`make check` 子项固定为：

```
api-lint  api-types  api-test  api-migrate  web-lint  web-types  web-test  e2e
fmt-check  layout  secret-scan  spec-validate  docs-lint  gate-tamper
```

- **不得为了让门禁变绿而放宽其中的检查或删断言。**
- 骨架落地前可只跑 `make check-docs`（`spec-validate` / `docs-lint` / `secret-scan` / `layout`）。
- `gate-tamper` 会比对 `Makefile`、`.githooks/`、`AGENTS.md`、`.cursor/rules/` 的摘要；改动这些文件必须人审并在变更说明里写清改了什么、为什么、怎么验证。
- `t.Skip` / `pytest.skip` / `it.skip` 必须带理由与追踪编号；跳过用例数只许下降。

---

## 3. 提交与评审

提交信息正文写清「改了什么、依据哪条规约」，尾部写三个字段，值必须查得到：

```
Change: 2026-10-28-bootstrap-skeleton
Verify: make check-docs
Evidence: docs/changes/2026-10-28-bootstrap-skeleton.md
```

- 一次变更不超过 `tasks.md` 里的一组任务；超出即拆分。
- 合并前必跑 `make check`；主干保护规则要求 1 名评审人 + 门禁绿。
- 完成定义（DoD）五条见 `docs/specs/08-评审与完成定义规范.md` §1，勾不上即为未完成。

---

## 4. 八份规范落在哪里、什么时候被读到

| 规范 | 文件 | 落法 | 生效时机 |
| --- | --- | --- | --- |
| 产品设计 | `docs/specs/01-产品设计规范.md` | `.cursor/rules/product.mdc` | 改 `frontend/src/**` 时命中 |
| 后端开发 | `docs/specs/02-后端开发规范.md` | `.cursor/rules/backend.mdc` | 改 `backend/**` 时命中 |
| 安全开发 | `docs/specs/03-安全开发规范.md` | 本文件 §1（常驻）+ `.cursor/rules/security.mdc` | **每次会话都读** |
| 测试 | `docs/specs/04-测试规范.md` | `.cursor/rules/testing.mdc` + 技能 `write-tests` | 改 `*_test.py`、`tests/` 时命中 |
| 部署运维 | `docs/specs/05-部署运维规范.md` | `.cursor/rules/ops.mdc` + 技能 `release` | 改 `Dockerfile*`、`compose*`、`deploy/` 时命中 |
| AI 应用 | `docs/specs/06-AI应用规范.md` | `.cursor/rules/ai.mdc` + 技能 `prompt-eval` | 改 `app/integrations/`、`prompts/` 时命中 |
| 数据 | `docs/specs/07-数据规范.md` | `.cursor/rules/data.mdc` + 技能 `data-change` | 改 `migrations/`、`models/` 时命中 |
| 评审与完成定义 | `docs/specs/08-评审与完成定义规范.md` | 本文件 §2 §3（常驻）+ 技能 `review-change` | **每次会话都读** |

放法取决于**生效时机**，不取决于篇幅。

---

## 5. 变更流程（openspec 四命令）

```bash
openspec init --tools <你的 Harness>     # 仓库已初始化，无需重复执行
/opsx-propose <变更名>                   # 起草：proposal.md / design.md / specs/<能力>/spec.md / tasks.md
/opsx-validate <变更名> --strict         # 校验：四份文件齐、每条 Requirement 有 Scenario
/opsx-apply <变更名>                     # 只跑 tasks.md 里被指定的一组
/opsx-archive <变更名>                   # 验收通过后归档，能力基线并入 openspec/specs/
```

**当前变更**：`2026-10-28-bootstrap-skeleton`（骨架待 apply）。

Scenario 必须写三段——**前置条件 / 操作 / 可观测结果**；失败路径至少四条（参数非法、无权限、资源不存在、依赖不可达）；数值写具体，不写「大量」「较快」。

---

## 6. 对助手的要求

1. 改代码前先读对应规则文件；规则与本次请求冲突时，**说清冲突点再动手**，不静默绕过。
2. 不自行放宽门禁、不自行改 `Makefile` / `.githooks/` / `.cursor/` / `AGENTS.md` / `openspec/`。
3. 新增依赖前先说明理由与替代方案；依赖锁定文件必须入库。
4. 代码里不出现密钥字面量、不出现内网地址、不出现 `print` 调试输出（用结构化日志）。
5. 不确定产品行为时，回 `proposal.md` / `spec.md` 找答案；找不到就**先补规约再写代码**。
6. 生成的代码必须按规范分层、按规范命名；做不到时说明是哪条规范在当前场景不可执行，而不是悄悄降级。
