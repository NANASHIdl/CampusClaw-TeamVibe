## ADDED Requirements

### Requirement: 配置外置且缺失即启动失败

系统 SHALL 只从环境变量读取配置（`core/config.py`），必填键缺失或取值不合法时拒绝启动，不得以默认值或随机值继续运行。

必填键：`SESSION_SECRET`（≥ 32 字节）、`DATABASE_URL`、`QDRANT_URL`、`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`EMBEDDING_MODEL`、`WEB_PORT`。

#### Scenario: PC-01 完整配置下正常启动

- **前置条件**：`.env` 中上述 8 个必填键均已填值；PostgreSQL 与 Qdrant 容器可连通。
- **操作**：`docker compose up --build -d`，等待 15 秒后执行 `curl -si localhost:8080/health`。
- **可观测结果**：HTTP 200；响应体 `status="ok"`、`deps.db="up"`、`deps.qdrant="up"`、`deps.llm="up"`；响应头含 `X-Request-ID`，值为 26 位大写字母数字。

#### Scenario: PC-02 缺少必填键时启动失败

- **前置条件**：`.env` 中删去 `SESSION_SECRET` 一行，其余键完整。
- **操作**：`docker compose up api`。
- **可观测结果**：容器在 10 秒内以退出码 1 结束；标准错误输出最后一行是单行 JSON，含 `"level":"error"`、`"event":"missing_env"`、`"keys":["SESSION_SECRET"]`；进程不监听 8000 端口（`curl localhost:8000` 连接被拒）。

#### Scenario: PC-03 `SESSION_SECRET` 过短视为缺失

- **前置条件**：`SESSION_SECRET` 设为 31 字节字符串，其余键完整。
- **操作**：启动 `api`。
- **可观测结果**：退出码 1，日志 `"event":"invalid_env"`、`"keys":["SESSION_SECRET"]`、`"reason":"min_length_32"`。

### Requirement: 统一响应结构与错误码

系统 SHALL 让成功与失败走同一外层结构 `{code, message, data, request_id}`，由全局异常处理器产出；路由函数只返回业务对象。

错误码分区：1000 参数 / 1100 未认证 / 1200 越权与跨资源 / 1300 不存在 / 1400 业务规则 / 1500 依赖不可达 / 1600 频率。

#### Scenario: PC-04 成功响应结构固定

- **前置条件**：已登录会话。
- **操作**：`GET /api/v1/me`。
- **可观测结果**：HTTP 200；`code=0`、`message="ok"`；`data` 为对象；`request_id` 与响应头 `X-Request-ID` 完全一致；响应体不含 `traceback`、`stack`、`sql` 任一字段。

#### Scenario: PC-05 未知路径返回 404 与登记错误码

- **前置条件**：服务已启动。
- **操作**：`GET /api/v1/not-exist-route`。
- **可观测结果**：HTTP 404；`code=1301`、`message="资源不存在"`、`data=null`；响应体字段名与顺序与其它 404 响应一致。

#### Scenario: PC-06 未认证请求被拒且不泄露资源

- **前置条件**：请求不带 Cookie。
- **操作**：`GET /api/v1/materials`。
- **可观测结果**：HTTP 401；`code=1101`；`message` 不含「班级」「资料」等资源词；响应体不出现任何 `material_id`。

#### Scenario: PC-07 分页参数非法返回 400

- **前置条件**：已登录。
- **操作**：`GET /api/v1/materials?page=0&page_size=500`。
- **可观测结果**：HTTP 400；`code=1004`；`data=null`；响应体不含任何资料条目（**不得静默钳位后返回数据**）。

### Requirement: 请求标识贯穿全链路

系统 SHALL 为每个请求分配或继承 `request_id`（ULID 26 位），写入日志上下文与响应头；请求头带 `X-Request-ID` 且格式合法时继承之。

#### Scenario: PC-08 请求标识可从响应头串到日志

- **前置条件**：服务已启动，日志输出到 stdout。
- **操作**：`curl -si -H "X-Request-ID: 01HQ7Z3K9V2M4T8R6B1C0X5DNP" localhost:8080/api/v1/materials`，随后 `docker compose logs api | grep 01HQ7Z3K9V2M4T8R6B1C0X5DNP`。
- **可观测结果**：响应头 `X-Request-ID` 原样返回该值；日志中至少 2 条记录（`module=api` 与 `module=services`）含同一 `request_id`；每条记录都是单行合法 JSON。

#### Scenario: PC-09 非法请求标识被替换而非透传

- **前置条件**：服务已启动。
- **操作**：`curl -si -H "X-Request-ID: <script>alert(1)</script>" localhost:8080/health`。
- **可观测结果**：HTTP 200；响应头 `X-Request-ID` 为新生成的 26 位 ULID，不等于传入值；日志中不出现 `<script>` 字样。

### Requirement: 结构化日志一行一条 JSON

系统 SHALL 以单行 JSON 输出日志，必填字段 `ts`、`level`、`module`、`request_id`、`event`；错误事件必带 `error_code`；带耗时的事件必带整数 `latency_ms`。

#### Scenario: PC-10 访问日志字段齐全

- **前置条件**：服务已启动，`LOG_LEVEL=info`。
- **操作**：`curl -s localhost:8080/api/v1/me`（带有效 Cookie）。
- **可观测结果**：stdout 出现一条记录，`json.loads` 成功；含 `ts`（ISO8601 带毫秒与 `Z`）、`level="info"`、`module="api"`、`request_id`（26 位）、`event="request_done"`、`latency_ms`（整数 ≥ 0）、`route="/api/v1/me"`、`status=200`。

#### Scenario: PC-11 敏感值不落日志

- **前置条件**：以 `LOG_LEVEL=debug` 启动，执行一次登录与一次提问。
- **操作**：`docker compose logs api`，用 `SESSION_SECRET` 的原值、口令原值、提问原文分别检索。
- **可观测结果**：三者均 0 命中；日志中出现的会话标识是哈希前 8 位或省略，不是原值。

### Requirement: 健康检查免认证并返回依赖连通状态

系统 SHALL 提供 `/health`、`/health/live`、`/health/ready` 三个免认证端点；依赖探测各带 2 秒超时；任一依赖不可达时 `/health` 与 `/health/ready` 返回 503，进程不退出。

`llm` 探测只做 HTTP 可达性检查，不得发起计费调用。

#### Scenario: PC-12 依赖全部可达

- **前置条件**：三个依赖容器均 `Up`。
- **操作**：`curl -s localhost:8080/health`。
- **可观测结果**：HTTP 200；`deps` 三个键值均为 `"up"`；`version` 与 `commit` 非空；`time` 为 UTC ISO8601；整个响应耗时 < 2500 ms。

#### Scenario: PC-13 向量库不可达时降级不崩溃

- **前置条件**：服务已启动且 `/health` 返回 200。
- **操作**：`docker compose stop qdrant`，等待 5 秒后 `curl -s -o /dev/null -w "%{http_code}" localhost:8080/health`，再 `docker compose ps api`。
- **可观测结果**：HTTP 503；响应体 `deps.qdrant="down"`、`deps.db="up"`；`api` 容器状态仍为 `Up`（不重启、不退出）；日志出现 `"event":"dep_unreachable"`、`"dep":"qdrant"`、`"error_code":1502`。

### Requirement: 优雅停机

系统 SHALL 在收到 `SIGTERM` 后停止接受新连接、处理完在途请求再退出，上限 30 秒；超时强制退出并记录 `event="shutdown_forced"`。

#### Scenario: PC-14 在途请求不被中断

- **前置条件**：服务已启动；构造一个耗时约 3 秒的请求（`GET /api/v1/materials?page_size=50` 在大数据量下或注入延迟的测试端点）。
- **操作**：发出请求后 1 秒执行 `docker compose stop api`。
- **可观测结果**：该请求返回完整响应（HTTP 200 或业务错误码），不出现连接重置；容器在 5 秒内退出；日志最后一条 `event="shutdown_complete"` 且 `latency_ms` < 30000。

### Requirement: 未实现路由显式声明

系统 SHALL 让骨架期未实现的能力路由返回 501 与 `code=1500`，响应体注明「未实现」，不得返回 404（避免被误认为路由未挂载）。

#### Scenario: PC-15 骨架期业务路由返回 501

- **前置条件**：骨架版本（未落地业务实现），带有效会话。
- **操作**：`GET /api/v1/materials`。
- **可观测结果**：HTTP 501；`code=1500`；`message="未实现"`；响应头 `X-Request-ID` 存在；日志 `event="not_implemented"`、`route="/api/v1/materials"`。
