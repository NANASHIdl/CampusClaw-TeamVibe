---
name: release
description: 按部署运维规范发一次版本（构建打标签 → 迁移 → 发布 → 就绪接流量 → 打版本标签 → 留痕 → 回滚演练）。当要把某个提交部署到 test / prod 时使用。
---

# 技能：按规范发一次版本

## 何时用

- 一组任务完成、门禁全绿，需要部署到 test 或 prod；
- 需要演练回滚。

## 步骤

1. **确认门禁**：`make check` 全绿（14 项）。有红项不发布，先修。
2. **构建**：`docker build -f Dockerfile.api -t campusclaw/api:<短SHA> .`、`docker build -f Dockerfile.web -t campusclaw/web:<短SHA> .`。**禁止 `latest`**。
3. **检查镜像不含密钥**：`docker history --no-trunc campusclaw/api:<短SHA> | grep -iE "secret|api_key"` 应为空；`docker run --rm campusclaw/api:<短SHA> env | grep -E "SESSION_SECRET|API_KEY"` 应为空。
4. **迁移**：`alembic upgrade head`（先加后删，向后兼容）。确认 `downgrade()` 可用：`alembic downgrade -1 && alembic upgrade head`。
5. **发布**：`IMAGE_TAG=<短SHA> docker compose up -d --no-deps api`，再 `web`。滚动期间旧实例继续服务。
6. **接流量判定**：`curl -s localhost:8080/health/ready` 返回 200 且 `deps` 三项 `up`。未通过不接流量，直接回滚。
7. **打标签**：`git tag v0.x.y-<短名>`（骨架为 `v0.0.1-skeleton`）。
8. **留痕**：写 `docs/changes/YYYY-MM-DD-<变更名>.md`：版本号、包含变更、门禁结果、健康检查结果、回滚演练耗时。
9. **回滚演练**：`IMAGE_TAG=<上一短SHA> docker compose up -d --no-deps api`，记录耗时；恢复为当前版本。

## 完成判据

- `/health/ready` 200 且依赖三项 `up`；
- 版本标签存在，`docs/changes/` 能按标签检索到记录；
- 回滚演练耗时已记录（**未演练过的回滚不算可用**）；
- 发布前后 `uploads/` 与数据库行数无意外变化。
