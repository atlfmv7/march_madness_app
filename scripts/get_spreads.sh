#!/usr/bin/env bash
# Purpose: Fetch and store spreads for today's date (UTC) via Flask CLI.
# Safety:   - set -Eeuo pipefail for strict mode
#           - flock to prevent overlapping cron runs
# Logging:  - appends to logs/get_spreads.log
set -Eeuo pipefail

# ----- Adjust these paths if your layout changes -----
PROJECT_DIR="$HOME/march_madness_app"
VENV_DIR="$PROJECT_DIR/env"
FLASK_APP_FILE="app.py"
LOG_FILE="$PROJECT_DIR/logs/get_spreads.log"
LOCK_FILE="/tmp/mmm_get_spreads.lock"
# -----------------------------------------------------

{
  echo "[$(date -Is)] START get-spreads"

  # Ensure we run in project directory
  cd "$PROJECT_DIR"

  # Activate venv
  source "$VENV_DIR/bin/activate"

  # Ensure Flask picks up the app factory file
  export FLASK_APP="$FLASK_APP_FILE"
  export PYTHONUNBUFFERED=1

  # Optional: set timezone for any local time functions (cron uses system TZ)
  export TZ="America/New_York"

  # Run the CLI; default grabs today (UTC) already
  flask get-spreads

  echo "[$(date -Is)] DONE get-spreads"
} | /usr/bin/flock -n "$LOCK_FILE" -c "tee -a '$LOG_FILE'" >/dev/null 2>&1
