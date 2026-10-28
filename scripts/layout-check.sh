#!/usr/bin/env bash
# 分层门禁：检查后端 import 图是否存在反向依赖、路由是否声明准入。
# 骨架未落地时为空跑（没有代码可违规），但会明确打印，不静默通过。
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/backend/app"
fail=0
err() { echo "  ✗ $1"; fail=1; }
ok()  { echo "  ✓ $1"; }

echo "layout"

if [ ! -d "$APP" ]; then
  echo "  · 无 backend/app：骨架未落地，空跑通过（第 1 组任务完成后生效）"
  echo "layout: 空跑"
  exit 0
fi

for d in api services repositories models schemas core integrations; do
  [ -d "$APP/$d" ] && ok "分层目录 app/$d" || err "缺分层目录 app/$d"
done

# 反向依赖
# 只匹配真实的 import 语句：原实现用全文 grep，把注释里写「不 import fastapi」也算违规，
# 于是「解释规则」本身会触发规则。收窄到 import 行是提高精度，不是放宽——漏报的只有散文。
IMPORT_RE='^[[:space:]]*(from|import)[[:space:]]+'
if grep -rnE "${IMPORT_RE}app\.repositories" "$APP/api" >/dev/null 2>&1; then
  err "api/ 直接依赖 repositories/（应经 services/）"
else
  ok "api/ 未依赖 repositories/"
fi

if grep -rnE "${IMPORT_RE}app\.services" "$APP/repositories" >/dev/null 2>&1; then
  err "repositories/ 依赖 services/（反向）"
else
  ok "repositories/ 未依赖 services/"
fi

if grep -rnE "${IMPORT_RE}fastapi" "$APP/services" >/dev/null 2>&1; then
  err "services/ 出现 fastapi 依赖（业务层不应知道 HTTP）"
else
  ok "services/ 无 fastapi 依赖"
fi

# SQL 只允许出现在 repositories/
sql_hits=$(grep -rnE '(text\("|select\(|INSERT INTO|UPDATE .* SET )' "$APP" \
             --include='*.py' 2>/dev/null | grep -v "/repositories/" || true)
if [ -n "$sql_hits" ]; then
  echo "$sql_hits" | head -5
  err "repositories/ 之外出现 SQL"
else
  ok "SQL 只在 repositories/"
fi

# 出站调用只允许在 integrations/
net_hits=$(grep -rnE '(httpx\.|AsyncClient\(|qdrant_client)' "$APP" --include='*.py' 2>/dev/null \
             | grep -v "/integrations/" | grep -v "/core/" || true)
if [ -n "$net_hits" ]; then
  echo "$net_hits" | head -5
  err "integrations/ 之外出现出站调用"
else
  ok "出站调用只在 integrations/"
fi

# 路由准入声明
missing=0
while IFS= read -r f; do
  if ! grep -qE 'require_role|get_current_user|免认证' "$f"; then
    err "路由未声明准入: ${f#$ROOT/}"
    missing=1
  fi
done < <(find "$APP/api" -name '*.py' ! -name '__init__.py' 2>/dev/null)
[ "$missing" -eq 0 ] && ok "所有路由声明了准入"

echo
if [ "$fail" -ne 0 ]; then echo "layout: 未通过"; exit 1; fi
echo "layout: 通过"
