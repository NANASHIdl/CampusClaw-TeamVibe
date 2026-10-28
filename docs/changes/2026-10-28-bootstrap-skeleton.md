# 变更记录 · 2026-10-28-bootstrap-skeleton

| 项 | 值 |
| --- | --- |
| 变更名 | `2026-10-28-bootstrap-skeleton` |
| 作者 | TeamVibe |
| 评审人 | 待指派（组内另一人） |
| 状态 | 规约与规范已入库；骨架待 apply |
| 版本 | 骨架验收后打 `v0.0.1-skeleton` |

## 改了什么

本次提交把第 7 课要求的三件事落成文件，**不含任何项目业务代码**：

1. **规约**（`openspec/changes/2026-10-28-bootstrap-skeleton/`）：`proposal.md` 定边界（10 条不做的事）、`design.md` 记 13 条选型取舍与 6 条被否决方案、`tasks.md` 分 6 组共 72 条可执行任务（骨架组 17 条排最前）、`specs/` 六条能力 46 条 Requirement 89 条 Scenario。
2. **工程规范**（`docs/specs/` 八份）：五类必修 + 三类补充，每份带「判据」或「违反时」。落法按生效时机分三处：常驻约束在 `AGENTS.md`（三条硬约束 + 门禁 + 提交评审），按 glob 的细则在 `.cursor/rules/`（8 个 `.mdc`），按场景的流程在 `skills/`（6 个 `SKILL.md`）。
3. **可执行门禁**（`Makefile` + `scripts/`）：把规范里的判据做成命令，而不是留在文档里当口号——`layout` 查反向依赖与路由准入、`docs-lint` 查数据字典是否同步、`spec-lint` 查规约结构、`gate-tamper` 查门禁文件是否被偷偷放宽。
4. **交付记录**（`docs/lesson-07/`）：核查清单逐条打勾（含 9 项未完成的说明）、能力↔Scenario 四张表、校验记录（含冷启动试验发现的 6 处缺陷）、交叉评审表格。

## 依据哪条规约

| 改动 | 依据 |
| --- | --- |
| 首次提交只放 4 个文件、`.gitignore` 先于代码 | 第 7 课任务清单 §一 |
| 四份文件齐、Scenario 三段、失败路径四类 | 任务清单 §二；`openspec/project.md`「spec 写法」 |
| 八份规范 + 规则/技能两种落法 | 任务清单 §三；`docs/specs/08` §8 |
| 骨架拆成 17 条且排最前 | 任务清单 §四；`docs/specs/08` §2 变更规模上限 |
| 核查清单逐条打勾、不做粉饰 | 任务清单 §五；`docs/specs/08` §1 完成定义 |

## 门禁结果

```
make check-docs
  spec-lint   通过（6 份 spec / 89 条 Scenario / 三段齐 / 编号唯一 / 失败路径四类）
  docs-lint   通过（8 份规范 / 8 个规则 / 6 个技能 / 字典覆盖 8 表 / 无占位符）
  secret-scan 通过（.env 未跟踪 / 键名无值 / 无令牌形态 / 无私钥块）
  layout      空跑通过（无 backend/app，骨架落地后生效）
  gate-tamper 通过
```

完整输出与三次「先红后绿」的修法见 `docs/lesson-07/03-validate-record.md`。

## 依赖与扫描

| 项 | 结果 |
| --- | --- |
| 新增运行时依赖 | 无（本次不含代码，`requirements.lock` / `package-lock.json` 待第 1 组创建） |
| `pip-audit` | 未执行（无锁文件） |
| `npm audit` | 未执行（无 `package.json`） |
| 镜像扫描 | 未执行（无镜像） |
| 密钥扫描 | 通过（内置规则，`gitleaks` 未安装） |

## 未完成项（照实记）

| # | 项 | 原因 | 补法 |
| --- | --- | --- | --- |
| 1 | 骨架代码 | 本次任务要求「不写代码，只写规范」 | 跑 `tasks.md` 第 1 组 17 条 |
| 2 | `v0.0.1-skeleton` 标签 | 标签要打在可运行的壳上 | 第 1 组验收后 `make tag-skeleton` |
| 3 | 主干保护规则 | 需仓库管理员在 GitHub 设置界面开启 | 禁止直推 `main` + 1 名评审人 + `check` 绿 |
| 4 | 真实 `openspec validate --strict` | 本机未装 openspec | 装好后重跑并追加输出 |
| 5 | 交叉评审 | 骨架未落地无法启动 | `docs/lesson-07/04-peer-review.md` 表格 |
| 6 | 规范生效性验证（改一次代码看它是否按规范生成） | 无代码可改 | 骨架落地后按第 1 组验收重跑 |

## 回滚动作

本次只新增文档与门禁脚本，不涉及数据结构。回滚方式：`git revert <本变更的提交区间>`，或回到首个提交（`git reset --hard <首个提交>`）——后者会丢掉全部规范文件，仅在仓库需要重建时使用。

## 提交信息

```
Change: 2026-10-28-bootstrap-skeleton
Verify: make check-docs
Evidence: docs/changes/2026-10-28-bootstrap-skeleton.md
```
