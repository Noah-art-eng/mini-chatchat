# Backup And Restore

## What Is Backed Up

`scripts/backup.sh` includes:

- SQLite database
- uploaded files
- user-scoped Knowledge Base files
- FAISS vector stores
- extracted content
- KB metadata stored under `backend/data`

Default source paths:

- `backend/mini.db`
- `backend/data/`
- `backend/uploads/`

The script respects:

- `MINI_CHATCHAT_DB_PATH`
- `MINI_CHATCHAT_DATA_ROOT`
- `MINI_CHATCHAT_UPLOADS_DIR`
- `BACKUP_ROOT`

## Backup

```bash
scripts/backup.sh
```

Example output:

```text
backups/mini-chatchat-20260805T010203Z.tar.gz
backups/mini-chatchat-20260805T010203Z.tar.gz.sha256
```

For Docker production:

```bash
MINI_CHATCHAT_DB_PATH=runtime/prod/mini.db \
MINI_CHATCHAT_DATA_ROOT=runtime/prod/data \
MINI_CHATCHAT_UPLOADS_DIR=runtime/prod/uploads \
scripts/backup.sh
```

## Restore

Stop Mini ChatChat before restore.

```bash
scripts/restore.sh backups/mini-chatchat-20260805T010203Z.tar.gz
```

Restore verifies `*.sha256` when the checksum file is present.

Interactive restore requires typing:

```text
restore mini-chatchat
```

For controlled non-interactive restore jobs:

```bash
RESTORE_CONFIRM=yes scripts/restore.sh backups/mini-chatchat-20260805T010203Z.tar.gz
```

Then start the service and check:

```bash
curl http://127.0.0.1/api/health/deps
```

## Production Notes

- Store backups outside the application host.
- Encrypt backups if they contain private documents.
- Keep checksum files with backup archives and verify before restore.
- Test restore periodically.
- Keep at least one backup before every deployment.
- Do not commit backup archives.
