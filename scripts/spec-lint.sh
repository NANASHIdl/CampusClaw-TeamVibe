#!/usr/bin/env bash
# 规约结构校验：openspec 未安装时的本地兜底。
# 校验项与 openspec validate --strict 对齐：四份文件齐、Requirement 有 Scenario、
# Scenario 三段齐、编号唯一、失败路径覆盖四类、tasks 骨架组排最前。
set -uo pipefail

CHANGE="${1:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="$ROOT/openspec/changes/$CHANGE"
fail=0

err() { echo "  ✗ $1"; fail=1; }
ok()  { echo "  ✓ $1"; }

if [ -z "$CHANGE" ] || [ ! -d "$DIR" ]; then
  echo "spec-lint: 变更目录不存在: openspec/changes/$CHANGE"; exit 1
fi

echo "spec-lint: $CHANGE"

# 1. 四份文件齐
for f in proposal.md design.md tasks.md; do
  [ -s "$DIR/$f" ] && ok "$f" || err "缺 $f"
done
mapfile -t SPECS < <(find "$DIR/specs" -mindepth 2 -maxdepth 2 -name 'spec.md' 2>/dev/null | sort)
[ "${#SPECS[@]}" -ge 1 ] && ok "specs/<能力>/spec.md × ${#SPECS[@]}" || err "缺 specs/<能力>/spec.md"

# 2. proposal 必需章节
grep -q '^## Why' "$DIR/proposal.md" 2>/dev/null && ok "proposal: Why" || err "proposal 缺 ## Why"
grep -q '^## What Changes' "$DIR/proposal.md" 2>/dev/null && ok "proposal: What Changes" || err "proposal 缺 ## What Changes"
grep -q '^## Impact' "$DIR/proposal.md" 2>/dev/null && ok "proposal: Impact" || err "proposal 缺 ## Impact"

# 3. 每个 spec：ADDED 段、Requirement、Scenario 三段
all_ids=""
for s in "${SPECS[@]}"; do
  name="$(basename "$(dirname "$s")")"
  grep -q '^## ADDED Requirements' "$s" || err "$name: 缺 ## ADDED Requirements"
  reqs=$(grep -c '^### Requirement: ' "$s" || true)
  scen=$(grep -c '^#### Scenario: ' "$s" || true)
  [ "$reqs" -ge 1 ] || err "$name: 没有 Requirement"
  [ "$scen" -ge 4 ] || err "$name: Scenario 仅 $scen 条（要求 ≥ 4）"

  # 每个 Scenario 后必须有 前置条件/操作/可观测结果
  python_bin=""
  for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && { python_bin="$c"; break; }; done
  if [ -n "$python_bin" ]; then
    out=$("$python_bin" - "$s" <<'PY'
import re, sys
text = open(sys.argv[1], encoding='utf-8').read()
blocks = re.split(r'^#### Scenario: ', text, flags=re.M)[1:]
bad = []
for b in blocks:
    title = b.splitlines()[0].strip()
    body = b
    need = ['前置条件', '操作', '可观测结果']
    miss = [k for k in need if k not in body]
    if miss:
        bad.append(f"{title} 缺 {'/'.join(miss)}")
print('\n'.join(bad))
PY
)
    if [ -n "$out" ]; then
      while IFS= read -r line; do err "$name: $line"; done <<< "$out"
    else
      ok "$name: $scen 条 Scenario，三段齐"
    fi
  fi

  ids=$(grep -oE '^#### Scenario: [A-Z]{2}-[0-9]{2}' "$s" | sed 's/^#### Scenario: //' || true)
  [ -n "$ids" ] && all_ids="$all_ids$ids"$'\n'
done

# 4. 编号唯一
dupes=$(printf '%s' "$all_ids" | grep -v '^$' | sort | uniq -d)
[ -z "$dupes" ] && ok "Scenario 编号唯一" || err "编号重复: $(echo "$dupes" | tr '\n' ' ')"

# 5. 失败路径四类关键词覆盖
grep -rqiE '参数非法|取值非法|长度越界|格式非法' "$DIR/specs" && ok "失败路径: 参数非法" || err "失败路径缺「参数非法」"
grep -rqiE '未登录|越权|无权限|角色不足' "$DIR/specs" && ok "失败路径: 无权限" || err "失败路径缺「无权限」"
grep -rqiE '不存在|资源不存在' "$DIR/specs" && ok "失败路径: 资源不存在" || err "失败路径缺「资源不存在」"
grep -rqiE '不可达|依赖' "$DIR/specs" && ok "失败路径: 依赖不可达" || err "失败路径缺「依赖不可达」"

# 6. tasks：骨架组排最前
first_group=$(grep -m1 '^## [0-9]' "$DIR/tasks.md" | sed 's/^## //')
case "$first_group" in
  1.*) grep -q '骨架' <<< "$first_group" && ok "tasks: 第 1 组为骨架" || err "tasks: 第 1 组不是骨架（当前: $first_group）";;
  *) err "tasks: 首组不是第 1 组（当前: $first_group）";;
esac
grep -q '^- \[ \]' "$DIR/tasks.md" && ok "tasks: 有可执行条目" || err "tasks: 没有 - [ ] 条目"

echo
if [ "$fail" -ne 0 ]; then echo "spec-lint: 未通过"; exit 1; fi
echo "spec-lint: 通过"
