---
name: spec-change
description: 按 openspec 四命令走一次完整变更（propose → validate → apply → archive）。当需要新增能力、改行为、或规约与实现不一致时使用。
---

# 技能：走一次变更

## 何时用

- 要新增一条能力，或改变已有接口的行为；
- 实现时发现 `spec.md` 写错了（**先改规约，再改代码**）；
- 需要给现有代码补规约（发现某段行为没有对应 Requirement）。

## 步骤

1. **定名**：`YYYY-MM-DD-短横小写英文名`，全小写、只用连字符，例如 `2026-11-04-add-material-reindex`。
2. **先写三件事**（进 `proposal.md` 的 `## Why`）：给谁用、解决什么问题、比现有做法好在哪。写不出第三件，先别开工。
3. **列编号清单 + 边界**（`## What Changes`）：本次交付几条能力，逐条编号；再写「这次不做的事」，至少 5 条。
4. `/opsx-propose <变更名>` 起草四份文件：
   - `proposal.md`：Why / What Changes / Impact（新增依赖、新增配置键、风险与缓解）；
   - `design.md`：每条选型写「选了什么 / 放弃了什么 / 为什么 / 代价」；
   - `specs/<能力>/spec.md`：`## ADDED Requirements` → `### Requirement:` → `#### Scenario: <编号> <名称>`，每个 Scenario 三段（前置条件 / 操作 / 可观测结果）；
   - `tasks.md`：按组切分，**骨架组排最前**，每条任务可独立判定完成。
5. **补 Scenario**：失败路径 ≥ 4，且必须覆盖参数非法、无权限、资源不存在、依赖不可达四类；每条读写资源的 Requirement 配一条越权 Scenario；数值写具体。
6. **校验**：`/opsx-validate <变更名> --strict`。红了先改规约，不要改校验器。
7. **实现**：`/opsx-apply <变更名>`，**一次只跑一组**。实现中若发现规约不可执行，停下来改 `design.md` / `spec.md` / `tasks.md`，再继续。
8. **归档**：门禁全绿 + 交叉评审通过后 `/opsx-archive <变更名>`，能力并入 `openspec/specs/`。

## 完成判据

- `--strict` 通过；能力与 Scenario 的两列表能贴进 `docs/lesson-07/02-capability-scenario-matrix.md`；
- 另起一个不带历史上下文的会话，只给仓库路径与变更名，能照 `tasks.md` 实现；
- 提交信息尾部有 `Change` / `Verify` / `Evidence` 三字段。
