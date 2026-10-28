SHELL := /usr/bin/env bash
CHANGE ?= 2026-10-28-bootstrap-skeleton
TAG ?= v0.0.1-skeleton

.PHONY: help check check-docs \
        api-lint api-types api-test api-migrate \
        web-lint web-types web-test e2e \
        fmt-check layout secret-scan spec-validate docs-lint gate-tamper \
        test-api test-web eval seed-test gates-refresh tag-skeleton

help:
	@echo "make check            全量门禁（14 项）"
	@echo "make check-docs       文档与规约门禁（骨架落地前可用）"
	@echo "make test-api         只跑后端测试"
	@echo "make eval             跑提示词评测集（20 条，须 20/20）"
	@echo "make gates-refresh    重算门禁文件摘要（改门禁时必须人审）"

# ---------- 全量 ----------
check: api-lint api-types api-test api-migrate \
       web-lint web-types web-test e2e \
       fmt-check layout secret-scan spec-validate docs-lint gate-tamper
	@echo "check: 全部通过"

check-docs: layout secret-scan spec-validate docs-lint gate-tamper
	@echo "check-docs: 通过（代码类子项待骨架落地）"

# ---------- 骨架未落地时的显式失败 ----------
define require_backend
	@test -f backend/app/main.py || { \
	  echo "✗ 骨架未落地：见 openspec/changes/$(CHANGE)/tasks.md 第 1 组"; exit 1; }
endef

define require_frontend
	@test -f frontend/package.json || { \
	  echo "✗ 骨架未落地：见 openspec/changes/$(CHANGE)/tasks.md 第 1 组"; exit 1; }
endef

# ---------- 后端 ----------
# 后端工具链都从 backend/ 目录跑：pyproject.toml 在 backend/，ruff/mypy/pytest 的配置也在那里
api-lint:
	$(require_backend)
	@cd backend && ruff check app tests

api-types:
	$(require_backend)
	@cd backend && mypy app

api-test: test-api

test-api:
	$(require_backend)
	@cd backend && pytest -q tests

api-migrate:
	$(require_backend)
	@if [ -z "$$(ls backend/migrations/versions/*.py 2>/dev/null)" ]; then \
	  echo "· 骨架期无迁移文件（第 2 组起有），跳过 alembic"; \
	 else \
	  cd backend && alembic check && alembic downgrade -1 && alembic upgrade head; \
	 fi

# ---------- 前端 ----------
web-lint:
	$(require_frontend)
	@cd frontend && npx eslint src

web-types:
	$(require_frontend)
	@cd frontend && npx vue-tsc --noEmit

web-test: test-web

test-web:
	$(require_frontend)
	@cd frontend && npx vitest run

e2e:
	$(require_frontend)
	@if [ -n "$$(ls frontend/e2e/*.spec.ts 2>/dev/null)" ]; then \
	  cd frontend && npx playwright test; \
	 else \
	  echo "· e2e 空跑：frontend/e2e/*.spec.ts 不存在"; \
	  echo "  骨架期只有 /health 探活页，端到端链路（登录→资料→提问）第 2 组起落地，届时本项自动生效"; \
	 fi

# ---------- 通用 ----------
fmt-check:
	@if [ -f backend/app/main.py ]; then cd backend && ruff format --check app tests; \
	 else echo "· 后端未落地，跳过 ruff format"; fi
	@if [ -f frontend/package.json ]; then cd frontend && npx prettier --check "src/**/*.{vue,ts}"; \
	 else echo "· 前端未落地，跳过 prettier"; fi

layout:
	@bash scripts/layout-check.sh

secret-scan:
	@bash scripts/secret-scan.sh

spec-validate:
	@if command -v openspec >/dev/null 2>&1; then \
	  echo "· openspec 已安装，先跑真实 --strict"; \
	  openspec validate $(CHANGE) --strict; \
	 else \
	  echo "· openspec 未安装，跳过 --strict（scripts/spec-lint.sh 会覆盖结构类判据）"; \
	 fi
	@bash scripts/spec-lint.sh $(CHANGE)

docs-lint:
	@bash scripts/docs-lint.sh

# 门禁文件被改动时必须重算摘要；重算本身要人审（见 docs/specs/08 §8）
gate-tamper:
	@if [ -f .gates.sha256 ]; then sha256sum -c .gates.sha256 --quiet && echo "gate-tamper: 通过"; \
	 else echo "✗ 缺 .gates.sha256，先执行 make gates-refresh"; exit 1; fi

gates-refresh:
	@sha256sum Makefile .githooks/pre-commit AGENTS.md .cursor/rules/*.mdc > .gates.sha256
	@echo "gates-refresh: 已重算，共 $$(wc -l < .gates.sha256) 项"

# ---------- 其他 ----------
eval:
	$(require_backend)
	@cd backend && pytest -q tests/eval -m eval

seed-test:
	$(require_backend)
	@cd backend && python -m tests.seed

tag-skeleton:
	@git tag -a $(TAG) -m "skeleton: 可启动的壳，/health 免认证可用" && \
	 echo "tag-skeleton: 已打 $(TAG)"
