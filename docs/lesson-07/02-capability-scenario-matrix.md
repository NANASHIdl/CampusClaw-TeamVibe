# 能力 ↔ Scenario 对应表

六条能力、47 条 Requirement、90 条 Scenario。编号规则 `<能力前缀>-<两位序号>`，前缀：`PC` 平台基础 / `ID` 身份 / `CR` 班级 / `MT` 资料 / `RT` 检索 / `AS` 提问。

## 表 A · 能力 ↔ Scenario（两列表）

| 能力 | Scenario 编号与名称 |
| --- | --- |
| `platform-core`（15 条） | PC-01 完整配置下正常启动 · PC-02 缺少必填键时启动失败 · PC-03 `SESSION_SECRET` 过短视为缺失 · PC-04 成功响应结构固定 · PC-05 未知路径返回 404 与登记错误码 · PC-06 未认证请求被拒且不泄露资源 · PC-07 分页参数非法返回 400 · PC-08 请求标识可从响应头串到日志 · PC-09 非法请求标识被替换而非透传 · PC-10 访问日志字段齐全 · PC-11 敏感值不落日志 · PC-12 依赖全部可达 · PC-13 向量库不可达时降级不崩溃 · PC-14 在途请求不被中断 · PC-15 骨架期业务路由返回 501 |
| `identity`（13 条） | ID-01 口令不落明文 · ID-02 登录成功下发会话 Cookie · ID-03 口令错误与用户不存在返回一致 · ID-04 连续失败 5 次后锁定 · ID-05 第 4 次失败后仍可成功登录 · ID-06 锁定 15 分钟后自动解除 · ID-07 注销后旧令牌不可用 · ID-08 未登录访问当前用户信息 · ID-09 伪造角色请求头被忽略 · ID-10 邮箱格式非法 · ID-11 口令长度越界 · ID-12 数据库不可达时登录降级 · ID-13 会话过期后访问受保护接口 |
| `classroom`（13 条） | CR-01 教师建班成功 · CR-02 班名长度非法 · CR-03 学生调用建班接口被拒 · CR-04 学生入班成功 · CR-05 重复入班幂等 · CR-06 入班码不存在 · CR-07 入班码格式非法 · CR-08 加入已归档班级被拒 · CR-09 本班成员可见 · CR-10 跨班查看成员 · CR-11 只返回本人所属班级 · CR-12 入班码冲突时重试 · CR-13 数据库不可达时建班失败 |
| `materials`（21 条） | MT-01 教师上传单个 PDF 成功 · MT-02 扩展名不在白名单 · MT-03 文件恰好 20 MiB 与超 1 字节 · MT-04 单批 21 个文件 · MT-05 本班资料数达到 500 上限 · MT-06 原始文件名含路径与脚本片段 · MT-07 上传后异步转为 ready · MT-08 扫描版 PDF 置为 failed · MT-09 翻页不重复不遗漏 · MT-10 非法筛选值必须报错 · MT-11 `page_size` 超上限 · MT-12 本班查看详情 · MT-13 跨班查看详情 · MT-14 本班下载原文 · MT-15 跨班下载原文被拒 · MT-16 直接按文件名读取被拒 · MT-17 同一幂等键重复提交 · MT-18 删除后列表与详情同步消失 · MT-19 删除后检索不到残留 · MT-20 对象存储不可达时上传失败 · MT-21 学生调用上传与删除接口被拒 |
| `retrieval`（13 条） | RT-01 混合模式命中并返回出处 · RT-02 关键词模式不调用模型 · RT-03 模式取值非法 · RT-04 跨班内容不可被检索到 · RT-05 伪造 `class_id` 查询参数被忽略 · RT-06 阈值两侧 · RT-07 召回条数上限 · RT-08 空资料库检索 · RT-09 未完成处理的资料不参与检索 · RT-10 向量库不可达时的三模式表现 · RT-11 查询串为空或超长 · RT-12 未登录检索 · RT-13 会话班级已不存在 |
| `assistant`（15 条） | AS-01 建会话成功 · AS-02 问题长度越界 · AS-03 已关闭会话不可再提问 · AS-04 提问得到带出处的流式回答 · AS-05 引用编号与出处严格对应 · AS-06 模型自报的出处不被采信 · AS-07 心跳与首字节超时 · AS-08 空资料库提问 · AS-09 模型持续不可达 · AS-10 流式过程中失败 · AS-11 他人会话不可读 · AS-12 跨班会话不可读 · AS-13 提示词版本可追溯 · AS-14 资料中的注入内容被忽略 · AS-15 长会话截断 |

## 表 B · Requirement ↔ Scenario（每条 Requirement 至少一条）

| 能力 · Requirement | Scenario |
| --- | --- |
| platform-core · 配置外置且缺失即启动失败 | PC-01、PC-02、PC-03 |
| platform-core · 统一响应结构与错误码 | PC-04、PC-05、PC-06、PC-07 |
| platform-core · 请求标识贯穿全链路 | PC-08、PC-09 |
| platform-core · 结构化日志一行一条 JSON | PC-10、PC-11 |
| platform-core · 健康检查免认证并返回依赖连通状态 | PC-12、PC-13 |
| platform-core · 优雅停机 | PC-14 |
| platform-core · 未实现路由显式声明 | PC-15 |
| identity · 口令以加盐单向算法存储 | ID-01 |
| identity · 登录建立服务端会话 | ID-02、ID-03 |
| identity · 登录失败限制 | ID-04、ID-05、ID-06 |
| identity · 注销即服务端吊销 | ID-07 |
| identity · 当前用户信息 | ID-08、ID-09 |
| identity · 登录入参校验 | ID-10、ID-11 |
| identity · 认证依赖不可达时明确失败 | ID-12 |
| identity · 会话过期 | ID-13 |
| classroom · 教师建班 | CR-01、CR-02、CR-03 |
| classroom · 学生凭入班码加入班级 | CR-04、CR-05、CR-06、CR-07、CR-08 |
| classroom · 成员列表按班隔离 | CR-09、CR-10 |
| classroom · 班级列表 | CR-11 |
| classroom · 入班码唯一性冲突处理 | CR-12 |
| classroom · 数据库不可达时明确失败 | CR-13 |
| materials · 上传白名单与容量上限 | MT-01、MT-02、MT-03、MT-04、MT-05 |
| materials · 服务端重命名与原始名处理 | MT-06 |
| materials · 处理状态机 | MT-07、MT-08 |
| materials · 列表分页、排序与筛选 | MT-09、MT-10、MT-11 |
| materials · 资料详情 | MT-12、MT-13 |
| materials · 原文受控下载 | MT-14、MT-15、MT-16 |
| materials · 上传幂等 | MT-17 |
| materials · 软删与副本清理 | MT-18、MT-19 |
| materials · 依赖不可达时明确失败 | MT-20 |
| materials · 上传与删除仅限教师 | MT-21 |
| retrieval · 三种检索模式且枚举封闭 | RT-01、RT-02、RT-03 |
| retrieval · 检索只在本班范围内 | RT-04、RT-05 |
| retrieval · 阈值与召回上限 | RT-06、RT-07 |
| retrieval · 无命中时明确返回空结果 | RT-08、RT-09 |
| retrieval · 依赖降级 | RT-10 |
| retrieval · 检索入参校验 | RT-11、RT-12 |
| retrieval · 会话所属班级失效时明确失败 | RT-13 |
| assistant · 创建提问会话 | AS-01 |
| assistant · 提问入参与会话状态 | AS-02、AS-03 |
| assistant · 流式回答 | AS-04、AS-05、AS-06、AS-07 |
| assistant · 无命中时的固定行为 | AS-08 |
| assistant · 超时、重试与降级 | AS-09、AS-10 |
| assistant · 会话隔离 | AS-11、AS-12 |
| assistant · 提示词随版本入库 | AS-13 |
| assistant · 外部内容不改变行为 | AS-14 |
| assistant · 上下文窗口固定 | AS-15 |

## 表 C · 失败路径四类覆盖（每类至少一条，每条能力都齐）

| 能力 | 参数非法 | 无权限 / 越权 | 资源不存在 | 依赖不可达 | 失败路径合计 |
| --- | --- | --- | --- | --- | --- |
| platform-core | PC-07 | PC-06 | PC-05 | PC-13 | 8（另 PC-02/03/09/15） |
| identity | ID-10、ID-11 | ID-08 | ID-13（会话记录已不存在） | ID-12 | 8（另 ID-03/04/06） |
| classroom | CR-02、CR-07 | CR-03、CR-10 | CR-06 | CR-13 | 7（另 CR-08） |
| materials | MT-02、MT-04、MT-10、MT-11 | MT-13、MT-15、MT-21 | MT-15、MT-16 | MT-20 | 11（另 MT-03/05） |
| retrieval | RT-03、RT-11 | RT-12 | RT-13（班级已硬删） | RT-10 | 6 |
| assistant | AS-02 | AS-11、AS-12 | AS-11（他人会话） | AS-09、AS-10 | 8（另 AS-03/06/14） |

## 表 D · 越权 Scenario 配对核对

| 资源 | 水平越权 | 功能级越权 |
| --- | --- | --- |
| 班级成员 | CR-10 | CR-03 |
| 资料详情 | MT-13 | MT-21 |
| 资料原文 | MT-15、MT-16 | — |
| 检索结果 | RT-04、RT-05 | — |
| 提问会话 | AS-11、AS-12 | — |
| 当前用户 | — | ID-09（伪造角色头被忽略） |

判据一致性：所有越权 Scenario 都要求「越权响应与不存在响应除 `request_id` 外逐字节相同」，实现时只写一条 `fetch-then-check` 分支即可全部满足，不需要按场景分别写代码。
