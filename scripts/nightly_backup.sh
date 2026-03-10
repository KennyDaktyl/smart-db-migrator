#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/env/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

BACKUP_ROOT="${BACKUP_ROOT:-$ROOT_DIR/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
VERIFY_BACKUP="${BACKUP_VERIFY:-1}"
RCLONE_REMOTE="${RCLONE_REMOTE:-}"

cmd=(
  "$PYTHON_BIN"
  "$ROOT_DIR/scripts/db_ops.py"
  backup
  --env all
  --output-root "$BACKUP_ROOT"
  --retention-days "$RETENTION_DAYS"
)

if [[ "$VERIFY_BACKUP" != "1" ]]; then
  cmd+=(--no-verify)
fi

if [[ -n "$RCLONE_REMOTE" ]]; then
  cmd+=(--upload-remote "$RCLONE_REMOTE")
fi

"${cmd[@]}"
