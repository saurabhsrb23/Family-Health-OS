# Family Health OS

A 90-day family care platform with nutrition tracking, strength training, and clinical monitoring.

---

## Quick Start (Docker — recommended)

> One command starts everything: PostgreSQL + Redis + FastAPI backend + seed data.

```bash
# Clone the repo
git clone https://github.com/saurabhsrb23/Family-Health-OS.git
cd Family-Health-OS

# Build and start all services
docker-compose up --build
```

On first boot, Docker will automatically:
1. Start PostgreSQL + Redis
2. Wait for both to be healthy
3. Run Alembic database migrations (creates all 10 tables)
4. Populate demo seed data (1 user, 2 members, 1 program, sample logs)
5. Start the FastAPI server on port 8000

**That's it.** Open:
- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

---

## Demo Credentials
| Field | Value |
|---|---|
| Email | demo@familyhealthos.com |
| Password | Demo@1234 |

---

## Seed Data Included
- **1 demo user** — demo@familyhealthos.com
- **2 family members** — Alex Johnson (self) + Sarah Johnson (spouse)
- **1 active 90-day care program** — started 10 days ago
- **3 program components** — nutrition (60g protein/day), strength (4x/week), clinical (BP + weight)
- **7 days of meal logs** — breakfast, lunch, dinner with extracted nutrition data
- **3 workout sessions** — strength training with exercise logs
- **7 days of health measurements** — blood pressure + weight
- **7 days of adherence metrics** — nutrition component tracking

---

## Useful Docker Commands

```bash
# Start in background
docker-compose up -d --build

# View live logs
docker-compose logs -f backend

# Stop everything
docker-compose down

# Stop + wipe database (fresh start)
docker-compose down -v

# Re-seed data (if needed)
docker-compose exec backend python seed.py

# Open a shell inside the backend container
docker-compose exec backend bash

# Run Alembic migration manually
docker-compose exec backend alembic upgrade head

# Check container health
docker-compose ps
```

---

## Database Schema

| Table | Description |
|---|---|
| `users` | Account credentials and profile |
| `family_members` | Members linked to a user account |
| `care_programs` | 90-day programs per family member |
| `program_components` | Nutrition / Strength / Clinical config per program |
| `meal_logs` | Meal photo uploads + AI-extracted nutrition data |
| `workout_sessions` | Workout sessions with energy level and duration |
| `exercise_logs` | Individual exercises per session (sets/reps/weight) |
| `health_measurements` | BP, weight, glucose readings |
| `adherence_metrics` | Daily adherence scores per component (unique per member/component/day) |
| `program_summaries` | AI-generated weekly summaries (unique per program/week) |
| `audit_logs` | Append-only PHI access log (no soft delete) |

---

## Project Structure

```
Family-Health-OS/
├── docker-compose.yml       # Full stack: backend + PostgreSQL + Redis
├── backend/
│   ├── Dockerfile           # Backend container
│   ├── entrypoint.sh        # Startup: wait → migrate → seed → serve
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings (pydantic-settings + env vars)
│   ├── database.py          # SQLAlchemy engine + session + Base
│   ├── seed.py              # Demo data population (idempotent)
│   ├── alembic.ini          # Alembic config
│   ├── models/              # SQLAlchemy ORM models (10 models)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routes/              # FastAPI route handlers
│   ├── services/            # Business logic layer
│   ├── cache/               # Redis caching layer
│   ├── middleware/          # Auth + logging middleware
│   ├── utils/               # Shared helpers
│   ├── alembic/             # DB migrations (auto-generated)
│   └── uploads/             # Local meal photo storage
└── mobile/                  # React Native + Expo app (Module 11)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL 15 (SQLAlchemy ORM + Alembic) |
| Cache | Redis 7 |
| Auth | JWT (python-jose + passlib bcrypt) |
| Mobile | React Native + Expo |
| Containerization | Docker + Docker Compose |

---

## GCP Services (Production Design)

| GCP Service | Role |
|---|---|
| **Cloud Run** | Host FastAPI backend (serverless, auto-scaling) |
| **Cloud SQL (PostgreSQL)** | Managed relational DB with read replicas |
| **Cloud Storage** | Meal photo storage with signed URLs (replaces local `uploads/`) |
| **Memorystore (Redis)** | Managed Redis for distributed caching |
| **Pub/Sub** | Async event queue for AI extraction jobs + adherence recalculation |
| **Cloud Tasks** | Scheduled jobs — weekly summary generation, adherence rollups |
| **Secret Manager** | Store JWT secret, DB credentials, AI API keys |
| **Cloud Logging** | Centralized audit logs (PHI access tracking) |
| **Vertex AI / Gemini** | LLM-powered meal photo nutrition extraction + weekly summaries |

---

## Environment Variables

All config is in `docker-compose.yml` for local dev. For manual setup, copy `backend/.env.example` to `backend/.env`.

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | docker internal |
| `REDIS_URL` | Redis connection string | docker internal |
| `JWT_SECRET_KEY` | Secret for signing JWTs | **change in prod** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | 30 |
| `UPLOAD_DIR` | Directory for meal photo uploads | /app/uploads |
| `MAX_UPLOAD_SIZE_MB` | Max file size for uploads | 10 |
| `ENVIRONMENT` | development / production | development |

---

## Modules Built

- [x] Module 1 — Project Foundation & Structure (Docker full-stack setup)
- [x] Module 2 — Database Models (10 SQLAlchemy models + seed data)
- [x] Module 3 — Alembic Migrations (manual migration, 11 tables, all indexes + constraints)
- [x] Module 4 — Auth System (JWT access/refresh tokens, bcrypt, Redis blacklist, rate limiting)
- [x] Module 5 — Member & Care Program APIs (CRUD, access control, caching, program components)
- [x] Module 6 — Health Data Logging (meal photo upload + mock AI, workouts, measurements)
- [ ] Module 4 — Member Management APIs
- [ ] Module 5 — Care Program APIs
- [ ] Module 6 — Health Data Logging APIs
- [ ] Module 7 — Image Upload + Mock AI Extraction
- [ ] Module 8 — Adherence Calculation
- [ ] Module 9 — AI Weekly Summary
- [ ] Module 10 — Caching Layer
- [ ] Module 11 — React Native App
