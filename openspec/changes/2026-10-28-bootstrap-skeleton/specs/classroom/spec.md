## ADDED Requirements

### Requirement: 教师建班

系统 SHALL 允许 `role=teacher` 的用户创建班级：班名 2–40 字符，自动生成 8 位 `join_code`（大写字母与数字，全库唯一，冲突时重试至多 5 次）。

#### Scenario: CR-01 教师建班成功

- **前置条件**：以教师身份登录。
- **操作**：`POST /api/v1/classes`，body `{"name":"2026 秋 · 数据结构 · 3 班"}`。
- **可观测结果**：HTTP 201；`code=0`；`data` 含 `id`（26 位 ULID）、`name`、`join_code`（长度 8，仅大写字母与数字）、`owner_id` 等于当前用户；创建者自动成为该班 `role=teacher` 的成员（`memberships` 新增 1 行）。

#### Scenario: CR-02 班名长度非法

- **前置条件**：以教师身份登录。
- **操作**：分别提交 1 字符与 41 字符班名。
- **可观测结果**：两次均 HTTP 400、`code=1001`、`message` 含 `2–40`；`classes` 表行数不变。

#### Scenario: CR-03 学生调用建班接口被拒（功能级越权）

- **前置条件**：以学生身份登录。
- **操作**：`POST /api/v1/classes`，body 合法。
- **可观测结果**：HTTP 404；`code=1202`；响应体与「`POST /api/v1/classes/nonexistent` 的 404」除 `request_id` 外逐字节相同；不返回 403；`classes` 表行数不变。

### Requirement: 学生凭入班码加入班级

系统 SHALL 允许学生用 8 位 `join_code` 加入班级；已是成员时幂等返回 200 与当前成员信息，不报冲突；班级已归档时拒绝。

#### Scenario: CR-04 学生入班成功

- **前置条件**：以学生身份登录；存在未归档班级，`join_code="A7K2M9QX"`。
- **操作**：`POST /api/v1/classes/join`，body `{"join_code":"A7K2M9QX"}`。
- **可观测结果**：HTTP 200；`code=0`；`data` 含 `class_id`、`name`、`role="student"`；`memberships` 新增 1 行；随后 `GET /api/v1/me` 的 `classes` 含该班。

#### Scenario: CR-05 重复入班幂等

- **前置条件**：学生已加入班级 X。
- **操作**：再次提交同一 `join_code`。
- **可观测结果**：HTTP 200；`code=0`；`data.class_id` 与首次相同；`memberships` 中 `(class_id, user_id)` 仍只有 1 行（不新增、不报 409）。

#### Scenario: CR-06 入班码不存在

- **前置条件**：以学生身份登录。
- **操作**：`POST /api/v1/classes/join`，body `{"join_code":"ZZZZZZZZ"}`。
- **可观测结果**：HTTP 404；`code=1301`；`message="资源不存在"`；不创建成员关系；日志 `event="join_code_miss"`（不记录传入的码值）。

#### Scenario: CR-07 入班码格式非法

- **前置条件**：以学生身份登录。
- **操作**：提交 `"a7k2"`（4 位小写）与 `"A7K2M9Q!"`（含符号）。
- **可观测结果**：两次均 HTTP 400、`code=1001`、`message` 含 `8 位大写字母或数字`；不触发任何查询（日志无 `join_code_miss`）。

#### Scenario: CR-08 加入已归档班级被拒

- **前置条件**：班级 Y 的 `archived_at` 非空。
- **操作**：用 Y 的 `join_code` 入班。
- **可观测结果**：HTTP 409；`code=1401`；`message="该班级已结课"`；不创建成员关系。

### Requirement: 成员列表按班隔离

系统 SHALL 通过 `GET /api/v1/classes/{id}/members` 返回本班成员（`user_id`、`display_name`、`role`、`joined_at`），分页 `page/page_size`（默认 20，上限 50），跨班访问返回与「不存在」一致的 404。

#### Scenario: CR-09 本班成员可见

- **前置条件**：A 班有 1 名教师与 2 名学生；以 A 班学生登录。
- **操作**：`GET /api/v1/classes/{A}/members`。
- **可观测结果**：HTTP 200；`data.total=3`；`data.items` 的 `role` 计数为 `teacher:1`、`student:2`；不出现 `email` 字段（成员列表不暴露邮箱）。

#### Scenario: CR-10 跨班查看成员（水平越权）

- **前置条件**：A 班与 B 班各 1 名教师；以 A 班学生登录。
- **操作**：`GET /api/v1/classes/{B}/members`，并与 `GET /api/v1/classes/{不存在ID}/members` 对比。
- **可观测结果**：两次均 HTTP 404、`code=1201` 与 `code=1301` 的响应体除 `request_id` 外逐字节相同；响应中不出现 B 班任何成员的 `display_name`。

### Requirement: 班级列表

系统 SHALL 通过 `GET /api/v1/classes` 返回当前用户所属且未归档的班级，按 `joined_at` 倒序，最多 20 条。

#### Scenario: CR-11 只返回本人所属班级

- **前置条件**：学生 S 属于 A 班；B 班存在但与 S 无关。
- **操作**：`GET /api/v1/classes`。
- **可观测结果**：HTTP 200；`data` 数组长度 1，元素 `id` 为 A；响应体中不出现 B 班的 `id`、`name`、`join_code` 任一值。

### Requirement: 入班码唯一性冲突处理

系统 SHALL 在生成的 `join_code` 与已有值冲突时重新生成，至多 5 次；5 次仍冲突则返回 503 `1503` 并记录 `event="join_code_exhausted"`。

#### Scenario: CR-12 入班码冲突时重试

- **前置条件**：构造随机源使其前 2 次返回已存在的码（测试替身注入固定序列）。
- **操作**：教师建班。
- **可观测结果**：HTTP 201；返回的 `join_code` 不等于被占用的两个值；日志出现 2 条 `event="join_code_collision"` 与 1 条 `event="class_created"`。

### Requirement: 数据库不可达时明确失败

系统 SHALL 在数据库不可达时让建班与入班返回 503 `1503`。

#### Scenario: CR-13 数据库不可达时建班失败

- **前置条件**：`docker compose stop db`；已持有有效会话。
- **操作**：`POST /api/v1/classes`，body 合法。
- **可观测结果**：HTTP 503；`code=1503`；不返回 500 裸堆栈；日志 `event="dep_unreachable"`、`dep="db"`。
