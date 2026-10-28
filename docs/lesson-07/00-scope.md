# 交付范围

## 本次交付什么

按第 7 课任务清单，本次交付**任务二（规约）、任务三（工程规范）、任务五（核查清单）**的完整产物，以及任务四（骨架）的**可执行规约与任务清单**：

| 任务 | 交付物 | 状态 |
| --- | --- | --- |
| 一 · 建仓库 | `README.md`（一句话定位 + 启动）、`.gitignore`、`LICENSE`、`.env.example`（只写键名） | ✅ 完成 |
| 二 · 功能边界与规约 | `openspec/changes/2026-10-28-bootstrap-skeleton/` 四份文件 + 六份能力 spec | ✅ 完成 |
| 三 · 工程规范 | `docs/specs/` 八份 + `AGENTS.md` + `.cursor/rules/` 八个 + `skills/` 六个 | ✅ 完成 |
| 四 · 项目框架（骨架） | `tasks.md` 第 1 组（17 条任务）+ `design.md` §7 的骨架范围 | ⬜ 未落地代码 |
| 五 · 核查清单 | `docs/lesson-07/01-checklist.md` | ✅ 完成（含未完成项的说明） |

## 为什么骨架没有代码

本次任务明确要求「**不写代码，只写规范**」。因此任务四以两种形式交付：

1. `tasks.md` 第 1 组把骨架拆成 17 条可独立判定的任务（目录、配置、日志、错误码、中间件、健康检查、空壳路由、compose、Makefile、钩子、CI、验收、打标签）；
2. `design.md` §7 明确骨架的**边界**：落地 `main.py` + `core/*` + `health.py` + 空壳路由 + 前端探活页 + 容器与门禁；不落地任何业务表迁移与业务接口。

`README.md` 的「本机怎么跑起来」按骨架落地后的目标状态写，并在该节开头注明「现在执行会在第一步失败——这是预期的」。

## 交付物的自检方式

不依赖口头说明，四条命令即可验证：

```bash
make check-docs        # 文档与规约门禁：layout / secret-scan / spec-validate / docs-lint / gate-tamper
make spec-validate     # 规约结构：四份文件、Requirement 有 Scenario、三段齐、编号唯一、失败路径四类
make docs-lint         # 八份规范章节齐、术语表与页面清单可解析、数据字典覆盖 8 张表
make secret-scan       # 已知键名无值、无 sk-/ghp_/AKIA 形态令牌、无私钥块、.env 未被跟踪
```

输出见 `03-validate-record.md`。

## 已知缺口（不掩饰）

| 缺口 | 影响 | 补法 |
| --- | --- | --- |
| 骨架代码未落地 | `/health` 目前不可访问；`make check` 的 10 个代码子项红 | 执行 `tasks.md` 第 1 组 |
| `v0.0.1-skeleton` 标签未打 | 交付项「骨架标签存在」未满足 | 骨架验收通过后 `make tag-skeleton` |
| 主干保护规则未设置 | 需仓库管理员在 GitHub 设置界面操作 | 见 `01-checklist.md` R1 |
| 未跑真实 `openspec validate --strict` | 本机未安装 openspec，用 `scripts/spec-lint.sh` 按同一组判据兜底 | 装 openspec 后重跑，记录追加到 `03-validate-record.md` |
| 交叉评审未进行 | 需组内另一人在自己机器上从零启动 | `04-peer-review.md` 留了表格，填完即完成 |
