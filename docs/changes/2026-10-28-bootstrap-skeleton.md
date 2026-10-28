# 变更记录 · 2026-10-28-bootstrap-skeleton

| 项 | 值 |
| --- | --- |
| 变更名 | `2026-10-28-bootstrap-skeleton` |
| 作者 | TeamVibe |
| 评审人 | 待指派（组内另一人） |
| 状态 | 规约、规范与**骨架**均已入库；容器验收待执行 |
| 版本 | 骨架验收后打 `v0.0.1-skeleton` |

## 改了什么

分两批落地，第二批是骨架。

### 第一批：规约与规范（不含业务代码）

1. **规约**（`openspec/changes/2026-10-28-bootstrap-skeleton/`）：`proposal.md` 定边界（10 条不做的事）、
   `design.md` 记 13 条选型取舍与 6 条被否决方案、`tasks.md` 分 6 组共 72 条可执行任务（骨架组 17 条排最前）、
   `specs/` 六条能力 **47 条 Requirement / 90 条 Scenario**。
2. **工程规范**（`docs/specs/` 八份）：五类必修 + 三类补充，每份带「判据」或「违反时」。
   落法按生效时机分三处：常驻约束在 `AGENTS.md`，按 glob 的细则在 `.cursor/rules/`（8 个 `.mdc`，带 `globs` frontmatter），
   按场景的流程在 `skills/`（6 个 `SKILL.md`）。
3. **可执行门禁**（`Makefile` + `scripts/`）：把规范里的判据做成命令。
4. **交付记录**（`docs/lesson-07/`）。

### 第二批：骨架（`tasks.md` 第 1 组 1.1–1.15）

**后端**（`backend/`，FastAPI + SQLAlchemy 2.x async + pydantic-settings + structlog）：

| 文件 | 职责 |
| --- | --- |
| `app/main.py` | 装配顺序 Settings → 日志 → 中间件 → 异常处理器 → 路由；`SIGTERM` 优雅停机 30 秒 |
| `app/core/config.py` | 8 个必填键（清单以 `02` §7 为唯一权威）；缺失打一行 JSON 到 stderr 并 `SystemExit(1)` |
| `app/core/logging.py` | structlog 单行 JSON，字段 `ts/level/module/request_id/event` |
| `app/core/ids.py` | ULID 生成与校验（26 位 Crockford Base32，无第三方依赖） |
| `app/core/errors.py` | `ErrorCode` 枚举（0 / 10xx–17xx）+ 统一信封 + 四个全局异常处理器 |
| `app/core/middleware.py` | 纯 ASGI 中间件：`X-Request-ID` 继承或生成 → 日志上下文 → 回写响应头 → 计时 |
| `app/core/deps.py` | `get_current_user` / `require_role` 占位（第 2 组替换函数体，签名不变） |
| `app/api/v1/health.py` | `/health`、`/health/live`、`/health/ready`，免认证、不走信封 |
| `app/api/v1/{auth,me,classes,materials,search,sessions}.py` | 空壳路由，一律 501 `1500` |
| `app/services/health.py` | 并发探测三项依赖，返回纯数据（本层不 import fastapi） |
| `app/repositories/base.py` | 异步引擎与会话工厂 + `ping_db()`（SQL 只在此层） |
| `app/integrations/probes.py` | 出站可达性探测，`llm` 只打 `/models`，不发起计费调用 |

**前端**（`frontend/`，Vue3 + Vite + Element Plus + Pinia）：`main.ts`、`router/index.ts`（仅 `/health`）、
`views/HealthView.vue`（四状态齐全）、`styles/tokens.scss`（间距 8/16/24/32、字号 14/16/20、覆盖 `--el-*`）、
`constants/copy.ts`（全部中文文案）、`api/client.ts`（信封解包 + `ApiError` + ULID）、`nginx.conf`。

**容器**：`Dockerfile.api`（只用 `requirements.lock`、非 root、`--timeout-graceful-shutdown 30`、`--no-access-log`）、
`Dockerfile.web`（node 构建 → nginx）、`docker-compose.yml`（只有 `web` 映射宿主端口）、`.dockerignore`（排除 `.env`）。

**测试**：`backend/tests/` 13 条，覆盖 PC-05 / PC-08 / PC-09 / PC-12 / PC-13 / PC-15。

## 依据哪条规约

| 改动 | 依据 |
| --- | --- |
| 首次提交只放 4 个文件、`.gitignore` 先于代码 | 第 7 课任务清单 §一 |
| 四份文件齐、Scenario 三段、失败路径四类 | 任务清单 §二；`openspec/project.md`「spec 写法」 |
| 八份规范 + 规则/技能两种落法 | 任务清单 §三；`docs/specs/08` §8 |
| 骨架拆成 17 条且排最前，只跑骨架不写业务 | 任务清单 §四；`docs/specs/08` §2 变更规模上限 |
| 分层与依赖方向、错误码分区、校验位置 | `docs/specs/02` §1 §3 §4 |
| `/health` 三端点、2 秒探测、优雅停机 30 秒 | `docs/specs/05` §3 |
| 日志字段与「不得落日志」清单 | `docs/specs/05` §4 |
| 间距 8/16/24/32、字号三级、组件清单 | `docs/specs/01` §8 |
| 只有 `web` 映射宿主端口、`.env` 不进镜像 | `AGENTS.md` §1.3；`docs/specs/03` §4 |

## 门禁结果

```
make check        # 14 项，CI 同环境（gitleaks 8.21.2 + openspec 1.15.0 + 已装前端依赖）
  api-lint api-types api-test api-migrate          ✓
  web-lint web-types web-test e2e                  ✓（e2e 空跑：无 e2e 用例，第 2 组起落地）
  fmt-check layout secret-scan spec-validate docs-lint gate-tamper  ✓
  14 项门禁：fail=0

openspec validate 2026-10-28-bootstrap-skeleton --strict
  Change '2026-10-28-bootstrap-skeleton' is valid

cd backend && pytest -q tests       13 passed
cd frontend && npx vitest run       4 passed
pip-audit -r backend/requirements.lock          No known vulnerabilities found
npm audit --omit=dev --audit-level=high        found 0 vulnerabilities
```

完整输出、端点实测记录与「先红后绿」的修法见 `docs/lesson-07/03-validate-record.md`。

> 上一版这里写的 `gate-tamper 通过` 是错的——实测恒失败（CRLF + 摘要过期）。本轮已修，见校验记录 §7 第 1 条。

## 依赖与扫描

| 项 | 结果 |
| --- | --- |
| 新增运行时依赖 | 后端 11 个（fastapi / uvicorn / pydantic / pydantic-settings / sqlalchemy / asyncpg / alembic / structlog / httpx / qdrant-client / bcrypt），全部锁在 `backend/requirements.lock`（44 项全钉版本）；前端 6 个生产依赖 + 16 个开发依赖，锁在 `frontend/package-lock.json` |
| 平台标记 | `uvloop` 带 `; sys_platform != "win32"`——不加这条 Windows 开发机装不上 |
| `pip-audit` | **通过**：`No known vulnerabilities found`（升级前 starlette 0.41.3 十余条、urllib3 2.3.0 八条） |
| `npm audit` | **通过**：`--omit=dev` 0 漏洞（升级前 markdown-it / vue / axios / element-plus 共 4 high）。devDependencies 的告警单独分诊，不进最终镜像 |
| 镜像扫描 | 未执行（Docker 守护进程未启动） |
| 密钥扫描 | 通过（内置规则，`gitleaks` 未安装） |

## 未完成项（照实记）

| # | 项 | 原因 | 补法 |
| --- | --- | --- | --- |
| 1 | 容器内验收（`docker compose up` + `curl /health` 200） | 编写环境无 Docker 守护进程 | 在能起 Docker 的机器上跑 `tasks.md` 1.16；进程内等价验证见校验记录 §6 |
| 2 | `v0.0.1-skeleton` 标签 | 标签要打在验收通过的壳上，1.16 未完成前不打 | 1.16 通过后 `make tag-skeleton` |
| 3 | 主干保护规则 | 需仓库管理员在 GitHub 设置界面开启 | 禁止直推 `main` + 1 名评审人 + `check` 绿 |
| 4 | 交叉评审 | 需组内另一人 | `docs/lesson-07/04-peer-review.md` 表格 |
| 5 | 另起会话验证「生成代码仍按规范」 | 需第二个会话做对照 | 方法见校验记录 §5 |
| 6 | `e2e` 空跑 | 骨架期只有 `/health` 探活页 | `frontend/e2e/*.spec.ts` 出现后 `make e2e` 自动生效 |
| 7 | 业务实现（第 2–6 组） | 本次只跑骨架，按任务清单 §四「不要一次生成整套业务代码」 | 后续变更逐组 apply |

## 回滚动作

本次涉及代码、容器与门禁文件，回滚分两层：

- 只回滚骨架：`git revert <第二批提交>`，回到「只有规约与规范」的状态；此时 `make layout` 会退回空跑。
- 全部回滚：`git reset --hard <首个提交>`——会丢掉全部规范与骨架，仅在仓库需要重建时使用。
- 数据结构：**无**。骨架不含任何迁移文件，`migrations/versions/` 为空，`make api-migrate` 会显式跳过并打印原因。

## 提交信息

```
Change: 2026-10-28-bootstrap-skeleton
Verify: make check-docs && cd backend && pytest -q tests
Evidence: docs/lesson-07/03-validate-record.md
```
