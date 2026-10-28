#!/usr/bin/env bash
# 规约结构校验：openspec 未安装时的本地兜底。
#
# 校验项与 `openspec validate --strict` 对齐，并对任务清单 §二 §五 的判据做逐能力检查：
#   1. 四份文件齐（proposal / design / tasks / specs/<能力>/spec.md）
#   2. proposal 有 Why / What Changes / Impact
#   3. 每个 Scenario 三段齐（前置条件 / 操作 / 可观测结果）
#   4. Scenario 编号全局唯一
#   5. **每条能力的失败路径 ≥ 4 条**，且四类各至少一条（参数非法 / 无权限 / 资源不存在 / 依赖不可达）
#   6. tasks.md 第 1 组为骨架，且有可执行条目
#
# 第 5 项是 2026-10-28 收紧的：原实现只在整个 specs 目录里 grep 四个关键词，
# 任一文件出现「不存在」就算过，并不校验「每条能力」。见 docs/lesson-07/03-validate-record.md。
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

# ---------- 1. 四份文件齐 ----------
for f in proposal.md design.md tasks.md; do
  [ -s "$DIR/$f" ] && ok "$f" || err "缺 $f"
done
mapfile -t SPECS < <(find "$DIR/specs" -mindepth 2 -maxdepth 2 -name 'spec.md' 2>/dev/null | sort)
[ "${#SPECS[@]}" -ge 1 ] && ok "specs/<能力>/spec.md × ${#SPECS[@]}" || err "缺 specs/<能力>/spec.md"

# ---------- 2. proposal 必需章节 ----------
grep -q '^## Why' "$DIR/proposal.md" 2>/dev/null && ok "proposal: Why" || err "proposal 缺 ## Why"
grep -q '^## What Changes' "$DIR/proposal.md" 2>/dev/null && ok "proposal: What Changes" || err "proposal 缺 ## What Changes"
grep -q '^## Impact' "$DIR/proposal.md" 2>/dev/null && ok "proposal: Impact" || err "proposal 缺 ## Impact"

# ---------- 3/5. 逐能力解析 Scenario ----------
python_bin=""
for c in python3 python py; do command -v "$c" >/dev/null 2>&1 && { python_bin="$c"; break; }; done

if [ -z "$python_bin" ]; then
  echo "  ! 未找到 python，跳过 Scenario 三段与失败路径检查（不算通过）"
  fail=1
else
  report=$("$python_bin" - "${SPECS[@]}" <<'PY'
import re
import sys

REQUIRED_FIELDS = ("前置条件", "操作", "可观测结果")

# 失败路径的判据：可观测结果里必须断言一个错误状态码或登记过的错误码
ERROR_SIGNAL = re.compile(r"(HTTP\s*)?\b[45]\d{2}\b|code\s*=\s*1\d{3}")

CATEGORIES = {
    "参数非法": ("非法", "越界", "格式", "长度", "为空", "超长", "枚举", "取值", "上限", "冲突", "锁定"),
    "无权限": ("未登录", "越权", "跨班", "角色", "他人", "被拒", "伪造"),
    "资源不存在": ("不存在", "已删除", "不可见", "不可读", "残留"),
    "依赖不可达": ("不可达", "降级", "超时", "失败", "不可用"),
}

errors = []
oks = []
all_ids = []

for path in sys.argv[1:]:
    name = path.split("/")[-2]
    text = open(path, encoding="utf-8").read()

    if "## ADDED Requirements" not in text:
        errors.append(f"{name}: 缺 ## ADDED Requirements")

    reqs = re.findall(r"^### Requirement: ", text, flags=re.M)
    blocks = re.split(r"^#### Scenario: ", text, flags=re.M)[1:]
    if not reqs:
        errors.append(f"{name}: 没有 Requirement")
    if not blocks:
        errors.append(f"{name}: 没有 Scenario")
        continue

    failures = 0
    covered: dict[str, set[str]] = {key: set() for key in CATEGORIES}
    missing_fields = []

    for block in blocks:
        title = block.splitlines()[0].strip()
        scenario_id = title.split()[0] if title else "(无编号)"
        all_ids.append(scenario_id)

        for field in REQUIRED_FIELDS:
            if field not in block:
                missing_fields.append(f"{scenario_id} 缺 {field}")

        observable = re.search(r"\*\*可观测结果\*\*[：:](.*?)(?=\n####|\Z)", block, flags=re.S)
        observable_text = observable.group(1) if observable else block

        if ERROR_SIGNAL.search(observable_text):
            failures += 1
            for category, keywords in CATEGORIES.items():
                if any(keyword in block for keyword in keywords):
                    covered[category].add(scenario_id)

    if missing_fields:
        errors.extend(f"{name}: {item}" for item in missing_fields)

    if failures < 4:
        errors.append(f"{name}: 失败路径仅 {failures} 条（要求 ≥ 4）")
    else:
        gaps = [category for category, hits in covered.items() if not hits]
        if gaps:
            errors.append(f"{name}: 失败路径未覆盖 {'/'.join(gaps)}")
        else:
            oks.append(
                f"{name}: {len(blocks)} 条 Scenario，失败路径 {failures} 条，四类齐"
            )

dupes = sorted({item for item in all_ids if all_ids.count(item) > 1})
if dupes:
    errors.append("编号重复: " + " ".join(dupes))

for line in oks:
    print("OK|" + line)
if not dupes:
    print("OK|Scenario 编号唯一")
for line in errors:
    print("ERR|" + line)
PY
)

  while IFS= read -r line; do
    [ -z "$line" ] && continue
    case "$line" in
      OK\|*)  ok  "${line#OK|}" ;;
      ERR\|*) err "${line#ERR|}" ;;
    esac
  done <<< "$report"
fi

# ---------- 6. tasks：骨架组排最前 ----------
first_group=$(grep -m1 '^## [0-9]' "$DIR/tasks.md" | sed 's/^## //')
case "$first_group" in
  1.*) grep -q '骨架' <<< "$first_group" && ok "tasks: 第 1 组为骨架" || err "tasks: 第 1 组不是骨架（当前: $first_group）";;
  *) err "tasks: 首组不是第 1 组（当前: $first_group）";;
esac
grep -q '^- \[ \]' "$DIR/tasks.md" && ok "tasks: 有可执行条目" || err "tasks: 没有 - [ ] 条目"

echo
if [ "$fail" -ne 0 ]; then echo "spec-lint: 未通过"; exit 1; fi
echo "spec-lint: 通过"
