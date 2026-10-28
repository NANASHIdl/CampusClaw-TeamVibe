# CampusClaw · TeamVibe

**按班级隔离的课程知识库与解题助手：教师上传本班资料，学生只检索本班资料提问，每条回答都必须带得出出处。**

---

## 当前状态（先读这一段）

本仓库交付**规约、工程规范与可启动的骨架**；业务能力（登录、建班、上传、检索、提问）尚未实现，
对应路由返回 501 `1500`。

| 部分 | 状态 | 位置 |
| --- | --- | --- |
| 变更规约（proposal / design / specs / tasks） | ✅ 已入库 | `openspec/changes/2026-10-28-bootstrap-skeleton/` |
| 五类必修 + 三类补充规范（八份文件） | ✅ 已入库 | `docs/specs/` |
| 常驻约束（规则）与按场景流程（技能） | ✅ 已入库 | `AGENTS.md`、`.cursor/rules/`、`skills/` |
| 核查清单、能力↔Scenario 矩阵、验证记录 | ✅ 已入库 | `docs/lesson-07/` |
| 应用骨架（FastAPI + Vue3 可启动的壳） | ✅ 已落地 | `backend/`、`frontend/`、`Dockerfile.api`、`Dockerfile.web`、`docker-compose.yml` |
| 骨架标签 `v0.0.1-skeleton` | ⬜ 待打 | 容器内验收通过后 `make tag-skeleton` |

`docs/lesson-07/01-checklist.md` 逐条记录了哪一项已完成、哪一项还空着，不做粉饰。

## 给谁用、解决什么问题、比现有做法好在哪

| | 内容 |
| --- | --- |
| **给谁用** | 同一门课的一个班：教师（含助教）与学生。教师 1 人维护资料，学生 20–120 人。 |
| **解决什么问题** | 课件、往届题解、课堂补充说明散落在群聊与网盘里，学期中就会失联；学生搜不到「本班」的那一份，通用大模型答课程题会编造公式与页码；教师无法确认某个回答到底引了哪份材料。 |
| **比现有做法好在哪** | ① 隔离在班级这一层，不是全校一把梭——A 班搜不到 B 班的资料，跨班访问与「不存在」返回完全一致的 404；② 每条回答带 `[n]` 引用，点开可定位到具体资料的切片序号；③ 检索没越过阈值就直说「资料中未找到相关内容」，不编造出处。 |

三条能力落到页面的对应关系见 `docs/specs/01-产品设计规范.md` §1。

## 本机怎么跑起来

前置：Docker Desktop 已启动（`docker info` 能返回）。

```bash
# 1. 克隆并进入仓库
git clone https://github.com/NANASHIdl/CampusClaw-TeamVibe.git
cd CampusClaw-TeamVibe

# 2. 配置：只复制键名模板，值填在本机 .env（不进版本库）
cp .env.example .env
#    必填 8 个键的权威清单见 docs/specs/02-后端开发规范.md §7
#    开发/测试环境额外需要 SEED_*（预置账号），生产环境出现 SEED_* 即启动失败
#    SESSION_SECRET 至少 32 字节：
#      python -c "import secrets;print(secrets.token_urlsafe(48))"

# 3. 一条命令起全栈
docker compose up --build -d

# 4. 验收：健康检查免认证
curl -s http://localhost:8080/health
```

`DATABASE_URL` / `QDRANT_URL` 留空即可：compose 会把容器内网地址
（`db:5432`、`qdrant:6333`）注入 api；只有在宿主机直接跑 `uvicorn` 时才需要填 `localhost`。

- 入口：`http://localhost:8080`（端口取自 `.env` 的 `WEB_PORT`）
- 健康检查：`GET /health`，返回版本、时间、`db` / `qdrant` / `llm` 三项依赖连通状态
- 业务路由：骨架期一律 501 `{"code":1500,"message":"未实现"}`，不是 404
- 门禁：`make check`（14 项），任一子项非零退出码即未通过
- 只跑文档与规约相关的门禁：`make check-docs`（5 项）
- 不装 Docker 只跑后端：`cd backend && pip install -r requirements.lock && pytest -q tests`
- 只跑前端：`cd frontend && npm ci && npx vitest run`（类型检查 `npx vue-tsc --noEmit`）

密钥只放在各人本机的 `.env`：不进代码、不进镜像层、不进前端产物、不进版本历史。轮换步骤见 `docs/specs/03-安全开发规范.md` §3。

## 目录

```
.
├── AGENTS.md                    # 常驻约束：三条硬约束 + 门禁 + 提交与评审（每次会话都读）
├── CLAUDE.md                    # 指向 AGENTS.md 的一行指针
├── .env.example                 # 只有键名
├── Makefile                     # 门禁入口
├── .cursor/rules/*.mdc          # 按 glob 生效的规则文件（改到对应目录才读）
├── skills/<name>/SKILL.md       # 按场景执行的流程（补测试、发版本、跑评测、数据变更、评审）
├── openspec/
│   ├── project.md               # 项目上下文约定
│   └── changes/2026-10-28-bootstrap-skeleton/
│       ├── proposal.md          # 为什么做、边界在哪
│       ├── design.md            # 选型与取舍
│       ├── tasks.md             # 可执行清单（骨架排最前）
│       └── specs/<能力>/spec.md # 六条能力，逐条 Requirement + Scenario
├── docs/
│   ├── specs/                   # 八份规范文件（01–08）
│   ├── data-dictionary.md       # 数据字典（唯一处）
│   ├── changes/                 # 变更说明与验证记录
│   └── lesson-07/               # 本课交付：核查清单、能力矩阵、验证与评审记录
├── backend/                     # FastAPI：app/{api,services,repositories,models,schemas,core,integrations}
│   ├── app/main.py              # 装配顺序 Settings → 日志 → 中间件 → 异常处理器 → 路由
│   ├── app/api/v1/health.py     # /health、/health/live、/health/ready（免认证，不走信封）
│   ├── migrations/              # Alembic（骨架期无迁移）
│   └── tests/                   # pytest：健康检查、空壳 501、404 信封、request_id
├── frontend/                    # Vue3 + Element Plus + Vite，仅 /health 探活页
│   ├── src/styles/tokens.scss   # 间距 8/16/24/32、字号 14/16/20、Element Plus 变量覆盖
│   └── nginx.conf               # 反代 /api/ 与 /health 到 api:8000，不服务 uploads/
├── Dockerfile.api               # 只用 requirements.lock，非 root 运行
├── Dockerfile.web               # node 构建 → nginx 托管
├── docker-compose.yml           # 只有 web 映射宿主端口；api/db/qdrant 不映射
└── .dockerignore                # .env 与版本历史不进镜像层
```

## 文档索引

| 想做什么 | 先读 |
| --- | --- |
| 知道这次做什么、不做什么 | `openspec/changes/2026-10-28-bootstrap-skeleton/proposal.md` |
| 知道为什么这么选型 | `.../design.md` |
| 知道每条能力的确切行为与失败路径 | `.../specs/<能力>/spec.md` |
| 照着把骨架写出来 | `.../tasks.md` 第 1 组 |
| 改前端代码前 | `docs/specs/01-产品设计规范.md`、`.cursor/rules/product.mdc` |
| 改后端代码前 | `docs/specs/02-后端开发规范.md`、`.cursor/rules/backend.mdc` |
| 提交前 | `docs/specs/08-评审与完成定义规范.md`、`docs/lesson-07/01-checklist.md` |

## 团队

CampusClaw · TeamVibe。主干保护规则、评审人与响应时限见 `docs/specs/08-评审与完成定义规范.md`。
