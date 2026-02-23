#!/usr/bin/env bash
set -euo pipefail

QUIET=0
POSITIONAL=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --quiet)
      QUIET=1
      shift
      ;;
    -h|--help)
      cat <<USAGE
Usage: snapshot.sh [target_dir] [output_file] [--quiet]

Examples:
  ./scripts/snapshot.sh . SNAPSHOT.md
  ./scripts/snapshot.sh ../my-app ./SNAPSHOT.md --quiet
USAGE
      exit 0
      ;;
    *)
      POSITIONAL+=("$1")
      shift
      ;;
  esac
done

TARGET_DIR="${POSITIONAL[0]:-.}"
OUTPUT_FILE="${POSITIONAL[1]:-SNAPSHOT.md}"

if [ ! -d "$TARGET_DIR" ]; then
  echo "[error] target directory not found: $TARGET_DIR" >&2
  exit 1
fi

USE_RG=0
if command -v rg >/dev/null 2>&1; then
  USE_RG=1
fi

TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"
DATE_NOW="$(date +%Y-%m-%d)"

# Optional project-level tuning file to reduce false positives.
# Supported keys (regex fragments, no surrounding slashes):
# - SNAPSHOT_IGNORE_DIRS (comma-separated)
# - SNAPSHOT_AUTH_KEYWORDS_EXTRA
# - SNAPSHOT_AUTH_FILE_PATTERNS_EXTRA
# - SNAPSHOT_BILLING_KEYWORDS_EXTRA
# - SNAPSHOT_COMPLIANCE_KEYWORDS_EXTRA
# - SNAPSHOT_RELIABILITY_KEYWORDS_EXTRA
# - SNAPSHOT_ANALYTICS_KEYWORDS_EXTRA
CONFIG_FILE="$TARGET_DIR/.snapshotrc"
SNAPSHOT_IGNORE_DIRS="${SNAPSHOT_IGNORE_DIRS:-}"
SNAPSHOT_AUTH_KEYWORDS_EXTRA="${SNAPSHOT_AUTH_KEYWORDS_EXTRA:-}"
SNAPSHOT_AUTH_FILE_PATTERNS_EXTRA="${SNAPSHOT_AUTH_FILE_PATTERNS_EXTRA:-}"
SNAPSHOT_BILLING_KEYWORDS_EXTRA="${SNAPSHOT_BILLING_KEYWORDS_EXTRA:-}"
SNAPSHOT_COMPLIANCE_KEYWORDS_EXTRA="${SNAPSHOT_COMPLIANCE_KEYWORDS_EXTRA:-}"
SNAPSHOT_RELIABILITY_KEYWORDS_EXTRA="${SNAPSHOT_RELIABILITY_KEYWORDS_EXTRA:-}"
SNAPSHOT_ANALYTICS_KEYWORDS_EXTRA="${SNAPSHOT_ANALYTICS_KEYWORDS_EXTRA:-}"

trim_space() {
  local s="$1"
  s="$(echo "$s" | sed 's/^ *//; s/ *$//')"
  echo "$s"
}

strip_quotes() {
  local s="$1"
  if [[ "$s" == \"*\" && "$s" == *\" ]]; then
    s="${s:1:${#s}-2}"
  elif [[ "$s" == \'*\' && "$s" == *\' ]]; then
    s="${s:1:${#s}-2}"
  fi
  echo "$s"
}

load_snapshot_config_safe() {
  local file="$1"
  local line key value
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%%#*}"
    line="$(trim_space "$line")"
    [ -z "$line" ] && continue
    if [[ ! "$line" =~ ^[A-Za-z0-9_]+[[:space:]]*= ]]; then
      continue
    fi
    key="${line%%=*}"
    value="${line#*=}"
    key="$(trim_space "$key")"
    value="$(trim_space "$value")"
    value="$(strip_quotes "$value")"
    case "$key" in
      SNAPSHOT_IGNORE_DIRS) SNAPSHOT_IGNORE_DIRS="$value" ;;
      SNAPSHOT_AUTH_KEYWORDS_EXTRA) SNAPSHOT_AUTH_KEYWORDS_EXTRA="$value" ;;
      SNAPSHOT_AUTH_FILE_PATTERNS_EXTRA) SNAPSHOT_AUTH_FILE_PATTERNS_EXTRA="$value" ;;
      SNAPSHOT_BILLING_KEYWORDS_EXTRA) SNAPSHOT_BILLING_KEYWORDS_EXTRA="$value" ;;
      SNAPSHOT_COMPLIANCE_KEYWORDS_EXTRA) SNAPSHOT_COMPLIANCE_KEYWORDS_EXTRA="$value" ;;
      SNAPSHOT_RELIABILITY_KEYWORDS_EXTRA) SNAPSHOT_RELIABILITY_KEYWORDS_EXTRA="$value" ;;
      SNAPSHOT_ANALYTICS_KEYWORDS_EXTRA) SNAPSHOT_ANALYTICS_KEYWORDS_EXTRA="$value" ;;
      *)
        ;;
    esac
  done < "$file"
}

if [ -f "$CONFIG_FILE" ]; then
  load_snapshot_config_safe "$CONFIG_FILE"
fi

IGNORE_DIRS_BASE=".git,node_modules"
if [ -n "${SNAPSHOT_IGNORE_DIRS:-}" ]; then
  IGNORE_DIRS="$IGNORE_DIRS_BASE,$SNAPSHOT_IGNORE_DIRS"
else
  IGNORE_DIRS="$IGNORE_DIRS_BASE"
fi

IFS=',' read -r -a IGNORE_DIR_ARR <<< "$IGNORE_DIRS"

build_rg_ignore_args() {
  RG_IGNORE_ARGS=()
  local d
  for d in "${IGNORE_DIR_ARR[@]}"; do
    d="$(echo "$d" | sed 's/^ *//; s/ *$//')"
    [ -z "$d" ] && continue
    RG_IGNORE_ARGS+=("-g" "!$d/**")
  done
}

build_grep_exclude_args() {
  GREP_EXCLUDE_ARGS=()
  local d
  for d in "${IGNORE_DIR_ARR[@]}"; do
    d="$(echo "$d" | sed 's/^ *//; s/ *$//')"
    [ -z "$d" ] && continue
    GREP_EXCLUDE_ARGS+=("--exclude-dir=$d")
  done
}

build_rg_ignore_args
build_grep_exclude_args

merge_regex() {
  local base="$1"
  local extra="$2"
  if [ -n "$extra" ]; then
    echo "($base|$extra)"
  else
    echo "$base"
  fi
}

REGEX_FRONTEND_FILES='(package\.json|pnpm-lock\.yaml|bun\.lockb|yarn\.lock)'
REGEX_FRONTEND_ENTRY='(src/main\.(t|j)sx?|src/App\.(t|j)sx?|app/layout\.(t|j)sx?)'
REGEX_FRONTEND_TEXT='(next|react|vite|tailwind)'
REGEX_AUTH_TEXT="$(merge_regex '(next-auth|nextauth|clerk|supabase\.auth|firebase auth|auth0)' "${SNAPSHOT_AUTH_KEYWORDS_EXTRA:-}")"
REGEX_AUTH_FILE="$(merge_regex '(auth|login|signup|register|session|oauth)' "${SNAPSHOT_AUTH_FILE_PATTERNS_EXTRA:-}")"
REGEX_BILLING_TEXT="$(merge_regex '(stripe|paddle|paypal|toss|iamport|billing|subscription|checkout)' "${SNAPSHOT_BILLING_KEYWORDS_EXTRA:-}")"
REGEX_BILLING_SAFE='(webhook|idempotency|refund|invoice)'
REGEX_COMPLIANCE_FILE='(privacy|terms|policy|gdpr|compliance)'
REGEX_COMPLIANCE_TEXT="$(merge_regex '(privacy policy|terms of service|data deletion|delete account)' "${SNAPSHOT_COMPLIANCE_KEYWORDS_EXTRA:-}")"
REGEX_RELIABILITY_FILE='(\.github/workflows/|Dockerfile|docker-compose|Procfile)'
REGEX_RELIABILITY_TEXT="$(merge_regex '(sentry|monitoring|alert|backup|incident|retry|circuit)' "${SNAPSHOT_RELIABILITY_KEYWORDS_EXTRA:-}")"
REGEX_ANALYTICS_TEXT="$(merge_regex '(google analytics|gtag|plausible|posthog|mixpanel|amplitude|event tracking)' "${SNAPSHOT_ANALYTICS_KEYWORDS_EXTRA:-}")"
REGEX_ANALYTICS_SEO='(utm_|sitemap|robots\.txt|og:|open graph)'

has_file() {
  local pattern="$1"
  if [ "$USE_RG" -eq 1 ]; then
    rg --files "$TARGET_DIR" "${RG_IGNORE_ARGS[@]}" | rg -q "$pattern"
  else
    # find fallback (may be slower on very large repos)
    find "$TARGET_DIR" -type f 2>/dev/null | grep -E -q "$pattern"
  fi
}

has_text() {
  local pattern="$1"
  if [ "$USE_RG" -eq 1 ]; then
    rg -n -S "$pattern" "$TARGET_DIR" "${RG_IGNORE_ARGS[@]}" >/dev/null 2>&1
  else
    grep -RInE "${GREP_EXCLUDE_ARGS[@]}" "$pattern" "$TARGET_DIR" >/dev/null 2>&1
  fi
}

score_frontend=0
score_auth=0
score_billing=0
score_compliance=0
score_reliability=0
score_analytics=0

notes_frontend=()
notes_auth=()
notes_billing=()
notes_compliance=()
notes_reliability=()
notes_analytics=()
missing_frontend=()
missing_auth=()
missing_billing=()
missing_compliance=()
missing_reliability=()
missing_analytics=()

# Frontend
if has_file "$REGEX_FRONTEND_FILES"; then
  score_frontend=$((score_frontend + 1)); notes_frontend+=("Build/package files detected")
else
  missing_frontend+=("No package/lock file detected")
fi
if has_file "$REGEX_FRONTEND_ENTRY"; then
  score_frontend=$((score_frontend + 1)); notes_frontend+=("Frontend entry files detected")
else
  missing_frontend+=("No clear frontend entry file detected")
fi
if has_text "$REGEX_FRONTEND_TEXT"; then
  score_frontend=$((score_frontend + 1)); notes_frontend+=("Frontend stack keywords detected")
else
  missing_frontend+=("No frontend framework keyword detected")
fi

# Auth
if has_text "$REGEX_AUTH_TEXT"; then
  score_auth=$((score_auth + 2)); notes_auth+=("Auth provider/library keywords detected")
else
  missing_auth+=("No auth provider/library keyword detected")
fi
if has_file "$REGEX_AUTH_FILE"; then
  score_auth=$((score_auth + 1)); notes_auth+=("Auth-related files/routes detected")
else
  missing_auth+=("No auth route/file pattern detected")
fi

# Billing
if has_text "$REGEX_BILLING_TEXT"; then
  score_billing=$((score_billing + 2)); notes_billing+=("Billing/subscription keywords detected")
else
  missing_billing+=("No billing/subscription keyword detected")
fi
if has_text "$REGEX_BILLING_SAFE"; then
  score_billing=$((score_billing + 1)); notes_billing+=("Webhook/refund/idempotency keywords detected")
else
  missing_billing+=("No webhook/idempotency/refund keyword detected")
fi

# Compliance
if has_file "$REGEX_COMPLIANCE_FILE"; then
  score_compliance=$((score_compliance + 1)); notes_compliance+=("Policy/compliance files detected")
else
  missing_compliance+=("No Privacy/Terms/Policy file detected")
fi
if has_text "$REGEX_COMPLIANCE_TEXT"; then
  score_compliance=$((score_compliance + 1)); notes_compliance+=("Policy/data deletion text detected")
else
  missing_compliance+=("No policy/data deletion text detected")
fi

# Reliability
if has_file "$REGEX_RELIABILITY_FILE"; then
  score_reliability=$((score_reliability + 1)); notes_reliability+=("CI/deploy files detected")
else
  missing_reliability+=("No CI/deploy artifact detected")
fi
if has_text "$REGEX_RELIABILITY_TEXT"; then
  score_reliability=$((score_reliability + 1)); notes_reliability+=("Monitoring/incident keywords detected")
else
  missing_reliability+=("No monitoring/incident keyword detected")
fi

# Analytics
if has_text "$REGEX_ANALYTICS_TEXT"; then
  score_analytics=$((score_analytics + 1)); notes_analytics+=("Analytics tool keywords detected")
else
  missing_analytics+=("No analytics tool keyword detected")
fi
if has_text "$REGEX_ANALYTICS_SEO"; then
  score_analytics=$((score_analytics + 1)); notes_analytics+=("SEO/traffic signal keywords detected")
else
  missing_analytics+=("No SEO/traffic signal keyword detected")
fi

clamp_3() {
  local v="$1"
  if [ "$v" -gt 3 ]; then
    echo 3
  else
    echo "$v"
  fi
}

score_frontend="$(clamp_3 "$score_frontend")"
score_auth="$(clamp_3 "$score_auth")"
score_billing="$(clamp_3 "$score_billing")"
score_compliance="$(clamp_3 "$score_compliance")"
score_reliability="$(clamp_3 "$score_reliability")"
score_analytics="$(clamp_3 "$score_analytics")"

join_notes() {
  local filtered=()
  local item
  for item in "$@"; do
    if [ -n "${item:-}" ]; then
      filtered+=("$item")
    fi
  done
  if [ "${#filtered[@]}" -eq 0 ]; then
    echo "-"
    return
  fi
  local IFS='; '
  echo "${filtered[*]}"
}

level_label() {
  local s="$1"
  if [ "$s" -eq 0 ]; then
    echo "critical"
  elif [ "$s" -eq 1 ]; then
    echo "weak"
  elif [ "$s" -eq 2 ]; then
    echo "partial"
  else
    echo "strong"
  fi
}

signal_frontend="$(join_notes "${notes_frontend[@]-}")"
signal_auth="$(join_notes "${notes_auth[@]-}")"
signal_billing="$(join_notes "${notes_billing[@]-}")"
signal_compliance="$(join_notes "${notes_compliance[@]-}")"
signal_reliability="$(join_notes "${notes_reliability[@]-}")"
signal_analytics="$(join_notes "${notes_analytics[@]-}")"
gap_frontend="$(join_notes "${missing_frontend[@]-}")"
gap_auth="$(join_notes "${missing_auth[@]-}")"
gap_billing="$(join_notes "${missing_billing[@]-}")"
gap_compliance="$(join_notes "${missing_compliance[@]-}")"
gap_reliability="$(join_notes "${missing_reliability[@]-}")"
gap_analytics="$(join_notes "${missing_analytics[@]-}")"

risk_lines=()
action_lines=()
risk_idx=0
action_idx=0

add_risk() {
  risk_idx=$((risk_idx + 1))
  risk_lines+=("${risk_idx}. $1")
}

add_action() {
  action_idx=$((action_idx + 1))
  action_lines+=("${action_idx}. $1")
}

if [ "$score_frontend" -ge 2 ] && [ "$score_auth" -eq 0 ]; then
  add_risk "[critical] Heavy frontend progress but no auth baseline detected"
  add_action "Add login/session/recovery baseline this sprint"
fi
if [ "$score_frontend" -ge 2 ] && [ "$score_billing" -eq 0 ]; then
  add_risk "[critical] Product UX exists but monetization path is missing"
  add_action "Define pricing and checkout path (success/failure/refund)"
fi
if [ "$score_billing" -ge 1 ] && [ "$score_reliability" -eq 0 ]; then
  add_risk "[high] Billing signals exist but webhook reliability controls are missing"
  add_action "Add webhook signature verification and idempotency"
fi
if [ "$score_compliance" -eq 0 ]; then
  add_risk "[high] Privacy/Terms baseline not detected"
  add_action "Add Privacy, Terms, and data deletion flow"
fi
if [ "$score_analytics" -eq 0 ]; then
  add_risk "[medium] No analytics/SEO signal detected"
  add_action "Add core events + robots/sitemap/OG metadata"
fi

if [ "${#risk_lines[@]}" -eq 0 ]; then
  add_risk "[info] No critical gap detected from heuristic scan"
  add_action "Run mmu doctor for deeper checks"
  add_action "Decide gate enforcement scope (M0/M1)"
  add_action "Add one measurable KPI for this week"
fi

risk_block="$(printf '%s\n' "${risk_lines[@]}")"
action_block="$(printf '%s\n' "${action_lines[@]}")"

cat > "$OUTPUT_FILE" <<MARKDOWN
# Project Snapshot

- Date: $DATE_NOW
- Target: $TARGET_DIR
- Method: file+keyword heuristic (quick triage)

## Domain Coverage (0-3)
| Domain | Score | Level | Signals |
|---|---:|---|---|
| Frontend | $score_frontend | $(level_label "$score_frontend") | $signal_frontend |
| Auth | $score_auth | $(level_label "$score_auth") | $signal_auth |
| Billing | $score_billing | $(level_label "$score_billing") | $signal_billing |
| Compliance | $score_compliance | $(level_label "$score_compliance") | $signal_compliance |
| Reliability | $score_reliability | $(level_label "$score_reliability") | $signal_reliability |
| Analytics | $score_analytics | $(level_label "$score_analytics") | $signal_analytics |

## Missing by Domain
| Domain | Missing Signals |
|---|---|
| Frontend | $gap_frontend |
| Auth | $gap_auth |
| Billing | $gap_billing |
| Compliance | $gap_compliance |
| Reliability | $gap_reliability |
| Analytics | $gap_analytics |

## Top Risks (Priority)
$risk_block

## Immediate Actions
$action_block

## Notes
- This snapshot is a fast directional check.
- Use mmu doctor/mmu gate for strict validation.
MARKDOWN

if [ "$QUIET" -ne 1 ]; then
  echo "[ok] snapshot written: $OUTPUT_FILE"
fi
