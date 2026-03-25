#!/usr/bin/env bash
# 데이터 보관 정책 적용 스크립트
# 대화 원문: 6개월, 요약: 1년
# crontab: 0 3 * * * /app/scripts/data_retention.sh

set -euo pipefail

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-ai_health}"

echo "[$(date)] 데이터 보관 정책 적용 시작"

# 대화 원문 6개월 초과 삭제
PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
  "DELETE FROM chatbot_messages WHERE created_at < NOW() - INTERVAL '6 months';"

# 대화 요약 1년 초과 삭제
PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
  "DELETE FROM chatbot_session_summaries WHERE created_at < NOW() - INTERVAL '1 year';"

# 종료된 세션 중 메시지/요약 모두 삭제된 빈 세션 정리
PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c \
  "DELETE FROM chatbot_sessions s
   WHERE s.ended_at IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM chatbot_messages m WHERE m.session_id = s.id)
     AND NOT EXISTS (SELECT 1 FROM chatbot_session_summaries ss WHERE ss.session_id = s.id);"

echo "[$(date)] 데이터 보관 정책 적용 완료"
