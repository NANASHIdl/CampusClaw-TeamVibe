## ADDED Requirements

### Requirement: 口令以加盐单向算法存储

系统 SHALL 使用 bcrypt（cost=12）存储口令，不保存明文或可逆密文；比对使用 `bcrypt.checkpw`。

#### Scenario: ID-01 口令不落明文

- **前置条件**：预置账号由 `SEED_*_PASSWORD` 创建完成。
- **操作**：`SELECT password_hash FROM users WHERE email = '<预置教师邮箱>'`；并用该口令原文在全部日志与响应体中检索。
- **可观测结果**：`password_hash` 以 `$2b$12$` 开头、长度 60；口令原文在日志、接口响应、`docs/` 中 0 命中。

### Requirement: 登录建立服务端会话

系统 SHALL 在 `POST /api/v1/auth/login` 校验通过后创建服务端会话，并通过 `Set-Cookie` 下发令牌：`HttpOnly`、`Secure`（`APP_ENV=prod` 时强制）、`SameSite=Lax`、`Path=/`、`Max-Age=SESSION_TTL_MINUTES*60`（默认 43200 秒）。

#### Scenario: ID-02 登录成功下发会话 Cookie

- **前置条件**：用户已存在且未锁定。
- **操作**：`POST /api/v1/auth/login`，body `{"email":"...","password":"..."}`。
- **可观测结果**：HTTP 200；`code=0`；`data` 含 `id`、`display_name`、`role`、`classes`；响应头 `Set-Cookie` 含 `HttpOnly` 与 `SameSite=Lax`，`Max-Age=43200`；响应体不含令牌原值；`data` 中不含 `password_hash`。

#### Scenario: ID-03 口令错误与用户不存在返回一致

- **前置条件**：存在用户 A，不存在用户 B 的邮箱。
- **操作**：分别用「A 的正确邮箱 + 错误口令」与「B 的邮箱 + 任意口令」调用登录。
- **可观测结果**：两次均 HTTP 401、`code=1101`、`message="邮箱或口令不正确"`；两次响应体除 `request_id` 外逐字节相同；两次耗时差 < 200 ms（不因用户不存在而提前返回）。

### Requirement: 登录失败限制

系统 SHALL 按 `(email, 来源 IP)` 计数，连续失败 5 次锁定 15 分钟，锁定期间返回 429 `1601`；成功登录后计数清零。

#### Scenario: ID-04 连续失败 5 次后锁定

- **前置条件**：该 `(email, IP)` 计数为 0。
- **操作**：用错误口令连续调用登录 5 次，第 6 次改用正确口令。
- **可观测结果**：前 5 次均 401 `1101`；第 6 次 HTTP 429、`code=1601`、`message` 含剩余秒数；第 6 次即使口令正确也不下发 Cookie。

#### Scenario: ID-05 第 4 次失败后仍可成功登录（边界）

- **前置条件**：该 `(email, IP)` 计数为 3。
- **操作**：用错误口令失败 1 次（计数变 4），随后用正确口令登录。
- **可观测结果**：第 4 次失败返回 401 `1101`；随后正确登录返回 200 并下发 Cookie；计数清零（再次用错误口令登录返回 401 而非 429）。

#### Scenario: ID-06 锁定 15 分钟后自动解除（边界）

- **前置条件**：该 `(email, IP)` 处于锁定状态，锁定时间戳已过去 15 分 1 秒（用可控时钟或直接改库时间）。
- **操作**：用正确口令登录。
- **可观测结果**：HTTP 200；`code=0`；下发 Cookie。

### Requirement: 注销即服务端吊销

系统 SHALL 在 `POST /api/v1/auth/logout` 时删除服务端会话记录并清除 Cookie，令牌立即失效，不等自然过期。

#### Scenario: ID-07 注销后旧令牌不可用

- **前置条件**：已登录，持有有效 Cookie。
- **操作**：`POST /api/v1/auth/logout`，随后用**同一个**旧 Cookie 调用 `GET /api/v1/me`。
- **可观测结果**：注销返回 200 且 `Set-Cookie` 的 `Max-Age=0`；旧 Cookie 调用 `/me` 返回 401 `1101`；会话表对应行已删除。

### Requirement: 当前用户信息

系统 SHALL 通过 `GET /api/v1/me` 返回 `id`、`display_name`、`role`、`classes[]`（每项含 `id`、`name`、`role`），角色与班级来自服务端会话，不采信客户端声明。

#### Scenario: ID-08 未登录访问当前用户信息

- **前置条件**：请求不带 Cookie。
- **操作**：`GET /api/v1/me`。
- **可观测结果**：HTTP 401；`code=1101`；`data=null`；响应体不含任何用户字段。

#### Scenario: ID-09 伪造角色请求头被忽略

- **前置条件**：以学生身份登录，持有学生会话 Cookie。
- **操作**：`GET /api/v1/me`，附加请求头 `X-Role: teacher`。
- **可观测结果**：HTTP 200；`data.role="student"`；`data.classes[].role` 均为 `"student"`；响应头与日志中不出现 `teacher` 作为该用户的角色。

### Requirement: 登录入参校验

系统 SHALL 在接口入口校验邮箱格式与口令长度（8–72 字符），不合法返回 400 `1001`，不进入业务层。

#### Scenario: ID-10 邮箱格式非法

- **前置条件**：服务已启动。
- **操作**：`POST /api/v1/auth/login`，body `{"email":"not-an-email","password":"12345678"}`。
- **可观测结果**：HTTP 400；`code=1001`；`message` 指明字段名 `email`；不创建会话；不增加失败计数（随后用正确口令仍可登录）。

#### Scenario: ID-11 口令长度越界（边界）

- **前置条件**：服务已启动。
- **操作**：分别用 7 字符与 73 字符口令登录。
- **可观测结果**：两次均 HTTP 400、`code=1001`、`message` 含 `8–72`；均不下发 Cookie。

### Requirement: 认证依赖不可达时明确失败

系统 SHALL 在数据库不可达时让登录返回 503 `1503`，不得返回 500 或 401。

#### Scenario: ID-12 数据库不可达时登录降级

- **前置条件**：`docker compose stop db`。
- **操作**：`POST /api/v1/auth/login`（合法入参）。
- **可观测结果**：HTTP 503；`code=1503`；`message="服务暂时不可用，请稍后再试"`；日志 `event="dep_unreachable"`、`dep="db"`；不返回 401（不得把依赖故障说成口令错误）。

### Requirement: 会话过期

系统 SHALL 让会话在 `SESSION_TTL_MINUTES`（默认 720 分钟）后失效，过期后按未登录处理。

#### Scenario: ID-13 会话过期后访问受保护接口

- **前置条件**：会话 `expires_at` 被改为当前时间前 1 分钟。
- **操作**：用该 Cookie 调用 `GET /api/v1/me`。
- **可观测结果**：HTTP 401；`code=1101`；日志 `event="session_expired"`；会话行被清理（再次访问同一 Cookie 仍为 401）。
