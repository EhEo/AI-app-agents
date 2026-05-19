#!/usr/bin/env bash
# team-layout.sh — 3-에이전트 tmux 레이아웃 설정. ~/.agents-dev/scripts/ 에 위치 (전역).
set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/bin:$PATH:$HOME/AppData/Local/Microsoft/WinGet/Links"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASH="$SCRIPT_DIR/dashboard.sh"

SESSION=""
PROJECT_DIR=""
HERE=0
ATTACH=1
BYPASS=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]
  --project-dir PATH  프로젝트 루트 경로 (없으면 AGENT_PROJECT_DIR 또는 CWD)
  --session NAME      tmux 세션명 (없으면 프로젝트 폴더명)
  --here              현재 tmux 창에 레이아웃 적용
  --no-attach         세션 생성만 하고 attach 안 함
  --bypass            claude --dangerously-skip-permissions 로 시작
  -h, --help          도움말
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    -n|--session)  SESSION="$2"; shift 2 ;;
    --here)        HERE=1; shift ;;
    --no-attach)   ATTACH=0; shift ;;
    --bypass)      BYPASS=1; shift ;;
    -h|--help)     usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

[ -z "$PROJECT_DIR" ] && PROJECT_DIR="${AGENT_PROJECT_DIR:-$(pwd)}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"

if [ -z "$SESSION" ]; then
  SESSION="${AGENT_SESSION:-$(basename "$PROJECT_DIR" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')}"
fi

LOG_DIR="$PROJECT_DIR/.agents-dev/log"
mkdir -p "$LOG_DIR"

CLAUDE_CMD="claude"
[ "$BYPASS" = "1" ] && CLAUDE_CMD="claude --dangerously-skip-permissions"

command -v tmux >/dev/null 2>&1 || { echo "error: tmux not found. Run: source ~/.bashrc" >&2; exit 2; }
[ -x "$DASH" ] || { echo "error: $DASH not found or not executable" >&2; exit 2; }

if [ "$HERE" = "1" ]; then
  [ -n "${TMUX:-}" ] || { echo "error: --here requires running inside tmux" >&2; exit 2; }
  tmux rename-window "$SESSION" 2>/dev/null || true

  tmux split-window -h -c "$PROJECT_DIR"
  tmux send-keys "AGENT_LOG_DIR='$LOG_DIR' AGENT_SESSION='$SESSION' /usr/bin/bash '$DASH' gemini" Enter

  tmux split-window -v -c "$PROJECT_DIR"
  tmux send-keys "AGENT_LOG_DIR='$LOG_DIR' AGENT_SESSION='$SESSION' /usr/bin/bash '$DASH' codex" Enter

  tmux select-pane -L
  tmux send-keys "cd '$PROJECT_DIR'" Enter
  tmux send-keys "export AGENT_LOG_DIR='$LOG_DIR'" Enter
  tmux send-keys "$CLAUDE_CMD" Enter
  echo "✓ Layout ready (session: $SESSION). Launched: $CLAUDE_CMD"
  echo "  log: $LOG_DIR"
  exit 0
fi

if tmux has-session -t "$SESSION" >/dev/null 2>&1; then
  echo "Session '$SESSION' already exists — attaching."
else
  tmux new-session -d -s "$SESSION" -c "$PROJECT_DIR"
  tmux send-keys -t "$SESSION" "export AGENT_LOG_DIR='$LOG_DIR'" Enter

  tmux split-window -h -t "$SESSION" -c "$PROJECT_DIR"
  tmux send-keys -t "$SESSION" "AGENT_LOG_DIR='$LOG_DIR' AGENT_SESSION='$SESSION' /usr/bin/bash '$DASH' gemini" Enter

  tmux split-window -v -t "$SESSION" -c "$PROJECT_DIR"
  tmux send-keys -t "$SESSION" "AGENT_LOG_DIR='$LOG_DIR' AGENT_SESSION='$SESSION' /usr/bin/bash '$DASH' codex" Enter

  tmux select-pane -t "$SESSION" -L
  tmux send-keys -t "$SESSION" "$CLAUDE_CMD" Enter
fi

if [ "$ATTACH" = "1" ]; then
  if [ -n "${TMUX:-}" ]; then
    tmux switch-client -t "$SESSION"
  else
    tmux attach -t "$SESSION"
  fi
else
  MSG="✓ Session '$SESSION' ready. Attach with: tmux attach -t $SESSION"
  [ "$BYPASS" = "1" ] && MSG="$MSG  (bypass: $CLAUDE_CMD)"
  echo "$MSG"
  echo "  log: $LOG_DIR"
fi
