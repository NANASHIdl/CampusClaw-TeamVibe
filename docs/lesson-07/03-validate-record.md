# 校验记录

## 1. 环境

| 项 | 值 |
| --- | --- |
| 日期 | 2026-10-28 |
| 平台 | Windows 11 · Git Bash（`bash 5.x`） |
| Python | 3.13.12（仅用于 `spec-lint` 的三段解析） |
| `openspec` CLI | 未安装（本机 `command -v openspec` 为空），用 `scripts/spec-lint.sh` 按同一组判据兜底 |
| `gitleaks` | 未安装，用 `scripts/secret-scan.sh` 的内置规则兜底 |

> 兜底不等于放宽：`spec-lint.sh` 的判据逐条对应 `openspec validate --strict` 的检查项（四份文件齐、Requirement 有 Scenario、Scenario 三段齐、编号唯一、失败路径四类、tasks 骨架组最前），任一条不满足即非零退出。

## 2. 四条门禁的实际输出

### `make spec-validate`（→ `scripts/spec-lint.sh 2026-10-28-bootstrap-skeleton`）

```
spec-lint: 2026-10-28-bootstrap-skeleton
  ✓ proposal.md   ✓ design.md   ✓ tasks.md   ✓ specs/<能力>/spec.md × 6
  ✓ proposal: Why   ✓ proposal: What Changes   ✓ proposal: Impact
  ✓ assistant: 15 条 Scenario，三段齐
  ✓ classroom: 13 条 Scenario，三段齐
  ✓ identity: 13 条 Scenario，三段齐
  ✓ materials: 21 条 Scenario，三段齐
  ✓ platform-core: 15 条 Scenario，三段齐
  ✓ retrieval: 12 条 Scenario，三段齐
  ✓ Scenario 编号唯一
  ✓ 失败路径: 参数非法   ✓ 无权限   ✓ 资源不存在   ✓ 依赖不可达
  ✓ tasks: 第 1 组为骨架   ✓ tasks: 有可执行条目
spec-lint: 通过
```

首次执行时此项**未通过**：`tasks.md` 的「0. 前置」被当成首组，报「首组不是第 1 组」。修法是把前置段去掉编号，让「1. 骨架」成为第一个编号组——这正好是任务清单「骨架排最前」的要求，不是改判据。

### `make docs-lint`（→ `scripts/docs-lint.sh`）

```
  ✓ 01-产品设计规范.md（10 章）  ✓ 02-后端开发规范.md（11 章）
  ✓ 03-安全开发规范.md（11 章）  ✓ 04-测试规范.md（10 章）
  ✓ 05-部署运维规范.md（9 章）   ✓ 06-AI应用规范.md（9 章）
  ✓ 07-数据规范.md（9 章）       ✓ 08-评审与完成定义规范.md（10 章）
  ✓ 术语表存在   ✓ 页面清单存在   ✓ 数据字典覆盖 8 张表
  ✓ 8 个规则文件   ✓ 6 个技能
  ✓ AGENTS.md: 硬约束 1 / 2 / 3
  ✓ docs/ 无占位符
docs-lint: 通过
```

### `make secret-scan`（→ `scripts/secret-scan.sh`）

```
  · gitleaks 未安装，使用内置规则
  ✓ .env 未被跟踪
  ✓ 已知键名均为空或占位
  ✓ 无 sk-/ghp_/AKIA 形态令牌
  ✓ 无私钥块
secret-scan: 通过
```

首次执行此项**未通过**，但命中原因是 `docs/specs/03` 里「检索 `SESSION_SECRET=`、`LLM_API_KEY=` 后的非空值」这句判据本身被正则当成赋值。修法是收紧正则：只匹配 `=` 后跟 token 形态字符（`[A-Za-z0-9_/+.-]{8,}`）的值，键名引用不再误判。**没有把 docs 排除出扫描范围**——那才是放宽。

### `make layout`（→ `scripts/layout-check.sh`）

```
layout
  · 无 backend/app：骨架未落地，空跑通过（第 1 组任务完成后生效）
layout: 空跑
```

这是本次唯一「空跑通过」的项，原因是没有代码可检查。骨架落地后它会检：七个分层目录齐、`api/` 不依赖 `repositories/`、`repositories/` 不依赖 `services/`、`services/` 无 `fastapi`、SQL 只在 `repositories/`、出站调用只在 `integrations/`、每个路由文件声明准入。

## 3. 未执行项

| 项 | 原因 | 何时补 |
| --- | --- | --- |
| `openspec validate --strict` | 本机无 openspec | 装好后重跑，把输出追加到本节 |
| `make check` 的 10 个代码子项 | 骨架未落地，目标会显式报错退出 | 第 1 组完成后 |
| `make eval` | 无 `backend/tests/eval/` | 第 6 组任务 6.10 完成后 |

## 4. 冷启动 Harness 试验

任务要求：**另起一个不带历史上下文的 Harness 会话，只给仓库路径与变更名，它能照 `tasks.md` 实现。**

做法：新开一个独立会话，只提供仓库路径 `E:/桌面/PKU/starter/Workbuddy/2026-10-28-10-29-20/repo` 与变更名 `2026-10-28-bootstrap-skeleton`，不提供任何背景，要求它回答四个问题：要创建哪些文件、`/health` 的返回结构、文件之间有无矛盾、必填配置键有哪些。**只许读，不许写。**

结论：**能列出实现路径，但暴露出 6 处缺陷**。全部已修，逐条记录如下。

| # | 缺陷 | 类型 | 修法 |
| --- | --- | --- | --- |
| C1 | 骨架组编号不一致：`README.md` 与 `proposal.md` 说「第 4 组」，`tasks.md` 里骨架是第 1 组 | 引用错误 | 两处改为「第 1 组」 |
| C2 | `AGENTS.md` §1.1 说「先取行再校验归属（fetch-then-check）」，`02` §4 说归属判定落在 `repositories/` 查询条件、不在业务层先查再判——**读起来像两套做法** | 规范冲突 | 统一表述：归属条件写进 `WHERE`（`id` + `class_id`），取不到即 1301；明确这就是 fetch-then-check 的落地形式。`AGENTS.md` §1.1 与 `03` §2 同步改 |
| C3 | `02` §8 允许 `page_size` 超限「钳到 50 或报 1004，二者选一」，`platform-core` PC-07 要求「不得静默钳位」 | 规范冲突 | 定为必须报 400 `1004`，删掉「二者选一」 |
| C4 | 必填配置键有三份不一致的清单：`platform-core` 列 8 个、`README.md` 列 7 个（含 `SEED_*`、漏 `WEB_PORT`）、`02` §7 没有清单 | 事实缺失 | `02` §7 立为唯一权威清单（8 个必填 + `SEED_*` 条件必填 + `APP_ENV=prod` 禁 `SEED_*`），`README.md` 改为指向该表 |
| C5 | 中间件文件没有路径（任务 1.6 只写「中间件」），探活页文件名缺失 | 任务不可执行 | 1.6 定为 `core/middleware.py`；1.11 定为 `views/HealthView.vue` |
| C6 | `05` §1 要求的 `requirements.lock`、`package.json`、`package-lock.json`、`nginx.conf` 没有任何任务负责 | 任务缺口 | 新增任务 1.12「依赖与构建文件」，原 1.12–1.15 顺延重编 |

顺带确认的两件事（无需改动）：

- `/health` 不走 `{code,message,data,request_id}` 信封——原先只在 `05` §3 隐含，现已在 `02` §3 加「唯一例外」条款写明，避免实现时两难。
- `Makefile`、`.githooks/pre-commit`、`.github/workflows/check.yml` 仓库里已存在，所以 1.14/1.15 的措辞从「创建」改为「核对生效」。

**这次试验的价值不在「能列出文件」，而在 C2 / C3 / C4 三条**：它们都是「两份文件各自都说得通、放在一起就矛盾」的问题，靠人逐份读很难发现，只有让一个没有上下文的执行者照着做才会撞上。这也是任务清单要求「另起会话」的原因。

## 5. 复核方式

任何人可复现本节结论：

```bash
git clone https://github.com/NANASHIdl/CampusClaw-TeamVibe.git && cd CampusClaw-TeamVibe
make check-docs          # 或逐条：bash scripts/{spec-lint,docs-lint,secret-scan,layout-check}.sh
```
