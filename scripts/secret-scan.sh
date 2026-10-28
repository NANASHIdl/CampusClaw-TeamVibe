#!/usr/bin/env bash
# 密钥扫描：优先 gitleaks，未安装时用本脚本兜底（覆盖本项目已知键名与常见令牌形态）。
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
err() { echo "  ✗ $1"; fail=1; }
ok()  { echo "  ✓ $1"; }

echo "secret-scan"

if command -v gitleaks >/dev/null 2>&1; then
  if gitleaks detect --no-git --redact -v -s "$ROOT" >/dev/null 2>&1; then
    ok "gitleaks 未发现密钥"
  else
    err "gitleaks 命中（详见 gitleaks detect --no-git -v）"
  fi
  exit "$fail"
fi

echo "  · gitleaks 未安装，使用内置规则"

# 1. .env 不得入库
if git -C "$ROOT" ls-files --error-unmatch .env >/dev/null 2>&1; then
  err ".env 被版本库跟踪"
else
  ok ".env 未被跟踪"
fi

# 2. 已知键名不得带非空值（.env.example 例外）
# 只匹配「= 后面跟着 token 形态的值」，避免把文档里的 `SESSION_SECRET=` 这种键名引用误判
KEYS='SESSION_SECRET|LLM_API_KEY|EMBEDDING_API_KEY|SEED_TEACHER_PASSWORD|SEED_STUDENT_PASSWORD'
hits=$(grep -rnE "(${KEYS})[[:space:]]*=[[:space:]]*[A-Za-z0-9_/+.-]{8,}" "$ROOT" \
        --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=scripts \
        --exclude=".env.example" 2>/dev/null || true)
if [ -n "$hits" ]; then
  echo "$hits" | head -5
  err "已知键名出现非空值"
else
  ok "已知键名均为空或占位"
fi

# 3. 常见令牌形态
if grep -rnE '(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})' "$ROOT" \
     --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=scripts >/dev/null 2>&1; then
  err "疑似真实令牌（sk- / ghp_ / AKIA 前缀）"
else
  ok "无 sk-/ghp_/AKIA 形态令牌"
fi

# 4. 私钥块
if grep -rn 'BEGIN \(RSA \|OPENSSH \|EC \)\?PRIVATE KEY' "$ROOT" \
     --exclude-dir=.git --exclude-dir=scripts >/dev/null 2>&1; then
  err "仓库中存在私钥块"
else
  ok "无私钥块"
fi

echo
if [ "$fail" -ne 0 ]; then echo "secret-scan: 未通过（处置方式是轮换，不是删文件）"; exit 1; fi
echo "secret-scan: 通过"
