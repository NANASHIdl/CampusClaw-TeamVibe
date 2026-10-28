# 交付范围

## 本次交付什么

按第 7 课任务清单，五节全部交付：仓库、规约、工程规范、**可启动的骨架**、核查清单。

| 任务 | 交付物 | 状态 |
| --- | --- | --- |
| 一 · 建仓库 | `README.md`（一句话定位 + 启动）、`.gitignore`、`LICENSE`、`.env.example`（只写键名） | ✅ 完成 |
| 二 · 功能边界与规约 | `openspec/changes/2026-10-28-bootstrap-skeleton/` 四份文件 + 六份能力 spec（47 Requirement / 90 Scenario） | ✅ 完成 |
| 三 · 工程规范 | `docs/specs/` 八份 + `AGENTS.md` + `.cursor/rules/` 八个 + `skills/` 六个 | ✅ 完成 |
| 四 · 项目框架（骨架） | `backend/`（FastAPI 七层 + `/health` 三端点 + 空壳路由）、`frontend/`（Vue3 探活页）、`Dockerfile.api`、`Dockerfile.web`、`docker-compose.yml` | ✅ 已落地（容器验收待执行，见 tasks.md 1.16） |
| 五 · 核查清单 | `docs/lesson-07/01-checklist.md` | ✅ 完成（26 ✅ / 3 ⚠️ / 3 ⬜，逐条给证据） |

## 骨架做了什么、没做什么

**落地**（`tasks.md` 第 1 组 1.1–1.15）：

- 后端七层目录 + `core/{config,logging,ids,errors,middleware,deps}.py` + `main.py`；
- `/health`、`/health/live`、`/health/ready` 三个免认证端点，依赖探测各 2 秒超时、`llm` 只查可达性；
- 六组业务路由挂空壳，一律 501 `1500`（不是 404，避免被误认为路由没挂上）；
- `repositories/base.py` 只有会话工厂与 `ping_db`，无任何业务查询；
- 前端只有 `/health` 探活页，四状态齐全，样式全部走 `tokens.scss`；
- 容器：只有 `web` 映射宿主端口，`api` / `db` / `qdrant` 不映射；`healthcheck` 打 `/health/ready`；
- 门禁 14 项落地为可执行命令，`layout` / `spec-lint` / `docs-lint` / `secret-scan` / `gate-tamper` 实跑通过。

**未落地**（留给第 2–6 组）：

- 任何业务表迁移、任何业务接口实现、任何业务页面；
- `frontend/package-lock.json`（需 `npm install` 生成，编写环境无外网到 npm registry）；
- `backend/tests/eval/`（第 6 组任务 6.10）。

## 交付物的自检方式

不依赖口头说明，五条命令即可验证：

```bash
make check             # 全量 14 项门禁（CI 跑的就是这一条）
make check-docs        # 其中文档与规约的 5 项：layout / secret-scan / spec-validate / docs-lint / gate-tamper
make spec-validate     # 真实 openspec --strict + 逐能力失败路径校验（两道都跑）
cd backend && pytest -q tests   # 骨架行为：健康检查 200/503、空壳 501、404 信封、request_id 继承与替换
cd frontend && npm ci && npx vitest run   # 前端：ULID 生成器 4 条用例
```

`make check` 的 14 项在 CI 同环境（gitleaks 8.21.2 + openspec 1.15.0 + 已装前端依赖）下全部通过，
输出见 `03-validate-record.md` §2.2。

输出见 `03-validate-record.md`。

## 已知缺口（不掩饰）

| 缺口 | 影响 | 补法 |
| --- | --- | --- |
| 容器内验收未执行 | `docker compose up` 与 `curl localhost:8080/health` 的 200 分支未在真实容器里跑过；进程内验证已覆盖同一批断言 | 在能起 Docker 的机器上跑 `tasks.md` 1.16 |
| `v0.0.1-skeleton` 标签未打 | 交付项「骨架标签存在」未满足 | 1.16 通过后 `make tag-skeleton` |
| 主干保护规则未设置 | 需仓库管理员在 GitHub 设置界面操作 | 见 `01-checklist.md` R1 |
| 交叉评审未进行 | 需组内另一人在自己机器上从零启动 | `04-peer-review.md` 留了表格，填完即完成 |
| `e2e` 空跑 | 骨架期只有 `/health` 探活页，端到端链路第 2 组起落地 | `frontend/e2e/*.spec.ts` 出现后自动生效 |
