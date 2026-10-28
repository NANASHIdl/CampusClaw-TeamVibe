## ADDED Requirements

### Requirement: 三种检索模式且枚举封闭

系统 SHALL 通过 `GET /api/v1/search` 提供三种模式：`keyword`（PostgreSQL 全文）、`vector`（Qdrant 向量）、`hybrid`（两路融合，默认）。`mode` 只接受这三个值，其余一律按参数错误处理。

#### Scenario: RT-01 混合模式命中并返回出处

- **前置条件**：A 班有 `ready` 资料 M（含短语「主定理的递归树证明」）；学生登录。
- **操作**：`GET /api/v1/search?q=主定理怎么用递归树证明&mode=hybrid`。
- **可观测结果**：HTTP 200；`code=0`；`data.hits` 长度 1–8；首条含 `material_id`（等于 M）、`chunk_index`（整数 ≥ 0）、`title`、`snippet`（含「递归树」）、`score`（0–1 之间）；`data.mode="hybrid"`；`data.total` 等于 `hits` 长度。

#### Scenario: RT-02 关键词模式不调用模型

- **前置条件**：`LLM_API_KEY` 置空。
- **操作**：`GET /api/v1/search?q=递归树&mode=keyword`。
- **可观测结果**：HTTP 200；`code=0`；`hits` 非空；日志中该请求无 `event="llm_call"` 记录；无 5xx。

#### Scenario: RT-03 模式取值非法

- **前置条件**：学生登录。
- **操作**：`GET /api/v1/search?q=递归树&mode=semantic`。
- **可观测结果**：HTTP 400；`code=1003`；`message` 含 `keyword/vector/hybrid`；`data=null`；**不返回任何检索结果**。

### Requirement: 检索只在本班范围内

系统 SHALL 让所有检索强制带当前会话的 `class_id` 过滤：关键词检索的 SQL 条件、向量检索的 payload 过滤、融合后的结果集三处都必须带；请求中出现的 `class_id` 参数一律忽略。

#### Scenario: RT-04 跨班内容不可被检索到

- **前置条件**：A 班资料 M1 含短语「B 树分裂的三种情况」；B 班资料 M2 含同一短语。
- **操作**：以 A 班学生身份 `GET /api/v1/search?q=B 树分裂的三种情况&mode=hybrid`。
- **可观测结果**：HTTP 200；`hits` 中所有 `material_id` 均属 A 班；**不含 M2 的 `material_id`、`title`、`snippet` 任一内容**；日志 `event="search_done"` 的 `class_id` 为 A 班。

#### Scenario: RT-05 伪造 `class_id` 查询参数被忽略

- **前置条件**：A 班学生登录；已知 B 班 `class_id`。
- **操作**：`GET /api/v1/search?q=B 树分裂&mode=keyword&class_id=<B班ID>`。
- **可观测结果**：HTTP 200；结果仍为 A 班数据（与不带该参数时的 `hits` 完全一致）；日志 `class_id` 为 A 班；响应体不出现 B 班任何标识。

### Requirement: 阈值与召回上限

系统 SHALL 让向量命中必须越过 `SEARCH_VECTOR_MIN`（默认 0.35），最终返回条数不超过 `SEARCH_TOP_K`（默认 8）；两个值只从配置读取。

#### Scenario: RT-06 阈值两侧（边界）

- **前置条件**：构造两条切片，与查询的余弦相似度分别为 0.34 与 0.36（测试替身固定嵌入）。
- **操作**：`GET /api/v1/search?q=<构造查询>&mode=vector`。
- **可观测结果**：`hits` 只含 0.36 那条；`hits[0].score ≥ 0.35`；0.34 那条的 `material_id` 不在结果中。

#### Scenario: RT-07 召回条数上限

- **前置条件**：A 班有 30 条与查询高度相关的切片。
- **操作**：`GET /api/v1/search?q=<通用词>&mode=hybrid`。
- **可观测结果**：`hits` 长度恰好为 8；`score` 降序；`data.total=8`（不是 30）。

### Requirement: 无命中时明确返回空结果

系统 SHALL 在无命中时返回 `hits=[]`、`message="资料中未找到相关内容"`，且不返回任何 `material_id` 或伪造片段；前端按「检索无命中」形态渲染，不显示空白列表。

#### Scenario: RT-08 空资料库检索

- **前置条件**：A 班无任何 `ready` 资料。
- **操作**：`GET /api/v1/search?q=任意问题&mode=hybrid`。
- **可观测结果**：HTTP 200；`code=0`；`hits=[]`；`data.message="资料中未找到相关内容"`；响应体中不出现任何 26 位 ULID 形式的 `material_id`；前端页面显示该文案与「换个关键词」「请本班教师补充资料」两个动作。

#### Scenario: RT-09 未完成处理的资料不参与检索

- **前置条件**：A 班资料 M 处于 `processing`，正文含短语「贪心选择的交换论证」。
- **操作**：`GET /api/v1/search?q=贪心选择的交换论证&mode=keyword`。
- **可观测结果**：`hits=[]`；`materials.status` 仍为 `processing`；资料详情页显示「处理中，暂不可检索」。

### Requirement: 依赖降级

系统 SHALL 在向量库不可达时保持 `keyword` 可用，`vector` 与 `hybrid` 返回 503 `1502` 并给出「改用关键词模式」的下一步提示；不得无限等待或返回空结果冒充成功。

#### Scenario: RT-10 向量库不可达时的三模式表现

- **前置条件**：`docker compose stop qdrant`。
- **操作**：依次请求 `mode=keyword`、`mode=vector`、`mode=hybrid`。
- **可观测结果**：`keyword` 返回 200 且 `hits` 非空；`vector` 与 `hybrid` 均返回 503、`code=1502`、`message` 含「改用关键词模式」；三次请求耗时均 < 5000 ms（不挂起）；日志 2 条 `event="dep_unreachable"`、`dep="qdrant"`。

### Requirement: 检索入参校验

系统 SHALL 校验 `q` 长度 2–200 字符；空串、纯空白、超长均返回 400 `1001`。

#### Scenario: RT-11 查询串为空或超长（边界）

- **前置条件**：学生登录。
- **操作**：分别请求 `q=`（空）、`q=%20%20`（两个空格）、`q=<201 个字符>`。
- **可观测结果**：三次均 HTTP 400、`code=1001`、`message` 含 `2–200`；均不触发检索（日志无 `search_done`）。

#### Scenario: RT-12 未登录检索

- **前置条件**：请求不带 Cookie。
- **操作**：`GET /api/v1/search?q=递归树`。
- **可观测结果**：HTTP 401；`code=1101`；不返回任何命中；日志无 `search_done`。
