#!/usr/bin/env bash
# Purpose: Update scores and finalize games (if Final) via Flask CLI.
# Safety:   - set -Eeuo pipefail for strict mode
#           - flock to prevent overlapping cron runs
# Logging:  - appends to logs/update_scores.log
set -Eeuo pipefail

# ----- Adjust these paths if your layout changes -----
PROJECT_DIR="$HOME/march_madness_app"
VENV_DIR="$PROJECT_DIR/env"
FLASK_APP_FILE="app.py"
LOG_FILE="$PROJECT_DIR/logs/update_scores.log"
LOCK_FILE="/tmp/mmm_update_scores.lock"
# -----------------------------------------------------

{
  echo "[$(date -Is)] START update-scores"

  cd "$PROJECT_DIR"
  source "$VENV_DIR/bin/activate"
  export FLASK_APP="$FLASK_APP_FILE"
  export PYTHONUNBUFFERED=1
  export TZ="America/New_York"

  # Default updates today's games (UTC). You can pass --date YYYY-MM-DD if needed.
  flask update-scores

  echo "[$(date -Is)] DONE update-scores"
} | /usr/bin/flock -n "$LOCK_FILE" -c "tee -a '$LOG_FILE'" >/dev/null 2>&1
