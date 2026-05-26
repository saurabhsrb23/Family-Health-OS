# Family Health OS — Backend

FastAPI + PostgreSQL + Redis backend for the Family Health OS platform.

---

## Quick Start (Docker — recommended)

```bash
# From the project root
docker-compose up --build
```

API available at: http://localhost:8000
Swagger docs: http://localhost:8000/docs

---

## Manual Setup (without Docker)

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
cp .env.example .env           # then edit JWT_SECRET_KEY

# Start Postgres + Redis via Docker (just the infra, not the app)
docker-compose up postgres redis -d

# Run migrations
alembic upgrade head

# Seed demo data
python seed.py

# Start server
uvicorn main:app --reload
```

---

## Demo Credentials

| Field    | Value                      |
|----------|----------------------------|
| Email    | demo@familyhealthos.com    |
| Password | Demo@1234                  |

---

## Architecture

```
Request
  │
  ▼
CORSMiddleware           ← Allow all origins (dev), restrict in prod
  │
  ▼
AuditMiddleware          ← Append-only audit log for every request (PHI compliance)
  │
  ▼
Route Handler
  │
  ├── utils/security.py  ← JWT decode, blacklist check, user lookup
  │
  ├── services/          ← Business logic (cache-first, DB fallback)
  │   ├── member_service.py
  │   ├── program_service.py
  │   ├── adherence_service.py
  │   ├── summary_service.py
  │   └── ai_service.py
  │
  ├── cache/redis_client.py  ← Redis wrapper with graceful fallback
  │
  └── database.py        ← SQLAlchemy session
```

---

## API Endpoints

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login (rate limited: 5/min) |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Blacklist current token |
| GET  | `/api/v1/auth/me` | Get current user |

### Members
| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/v1/members` | List all family members (paginated) |
| POST | `/api/v1/members` | Add a family member |
| GET  | `/api/v1/members/{id}` | Get member detail |
| PUT  | `/api/v1/members/{id}` | Update member |
| DELETE | `/api/v1/members/{id}` | Soft delete member |

### Care Programs
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/members/{id}/programs` | Create 90-day program |
| GET  | `/api/v1/members/{id}/programs` | List programs |
| GET  | `/api/v1/members/{id}/programs/{id}` | Program detail |
| PUT  | `/api/v1/members/{id}/programs/{id}` | Update program |
| DELETE | `/api/v1/members/{id}/programs/{id}` | Soft delete |

### Meal Logs
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/members/{id}/meals` | Upload meal photo (multipart) |
| GET  | `/api/v1/members/{id}/meals` | List meal logs (date range filter) |
| GET  | `/api/v1/members/{id}/meals/{id}` | Single meal log |
| GET  | `/api/v1/members/{id}/meals/{id}/status` | AI extraction status (poll) |

### Workouts
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/members/{id}/workouts` | Log workout + exercises |
| GET  | `/api/v1/members/{id}/workouts` | List workouts (date range) |
| GET  | `/api/v1/members/{id}/workouts/{id}` | Session with all exercises |

### Health Measurements
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/members/{id}/measurements` | Log BP / weight / glucose |
| GET  | `/api/v1/members/{id}/measurements` | List (type + date filter) |
| GET  | `/api/v1/members/{id}/measurements/latest` | Latest per type (dashboard) |
| GET  | `/api/v1/members/{id}/measurements/{id}` | Single measurement |

### Adherence
| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/v1/members/{id}/adherence` | Full adherence dashboard |
| POST | `/api/v1/members/{id}/adherence/recompute` | Force cache bust + recalculate |
| GET  | `/api/v1/members/{id}/adherence/nutrition/daily` | Historical daily nutrition |

### Weekly Summaries
| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/v1/members/{id}/programs/{id}/summaries` | List all week summaries |
| GET  | `/api/v1/members/{id}/programs/{id}/summaries/{week}` | Full week summary |
| POST | `/api/v1/members/{id}/programs/{id}/summaries/generate` | Trigger AI generation |

---

## Data Models

| Table | Description |
|-------|-------------|
| `users` | Account credentials, soft delete |
| `family_members` | Members linked to a user account |
| `care_programs` | 90-day programs (one active per member) |
| `program_components` | Nutrition / Strength / Clinical config (JSONB) |
| `meal_logs` | Photo upload + AI-extracted nutrition data |
| `workout_sessions` | Sessions with energy level and duration |
| `exercise_logs` | Individual exercises (sets/reps/weight) |
| `health_measurements` | BP, weight, glucose readings |
| `adherence_metrics` | Daily adherence per component (unique per member/component/day) |
| `program_summaries` | AI weekly summaries (unique per program/week) |
| `audit_logs` | Append-only PHI access log (no soft delete) |

---

## Caching Strategy

| Data | Cache Key | TTL | Invalidated by |
|------|-----------|-----|----------------|
| User profile | `user:{id}` | 1h | Profile update |
| Member list | `members:user:{id}` | 1h | Create/update/delete member |
| Single member | `member:{id}` | 1h | Member update |
| Program | `program:{id}` | 1h | Program update |
| Daily adherence | `adherence:{member}:{component}:{date}` | 15min | Any new health data |
| Rolling adherence | `adherence:rolling:{member}:{component}` | 15min | Any new health data |
| Weekly summary | `summary:{program}:{week}` | 7 days | On regeneration |
| Login rate limit | `rate:login:{ip}:{minute}` | 60s | Auto-expires |
| Token blacklist | `blacklist:token:{jti}` | Token TTL | Auto-expires |

**PHI is never cached** — raw meal logs, measurements, and workout data always come from DB.

---

## Security

- **Authentication**: JWT access tokens (30min) + refresh tokens (7 days)
- **Token revocation**: logout blacklists `jti` in Redis with remaining TTL
- **Rate limiting**: 5 login attempts per IP per minute (Redis counter)
- **Access control**: every member endpoint verifies `member.user_id == current_user.id`
- **Soft deletes**: PHI data is never hard-deleted — `deleted_at` timestamp set
- **Audit logging**: every API request logged to `audit_logs` (append-only, no FK constraints)
- **Password hashing**: bcrypt via passlib

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Docker internal |
| `REDIS_URL` | Redis connection string | Docker internal |
| `JWT_SECRET_KEY` | JWT signing secret | **change in prod** |
| `JWT_ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | 7 |
| `UPLOAD_DIR` | Local photo upload directory | /app/uploads |
| `MAX_UPLOAD_SIZE_MB` | Max photo upload size | 10 |
| `ENVIRONMENT` | development / production | development |

---

## GCP Production Design

| Service | Local equivalent | Purpose |
|---------|-----------------|---------|
| Cloud Run | Uvicorn in Docker | Serverless backend, auto-scaling |
| Cloud SQL (PostgreSQL) | PostgreSQL container | Managed DB with read replicas |
| Cloud Storage | Local `uploads/` | Meal photo storage with signed URLs |
| Memorystore (Redis) | Redis container | Distributed caching |
| Pub/Sub | Background tasks | Async AI extraction queue |
| Cloud Tasks | Background tasks | Weekly summary generation |
| Secret Manager | `.env` file | JWT secret, DB creds, AI API keys |
| Cloud Logging | stdout | Centralized audit log aggregation |
| Vertex AI / Gemini | Mock `ai_service.py` | Meal photo nutrition extraction |

---

## Useful Commands

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Roll back migrations
docker-compose exec backend alembic downgrade base

# Re-seed data
docker-compose exec backend python seed.py

# Check Redis cache
docker-compose exec redis redis-cli keys "*"
docker-compose exec redis redis-cli flushall   # clear all cache

# Check DB tables
docker-compose exec postgres psql -U praan_user -d praan_health -c "\dt"

# Check audit logs
docker-compose exec postgres psql -U praan_user -d praan_health \
  -c "SELECT action, resource_type, status_code, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 20;"
```
