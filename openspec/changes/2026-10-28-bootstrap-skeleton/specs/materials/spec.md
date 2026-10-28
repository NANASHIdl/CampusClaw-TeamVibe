## ADDED Requirements

### Requirement: 上传白名单与容量上限

系统 SHALL 只接受扩展名与 MIME 双重白名单命中的文件：`pdf`（`application/pdf`）、`md`（`text/markdown`）、`txt`（`text/plain`）、`docx`（`application/vnd.openxmlformats-officedocument.wordprocessingml.document`）。

单文件 ≤ 20 MiB（20971520 字节）；单批 ≤ 20 个文件；本班资料总数 ≤ 500。任一条件不满足时整批拒绝，不落半批数据。

#### Scenario: MT-01 教师上传单个 PDF 成功

- **前置条件**：以 A 班教师登录；文件 `chapter3.pdf`，4.2 MiB，MIME `application/pdf`。
- **操作**：`POST /api/v1/materials`，multipart 上传。
- **可观测结果**：HTTP 201；`code=0`；`data.status="pending"`；`data.id` 为 26 位 ULID；`uploads/<class_id>/<material_id>.pdf` 文件存在且大小等于 4404019 字节；`materials` 新增 1 行，`uploaded_by` 为当前用户。

#### Scenario: MT-02 扩展名不在白名单

- **前置条件**：以 A 班教师登录。
- **操作**：上传 `malware.exe`（MIME 声明为 `application/pdf`，实际为可执行文件）。
- **可观测结果**：HTTP 400；`code=1001`；`message` 含 `pdf/md/txt/docx`；`uploads/` 下无新文件；`materials` 行数不变；日志 `event="upload_rejected"`、`reason="ext_not_allowed"`。

#### Scenario: MT-03 文件恰好 20 MiB 与超 1 字节（边界）

- **前置条件**：准备两个文件：A 为 20971520 字节，B 为 20971521 字节，均为合法 PDF。
- **操作**：分别上传 A 与 B。
- **可观测结果**：A 返回 201 且 `data.size_bytes=20971520`；B 返回 400 `code=1002`、`message` 含 `20 MiB`；B 不留残留文件。

#### Scenario: MT-04 单批 21 个文件

- **前置条件**：以 A 班教师登录。
- **操作**：一次上传 21 个合法 PDF。
- **可观测结果**：HTTP 400；`code=1002`；`message` 含 `20`；`materials` 行数为 0（整批回滚，不留 20 条半批数据）。

#### Scenario: MT-05 本班资料数达到 500 上限（边界）

- **前置条件**：A 班已有 500 条未删除资料。
- **操作**：再上传 1 个合法 PDF。
- **可观测结果**：HTTP 409；`code=1402`；`message` 含 `500`；`materials` 行数仍为 500。

### Requirement: 服务端重命名与原始名处理

系统 SHALL 以 `<material_id>.<ext>` 命名落盘文件，不采信上传时的原始文件名；原始名只作为展示字段入库，截断至 ≤ 200 字符并过滤不可见字符。

#### Scenario: MT-06 原始文件名含路径与脚本片段

- **前置条件**：以 A 班教师登录。
- **操作**：上传文件名 `../../etc/pa<script>alert(1)</script>sswd.pdf`。
- **可观测结果**：HTTP 201；`data.original_filename` 不含 `../` 与 `<`；落盘路径为 `uploads/<class_id>/<material_id>.pdf`；文件系统上不存在越出 `uploads/` 的文件。

### Requirement: 处理状态机

系统 SHALL 让资料状态只按 `pending → processing → ready | failed` 流转，不允许跳级或回退；`processing` 超过 10 分钟未完成的记录在服务启动时重置为 `pending`。

#### Scenario: MT-07 上传后异步转为 ready

- **前置条件**：A 班教师上传一份 8 页可提取文本的 PDF。
- **操作**：轮询 `GET /api/v1/materials/{id}`，每 2 秒一次，最多 60 秒。
- **可观测结果**：状态序列为 `pending`（首次）→ `processing`（至少观察到一次）→ `ready`；`data.chunk_count ≥ 1`；`chunks` 中该资料的 `chunk_index` 从 0 连续无缺口。

#### Scenario: MT-08 扫描版 PDF 置为 failed

- **前置条件**：上传一份无文本层的扫描 PDF。
- **操作**：轮询详情至终态。
- **可观测结果**：`status="failed"`；`failure_reason` 含「无可提取文本」；`chunk_count=0`；该资料不出现在检索结果中。

### Requirement: 列表分页、排序与筛选

系统 SHALL 通过 `GET /api/v1/materials` 返回本班未删除资料：`page`（默认 1）、`page_size`（默认 20，上限 50）；排序字段白名单 `created_at` / `title`；**排序必须带唯一兜底键 `id`**；`status` 筛选只接受四个枚举值。

#### Scenario: MT-09 翻页不重复不遗漏

- **前置条件**：A 班有 25 条资料，`created_at` 中 5 条完全相同。
- **操作**：`GET /api/v1/materials?page=1&page_size=20` 与 `page=2&page_size=20`。
- **可观测结果**：两页合计 25 条，`id` 无重复；`total=25`；第 1 页 20 条、第 2 页 5 条；两次响应中 `created_at` 相同的 5 条相对顺序一致（按 `id DESC`）。

#### Scenario: MT-10 非法筛选值必须报错

- **前置条件**：以 A 班成员登录。
- **操作**：`GET /api/v1/materials?status=deleted` 与 `GET /api/v1/materials?sort=password`。
- **可观测结果**：两次均 HTTP 400；前者 `code=1003`、后者 `code=1005`；**均不返回任何资料条目**（不得忽略参数后返回全量）。

#### Scenario: MT-11 `page_size` 超上限（边界）

- **前置条件**：A 班有 60 条资料。
- **操作**：`GET /api/v1/materials?page_size=1000`。
- **可观测结果**：HTTP 400；`code=1004`；`data=null`。

### Requirement: 资料详情

系统 SHALL 通过 `GET /api/v1/materials/{id}` 返回元信息与切片列表（按 `chunk_index` 升序，单次最多 200 条，超出用 `?chunk_page=` 翻页）。

#### Scenario: MT-12 本班查看详情

- **前置条件**：A 班教师上传并已 `ready` 的资料 M（`chunk_count=6`）。
- **操作**：`GET /api/v1/materials/{M}`。
- **可观测结果**：HTTP 200；`data.chunk_count=6`；`data.chunks` 长度 6；`chunk_index` 为 `[0,1,2,3,4,5]` 严格升序；每条含 `chunk_index`、`content`、`char_count`。

#### Scenario: MT-13 跨班查看详情（水平越权）

- **前置条件**：A 班资料 M，B 班学生登录。
- **操作**：`GET /api/v1/materials/{M}`，并与 `GET /api/v1/materials/{不存在ID}` 对比。
- **可观测结果**：两次均 HTTP 404；`code` 分别为 `1201` 与 `1301`，但响应体除 `request_id` 外**逐字节相同**；响应中不出现 M 的 `title` 或任何切片 `content`。

### Requirement: 原文受控下载

系统 SHALL 只通过 `GET /api/v1/materials/{id}/file` 提供原文下载，先做归属判定再流式返回；不提供按文件标识直接读取的通用接口，不提供对象存储直链或预签名 URL。

#### Scenario: MT-14 本班下载原文

- **前置条件**：A 班学生登录；资料 M 已 `ready`。
- **操作**：`GET /api/v1/materials/{M}/file`。
- **可观测结果**：HTTP 200；`Content-Type` 为登记的 MIME；`Content-Disposition` 的 `filename*` 为 URL 编码后的原始名；响应头含 `X-Content-Type-Options: nosniff`；响应体字节数与 `size_bytes` 相同。

#### Scenario: MT-15 跨班下载原文被拒

- **前置条件**：B 班学生登录；资料 M 属 A 班。
- **操作**：`GET /api/v1/materials/{M}/file`。
- **可观测结果**：HTTP 404；`code=1201`；响应体与「不存在」一致；响应中不含文件字节流（`Content-Length` 为错误体长度，不是文件长度）。

#### Scenario: MT-16 直接按文件名读取被拒

- **前置条件**：服务已启动，已知落盘文件名 `<material_id>.pdf`。
- **操作**：`GET /static/uploads/<material_id>.pdf` 与 `GET /files/<material_id>.pdf`。
- **可观测结果**：两次均 HTTP 404；Nginx 不服务 `uploads/` 目录；日志无对应静态文件访问记录。

### Requirement: 上传幂等

系统 SHALL 接受请求头 `Idempotency-Key`（客户端生成的 ULID）：同键重复请求返回首次结果（HTTP 200），不新建资料。

#### Scenario: MT-17 同一幂等键重复提交

- **前置条件**：A 班教师登录，客户端生成一个 26 位 ULID 作为幂等键（本例用 `01HQ7Z3K9V2M4T8R6B1C0X5DNP`），放入请求头 `Idempotency-Key`。
- **操作**：用同一键与同一文件连续提交 2 次。
- **可观测结果**：首次 HTTP 201，第二次 HTTP 200；两次 `data.id` 相同；`materials` 行数增加 1；`uploads/` 下该资料文件只有 1 个。

### Requirement: 软删与副本清理

系统 SHALL 对删除做软删（`deleted_at`），7 天后硬删；删除后按副本清单清理 `chunks`、向量库点、落盘文件与检索缓存。

#### Scenario: MT-18 删除后列表与详情同步消失

- **前置条件**：A 班教师登录；资料 M 已 `ready`。
- **操作**：`DELETE /api/v1/materials/{M}`，随后 `GET /api/v1/materials` 与 `GET /api/v1/materials/{M}`。
- **可观测结果**：删除返回 200；列表中不再出现 M；详情返回 404 `1301`；`materials` 行仍在但 `deleted_at` 非空。

#### Scenario: MT-19 删除后检索不到残留

- **前置条件**：M 已删除 8 天（推进时钟或直接改 `deleted_at`），清理任务已执行。
- **操作**：`GET /api/v1/search?q=<M 中的独有短语>&mode=hybrid`；并检查 `uploads/` 与 Qdrant。
- **可观测结果**：`hits=[]`；`uploads/<class_id>/<material_id>.*` 不存在；Qdrant 中该 `material_id` 的点数为 0；`chunks` 中该资料行数为 0。

### Requirement: 依赖不可达时明确失败

系统 SHALL 在对象存储或数据库不可达时让上传返回 503 `1503`，不落半条记录。

#### Scenario: MT-20 对象存储不可达时上传失败

- **前置条件**：把 `uploads/` 挂载点改为只读（或在测试中让写入抛错）。
- **操作**：上传合法 PDF。
- **可观测结果**：HTTP 503；`code=1503`；`materials` 行数不变（不留 `pending` 孤儿行）；日志 `event="dep_unreachable"`、`dep="storage"`。

### Requirement: 上传与删除仅限教师

系统 SHALL 只允许本班 `role=teacher` 的成员调用 `POST /api/v1/materials` 与 `DELETE /api/v1/materials/{id}`；学生调用返回 404 `1202`，响应体与「资源不存在」一致，不使用 403。

#### Scenario: MT-21 学生调用上传与删除接口被拒（功能级越权）

- **前置条件**：A 班学生 S 登录；A 班资料 M 存在且 `ready`。
- **操作**：S 分别调用 `POST /api/v1/materials`（合法 PDF）与 `DELETE /api/v1/materials/{M}`，并与 `GET /api/v1/materials/{不存在ID}` 的响应对比。
- **可观测结果**：两次均 HTTP 404、`code=1202`；两次响应体与「不存在」的 404 除 `request_id` 外逐字节相同；`materials` 行数与 `uploads/` 文件数均不变；日志 `event="role_denied"`、`required_role="teacher"`。
