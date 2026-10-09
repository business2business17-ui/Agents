#!/usr/bin/env bash
# Local install of the Amazon agents for terminal work (macOS / Linux / WSL / Git Bash).
#   ./install.sh              install Python packages + register the agents in Claude Code (if the `claude` CLI is present)
#   ./install.sh --test       also run the self-tests
#   ./install.sh --no-claude  Python packages only (use the agents with other AIs from dist/)
#   ./install.sh --venv       use a virtual environment in ./.venv (then run `source .venv/bin/activate` before `claude`)
# Safe to re-run. Nothing is deleted or overwritten outside this folder except Claude Code's own plugin list.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
RUN_TESTS=0; USE_CLAUDE=1; USE_VENV=0
for a in "$@"; do case "$a" in --test) RUN_TESTS=1;; --no-claude) USE_CLAUDE=0;; --venv) USE_VENV=1;; -h|--help) sed -n '2,8p' "$0"; exit 0;; *) echo "unknown option $a"; exit 2;; esac; done

PY="${PYTHON:-}"
for c in python3 python; do [ -z "$PY" ] && command -v "$c" >/dev/null 2>&1 && PY="$c"; done
[ -z "$PY" ] && { echo "Python 3.9+ is required: https://www.python.org/downloads/"; exit 1; }
"$PY" - <<'PYV' || { echo "Python 3.9 or newer is required"; exit 1; }
import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)
PYV
echo "Python: $("$PY" --version)"

if [ "$USE_VENV" = 1 ]; then
  "$PY" -m venv .venv && PY="$HERE/.venv/bin/python"
  echo "virtualenv created: activate it with  source .venv/bin/activate  before starting claude"
fi
"$PY" -m pip install --quiet --disable-pip-version-check -r requirements.txt $([ "$USE_VENV" = 1 ] || echo --user) \
  || { echo "pip install failed. Try: $PY -m pip install -r requirements.txt  (or rerun with --venv)"; exit 1; }
echo "Python packages: OK"

"$PY" - <<'PYC' || exit 1
import importlib.util
miss = [m for m in ("openpyxl", "lxml", "PIL") if importlib.util.find_spec(m) is None]
print("check imports:", "OK" if not miss else f"MISSING {miss}")
raise SystemExit(1 if miss else 0)
PYC
command -v ffprobe >/dev/null 2>&1 && echo "ffprobe: found (video checks enabled)" || echo "ffprobe: not found (optional; only needed to validate video files: install ffmpeg)"

if [ "$USE_CLAUDE" = 1 ]; then
  if command -v claude >/dev/null 2>&1; then
    MP="$("$PY" -c "import json;print(json.load(open('.claude-plugin/marketplace.json'))['name'])")"
    claude plugin marketplace add "$HERE" || echo "(marketplace may already be registered)"
    for P in $("$PY" -c "import json,os;m=json.load(open('.claude-plugin/marketplace.json'));print(' '.join(p['name'] for p in m['plugins'] if os.path.isdir(p['source'])))"); do
      claude plugin install "$P@$MP" && echo "installed: $P" || echo "could not install $P (see message above)"
    done
    echo "Done. Start 'claude' in your project folder; list agents with /agents."
  else
    echo "Claude Code CLI not found (https://docs.claude.com/en/docs/claude-code). For other AIs use the files in dist/ (see docs/LOCAL_INSTALL.md)."
  fi
fi
[ "$RUN_TESTS" = 1 ] && "$PY" -W ignore -m unittest discover -s tests && echo "self-tests: OK"
echo "Create a working folder for a project:  $PY tools/init_project.py ~/amazon-projects/my-brand"
