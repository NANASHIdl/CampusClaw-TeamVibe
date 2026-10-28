# 交叉评审记录

按 `docs/specs/08-评审与完成定义规范.md` §1 第 6 条与 §4：**组内另一人在自己机器上从零启动成功**，才算完成。

## 本次评审

| 项 | 内容 |
| --- | --- |
| 变更名 | `2026-10-28-bootstrap-skeleton` |
| 作者 | TeamVibe |
| 评审人 | 待填（组内另一人，不与作者同一人） |
| 评审日期 | 待填 |
| 评审机器 | 待填（操作系统 + Docker 版本） |
| 结论 | 待填（通过 / 打回 + 原因） |

## 评审人执行步骤（照抄即可）

```bash
# 1. 从零克隆（不要用已有工作目录）
git clone https://github.com/NANASHIdl/CampusClaw-TeamVibe.git cc-peer
cd cc-peer

# 2. 配置：只填本机 .env，不提交
cp .env.example .env
#    SESSION_SECRET: python -c "import secrets;print(secrets.token_urlsafe(48))"
#    DATABASE_URL / QDRANT_URL / LLM_* / EMBEDDING_* / SEED_*_PASSWORD 全部填上

# 3. 一条命令启动
docker compose up --build -d

# 4. 验收
curl -s localhost:8080/health
```

## 记录表

| # | 检查项 | 期望 | 实测 | 结论 |
| --- | --- | --- | --- | --- |
| 1 | `git clone` 成功、仓库体积合理 | 无大文件、无 `uploads/` | | |
| 2 | `.env.example` 只有键名 | 无任何明文值 | | |
| 3 | 缺 `SESSION_SECRET` 时启动失败 | 退出码 1，日志 `missing_env` | | |
| 4 | 填全后一条命令启动 | `docker compose up --build -d` 后三个容器 `Up` | | |
| 5 | `/health` 免认证可访问 | HTTP 200，`deps` 三项 `up` | | |
| 6 | 停掉 qdrant 后降级 | `/health` 503，`deps.qdrant=down`，api 仍 `Up` | | |
| 7 | 日志一行一条 JSON | `docker compose logs api` 每行可 `json.loads` | | |
| 8 | 请求标识可串起链路 | 同一 `request_id` 出现在 ≥ 2 条日志 | | |
| 9 | `make check-docs` | 通过 | | |
| 10 | 中间是否需要口头补充 | **不需要** | | |

## 结论填写要求

- 第 10 项为「需要」时，视为 `README.md` 未达标：把缺的步骤补进 `README.md`，重跑一遍再记。
- 打回时必须写：哪条规约、哪条 Scenario、怎么复现。不写「感觉不太对」。

## 历史记录

| 日期 | 评审人 | 机器 | 结论 | 备注 |
| --- | --- | --- | --- | --- |
| — | — | — | 待执行 | 骨架未落地，无法启动；第 1 组完成后执行 |
