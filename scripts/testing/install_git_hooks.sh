#!/usr/bin/env bash
# Install the repo's git hooks. `.git/hooks` is not tracked, so a fresh clone
# has none of this and the Ansys-privacy rule is back to being held by
# discipline alone. Run once per clone:
#
#     scripts/testing/install_git_hooks.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$ROOT/.git/hooks/pre-commit"
cat > "$HOOK" <<'HOOKEOF'
#!/usr/bin/env bash
# Refuse a commit that carries an Ansys benchmark figure into a tracked file
# (licence terms; operator directive 2026-09-02). Applies to every committer,
# including non-Claude agents, which is the point — the project's other rails
# are Claude-Code-specific and would not.
#
# Bypass, only with a reason you would defend: git commit --no-verify
exec python3 "$(git rev-parse --show-toplevel)/scripts/testing/check_private_leak.py"
HOOKEOF
chmod +x "$HOOK"
echo "installed $HOOK"
