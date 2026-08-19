#!/usr/bin/env bash
# Список файлов ресурсов и архивный бэкап папки на сервере.
# Админка копирует скрипт на сервер и запускает по SSH.
set -euo pipefail

ROOT="${VITAGO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"

BACKUP_DIR="backups"
DISK_FOLDER="$(grep -E '^DISK_FOLDER=' secrets/app_config 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true)"
DISK_FOLDER="${DISK_FOLDER:-diskUploads}"

usage() {
  echo "usage: $0 list | last | backup [force]" >&2
  exit 2
}

latest_archive() {
  ls -1 "${BACKUP_DIR}"/disk-*.tar.gz 2>/dev/null | sort | tail -1 || true
}

cmd="${1:-}"
case "$cmd" in
  list)
    DB_USER="$(grep -E '^POSTGRES_USER=' secrets/db_credentials 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true)"
    DB_NAME="$(grep -E '^POSTGRES_DB=' secrets/db_credentials 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r' || true)"
    if [[ -z "$DB_USER" || -z "$DB_NAME" ]]; then
      echo "no POSTGRES_USER/POSTGRES_DB in secrets/db_credentials" >&2
      exit 1
    fi
    printf 'FOLDER\t%s\n' "$DISK_FOLDER"
    docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -tAc \
      "SELECT resource_file_path FROM resources WHERE resource_file_path IS NOT NULL AND btrim(resource_file_path) <> '';" \
      | tr -d '\r' \
      | while IFS= read -r path; do
          [[ -z "$path" ]] && continue
          printf 'DB\t%s\n' "$path"
        done
    docker compose exec -T -e DISK_FOLDER="$DISK_FOLDER" app sh -c '
      find "$DISK_FOLDER" -type f 2>/dev/null | while IFS= read -r f; do
        [ -z "$f" ] && continue
        size=$(stat -c %s "$f" 2>/dev/null || echo 0)
        mtime=$(stat -c %y "$f" 2>/dev/null | cut -d. -f1)
        printf "DISK\t%s\t%s\t%s\n" "$f" "$size" "$mtime"
      done
    '
    ;;
  last)
    mkdir -p "$BACKUP_DIR"
    latest="$(latest_archive)"
    if [[ -n "$latest" ]]; then
      size="$(stat -c %s "$latest" 2>/dev/null || echo 0)"
      printf 'ARCHIVE\t%s\t%s\n' "$latest" "$size"
    fi
    ;;
  backup)
    mkdir -p "$BACKUP_DIR"
    stamp="$(date +%Y-%m-%d)"
    archive="${BACKUP_DIR}/disk-${stamp}.tar.gz"
    if [[ -f "$archive" && "${2:-}" != "force" ]]; then
      size="$(stat -c %s "$archive" 2>/dev/null || echo 0)"
      printf 'ARCHIVE\t%s\t%s\tEXISTS\n' "$archive" "$size"
      exit 0
    fi
    tmp="${archive}.tmp"
    docker compose exec -T -e DISK_FOLDER="$DISK_FOLDER" app tar -C /app -czf - "$DISK_FOLDER" > "$tmp"
    mv "$tmp" "$archive"
    size="$(stat -c %s "$archive" 2>/dev/null || echo 0)"
    printf 'ARCHIVE\t%s\t%s\tCREATED\n' "$archive" "$size"
    ;;
  *)
    usage
    ;;
esac
