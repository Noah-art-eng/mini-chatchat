#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-$ROOT_DIR/backups}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
BACKUP_DIR="$BACKUP_ROOT/mini-chatchat-$TIMESTAMP"
ARCHIVE_PATH="$BACKUP_DIR.tar.gz"

DB_PATH="${MINI_CHATCHAT_DB_PATH:-$ROOT_DIR/backend/mini.db}"
DATA_ROOT="${MINI_CHATCHAT_DATA_ROOT:-$ROOT_DIR/backend/data}"
UPLOADS_DIR="${MINI_CHATCHAT_UPLOADS_DIR:-$ROOT_DIR/backend/uploads}"

mkdir -p "$BACKUP_DIR"

if [ -f "$DB_PATH" ]; then
  cp "$DB_PATH" "$BACKUP_DIR/mini.db"
fi

if [ -d "$DATA_ROOT" ]; then
  mkdir -p "$BACKUP_DIR/data"
  cp -R "$DATA_ROOT/." "$BACKUP_DIR/data/"
fi

if [ -d "$UPLOADS_DIR" ]; then
  mkdir -p "$BACKUP_DIR/uploads"
  cp -R "$UPLOADS_DIR/." "$BACKUP_DIR/uploads/"
fi

cat > "$BACKUP_DIR/manifest.json" <<MANIFEST
{
  "backup_version": "1",
  "service": "mini-chatchat",
  "created_at": "$TIMESTAMP",
  "db_path": "$DB_PATH",
  "data_root": "$DATA_ROOT",
  "uploads_dir": "$UPLOADS_DIR"
}
MANIFEST

tar -czf "$ARCHIVE_PATH" -C "$BACKUP_ROOT" "mini-chatchat-$TIMESTAMP"
shasum -a 256 "$ARCHIVE_PATH" > "$ARCHIVE_PATH.sha256"
rm -rf "$BACKUP_DIR"

echo "$ARCHIVE_PATH"
echo "$ARCHIVE_PATH.sha256"
