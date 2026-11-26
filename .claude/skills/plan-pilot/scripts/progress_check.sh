#!/bin/sh
# usage: progress_check.sh --install
#        progress_check.sh <prepare-commit-msg arguments>
# Git prepare-commit-msg hook guarding progress.md, the checklist plan-pilot
# keeps at the root. --install writes the hook into the repository's hooks
# directory (shared by every worktree). Runs even under --no-verify.
# The rules (numbered items, no hole, [x] lines frozen, at least one new
# [x]) are checked by progress_check.py, against the base: HEAD, or HEAD^
# for --amend. Deleting the file needs every base item [x]. Without the
# file, nothing is checked.
set -u

if [ "${1:-}" = "--install" ]; then
    hooks=$(git rev-parse --git-common-dir)/hooks
    mkdir -p "$hooks"
    cat >"$hooks/prepare-commit-msg" <<'EOF'
#!/bin/sh
exec "$(git rev-parse --show-toplevel)/.claude/skills/plan-pilot/scripts/progress_check.sh" "$@"
EOF
    chmod +x "$hooks/prepare-commit-msg"
    exit 0
fi

source_kind=${2:-}
source_commit=${3:-}
case $source_kind in
    merge|squash) exit 0 ;;
esac
base=HEAD
if [ "$source_kind" = "commit" ] && [ "$(git rev-parse "$source_commit" 2>/dev/null)" = "$(git rev-parse HEAD 2>/dev/null)" ]; then
    base=HEAD^
fi

old=$(mktemp)
new=$(mktemp)
trap 'rm -f "$old" "$new"' EXIT

has_old=1
has_new=1
git show "$base:progress.md" >"$old" 2>/dev/null || has_old=0
git show ":progress.md" >"$new" 2>/dev/null || has_new=0

fail() {
    echo "progress.md: $*" >&2
    echo "progress.md: commit refused (see .claude/skills/plan-pilot/scripts/progress_check.sh)" >&2
    exit 1
}

if [ $has_old -eq 0 ] && [ $has_new -eq 0 ]; then
    exit 0
fi

if [ $has_new -eq 0 ]; then
    if grep -q -- '- \[ \]' "$old"; then
        fail "deleted while items are still [ ]"
    fi
    exit 0
fi

if [ $has_old -eq 0 ]; then
    python3 "$(dirname "$0")/progress_check.py" - "$new" || fail "invalid file"
else
    python3 "$(dirname "$0")/progress_check.py" "$old" "$new" || fail "invalid change"
fi
