# 数据字典 · CampusClaw · TeamVibe

本文件是字段含义的**唯一处**。结构变更必须同步本文件（`make check` 的 `docs-lint` 会校验 `backend/app/models/` 中的表名与字段名在此都有条目）。
字段命名、审计字段、迁移纪律见 `docs/specs/07-数据规范.md`。

约定：

- 主键统一 `id CHAR(26)`（ULID），不展示给用户，只用于接口与日志。
- 时间统一 `TIMESTAMPTZ`，UTC 存储；后缀 `_at`。
- `敏感级` 取值：公开 / 内部 / 敏感 / 机密（定义见 `docs/specs/07-数据规范.md` §5）。
- 所有业务表带 `created_at`、`updated_at`、`created_by`（下文不再重复列出，除非有额外约束）。

---

## users — 用户

| 字段 | 类型 | 约束 | 含义 | 敏感级 |
| --- | --- | --- | --- | --- |
| `id` | CHAR(26) | PK | 用户标识 | 内部 |
| `email` | VARCHAR(160) | UNIQUE, NOT NULL | 登录名，校内邮箱 | 敏感 |
| `display_name` | VARCHAR(60) | NOT NULL | 显示名 | 内部 |
| `password_hash` | VARCHAR(72) | NOT NULL | bcrypt(cost=12) 结果 | 机密 |
| `is_active` | BOOLEAN | NOT NULL DEFAULT true | 是否可登录 | 内部 |

## classes — 班级

| 字段 | 类型 | 约束 | 含义 | 敏感级 |
| --- | --- | --- | --- | --- |
| `id` | CHAR(26) | PK | 班级标识，即 `class_id` | 内部 |
| `name` | VARCHAR(40) | NOT NULL | 班名，如「2026 秋 · 数据结构 · 3 班」 | 内部 |
| `join_code` | CHAR(8) | UNIQUE, NOT NULL | 学生入班码，大写字母+数字 | 敏感 |
| `owner_id` | CHAR(26) | FK users.id, NOT NULL | 建班教师 | 内部 |
| `archived_at` | TIMESTAMPTZ | NULL | 结课归档时间 | 内部 |

## memberships — 班级成员

| 字段 | 类型 | 约束 | 含义 | 敏感级 |
| --- | --- | --- | --- | --- |
| `id` | CHAR(26) | PK | 成员关系标识 | 内部 |
| `class_id` | CHAR(26) | FK classes.id, NOT NULL | 所属班级 | 内部 |
| `user_id` | CHAR(26) | FK users.id, NOT NULL | 成员 | 内部 |
| `role` | VARCHAR(10) | CHECK IN ('teacher','student') | 班内角色 | 内部 |

唯一索引：`UNIQUE(class_id, user_id)` —— 重复入班靠它保证幂等，不靠应用层「先查再插」。

## materials — 资料

| 字段 | 类型 | 约束 | 含义 | 敏感级 |
| --- | --- | --- | --- | --- |
| `id` | CHAR(26) | PK | 资料标识，即 `material_id` | 内部 |
| `class_id` | CHAR(26) | FK classes.id, NOT NULL | 所属班级（授权判定依据） | 内部 |
| `title` | VARCHAR(120) | NOT NULL | 展示标题，默认取原始文件名去扩展名 | 内部 |
| `original_filename` | VARCHAR(200) | NOT NULL | 上传时的原始文件名，仅展示 | 敏感 |
| `stored_filename` | VARCHAR(80) | NOT NULL | 服务端重命名：`<material_id>.<ext>` | 内部 |
| `mime` | VARCHAR(80) | NOT NULL | 校验后的 MIME | 内部 |
| `size_bytes` | BIGINT | CHECK > 0 AND <= 20971520 | 文件大小，上限 20 MiB | 内部 |
| `status` | VARCHAR(12) | CHECK IN ('pending','processing','ready','failed') | 处理状态，见产品规范 §6 | 内部 |
| `failure_reason` | VARCHAR(200) | NULL | `status=failed` 时的原因 | 内部 |
| `chunk_count` | INTEGER | NOT NULL DEFAULT 0 | 切片数 | 内部 |
| `uploaded_by` | CHAR(26) | FK users.id, NOT NULL | 上传者 | 内部 |
| `deleted_at` | TIMESTAMPTZ | NULL | 软删时间，7 天后硬删 | 内部 |

索引：`(class_id, created_at DESC, id DESC)`（列表分页与唯一兜底键）、`(class_id, status)`。

## chunks — 切片

| 字段 | 类型 | 约束 | 含义 | 敏感级 |
| --- | --- | --- | --- | --- |
| `id` | CHAR(26) | PK | 切片标识 | 内部 |
| `material_id` | CHAR(26) | FK materials.id, NOT NULL | 所属资料 | 内部 |
| `class_id` | CHAR(26) | NOT NULL | 冗余班级标识，检索时用于强制过滤 | 内部 |
| `chunk_index` | INTEGER | CHECK >= 0 | 资料内序号，从 0 起 | 内部 |
| `content` | TEXT | NOT NULL | 切片正文（800 字符，重叠 120） | 敏感 |
| `char_count` | INTEGER | NOT NULL | 字符数 | 内部 |
| `vector_id` | VARCHAR(64) | NULL | 向量库中的点 ID，与 `id` 相同 | 内部 |

唯一索引：`UNIQUE(material_id, chunk_index)`；索引 `(class_id)`。

## sessions — 提问会话

| 字段 | 类型 | 约束 | 含义 | 敏感级 |
| --- | --- | --- | --- | --- |
| `id` | CHAR(26) | PK | 会话标识，即 `session_id` | 内部 |
| `class_id` | CHAR(26) | NOT NULL | 所属班级 | 内部 |
| `user_id` | CHAR(26) | FK users.id, NOT NULL | 发起人；历史会话只本人可见 | 敏感 |
| `title` | VARCHAR(60) | NOT NULL | 取首个问题前 30 字 | 敏感 |
| `closed_at` | TIMESTAMPTZ | NULL | 关闭时间，关闭后不可再提问 | 内部 |

索引：`(user_id, created_at DESC, id DESC)`。

## messages — 消息

| 字段 | 类型 | 约束 | 含义 | 敏感级 |
| --- | --- | --- | --- | --- |
| `id` | CHAR(26) | PK | 消息标识 | 内部 |
| `session_id` | CHAR(26) | FK sessions.id, NOT NULL | 所属会话 | 内部 |
| `role` | VARCHAR(10) | CHECK IN ('user','assistant') | 说话方 | 内部 |
| `content` | TEXT | NOT NULL | 正文；助手正文带 `[n]` 编号 | 敏感 |
| `citations` | JSONB | NULL | 出处数组，结构见下 | 敏感 |
| `prompt_version` | INTEGER | NULL | 生成该回答的提示词版本 | 内部 |
| `truncated` | BOOLEAN | NOT NULL DEFAULT false | 是否因长度上限被截断 | 内部 |

`citations` 元素结构（由服务端按命中结果生成，不采信模型输出）：

```json
{ "n": 1, "material_id": "01HQ...", "chunk_index": 3, "title": "第三章 复杂度", "snippet": "……" }
```

只增不改：对消息的「修改」一律新增行。

## ask_logs — 提问日志

| 字段 | 类型 | 约束 | 含义 | 敏感级 |
| --- | --- | --- | --- | --- |
| `id` | CHAR(26) | PK | 日志标识 | 内部 |
| `class_id` | CHAR(26) | NOT NULL | 所属班级 | 内部 |
| `user_id` | CHAR(26) | NOT NULL | 提问人 | 敏感 |
| `session_id` | CHAR(26) | NULL | 关联会话 | 内部 |
| `question_len` | INTEGER | NOT NULL | 提问字符数（**不存原文**） | 内部 |
| `question_sha8` | CHAR(8) | NOT NULL | 提问 SHA256 前 8 位，用于去重统计 | 内部 |
| `mode` | VARCHAR(10) | CHECK IN ('keyword','vector','hybrid') | 检索模式 | 内部 |
| `hits` | INTEGER | NOT NULL | 命中切片数 | 内部 |
| `latency_ms` | INTEGER | NOT NULL | 端到端耗时 | 内部 |
| `outcome` | VARCHAR(12) | CHECK IN ('answered','no_hit','failed') | 结果分类 | 内部 |

只增不改。教师端 `/console/ask-logs` 读这张表，**不读 `messages`**，避免把学生提问原文暴露给非本人。

---

## 派生存储（非关系库）

| 存储 | 内容 | 一致性 |
| --- | --- | --- |
| Qdrant `campusclaw_chunks` | 点 ID = `chunks.id`，payload `{class_id, material_id, chunk_index}` | 以 `chunks` 表为准，可整表重建 |
| `uploads/<class_id>/<material_id>.<ext>` | 原始附件 | 以 `materials` 行为准；删除按副本清单执行 |
