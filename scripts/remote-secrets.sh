#!/usr/bin/env bash
# Читает/пишет Docker secrets и пересоздаёт контейнеры.
# Запускается на сервере из каталога vitago-backend (админка копирует скрипт по SSH).
set -euo pipefail

ROOT="${VITAGO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ROOT"

ALLOWED_FILES="app_config db_credentials nginx_backend"
ALLOWED_SERVICES="app db nginx"

usage() {
  echo "usage: $0 read <file> | write <file> | restart <service...>" >&2
  exit 2
}

allowed_in() {
  local needle="$1"
  shift
  local item
  for item in "$@"; do
    if [[ "$item" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

assert_file() {
  # shellcheck disable=SC2086
  if ! allowed_in "$1" $ALLOWED_FILES; then
    echo "unknown secret file: $1" >&2
    exit 2
  fi
}

assert_service() {
  # shellcheck disable=SC2086
  if ! allowed_in "$1" $ALLOWED_SERVICES; then
    echo "unknown service: $1" >&2
    exit 2
  fi
}

ensure_file() {
  local name="$1"
  mkdir -p secrets
  if [[ ! -f "secrets/$name" ]]; then
    cp "secrets.example/$name" "secrets/$name"
  fi
}

cmd="${1:-}"
shift || true

case "$cmd" in
  read)
    name="${1:-}"
    [[ -n "$name" ]] || usage
    assert_file "$name"
    ensure_file "$name"
    cat "secrets/$name"
    ;;
  write)
    name="${1:-}"
    [[ -n "$name" ]] || usage
    assert_file "$name"
    mkdir -p secrets
    tmp="$(mktemp)"
    cat > "$tmp"
    mv "$tmp" "secrets/$name"
    ;;
  restart)
    [[ "$#" -gt 0 ]] || usage
    for svc in "$@"; do
      assert_service "$svc"
    done
    docker compose up -d --force-recreate --no-deps "$@"
    docker compose ps
    ;;
  *)
    usage
    ;;
esac
