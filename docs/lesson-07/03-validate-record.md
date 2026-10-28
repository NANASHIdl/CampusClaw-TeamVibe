# 校验记录

## 1. 环境

| 项 | 值 |
| --- | --- |
| 日期 | 2026-10-28 |
| 平台 | Windows 11 · Git Bash（`bash 5.x`） |
| Python | 3.13.12（跑门禁脚本与后端测试） |
| `openspec` CLI | 未安装（本机 `command -v openspec` 为空），用 `scripts/spec-lint.sh` 按同一组判据兜底 |
| `gitleaks` | 未安装，用 `scripts/secret-scan.sh` 的内置规则兜底 |
| Docker | **守护进程未启动**（`npipe:////./pipe/dockerDesktopLinuxEngine` 连不上），因此容器验收未执行 |
| PyPI | 清华镜像不可达，官方源 `https://pypi.org/simple` 可用（`requirements.lock` 即从官方源安装验证） |

> 兜底不等于放宽：`spec-lint.sh` 的判据逐条对应 `openspec validate --strict` 的检查项，且**比它更严**——
> 见 §7 第 5 条，本轮把「失败路径四类」从全文 grep 改成了逐能力校验。

## 2. 五条门禁的实际输出（2026-10-28 骨架落地后重跑）

### `make spec-validate`（→ `scripts/spec-lint.sh 2026-10-28-bootstrap-skeleton`）

```
spec-lint: 2026-10-28-bootstrap-skeleton
  ✓ proposal.md   ✓ design.md   ✓ tasks.md   ✓ specs/<能力>/spec.md × 6
  ✓ proposal: Why   ✓ proposal: What Changes   ✓ proposal: Impact
  ✓ assistant: 15 条 Scenario，失败路径 8 条，四类齐
  ✓ classroom: 13 条 Scenario，失败路径 10 条，四类齐
  ✓ identity: 13 条 Scenario，失败路径 10 条，四类齐
  ✓ materials: 21 条 Scenario，失败路径 13 条，四类齐
  ✓ platform-core: 15 条 Scenario，失败路径 7 条，四类齐
  ✓ retrieval: 13 条 Scenario，失败路径 6 条，四类齐
  ✓ Scenario 编号唯一
  ✓ tasks: 第 1 组为骨架   ✓ tasks: 有可执行条目
spec-lint: 通过
```

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

### `make layout`（→ `scripts/layout-check.sh`）

**不再是空跑**——骨架落地后它真的在扫代码：

```
layout
  ✓ 分层目录 app/api  ✓ app/services  ✓ app/repositories  ✓ app/models
  ✓ app/schemas  ✓ app/core  ✓ app/integrations
  ✓ api/ 未依赖 repositories/
  ✓ repositories/ 未依赖 services/
  ✓ services/ 无 fastapi 依赖
  ✓ SQL 只在 repositories/
  ✓ 出站调用只在 integrations/
  ✓ 所有路由声明了准入
layout: 通过
```

反向验证（证明它不是摆设）：往 `backend/app/api/v1/me.py` 末尾追加一行
`from app.repositories.base import ping_db`，重跑立刻报
`✗ api/ 直接依赖 repositories/（应经 services/）`；删掉该行后恢复通过。

### `make gate-tamper`（→ `sha256sum -c .gates.sha256 --quiet`）

```
gate-tamper: 通过（退出码 0）
```

> **上一版这里写的是「通过」，但实测恒失败。** 详见 §7 第 1 条。

## 3. 后端测试

```
$ cd backend && pytest -q tests
.............                                                            [100%]
13 passed in 1.50s
```

覆盖的 Scenario：

| 用例文件 | 覆盖 |
| --- | --- |
| `tests/api/health/test_get.py`（5 条） | PC-12 依赖全 up → 200；PC-13 qdrant down → 503 且 `deps.qdrant=down`；`/health/live` 不查依赖；`/health` 不走统一信封；`/health/ready` 语义一致 |
| `tests/api/materials/test_get.py`（5 条，参数化） | PC-15 五条业务路由返回 501 + `code=1500` + `message="未实现"`，`request_id` 与响应头一致 |
| `tests/api/not_exist_route/test_get.py`（3 条） | PC-05 未知路径 404 `1301`；PC-08 合法 `X-Request-ID` 继承；PC-09 非法 `X-Request-ID` 被替换且不含 `<script>` |

## 4. 冷启动 Harness 试验（2026-10-28 上一轮，保留）

任务要求：**另起一个不带历史上下文的 Harness 会话，只给仓库路径与变更名，它能照 `tasks.md` 实现。**

做法：新开一个独立会话，只提供仓库路径与变更名 `2026-10-28-bootstrap-skeleton`，不提供任何背景，
要求它回答四个问题：要创建哪些文件、`/health` 的返回结构、文件之间有无矛盾、必填配置键有哪些。**只许读，不许写。**

结论：**能列出实现路径，但暴露出 6 处缺陷**。全部已修，逐条记录如下。

| # | 缺陷 | 类型 | 修法 |
| --- | --- | --- | --- |
| C1 | 骨架组编号不一致：`README.md` 与 `proposal.md` 说「第 4 组」，`tasks.md` 里骨架是第 1 组 | 引用错误 | 两处改为「第 1 组」 |
| C2 | `AGENTS.md` §1.1 说「先取行再校验归属（fetch-then-check）」，`02` §4 说归属判定落在 `repositories/` 查询条件、不在业务层先查再判——**读起来像两套做法** | 规范冲突 | 统一表述：归属条件写进 `WHERE`（`id` + `class_id`），取不到即 1301；明确这就是 fetch-then-check 的落地形式 |
| C3 | `02` §8 允许 `page_size` 超限「钳到 50 或报 1004，二者选一」，`platform-core` PC-07 要求「不得静默钳位」 | 规范冲突 | 定为必须报 400 `1004`，删掉「二者选一」 |
| C4 | 必填配置键有三份不一致的清单：`platform-core` 列 8 个、`README.md` 列 7 个、`02` §7 没有清单 | 事实缺失 | `02` §7 立为唯一权威清单，`README.md` 改为指向该表 |
| C5 | 中间件文件没有路径，探活页文件名缺失 | 任务不可执行 | 1.6 定为 `core/middleware.py`；1.11 定为 `views/HealthView.vue` |
| C6 | `05` §1 要求的 `requirements.lock`、`package.json`、`nginx.conf` 没有任何任务负责 | 任务缺口 | 新增任务 1.12「依赖与构建文件」 |

**这次试验的价值不在「能列出文件」，而在 C2 / C3 / C4 三条**：它们都是「两份文件各自都说得通、放在一起就矛盾」的问题，
靠人逐份读很难发现，只有让一个没有上下文的执行者照着做才会撞上。这也是任务清单要求「另起会话」的原因。

## 5. 未执行项

| 项 | 原因 | 何时补 |
| --- | --- | --- |
| `docker compose up --build -d` + `curl localhost:8080/health` | 编写环境 Docker 守护进程未启动 | 在能起 Docker 的机器上执行，勾 `tasks.md` 1.16 |
| `openspec validate --strict` | 本机无 openspec | 装好后重跑，把输出追加到本节 |
| `make eval` | 无 `backend/tests/eval/`（第 6 组任务 6.10） | 第 6 组完成后 |
| 交叉评审 | 需组内另一人 | `04-peer-review.md` |
| 另起会话验证「生成代码仍按规范」 | 需第二个会话做对照 | 方法：新开会话，只给仓库路径 + 一句话「按 `02-后端开发规范.md` 新增一个 `GET /api/v1/classes/{id}` 只读接口」，比对两次产出的分层与命名是否一致 |

## 6. 骨架的进程内验证（替代容器验收的等价证据）

容器起不来，改用进程内方式验证同一批断言。启动命令与容器内一致（`--no-access-log` 去掉 uvicorn 非 JSON 日志）：

```bash
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8125 --no-access-log --log-level warning
```

### 6.1 端点行为

| 请求 | 实测 | 对应 Scenario |
| --- | --- | --- |
| `GET /health/live` | `200` `{"status":"ok","version":"0.0.1","commit":"smoke","time":"2026-10-28T03:28:46.216Z"}` | PC-12 的免认证分支 |
| `GET /health`（依赖全挂） | `503` `{"status":"degraded",...,"deps":{"db":"down","qdrant":"down","llm":"down"}}` | PC-13 降级不崩溃 |
| `GET /api/v1/materials` | `501` `{"code":1500,"message":"未实现","data":null,"request_id":"01M6..."}` | PC-15 |
| `GET /api/v1/nope` | `404` `{"code":1301,"message":"资源不存在","data":null,"request_id":"01M6..."}` | PC-05 |
| `-H "X-Request-ID: 01HQ7Z3K9V2M4T8R6B1C0X5DNP"` | 响应头原样返回该值 | PC-08 |
| `-H "X-Request-ID: <script>alert(1)</script>"` | 响应头替换为新 ULID，日志无 `<script>` | PC-09 |

### 6.2 日志

stdout 每一行都是单行 JSON，`json.loads` 全部成功。样本：

```json
{"module": "api", "route": "/health", "status": 503, "latency_ms": 2412, "request_id": "01M608VB3JEYCMG5Y10JRWS8RX", "level": "info", "ts": "2026-10-28T03:28:53.215Z", "event": "request_done"}
{"module": "api", "dep": "qdrant", "error_code": 1502, "request_id": "01M608VB3JEYCMG5Y10JRWS8RX", "level": "warning", "ts": "2026-10-28T03:28:53.208Z", "event": "dep_unreachable"}
```

必填字段 `ts` / `level` / `module` / `request_id` / `event` 齐；`request_done` 另带 `route` / `status` / `latency_ms`；
同一次 `/health` 请求的 4 条日志（3 条 `dep_unreachable` + 1 条 `request_done`）`request_id` 完全一致。

### 6.3 配置缺失即启动失败

| 场景 | stderr | 退出码 |
| --- | --- | --- |
| 删掉 `SESSION_SECRET` | `{"ts":"...","level":"error","module":"config","event":"missing_env","keys":["SESSION_SECRET"]}` | **1** |
| `SESSION_SECRET` 设为 31 字节 | `{...,"event":"invalid_env","keys":["SESSION_SECRET"],"reason":"min_length_32"}` | **1** |
| `WEB_PORT=abc` | `{...,"event":"invalid_env","keys":["WEB_PORT"],"reason":"invalid_value"}` | **1** |
| 8 个必填键齐全 | 无输出，应用装配成功（24 条路由） | **0** |

## 7. 本轮修掉的缺陷

| # | 缺陷 | 怎么发现的 | 修法 |
| --- | --- | --- | --- |
| 1 | `gate-tamper` 恒失败，但上一版本文件写「通过」 | `sha256sum -c .gates.sha256`：11 个文件全部「无法读取」 | ① `.gates.sha256` 是 CRLF，`sha256sum` 把 `\r` 当文件名的一部分；② 去掉 `\r` 后 11 项摘要**全部不匹配**（`Makefile` 实际 `72af7a5a…`，记录 `9148771d…`），说明摘要在文件定稿前生成、之后没重算。已用 `sha256sum`（LF）重算，现退出码 0 |
| 2 | `requirements.lock` 在 Windows 上装不上 | `pip install -r requirements.lock` → `RuntimeError: uvloop does not support Windows` | `uvloop==0.21.0; sys_platform != "win32"`。团队开发机就是 Windows 11，不加这条全组都装不上 |
| 3 | 日志不是 JSON 而是 console 渲染 | 起服务看 stdout：`2026-10-28 11:27:12 [info] request_done latency_ms=0 ...` | `get_logger()` 里 `structlog.get_logger().bind(module=...)` 会**立刻实体化** lazy proxy，于是在 `configure_logging()` 之前 import 的 `core.errors`、`core.middleware` 永久停在默认 ConsoleRenderer。改为 `structlog.get_logger(module=...)` 延迟绑定；并把「dev 自动 console」改成显式 `LOG_FORMAT=console`，默认一律 JSON |
| 4 | `layout` 把散文当违规 | 骨架落地后报 `✗ services/ 出现 fastapi 依赖`，但该文件只 import 了 repositories 与 integrations | 命中的是注释里那句「本层不 import fastapi」。三个依赖检查从全文 grep 改为只匹配 `^[[:space:]]*(from\|import)[[:space:]]+`；已注入真实违规验证仍能抓到 |
| 5 | `retrieval` 缺「资源不存在」失败路径 | `spec-lint` 收紧为逐能力校验后立刻报 `retrieval: 失败路径未覆盖 资源不存在` | 补 RT-13「会话所属班级已不存在 → 404 `1301`」。原矩阵表 C 把 RT-09（资料未就绪，断言 `hits=[]`）当成「资源不存在」，语义不对——**这是门禁抓到规约缺口，不是为了让门禁变绿而放宽** |

## 8. 复核方式

任何人可复现本节结论：

```bash
git clone https://github.com/NANASHIdl/CampusClaw-TeamVibe.git && cd CampusClaw-TeamVibe
make check-docs                                  # 或逐条跑 scripts/ 下四个脚本 + sha256sum -c
cd backend && pip install -r requirements.lock && pytest -q tests
docker compose up --build -d && curl -s localhost:8080/health
```
