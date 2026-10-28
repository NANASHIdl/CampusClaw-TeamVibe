#!/usr/bin/env bash
# 文档门禁：八份规范文件存在且章节齐、术语表与页面清单可解析、
# 数据字典与规则文件/技能一一对应、文档中无 TODO 占位。
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
err() { echo "  ✗ $1"; fail=1; }
ok()  { echo "  ✓ $1"; }

echo "docs-lint"

SPECS=(
  "01-产品设计规范.md"
  "02-后端开发规范.md"
  "03-安全开发规范.md"
  "04-测试规范.md"
  "05-部署运维规范.md"
  "06-AI应用规范.md"
  "07-数据规范.md"
  "08-评审与完成定义规范.md"
)

for f in "${SPECS[@]}"; do
  p="$ROOT/docs/specs/$f"
  if [ ! -s "$p" ]; then err "缺 docs/specs/$f"; continue; fi
  n=$(grep -c '^## ' "$p")
  if [ "$n" -lt 5 ]; then err "$f 章节仅 $n 个（要求 ≥ 5）"; else ok "$f（$n 章）"; fi
done

# 每条规范必须写清「判据」或「违反时」
for f in "${SPECS[@]}"; do
  p="$ROOT/docs/specs/$f"
  [ -s "$p" ] || continue
  grep -qE '判据|违反时' "$p" || err "$f 没有任何「判据」或「违反时」"
done

# 产品规范：术语表与页面清单
p="$ROOT/docs/specs/01-产品设计规范.md"
[ -s "$p" ] && grep -q '术语表' "$p" && ok "术语表存在" || err "缺术语表"
[ -s "$p" ] && grep -q '页面（路由）清单' "$p" && ok "页面清单存在" || err "缺页面清单"

# 数据字典：每张表都要有条目
DD="$ROOT/docs/data-dictionary.md"
if [ -s "$DD" ]; then
  miss=0
  for t in users classes memberships materials chunks sessions messages ask_logs; do
    grep -q "^## $t " "$DD" || { err "数据字典缺表 $t"; miss=1; }
  done
  [ "$miss" -eq 0 ] && ok "数据字典覆盖 8 张表"
else
  err "缺 docs/data-dictionary.md"
fi

# 规则文件与技能一一对应
rn=0
for r in product backend security testing ops ai data review; do
  if [ -s "$ROOT/.cursor/rules/$r.mdc" ]; then rn=$((rn+1)); else err "缺 .cursor/rules/$r.mdc"; fi
done
[ "$rn" -eq 8 ] && ok "8 个规则文件" || err "规则文件仅 $rn/8"
sn=0
for s in spec-change write-tests release prompt-eval data-change review-change; do
  if [ -s "$ROOT/skills/$s/SKILL.md" ]; then sn=$((sn+1)); else err "缺 skills/$s/SKILL.md"; fi
done
[ "$sn" -eq 6 ] && ok "6 个技能" || err "技能仅 $sn/6"

# 常驻约束：三条硬约束在 AGENTS.md
grep -q '跨班一律 404' "$ROOT/AGENTS.md" && ok "AGENTS.md: 硬约束 1" || err "AGENTS.md 缺「跨班一律 404」"
grep -q '班级标识只取自会话' "$ROOT/AGENTS.md" && ok "AGENTS.md: 硬约束 2" || err "AGENTS.md 缺「班级标识只取自会话」"
grep -q '密钥不入库' "$ROOT/AGENTS.md" && ok "AGENTS.md: 硬约束 3" || err "AGENTS.md 缺「密钥不入库」"

# 无占位符
if grep -rniE '\bTODO\b|\bTBD\b|待补' "$ROOT/docs" >/dev/null 2>&1; then
  err "docs/ 中存在 TODO/TBD/待补 占位"
else
  ok "docs/ 无占位符"
fi

echo
if [ "$fail" -ne 0 ]; then echo "docs-lint: 未通过"; exit 1; fi
echo "docs-lint: 通过"
