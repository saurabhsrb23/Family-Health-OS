# Family Health OS

> **Founding Full-Stack Engineer Take-Home** — 90-day family care platform with AI-powered nutrition tracking, strength training, and clinical monitoring.

**Stack:** Python + FastAPI + PostgreSQL + Redis · React Native + Expo · Docker · GCP (architecture documented)

---

## Table of Contents

1. [Quick Start — Backend](#1-quick-start--backend)
2. [Quick Start — Mobile App](#2-quick-start--mobile-app)
3. [Demo Credentials & Seed Data](#3-demo-credentials--seed-data)
4. [Running on Mobile Device (Phone)](#4-running-on-mobile-device-phone)
5. [Running on Web Browser](#5-running-on-web-browser)
6. [Running on Emulator / Simulator](#6-running-on-emulator--simulator)
7. [API Reference](#7-api-reference)
8. [Project Structure](#8-project-structure)
9. [Tech Stack](#9-tech-stack)
10. [GCP Production Architecture](#10-gcp-production-architecture)
11. [Modules Built](#11-modules-built)
12. [Docker Commands](#12-docker-commands)
13. [Environment Variables](#13-environment-variables)
14. [Database Schema](#14-database-schema)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Quick Start — Backend

> One command starts everything: PostgreSQL + Redis + FastAPI + automatic migrations + seed data.

**Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)

```bash
git clone https://github.com/saurabhsrb23/Family-Health-OS.git
cd Family-Health-OS
docker-compose up --build
```

On first boot Docker automatically:
1. Starts PostgreSQL 15 + Redis 7
2. Waits for both to be healthy
3. Runs Alembic migrations (creates all 11 tables + indexes)
4. Seeds demo data (2 members, programs, 135 meals, 23 workouts, 30 measurements)
5. Starts FastAPI on port **8000**

| URL | Description |
|---|---|
| http://localhost:8000 | API root |
| http://localhost:8000/docs | Swagger UI (interactive) |
| http://localhost:8000/redoc | ReDoc documentation |
| http://localhost:8000/health | Health check |

---

## 2. Quick Start — Mobile App

**Prerequisites:** Node.js 18+ · Backend running (Step 1 above)

```bash
cd mobile
npm install
npx expo start
```

Metro bundler starts and shows a **QR code** in your terminal. See sections below for how to open on phone, browser, or emulator.

---

## 3. Demo Credentials & Seed Data

| Field | Value |
|---|---|
| **Email** | demo@familyhealthos.com |
| **Password** | Demo@1234 |

### What's pre-loaded

| Data | Detail |
|---|---|
| 1 demo user | demo@familyhealthos.com |
| **Rahul Sharma** (self) | Day 31 of 90 · Phase 2 — Build |
| **Priya Sharma** (spouse) | Day 15 of 90 · Phase 1 — Foundation |
| Rahul's program | 2,000 cal/day · 60g protein · 4 workouts/week |
| Priya's program | 1,600 cal/day · 50g protein · 3 workouts/week |
| 135 meal logs | 30 days × 3 meals (Rahul) + 15 days × 3 meals (Priya) — all AI-extracted |
| 23 workout sessions | Sets/reps/weight for each session |
| 30 health measurements | Blood pressure + weight (trending downward) |
| 45 adherence metrics | Daily nutrition scores pre-computed |
| 6 weekly summaries | AI-generated program summaries (weeks 1–4 for Rahul, 1–2 for Priya) |

---

## 4. Running on Mobile Device (Phone)

### Option A — Expo Go App (Recommended, no install needed)

**Step 1 — Install Expo Go on your phone**
- iPhone: [App Store → Expo Go](https://apps.apple.com/app/expo-go/id982107779)
- Android: [Play Store → Expo Go](https://play.google.com/store/apps/details?id=host.exp.exponent)

> Version required: **Expo Go 54.x** (matches SDK 54 used in this project)

**Step 2 — Find your machine's LAN IP**

```bash
# Mac / Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr "IPv4"
```

Example output: `192.168.0.6`

**Step 3 — Update the API URL**

Edit [mobile/src/services/api.ts](mobile/src/services/api.ts) line 5:

```typescript
// Replace with YOUR machine's LAN IP
const API_BASE_URL = 'http://192.168.0.6:8000/api/v1';
```

> Both your phone and your laptop must be on the **same Wi-Fi network**.

**Step 4 — Start Metro**

```bash
cd mobile
npx expo start --clear
```

**Step 5 — Open the app**
- **iPhone:** Open Camera → point at the QR code in your terminal → tap the banner
- **Android:** Open Expo Go → tap "Scan QR code" → point at QR code

---

### Option B — Development Build (Advanced)

For full native features without Expo Go:

```bash
# Install EAS CLI
npm install -g eas-cli

# Build for iOS
eas build --platform ios --profile development

# Build for Android
eas build --platform android --profile development
```

---

## 5. Running on Web Browser

The app runs in a web browser via Expo Web — no phone needed.

```bash
cd mobile
npx expo start --web
```

Opens at **http://localhost:8081** in your default browser.

**API URL for web:**

```typescript
// In mobile/src/services/api.ts
const API_BASE_URL = 'http://localhost:8000/api/v1';
```

> Web mode is great for development but photo capture uses the browser's file picker instead of the native camera.

---

## 6. Running on Emulator / Simulator

### Android Emulator (Android Studio)

1. Install [Android Studio](https://developer.android.com/studio) and create a virtual device (API 33+)
2. Start the emulator
3. Update API URL in `mobile/src/services/api.ts`:

```typescript
const API_BASE_URL = 'http://10.0.2.2:8000/api/v1';  // Android emulator alias for localhost
```

4. Run:
```bash
cd mobile
npx expo start --android
```

### iOS Simulator (Mac only)

1. Install Xcode from the App Store
2. Update API URL:

```typescript
const API_BASE_URL = 'http://localhost:8000/api/v1';  // iOS simulator uses localhost
```

3. Run:
```bash
cd mobile
npx expo start --ios
```

---

## 7. API Reference

Base URL: `http://localhost:8000/api/v1`

All protected endpoints require: `Authorization: Bearer <access_token>`

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Login → returns access_token + refresh_token |
| POST | `/auth/logout` | Logout → blacklists token in Redis |
| POST | `/auth/refresh` | Refresh access token using refresh_token |
| GET | `/auth/me` | Current authenticated user |

### Members
| Method | Endpoint | Description |
|---|---|---|
| GET | `/members` | List all family members (paginated) |
| POST | `/members` | Create a new family member |
| GET | `/members/{id}` | Get member by ID |
| PUT | `/members/{id}` | Update member |
| DELETE | `/members/{id}` | Soft-delete member |

### Care Programs
| Method | Endpoint | Description |
|---|---|---|
| GET | `/members/{id}/programs` | List member's programs |
| POST | `/members/{id}/programs` | Create a 90-day program |
| GET | `/members/{id}/programs/{pid}` | Get program details + components |
| PUT | `/members/{id}/programs/{pid}` | Update program |

### Meal Logs (AI Nutrition)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/members/{id}/meals` | Upload meal photo (multipart/form-data) |
| GET | `/members/{id}/meals` | List meal logs (paginated, date filter) |
| GET | `/members/{id}/meals/{mid}` | Get meal with extracted nutrition |
| GET | `/members/{id}/meals/{mid}/status` | Poll AI extraction status |

### Workouts
| Method | Endpoint | Description |
|---|---|---|
| POST | `/members/{id}/workouts` | Log a workout session |
| GET | `/members/{id}/workouts` | List workout sessions |
| GET | `/members/{id}/workouts/{wid}` | Get workout + exercises |

### Health Measurements
| Method | Endpoint | Description |
|---|---|---|
| POST | `/members/{id}/measurements` | Log BP / weight / glucose |
| GET | `/members/{id}/measurements` | List measurements |

### Adherence
| Method | Endpoint | Description |
|---|---|---|
| GET | `/members/{id}/adherence` | Full adherence report (nutrition + strength + clinical + overall) |
| GET | `/members/{id}/adherence/nutrition/daily` | Daily nutrition adherence |
| POST | `/members/{id}/adherence/recompute` | Force recalculate adherence |

### Summaries
| Method | Endpoint | Description |
|---|---|---|
| GET | `/members/{id}/programs/{pid}/summaries/{week}` | Get AI weekly summary |
| POST | `/members/{id}/programs/{pid}/summaries/{week}/generate` | Trigger summary generation |

---

## 8. Project Structure

```
Family-Health-OS/
├── README.md                    ← You are here
├── DESIGN.md                    ← Full system design (architecture, caching, security, wireframes)
├── docker-compose.yml           ← Full stack: backend + PostgreSQL + Redis
│
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh            ← wait-for-healthy → migrate → seed → serve
│   ├── main.py                  ← FastAPI app, middleware, routers
│   ├── config.py                ← pydantic-settings (env vars)
│   ├── database.py              ← SQLAlchemy engine + session
│   ├── seed.py                  ← Demo data (idempotent, skips if already seeded)
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── models/                  ← 10 SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── family_member.py
│   │   ├── care_program.py
│   │   ├── meal_log.py
│   │   ├── workout_session.py
│   │   ├── health_measurement.py
│   │   ├── adherence_metric.py
│   │   ├── program_summary.py
│   │   └── audit_log.py
│   ├── schemas/                 ← Pydantic request/response schemas
│   ├── routes/                  ← FastAPI route handlers (auth, members, meals, workouts, measurements, adherence, summaries)
│   ├── services/                ← Business logic
│   │   ├── ai_service.py        ← Mock AI (Gemini Vision documented)
│   │   ├── adherence_service.py ← Nutrition/strength/clinical adherence engine
│   │   └── summary_service.py   ← AI weekly summary generation
│   ├── cache/
│   │   └── redis_client.py      ← Redis wrapper with graceful fallback
│   ├── middleware/
│   │   └── audit.py             ← PHI access audit logging
│   └── utils/
│       ├── security.py          ← JWT, bcrypt, rate limiting
│       └── pagination.py        ← PaginatedResponse
│
└── mobile/
    ├── App.tsx                  ← Root: GestureHandlerRootView + AuthProvider + AppNavigator
    ├── app.json                 ← Expo config, permissions, icons
    ├── package.json             ← Expo SDK 54 + React Native 0.76.3
    └── src/
        ├── services/api.ts      ← Axios instance + interceptors (auto-refresh on 401)
        ├── context/AuthContext.tsx ← JWT state + AsyncStorage persistence
        ├── navigation/AppNavigator.tsx ← Stack navigator, auth-gated routing
        ├── components/
        │   ├── MemberCard.tsx   ← Family member card with progress bar
        │   ├── ProgressBar.tsx  ← Reusable progress bar
        │   └── LoadingOverlay.tsx
        └── screens/
            ├── LoginScreen.tsx
            ├── MemberListScreen.tsx
            ├── ProgramOverviewScreen.tsx
            ├── MealCaptureScreen.tsx
            ├── NutritionResultScreen.tsx
            └── AdherenceDashboard.tsx
```

---

## 9. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend language | Python | 3.11 |
| API framework | FastAPI | 0.111 |
| ORM | SQLAlchemy | 2.0 |
| Migrations | Alembic | 1.13 |
| Database | PostgreSQL | 15 |
| Cache | Redis | 7 |
| Auth | python-jose + passlib bcrypt | — |
| Validation | Pydantic v2 | 2.7 |
| Mobile framework | React Native + Expo | SDK 54 / RN 0.76.3 |
| Mobile language | TypeScript | 5.3 |
| HTTP client | Axios | 1.7 |
| Navigation | React Navigation v6 | Stack |
| Storage | AsyncStorage | 1.23 |
| Camera | expo-image-picker | 15.0 |
| Containerization | Docker + Compose | — |

---

## 10. GCP Production Architecture

> No cloud deployment required — architecture is documented in [DESIGN.md](DESIGN.md).

| GCP Service | Role |
|---|---|
| **Cloud Run** | Host FastAPI — serverless, auto-scales 0→100 instances |
| **Cloud SQL (PostgreSQL 15)** | Managed DB with read replicas + automated backups |
| **Cloud Storage** | Meal photo storage — replaces local `uploads/` directory |
| **Memorystore (Redis 7)** | Distributed cache — JWT blacklist, adherence cache, rate limits |
| **Pub/Sub** | Async queue — AI extraction jobs, adherence recomputation |
| **Cloud Scheduler** | Weekly summary generation cron (every Sunday 2am) |
| **Secret Manager** | JWT secret, DB credentials, Gemini API key |
| **Cloud Armor** | WAF — OWASP Top 10 blocking, rate limiting at edge |
| **Cloud CDN** | Meal photo delivery — 30-day TTL, immutable assets |
| **Cloud Logging** | Centralized PHI audit trail (HIPAA compliance) |
| **Vertex AI / Gemini 1.5 Flash** | Meal photo nutrition extraction + weekly summary generation |

---

## 11. Modules Built

| Module | Description | Status |
|---|---|---|
| **Module 1** | Project foundation — Docker Compose full-stack setup, directory structure, entrypoint | ✅ |
| **Module 2** | Database models — 10 SQLAlchemy ORM models (User, Member, Program, Component, MealLog, Workout, Measurement, Adherence, Summary, AuditLog) | ✅ |
| **Module 3** | Alembic migrations — 11 tables, all FK constraints, composite indexes for time-series queries | ✅ |
| **Module 4** | Auth system — JWT access/refresh tokens, bcrypt (cost 12), Redis token blacklist, rate limiting (5 req/min), audit middleware | ✅ |
| **Module 5** | Member & Program APIs — CRUD with ownership checks, JSONB component config, Redis caching, soft deletes | ✅ |
| **Module 6** | Health data logging — meal photo upload + mock AI extraction (Gemini path documented), workout sessions, health measurements | ✅ |
| **Module 7** | Adherence engine — nutrition (daily), strength (weekly), clinical (weekly), 7-day rolling trend, weighted overall score (nutrition 40% + strength 40% + clinical 20%) | ✅ |
| **Module 8** | Weekly AI summaries — structured JSON output schema, mock Gemini integration, schema validation, rich seed data (135 meals, 23 workouts, 30 measurements) | ✅ |
| **Module 9** | React Native mobile app — Expo SDK 54, navigation, AuthContext, all screens, camera integration | ✅ |
| **Module 10** | Screen implementation — all 6 screens fully wired to backend API with real data | ✅ |
| **Module 11** | DESIGN.md — 930-line system design document (architecture, DB decision, caching, API, security, scalability, wireframes) | ✅ |
| **Module 12** | Final wiring — API field alignment, meal upload fix, dashboard fixes, mobile README | ✅ |

---

## 12. Docker Commands

```bash
# Start everything (first run builds images + seeds DB)
docker-compose up --build

# Start in background
docker-compose up -d --build

# View backend logs live
docker-compose logs -f backend

# Stop everything (keeps database data)
docker-compose down

# Stop + wipe all data (fresh start)
docker-compose down -v

# Re-run seed (if DB is empty)
docker-compose exec backend python seed.py

# Open shell inside backend container
docker-compose exec backend bash

# Run migrations manually
docker-compose exec backend alembic upgrade head

# Check container status
docker-compose ps

# Restart just the backend (after code changes)
docker-compose restart backend
```

---

## 13. Environment Variables

Set in `docker-compose.yml` for local dev. Copy `backend/.env.example` for manual setup.

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | set in docker-compose |
| `REDIS_URL` | Redis connection string | set in docker-compose |
| `JWT_SECRET_KEY` | JWT signing secret | change in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime | 7 |
| `UPLOAD_DIR` | Local meal photo storage path | ./uploads |
| `MAX_UPLOAD_SIZE_MB` | Max photo upload size | 10 |
| `ENVIRONMENT` | development / production | development |

---

## 14. Database Schema

| Table | Description |
|---|---|
| `users` | Account credentials and profile (email, hashed password, full_name) |
| `family_members` | Members linked to a user account (name, relationship, DOB, soft delete) |
| `care_programs` | 90-day care programs per member (title, start/end date, phase, status) |
| `program_components` | Nutrition / Strength / Clinical config (JSONB targets per component) |
| `meal_logs` | Meal photo uploads + AI-extracted nutrition (calories, protein, carbs, fat) |
| `workout_sessions` | Workout sessions (duration, energy level, session type) |
| `exercise_logs` | Individual exercises per session (sets, reps, weight) |
| `health_measurements` | BP, weight, glucose readings with timestamps |
| `adherence_metrics` | Daily adherence scores — unique per (member, component, date), upserted |
| `program_summaries` | AI-generated weekly summaries — unique per (program, week_number) |
| `audit_logs` | Append-only PHI access log (user, action, IP, resource, timestamp) |

---

## 15. Troubleshooting

### Backend

**"Connection refused" on localhost:8000**
→ Make sure Docker is running: `docker-compose ps`
→ Check logs: `docker-compose logs backend`

**"Database already seeded" but data looks wrong**
→ Wipe and restart: `docker-compose down -v && docker-compose up --build`

**Backend returns 403 on /members**
→ JWT token expired — log out and log in again

---

### Mobile — Phone

**"Network Error" / can't reach backend**
→ Check `API_BASE_URL` in `src/services/api.ts` — must be your LAN IP (e.g. `192.168.0.6:8000`)
→ Phone and laptop must be on the same Wi-Fi
→ Check backend is running: open `http://<your-LAN-IP>:8000/health` in phone browser

**"Project is incompatible with this version of Expo Go"**
→ Install Expo Go version 54.x (this project uses SDK 54)
→ Or run: `npx expo start --clear`

**TurboModule / PlatformConstants crash**
→ Clear cache: `npx expo start --clear`
→ Delete node_modules: `rm -rf node_modules && npm install && npx expo start --clear`

**Camera permission denied**
→ iOS: Settings → Expo Go → Camera → Allow
→ Android: Settings → Apps → Expo Go → Permissions → Camera → Allow

---

### Mobile — Web

**"Network Error" on web browser**
→ Change `API_BASE_URL` to `http://localhost:8000/api/v1` (not LAN IP)
→ Backend must be running locally

**Blank screen after login**
→ Open browser DevTools (F12) → Console tab → share error message

**Camera doesn't work on web**
→ Web uses the browser file picker — click "Gallery" not "Take Photo"
→ Chrome/Safari required (Firefox may have permission issues)

---

### Mobile — Android Emulator

**"Network Error"**
→ API URL must be `http://10.0.2.2:8000/api/v1` (emulator's alias for localhost)

**Emulator not showing up**
→ Start Android Studio → Device Manager → Start virtual device first

---

### Mobile — iOS Simulator

**"Network Error"**
→ API URL must be `http://localhost:8000/api/v1`

**Simulator not found**
→ Open Xcode → Window → Devices and Simulators → check a simulator is installed

---

*Built for the Praan Health Founding Full-Stack Engineer take-home assignment.*
*Stack: Python + FastAPI + PostgreSQL + Redis + React Native + GCP*
