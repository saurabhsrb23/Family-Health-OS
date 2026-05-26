# Praan Health — Backend

FastAPI + PostgreSQL + Redis backend for the Family Health OS.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit JWT_SECRET_KEY
```

## Run

```bash
uvicorn main:app --reload
```

API docs: http://localhost:8000/docs

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | localhost praan_health DB |
| `REDIS_URL` | Redis connection string | localhost:6379 |
| `JWT_SECRET_KEY` | Secret for signing JWTs | **change this** |
| `JWT_ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | 7 |
| `UPLOAD_DIR` | Local directory for meal photo uploads | ./uploads |
| `MAX_UPLOAD_SIZE_MB` | Max file size for uploads | 10 |
| `ENVIRONMENT` | development / production | development |
