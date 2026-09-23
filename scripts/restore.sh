#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: scripts/restore.sh /path/to/mini-chatchat-YYYYMMDDTHHMMSSZ.tar.gz" >&2
  echo "Stop Mini ChatChat before restoring runtime data." >&2
  exit 2
fi

ARCHIVE_PATH="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESTORE_TMP="$(mktemp -d)"

DB_PATH="${MINI_CHATCHAT_DB_PATH:-$ROOT_DIR/backend/mini.db}"
DATA_ROOT="${MINI_CHATCHAT_DATA_ROOT:-$ROOT_DIR/backend/data}"
UPLOADS_DIR="${MINI_CHATCHAT_UPLOADS_DIR:-$ROOT_DIR/backend/uploads}"

if [ -f "$ARCHIVE_PATH.sha256" ]; then
  shasum -a 256 -c "$ARCHIVE_PATH.sha256"
fi

if [ "${RESTORE_CONFIRM:-}" != "yes" ]; then
  if [ -t 0 ]; then
    echo "Restore will overwrite:"
    echo "  DB: $DB_PATH"
    echo "  Data: $DATA_ROOT"
    echo "  Uploads: $UPLOADS_DIR"
    printf "Type 'restore mini-chatchat' to continue: "
    read -r confirmation
    if [ "$confirmation" != "restore mini-chatchat" ]; then
      echo "Restore cancelled." >&2
      exit 2
    fi
  else
    echo "Set RESTORE_CONFIRM=yes to restore in non-interactive mode." >&2
    exit 2
  fi
fi

cleanup() {
  rm -rf "$RESTORE_TMP"
}
trap cleanup EXIT

tar -xzf "$ARCHIVE_PATH" -C "$RESTORE_TMP"
BACKUP_DIR="$(find "$RESTORE_TMP" -maxdepth 1 -type d -name "mini-chatchat-*" | head -n 1)"

if [ "$BACKUP_DIR" = "" ]; then
  echo "Invalid backup archive: no mini-chatchat-* directory found." >&2
  exit 1
fi

mkdir -p "$(dirname "$DB_PATH")" "$DATA_ROOT" "$UPLOADS_DIR"

if [ -f "$BACKUP_DIR/mini.db" ]; then
  cp "$BACKUP_DIR/mini.db" "$DB_PATH"
fi

if [ -d "$BACKUP_DIR/data" ]; then
  rm -rf "$DATA_ROOT"
  mkdir -p "$DATA_ROOT"
  cp -R "$BACKUP_DIR/data/." "$DATA_ROOT/"
fi

if [ -d "$BACKUP_DIR/uploads" ]; then
  rm -rf "$UPLOADS_DIR"
  mkdir -p "$UPLOADS_DIR"
  cp -R "$BACKUP_DIR/uploads/." "$UPLOADS_DIR/"
fi

echo "Restore complete. Start Mini ChatChat and check /health/deps."
