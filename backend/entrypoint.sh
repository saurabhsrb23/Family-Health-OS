#!/bin/bash
set -e

echo "========================================="
echo " Family Health OS API — Starting Up"
echo "========================================="

# ── Wait for PostgreSQL ───────────────────────────────────────────────────────
echo "[1/4] Waiting for PostgreSQL..."
until python -c "
import psycopg2, os, sys
try:
    psycopg2.connect(os.environ['DATABASE_URL'])
    print('  PostgreSQL is ready.')
except Exception as e:
    print(f'  Not ready: {e}')
    sys.exit(1)
" 2>/dev/null; do
  sleep 2
done

# ── Wait for Redis ────────────────────────────────────────────────────────────
echo "[2/4] Waiting for Redis..."
until python -c "
import redis, os, sys
try:
    r = redis.from_url(os.environ['REDIS_URL'])
    r.ping()
    print('  Redis is ready.')
except Exception as e:
    print(f'  Not ready: {e}')
    sys.exit(1)
" 2>/dev/null; do
  sleep 2
done

# ── Run DB migrations ─────────────────────────────────────────────────────────
echo "[3/4] Running Alembic migrations..."
alembic upgrade head
echo "  Migrations applied."

# ── Seed demo data ────────────────────────────────────────────────────────────
echo "[4/4] Seeding demo data..."
python seed.py
echo "  Seed complete."

echo "========================================="
echo " Family Health OS — Starting Uvicorn on port 8000"
echo "========================================="
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
