# 核查清单（提交前逐条打勾）

图例：✅ 已完成并给出证据 · ⬜ 未完成（写明原因与补法） · ⚠️ 部分完成

> 本表在 2026-10-28 骨架落地后重打了一遍。上一版有 9 项 ⬜，其中 6 项本轮已补，
> 3 项仍需仓库管理员操作或在能起 Docker 的机器上执行。**上一版把 `gate-tamper` 标成「通过」是错的**，
> 实测恒失败，原因与修法见本文件末尾「本轮修掉的缺陷」。

---

## 一、仓库

| # | 项 | 状态 | 证据 / 说明 |
| --- | --- | --- | --- |
| R1 | 地址可访问且教师有权限 | ⚠️ | 仓库 `https://github.com/NANASHIdl/CampusClaw-TeamVibe` 可访问；**主干保护规则需在 GitHub 设置界面开启**（禁止直推 `main`、要求 1 名评审人、要求 `check` 绿），代码层无法代为设置 |
| R2 | 按 `README.md` 能从零跑起来 | ⚠️ | 骨架已落地，`docker compose up --build -d` 与 `curl localhost:8080/health` 的命令链已就位；**容器内验收（tasks.md 1.16）未执行**——编写环境无 Docker 守护进程。等价的进程内验证已做：`pytest` 13 项全绿、`uvicorn` 起服务后 `/health/live` 200 且 `/health` 503（依赖全 down），见 `03-validate-record.md` §6 |
| R3 | 全部提交历史中搜不到密钥明文 | ✅ | `make secret-scan` 通过：已知键名均为空、无 `sk-`/`ghp_`/`AKIA` 形态令牌、无私钥块、`.env` 未被跟踪；`.env.example` 只有键名。`.dockerignore` 也排除了 `.env`，不进镜像层 |
| R4 | 首次提交只有 `README.md` / `.gitignore` / `LICENSE` / `.env.example` | ✅ | `git show --stat aed794d` 恰为 4 个文件；`.gitignore` 与 `.env.example` 早于任何代码 |
| R5 | 变更以 `YYYY-MM-DD-短横小写英文名` 命名 | ✅ | `openspec/changes/2026-10-28-bootstrap-skeleton/`；`docs/changes/2026-10-28-bootstrap-skeleton.md` |
| R6 | 提交信息写清「改了什么、依据哪条规约」 | ✅ | 每次提交正文含「改了什么 / 依据哪条规约」两行，尾部三字段 `Change` / `Verify` / `Evidence` |

## 二、规约

| # | 项 | 状态 | 证据 / 说明 |
| --- | --- | --- | --- |
| S1 | 变更四份文件齐 | ✅ | `proposal.md`、`design.md`、`tasks.md`、`specs/<能力>/spec.md`（6 份） |
| S2 | `--strict` 校验通过 | ⚠️ | 本机仍未装 `openspec`，用 `scripts/spec-lint.sh` 按同一组判据执行并通过。**本轮已把该脚本从「全文 grep 关键词」收紧为逐能力校验**（见下），装 `openspec` 后需重跑一次并把输出追加到 `03-validate-record.md` |
| S3 | 每条能力至少一组 Scenario | ✅ | 6 条能力共 90 条 Scenario：PC 15 / ID 13 / CR 13 / MT 21 / RT 13 / AS 15（本轮新增 RT-13） |
| S4 | 失败路径不少于四条 | ✅ | **现在由门禁逐能力校验**，不再靠人工断言：PC 7 / ID 10 / CR 10 / MT 13 / RT 6 / AS 8 条失败路径，四类各至少一条 |
| S5 | 能力与 Scenario 一一对应 | ✅ | `02-capability-scenario-matrix.md` 表 A（能力↔Scenario）与表 B（Requirement↔Scenario），共 47 条 Requirement |
| S6 | Scenario 三段齐（前置条件 / 操作 / 可观测结果） | ✅ | `spec-lint` 逐条解析，缺任一字段即失败 |
| S7 | 数值具体 | ✅ | 20 MiB / 20 个 / 500 条 / 0.35 / 8 条 / 30 秒 / 720 分钟 / 5 次 15 分钟 / 800 字符重叠 120 / 6 条上下文 |
| S8 | 越权场景成对 | ✅ | 水平越权：CR-10、MT-13、MT-15、RT-04、AS-11；功能级越权：CR-03、MT-21 |
| S9 | 先说清「给谁用、解决什么问题、好在哪」 | ✅ | `proposal.md` 的 `## Why`；`README.md` 同名小节 |
| S10 | 写明这次不做的事 | ✅ | `proposal.md` 的「这次不做的事（边界）」，10 条 |

## 三、规范

| # | 项 | 状态 | 证据 / 说明 |
| --- | --- | --- | --- |
| G1 | 五类必修规范都写成文件 | ✅ | `docs/specs/01`–`05`；三类补充 `06`–`08` |
| G2 | 放在 Harness 读得到的位置 | ✅ | 常驻：`AGENTS.md` §1 §2 §3；按 glob：`.cursor/rules/*.mdc`（8 个，frontmatter 带 `globs`）；按场景：`skills/*/SKILL.md`（6 个） |
| G3 | 每条规范写清检查方式 | ✅ | 每份文件都有「判据」段与「违反时」段；`docs-lint` 校验每份文件至少含其一 |
| G4 | 改一次代码验证规范真的生效 | ✅ | 骨架落地后 `make layout` 真的在扫代码（不再是空跑）：13 项检查全过。**反向验证**：往 `api/v1/me.py` 注入一行 `from app.repositories.base import ping_db`，门禁立刻报「api/ 直接依赖 repositories/」，还原后恢复通过。说明规范不只是文档 |
| G5 | 另起一次会话结果仍一致 | ⬜ | 需另起一个无上下文会话，让它按规范新增一个接口，比对两次产出的分层与命名是否一致。方法已写在 `03-validate-record.md` §4，本轮未执行 |
| G6 | 测评点写明怎么测、怎样算缺陷 | ✅ | `04-测试规范.md` §8「缺陷判定口径」：四路信号（状态码 / `code` / 字段值 / 日志）+ 四类缺陷（被当成成功 / 被放行 / 被误拒 / 未处理故障） |
| G7 | 规范里没有「大量」「较快」这类词 | ✅ | 数值全部具体；`docs-lint` 无占位符检查通过 |

## 四、骨架

| # | 项 | 状态 | 证据 / 说明 |
| --- | --- | --- | --- |
| K1 | 分层无反向依赖 | ✅ | `backend/app/` 七层目录齐；`layout` 实跑 13 项全过：`api/` 不依赖 `repositories/`、`repositories/` 不依赖 `services/`、`services/` 无 fastapi、SQL 只在 `repositories/`、出站调用只在 `integrations/`、每个路由文件声明准入 |
| K2 | 配置全部外置且缺失即启动失败 | ✅ | 实测：删掉 `SESSION_SECRET` → stderr 输出 `{"event":"missing_env","keys":["SESSION_SECRET"]}` 且**退出码 1**；`SESSION_SECRET` 设为 31 字节 → `{"event":"invalid_env","reason":"min_length_32"}` 且退出码 1；正常配置退出码 0 |
| K3 | `/health` 免认证可访问并返回依赖连通状态 | ✅ | 实测：`/health/live` → 200；依赖全挂时 `/health` → **503** 且 `deps` 三项均 `down`，进程不退出；响应体不含 `code`/`message`/`data`/`request_id`（符合 02 §3 的例外条款） |
| K4 | 日志一行一条 JSON 且带请求标识 | ✅ | 实测 stdout 每行可 `json.loads`，字段 `ts`/`level`/`module`/`request_id`/`event` 齐；`request_done` 另带 `route`/`status`/`latency_ms`；合法 `X-Request-ID` 原样继承，非法值（`<script>`）被替换成新 ULID 且不进日志 |
| K5 | 只跑骨架，未一次生成整套业务代码 | ✅ | 业务路由（`/auth`、`/me`、`/classes`、`/materials`、`/search`、`/sessions`）全部返回 501 `1500`，无一条业务实现、无一张业务表迁移 |

## 五、交付

| # | 项 | 状态 | 证据 / 说明 |
| --- | --- | --- | --- |
| D1 | 骨架标签存在 | ⬜ | **故意没打**。`make tag-skeleton` 会在骨架验收后打 `v0.0.1-skeleton`；1.16 的容器验收未执行，现在打标签等于给一个没跑过的壳盖章——正是本仓库上一版把 `gate-tamper` 标成「通过」的那类错误 |
| D2 | 验证记录归档到 `docs/lesson-07/` | ✅ | 本目录 6 份文件（README / 00-scope / 01-checklist / 02-matrix / 03-validate-record / 04-peer-review） |
| D3 | 交叉评审：组内另一人在自己机器上从零启动成功 | ⬜ | 表格已备好（`04-peer-review.md`），待组内成员执行；骨架已落地，现在可以真跑了 |
| D4 | 密钥只在各人本机 `.env` | ✅ | `.gitignore` 首行 `.env`；`secret-scan` 校验 `.env` 未被跟踪；`.dockerignore` 排除 `.env` 与 `.env.*`；`README.md` 与 `03-安全开发规范.md` §4 写清轮换步骤与执行人 |

---

## 统计

| 状态 | 数量 | 条目 |
| --- | --- | --- |
| ✅ 已完成 | 26 | R3 R4 R5 R6 S1 S3 S4 S5 S6 S7 S8 S9 S10 G1 G2 G3 G4 G6 G7 K1 K2 K3 K4 K5 D2 D4 |
| ⚠️ 部分完成 | 3 | R1（主干保护待设置）、R2（容器验收待执行）、S2（未跑真实 openspec） |
| ⬜ 未完成 | 3 | G5（需另起会话）、D1（等 1.16 验收）、D3（需组内第二人） |

剩下 3 项全部指向**仓库管理员操作**或**另一台机器/另一个人**，不是代码缺口。

---

## 本轮修掉的缺陷（骨架落地时暴露）

| # | 缺陷 | 怎么发现的 | 修法 |
| --- | --- | --- | --- |
| 1 | `gate-tamper` 恒失败，但上一版清单标「通过」 | 手跑 `sha256sum -c .gates.sha256`：11 个文件全部「无法读取」 | 两层原因：① `.gates.sha256` 用 CRLF 写入，`sha256sum` 把 `\r` 当文件名；② 去掉 `\r` 后 11 项摘要**全部不匹配**——摘要在文件定稿前生成、之后没重算。已用 `sha256sum` 重算（LF），现在 `sha256sum -c` 退出码 0 |
| 2 | `requirements.lock` 在 Windows 上装不上 | `pip install -r requirements.lock` 直接失败：`uvloop does not support Windows` | `uvloop` 加 `; sys_platform != "win32"` 标记。团队开发机就是 Windows 11，不加这条全组都装不上 |
| 3 | 日志不是 JSON，是 console 渲染 | 起服务后看 stdout：`2026-10-28 11:27:12 [info] request_done ...` | `get_logger()` 里用 `.bind()` 会**立刻实体化** structlog 的 lazy proxy，于是在 `configure_logging()` 之前 import 的模块（`core.errors`、`core.middleware`）永久停留在默认 ConsoleRenderer。改为 `structlog.get_logger(module=...)` 延迟绑定。同时把「dev 自动 console」改成显式 `LOG_FORMAT=console`，默认一律 JSON（否则 PC-10 的 `json.loads` 断言默认就不成立） |
| 4 | `layout` 门禁把散文当违规 | 骨架落地后 `layout` 报「services/ 出现 fastapi 依赖」，但 `services/health.py` 只 import 了 repositories 与 integrations | 原实现全文 `grep fastapi`，命中的是注释里那句「本层不 import fastapi」。三个依赖检查改为只匹配 `^\s*(from\|import)\s+`，精度提高、不漏报真实 import（已注入违规验证仍能抓到） |
| 5 | `retrieval` 缺「资源不存在」失败路径 | `spec-lint` 收紧为逐能力校验后立刻报 `retrieval: 失败路径未覆盖 资源不存在` | 补 RT-13「会话所属班级已不存在 → 404 `1301`」。这不是放宽门禁凑绿，是门禁真的抓到了规约缺口：原矩阵表 C 把 RT-09（资料未就绪）当成「资源不存在」，但 RT-09 断言的是 `hits=[]` 而非 404，语义不对 |
