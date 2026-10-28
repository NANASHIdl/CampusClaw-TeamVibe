# CLAUDE.md

本仓库的常驻约束统一写在 [`AGENTS.md`](./AGENTS.md)，请直接阅读该文件。

要点摘录（完整内容以 `AGENTS.md` 为准）：

1. 三条硬约束：跨班一律 404；`class_id` 只取自会话；密钥不入库、不进镜像、不进前端。
2. 门禁：`make check`；骨架落地前用 `make check-docs`。不得为变绿而放宽检查或删断言。
3. 提交信息尾部写 `Change:` / `Verify:` / `Evidence:` 三字段，值必须查得到。
4. 八份规范文件在 `docs/specs/`，按 glob 生效的规则在 `.cursor/rules/`，按场景执行的流程在 `skills/`。
