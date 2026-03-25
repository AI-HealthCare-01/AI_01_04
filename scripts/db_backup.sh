#!/usr/bin/env bash
# 하루 1회 DB 백업 스크립트
# crontab: 0 2 * * * /app/scripts/db_backup.sh
# 7일 이상 된 백업은 자동 삭제

set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-ai_health}"
BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "[$(date)] DB 백업 시작: ${BACKUP_FILE}"

PGPASSWORD="${DB_PASSWORD}" pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --no-owner \
  --no-privileges \
  | gzip > "$BACKUP_FILE"

echo "[$(date)] DB 백업 완료: $(du -h "$BACKUP_FILE" | cut -f1)"

# 오래된 백업 삭제
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] ${RETENTION_DAYS}일 이상 된 백업 정리 완료"
