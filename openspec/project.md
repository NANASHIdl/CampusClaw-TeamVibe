# OpenSpec 项目约定 · CampusClaw · TeamVibe

本文件告诉 Harness 与本项目成员：规约放在哪、怎么写、怎么验收。

## 目录约定

```
openspec/
├── project.md                       # 本文件：约定
├── specs/<能力>/spec.md             # 已归档的能力基线（归档后由 changes 并入）
└── changes/<变更名>/
    ├── proposal.md                  # 为什么做、边界在哪
    ├── design.md                    # 选型与取舍
    ├── tasks.md                     # 可执行清单（骨架排最前）
    └── specs/<能力>/spec.md         # 本次变更新增/修改的能力，用 ADDED / MODIFIED 段
```

变更名格式：`YYYY-MM-DD-短横小写英文名`，例如 `2026-10-28-bootstrap-skeleton`。验收通过后 `openspec archive` 归档到 `changes/archive/<变更名>/`，能力并入 `specs/`。

## spec 写法

- 每个能力一份文件，标题层级固定：`## ADDED Requirements` → `### Requirement: <一句话，带 SHALL>` → `#### Scenario: <编号 + 名称>`。
- Scenario 编号格式 `<能力前缀>-<两位序号>`（`PC` / `ID` / `CR` / `MT` / `RT` / `AS`），全局唯一，被 `docs/lesson-07/02-capability-scenario-matrix.md` 引用。
- **每个 Scenario 必须写三段**：`前置条件` / `操作` / `可观测结果`。可观测结果必须能被一条测试断言（状态码、`code`、字段值、日志字段四者之一）。
- 失败路径至少四条，且必须覆盖这四类：**参数非法、无权限、资源不存在、依赖不可达**。
- 数值写具体（`20 MiB`、`0.35`、`8 条`、`30 秒`），不写「大量」「较快」「适当」。
- 每条读写资源的 Requirement 配一条越权 Scenario（水平越权 + 功能级越权）。

## 本项目的固定事实（写 spec 时直接用，不要再问）

| 项 | 值 |
| --- | --- |
| 技术栈 | 后端 FastAPI + SQLAlchemy 2.x(async) + Alembic + Pydantic v2；前端 Vue3 + Element Plus + Vite + Pinia |
| 存储 | PostgreSQL（业务与切片正文）、Qdrant（向量）、本地 `uploads/`（附件） |
| 接口前缀 | `/api/v1/`；健康检查 `/health`、`/health/live`、`/health/ready` |
| 隔离维度 | `class_id`，只取自会话 |
| 错误码 | 1000 参数 / 1100 未认证 / 1200 越权 / 1300 不存在 / 1400 业务规则 / 1500 依赖不可达 / 1600 频率 |
| 门禁 | `make check` |

## 验收标准（`/opsx-validate <变更名> --strict`）

1. 四份文件齐全：`proposal.md`、`design.md`、`tasks.md`、`specs/<能力>/spec.md`；
2. 每条 Requirement 至少一个 Scenario；
3. Scenario 三段齐、编号唯一、失败路径 ≥ 4 且覆盖四类；
4. `tasks.md` 每组任务可独立执行，骨架组排在最前；
5. 能力与 Scenario 的对应关系能列成两列表（见 `docs/lesson-07/02-capability-scenario-matrix.md`）。
