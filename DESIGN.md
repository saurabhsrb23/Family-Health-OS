# Praan Health — System Design Document

> **Family Health OS** — A 90-day family care platform with AI-powered nutrition tracking, strength training monitoring, and clinical health measurement.

---

## 1. Architecture Overview

### High-Level Architecture

The system is structured in four logical tiers: mobile client, API gateway, application backend, and data/storage layer. Each tier has a single responsibility and communicates over well-defined interfaces.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT TIER                                        │
│                                                                             │
│          React Native (Expo)                                                │
│          iOS & Android                                                      │
│          AsyncStorage (JWT)                                                 │
└────────────────────────┬────────────────────────────────────────────────────┘
                         │ HTTPS (TLS 1.3)
                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GATEWAY TIER                                       │
│                                                                             │
│   Cloud Armor (WAF + DDoS)  →  Cloud Load Balancer  →  Cloud CDN           │
│   (block SQLi, XSS, bad IPs)   (SSL termination)       (photo delivery)    │
└────────────────────────┬────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       APPLICATION TIER                                      │
│                                                                             │
│              Cloud Run — FastAPI (Python 3.11)                              │
│              Auto-scaling: 0 → 100 instances                                │
│              Stateless — no local state                                     │
│                                                                             │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│   │   Auth   │  │ Members  │  │  Meals   │  │Adherence │  │Summaries │   │
│   │  Router  │  │  Router  │  │  Router  │  │  Router  │  │  Router  │   │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                    │                                        │
│                              Background Task                                │
│                              (FastAPI BG tasks)                             │
└──────┬──────────────────┬──────────┼────────────────────────────────────────┘
       │                  │          │
       ▼                  ▼          ▼
┌────────────┐  ┌──────────────┐  ┌──────────────────────────────────────────┐
│ Memorystore│  │  Cloud SQL   │  │             ASYNC PROCESSING             │
│  (Redis 7) │  │ PostgreSQL15 │  │                                          │
│            │  │              │  │  Cloud Storage (meal photos)             │
│ • JWT      │  │ • 11 tables  │  │         ↓                                │
│   blacklist│  │ • ACID       │  │  Pub/Sub (job queue)                     │
│ • Cache    │  │ • JSONB      │  │         ↓                                │
│ • Rate lim │  │ • Read       │  │  Cloud Run Worker                        │
│            │  │   replica    │  │         ↓                                │
└────────────┘  └──────────────┘  │  Gemini Vision API (AI extraction)       │
                                  └──────────────────────────────────────────┘
```

The key architectural principle is **separation of the write path from the AI processing path**. A meal photo upload returns to the client immediately (201) while the AI extraction happens asynchronously. This keeps P95 API latency under 500ms regardless of AI provider latency.

---

### Request Flow: User Logs a Meal Photo (End-to-End)

1. **Mobile client** selects a photo from the camera or gallery. The app creates a `FormData` object containing the image binary, `meal_type`, `logged_at` timestamp, and `program_id`. The axios request interceptor automatically attaches the `Authorization: Bearer <access_token>` header before the request leaves the device.

2. **Cloud Armor WAF** inspects the incoming HTTPS request at the edge. It checks against rule sets for SQL injection patterns, oversized payloads beyond 10MB, and IP reputation lists. If clean, the request passes through to the load balancer.

3. **Cloud Load Balancer** terminates TLS and forwards the plain HTTP request to the next available Cloud Run instance. Session affinity is not required since the application is fully stateless.

4. **FastAPI route handler** (`POST /api/v1/members/{member_id}/meals`) runs three validations synchronously: (a) JWT signature verification and blacklist check via Redis, (b) ownership check — queries DB to confirm `member.user_id == current_user.id`, (c) file type validation — checks MIME type, not just file extension.

5. **Photo is saved** to Cloud Storage (local disk in prototype) with a structured key: `uploads/{member_id}/{uuid}.jpg`. A `MealLog` row is inserted into PostgreSQL with `extraction_status = 'pending'`. The database row is created atomically before the background task fires.

6. **HTTP 201 response** is returned to the client immediately with the `meal_log_id` and `extraction_status: "pending"`. The client is not blocked waiting for AI processing. This is the critical design decision that keeps the API fast regardless of AI provider latency spikes.

7. **Background task fires** (FastAPI `BackgroundTasks` in prototype; Pub/Sub message in production). The task updates `extraction_status = 'processing'` and calls the AI service with the photo path.

8. **Gemini Vision API** (mocked in prototype) analyzes the photo. It returns a structured JSON response containing `calories`, `protein_g`, `carbohydrates_g`, `fat_g`, `fiber_g`, and `foods_identified[]`. The mock introduces a 2-second delay to simulate real AI latency.

9. **Extraction results are persisted**: the `MealLog` row is updated with the extracted nutrition data and `extraction_status = 'completed'`. The adherence cache keys for today's nutrition (`adherence:{member_id}:nutrition:{date}`) and the rolling 7-day average are invalidated in Redis.

10. **Mobile client polls** `GET /api/v1/members/{member_id}/meals/{meal_id}/status` every 2 seconds. When it receives `status: "completed"`, it fetches the full meal record and navigates to the Nutrition Result screen displaying macros, calorie count, and today's protein progress against target.

---

### GCP Services Mapping

| Service | Purpose in Praan Health | Why Chosen over Alternatives |
|---|---|---|
| **Cloud Run** | Hosts FastAPI backend. Auto-scales from 0 to 100 instances based on request volume. Each instance is stateless. | Chosen over GKE because we don't need full Kubernetes orchestration at this scale. No cluster management overhead. Pay-per-request pricing suits variable health app traffic (low overnight, peaks morning/evening). Chosen over App Engine for finer concurrency control. |
| **Cloud SQL (PostgreSQL 15)** | Primary relational database. Stores all 11 tables: users, family members, programs, components, meal logs, workout sessions, exercise logs, health measurements, adherence metrics, program summaries, audit logs. | Chosen over Firestore because health data is deeply relational and requires ACID transactions. Chosen over Bigtable because our data volume (~10GB at 100K users) doesn't justify a distributed wide-column store. Managed PostgreSQL avoids self-hosting operational burden. |
| **Cloud Storage** | Stores meal photo binaries. Structured as `gs://praan-health-photos/{member_id}/{uuid}.jpg`. Pre-signed URLs with 15-minute expiry served to clients. | Chosen over storing photos in DB (BLOBs): terrible for DB performance, can't CDN-cache. Chosen over Firebase Storage: GCP-native, cheaper egress, better IAM integration. Immutable once uploaded, enabling aggressive CDN caching. |
| **Pub/Sub** | Decouples meal photo uploads from AI extraction. Each upload publishes a message with `meal_log_id` and `image_path`. Worker subscribers process at their own rate. | Chosen over Cloud Tasks for fan-out: one upload could trigger multiple downstream consumers (AI extraction + photo compression + audit event). At-least-once delivery with dead letter queues for failed extractions. Handles 10K/s bursts that would overwhelm synchronous AI calls. |
| **Memorystore (Redis 7)** | Distributed cache for member lists (1hr TTL), adherence reports (15min TTL), JWT blacklist (token lifetime TTL), and rate limit counters (60s TTL). | Chosen over in-process cache: Cloud Run scales to multiple instances, so local memory is not shared. Redis is the only correct solution for distributed rate limiting and token blacklisting across instances. Chosen over Cloud Firestore for caching: sub-millisecond reads vs 10-50ms. |
| **Secret Manager** | Stores `JWT_SECRET_KEY`, `DATABASE_URL` (with password), `REDIS_URL`, and Gemini API key. Accessed at application startup via service account binding. | Chosen over environment variables in Cloud Run config: secrets are versioned, auditable, and access is logged. Avoids secrets in container images or source control. Rotation can happen without redeployment. |
| **Cloud Armor** | Web Application Firewall at the load balancer level. Applies OWASP Top 10 rule sets, blocks SQL injection patterns in form fields, enforces rate limits at IP level, and provides DDoS protection. | PHI data mandates WAF protection. Cloud Armor integrates directly with Cloud Load Balancer with no additional hop. Chosen over Cloudflare: keeps everything GCP-native, simpler IAM and billing. |
| **Cloud CDN** | Caches meal photos at edge nodes globally. 30-day TTL since photos are immutable once uploaded. Intercepts photo GET requests before they reach Cloud Storage, dramatically reducing egress costs. | A user may view their meal history repeatedly. Without CDN, every thumbnail load hits Cloud Storage. With CDN, repeat views are served from the nearest edge PoP. Chosen over self-managed Nginx caching: zero operational overhead. |
| **Cloud Logging** | Centralized log aggregation. AuditMiddleware writes every PHI access event (who accessed what data, from which IP, at what time). Application errors, AI extraction failures, and cache misses are structured as JSON log entries. | HIPAA compliance requires audit trails. Cloud Logging provides tamper-resistant, append-only log storage with 30-day retention (configurable to 7 years for compliance). Log-based alerts fire to PagerDuty when error rates exceed threshold. |

---

## 2. Database Decision: PostgreSQL over NoSQL

### Why PostgreSQL

**1. Relational data model with deep foreign key chains**

The core data model is a strict hierarchy: `User → FamilyMember → CareProgram → ProgramComponent → (MealLog | WorkoutSession | HealthMeasurement) → AdherenceMetric`. Every entity in this chain depends on the ones above it — a meal log without a family member is meaningless, and an adherence metric without a component has no target to measure against. PostgreSQL's foreign key constraints enforce this referential integrity at the database level. Attempting to insert a `MealLog` for a nonexistent `FamilyMember` raises a constraint violation before the application layer even sees it. NoSQL databases offer no equivalent guarantee.

**2. ACID compliance is non-negotiable for PHI data**

Health data requires serializable consistency. Consider this sequence: a user logs breakfast at 8am (protein: 25g), the adherence engine computes today's total (protein: 25g, meets 42% of target). At 12pm the user logs lunch (protein: 30g). These two events must both commit or both rollback — a partial write (lunch log committed, adherence not updated) produces a permanently incorrect health record. With eventual consistency, a user might see their adherence drop and then jump as replicas sync. For a medical context where users make dietary decisions based on adherence data, stale or inconsistent reads are unacceptable. PostgreSQL's ACID guarantees — particularly durability (WAL) and isolation (REPEATABLE READ) — are the correct choice.

**3. Complex aggregations are first-class SQL operations**

The adherence engine performs operations like: "sum protein_g across all meal_logs for member X on date Y where extraction_status = 'completed'", "count workout_sessions this week where exercises contain at least 3 sets", and "7-day rolling average of adherence_rate grouped by component_type". In PostgreSQL, these are single queries using `SUM`, `GROUP BY`, `BETWEEN`, and window functions. In Firestore, there are no server-side aggregations — the client would have to download every meal log for the week and sum protein in JavaScript. At 3 meals/day × 90 days = 270 documents, this is prohibitively expensive on both bandwidth and client CPU. MongoDB aggregation pipelines can do this, but require complex pipeline stages for what PostgreSQL expresses in 4 lines of SQL.

**4. JSONB gives flexibility where schemas differ, without sacrificing queryability**

The `ProgramComponent.config` column stores entirely different shapes depending on `component_type`: nutrition components store `daily_protein_target_g`, `daily_calories_target`, and `meal_frequency`; strength components store `sessions_per_week`, `target_muscle_groups`, and `progressive_overload_pct`; clinical components store `measurement_types[]` and `frequency_days`. Using JSONB avoids three separate tables (NutritionConfig, StrengthConfig, ClinicalConfig), avoids a wide table with 15+ nullable columns, and avoids the Entity-Attribute-Value antipattern entirely. Critically, JSONB remains queryable — we can still `WHERE config->>'daily_protein_target_g' > '50'` or create a GIN index on the config column. This is genuinely the best of both worlds.

**5. Strong schema enforcement protects PHI data integrity**

Health data has strict semantic requirements: blood pressure systolic must be a positive integer, weight cannot be negative, a member's date of birth cannot be in the future. PostgreSQL enforces these at the column level using `NOT NULL`, `CHECK` constraints, and enum types (`relationship_type`, `measurement_type`, `component_type`). Pydantic validates at the API boundary; PostgreSQL provides the second line of defense at the persistence layer. A bug in application code that constructs a malformed health record will hit a constraint violation before corrupt data reaches disk. Document databases without schemas offer no equivalent safety net.

---

### Why NOT NoSQL

**Firestore** fails this use case for three structural reasons. First, it has no server-side aggregation queries — computing a weekly protein total requires downloading every meal document to the client or backend and summing in application memory, which becomes untenable at 90 days × 3 meals/day. Second, multi-document transactions in Firestore are limited to 500 documents per transaction and add significant latency (~100ms per round-trip); our adherence recomputation touches meal_logs, adherence_metrics, and program_summaries atomically, which requires reliable multi-table transactions. Third, time-range queries on Firestore require composite indexes that must be manually created per query pattern — our queries vary by member_id + date range + component_type, and Firestore's index limitations (one inequality per query) make these genuinely difficult to express. The pricing model is also punishing: Firestore charges per document read, and listing a member's 90-day meal history could cost 270 reads per request.

**MongoDB** is closer to viable but still has critical gaps. Its default write concern (`w:1`) acknowledges writes before they reach a majority of replica set members, creating a window where a committed transaction can be lost on primary failure. For financial data this is debatable; for a patient's medication adherence record it is not. MongoDB 4.0+ supports multi-document transactions, but they carry significant performance overhead compared to PostgreSQL's native transaction model. Access control in MongoDB is collection-level and harder to enforce at row level — our requirement that user A can never see user B's health data is naturally expressed in PostgreSQL with `WHERE user_id = current_user.id`, but requires application-level enforcement in MongoDB with no database-level fallback.

---

### Time-Series Strategy

Meal logs, workout sessions, and health measurements are time-series by nature: each row is associated with a point in time (`logged_at`) and is almost always queried for a specific member over a date range.

**Indexing:** Every time-series table carries a composite index on `(member_id, logged_at DESC)`. The `member_id` prefix ensures the index is selective — it immediately filters to the relevant member's rows before scanning dates. The `DESC` ordering matches the most common query pattern: "show me this week's meals" scans from the newest entry backward.

**Query pattern:** All date-range queries use `BETWEEN` with bound parameters:
```sql
SELECT * FROM meal_logs
WHERE member_id = :member_id
  AND logged_at BETWEEN :start_date AND :end_date
  AND extraction_status = 'completed'
  AND deleted_at IS NULL
ORDER BY logged_at DESC;
```
The planner uses the composite index for the `member_id` + `logged_at` filter, then applies `extraction_status` and `deleted_at` as post-index filters. With ~300 meal rows per member, this completes in under 1ms on a warm index.

**Future partitioning:** At 10M+ rows (approximately 30,000 active members), `meal_logs` and `adherence_metrics` will be partitioned by month using PostgreSQL declarative partitioning (`PARTITION BY RANGE (logged_at)`). Each partition covers one calendar month. This limits the index size per partition and allows old partitions (>2 years) to be archived to cheaper storage without affecting query performance on recent data. The application code does not need to change — PostgreSQL's partition pruning handles routing automatically.

---

### JSONB Usage

`ProgramComponent.config` is the canonical example of JSONB in this schema. The three component types require completely different configuration fields:

```json
// Nutrition component config
{
  "daily_protein_target_g": 60,
  "daily_calories_target": 2000,
  "meal_frequency": 3,
  "allowed_meal_types": ["breakfast", "lunch", "dinner"]
}

// Strength component config
{
  "sessions_per_week": 4,
  "target_muscle_groups": ["upper", "lower", "core"],
  "progressive_overload_pct": 2.5,
  "rest_days": [0, 3]
}

// Clinical component config
{
  "measurement_types": ["blood_pressure", "weight"],
  "frequency_days": 2,
  "bp_systolic_target": 120,
  "weight_target_kg": 75.0
}
```

The alternatives were worse in every direction:
- **Three separate config tables** (NutritionConfig, StrengthConfig, ClinicalConfig): requires a JOIN on every component read, complicates the ORM, and adds migration overhead when config fields change.
- **Wide table with nullable columns**: a `ProgramComponent` row would have 15 columns where 10 are always NULL depending on component type — a classic table smell, and misleading to any developer reading the schema.
- **EAV (Entity-Attribute-Value)**: `(component_id, key, value)` rows would require pivoting 6-10 rows into a single config object on every read, destroys type safety, and is notoriously difficult to query.

JSONB avoids all of these. The entire config is stored as one value, loaded in one column read, and still supports GIN-indexed queries when needed. The `_validate_summary_schema()` function in `summary_service.py` demonstrates that we can still assert structural correctness in application code before persisting.

---

## 3. Data Model Design

### Users & Family Members

**`user_id` on every `FamilyMember`** implements multi-tenancy at the row level. Every service method filters `WHERE family_members.user_id = current_user.id` before returning any data. This is not enforced only at the API route level — it is enforced inside every service function, so even if a route accidentally passes the wrong `member_id`, the service will return 403. The pattern treats each user's family data as a completely isolated namespace within the shared PostgreSQL instance, without requiring separate schemas or databases per tenant.

**Soft delete (`deleted_at` timestamp)** is a legal and operational requirement for PHI data. Hard-deleting a family member would destroy their entire health history: 90 days of meals, workouts, measurements, and adherence records. Even if a user removes a family member (e.g., after a divorce), the historical health data may be needed for medical continuity, legal disputes, or re-adding the member later. Soft delete preserves all data, allows recovery by support staff, and lets audit logs reference the member even after deletion. The `deleted_at IS NULL` filter is applied in every query — deleted members are invisible to the application but recoverable from the database.

**`relationship_type` as a string enum** (`self`, `spouse`, `child`, `parent`, `sibling`, `other`) serves two purposes. First, it drives the UI — the mobile app shows different default program templates, avatar colors, and recommended targets based on relationship type. A `child` member gets different calorie targets than a `parent`. Second, it constrains data entry — an unconstrained text field would produce data like "wife", "husband", "my wife", "spouse" that cannot be aggregated or used for program personalization.

---

### Care Programs & Components

**`end_date = start_date + 89 days`** (making the range exactly 90 days inclusive) is computed at creation time and stored to make range queries simple. Querying "is today within this program" is `WHERE start_date <= :today AND end_date >= :today` rather than computing the end date dynamically. The `day_number` is computed as `(today - start_date).days + 1`, clamped to [1, 90] so day 1 is the first day and day 90 is the last.

**`current_phase` is a computed property**, not a stored column. Phase is defined as `ceil(day_number / 30)`, producing values 1, 2, or 3. Storing it as a column would require an update trigger or background job to keep it in sync as time passes — an unnecessary write for a value that can be derived instantly from `start_date`. The `_compute_phase()` function in `program_service.py` is called at response serialization time, not at write time.

**JSONB for `component.config`** avoids the need for three separate configuration tables (discussed fully in Section 2). The trade-off is that component config has no database-level schema validation — only application-level validation via Pydantic schemas (`NutritionConfig`, `StrengthConfig`, `ClinicalConfig`). This is acceptable because config is written only at program creation time, not from arbitrary user input.

**Unique constraint `(program_id, component_type)`** would prevent a program from having two nutrition components. This constraint was intentionally not applied in the current prototype to allow for future program designs where a member might track two nutrition approaches simultaneously. However, the service layer enforces `component_type` uniqueness during program creation to prevent duplicates in the current 90-day program design.

---

### Health Data (MealLog, WorkoutSession, HealthMeasurement)

**`logged_at ≠ created_at`** because users routinely log past events. A user may eat breakfast at 8am but not open the app until noon. `logged_at` captures when the meal actually occurred (user-provided, defaults to `now()` in the UI). `created_at` captures when the database row was written. Adherence calculations use `logged_at` for all date bucketing — otherwise, a user who logs retroactively would be penalized with a "missed" day that they actually completed. The composite index on `(member_id, logged_at)` ensures date-range queries remain fast regardless of when records were created.

**Extraction status state machine** (`pending → processing → completed | failed`) reflects that AI extraction is an asynchronous operation with observable intermediate states. The client polls `GET /meals/{id}/status` to track progress. Each state transition is a deliberate choice:
- `pending`: the row exists, the photo is saved, but AI hasn't started yet
- `processing`: the worker has picked up the job and is calling the AI API
- `completed`: nutrition data is available, adherence can be recomputed
- `failed`: the AI could not process this image; the user should retry with a clearer photo

Storing status in the database (rather than just in Redis) ensures that if the backend restarts mid-extraction, the state is recoverable. A cleanup job can find rows stuck in `processing` for over 60 seconds and re-enqueue them.

**`photo_key` vs `photo_url`**: `photo_key` stores the Cloud Storage object path (`uploads/{member_id}/{uuid}.jpg`). `photo_url` is never stored — it is generated as a pre-signed URL at request time with a 15-minute expiry. This means photo links cannot be shared, scraped, or cached by unauthorized parties. If a user's account is suspended, their photo URLs become invalid within 15 minutes without any database changes. Storing a permanent URL would be a security vulnerability for PHI content.

**`ExerciseLog` is a separate table** from `WorkoutSession` because a workout session contains multiple exercises, each with their own sets, reps, weight, and name. These are a one-to-many relationship by definition — a workout might have 5 exercises with 3 sets each. Storing exercises as a JSON array in the session row would make querying individual exercise performance (e.g., "show me bench press history over 90 days") require scanning and deserializing JSON on every query. The separate table allows `WHERE exercise_name = 'bench_press' ORDER BY logged_at` to use the index efficiently.

---

### AdherenceMetric

**Upsert strategy (`ON CONFLICT DO UPDATE`)** is used instead of append-only because adherence for a given day is a single definitive value that should be recalculated as new data arrives. If a user logs three meals in a day, the nutrition adherence metric for that day is updated three times. An append-only approach would produce three rows for the same (member, component, date), requiring a `MAX()` or `LAST()` aggregation on every read — adding complexity for no benefit. Upsert with a unique constraint ensures exactly one row per (member, component, date), and the most recent calculation wins.

**Unique constraint `(member_id, component_type, metric_date)`** enforces the one-row-per-day-per-component invariant at the database level. Even if the application has a bug that calls `compute_adherence` twice concurrently for the same member and date, the PostgreSQL unique constraint combined with `ON CONFLICT DO UPDATE` guarantees exactly one outcome — the last writer wins atomically. This is the correct semantics: we want the latest calculation, not duplicates.

**Storing both `target_value` and `actual_value`** (not just a percentage) preserves the raw data needed for the UI. The percentage `(actual / target * 100)` can always be computed, but the reverse — recovering what the actual and target values were from a percentage — is impossible. Showing "52g / 60g protein" in the dashboard requires both values. Additionally, target values can change if a care provider updates the program mid-journey; by storing the target at calculation time, historical adherence records remain accurate even if the program is later modified.

---

### AuditLog

**No soft delete on `AuditLog`** because an audit log that can be deleted is not an audit log — it is a mutable record that provides false assurance of compliance. The legal purpose of an audit trail is to prove what happened and when, even (especially) in the event of a breach or dispute. If `deleted_at` existed on audit logs, a malicious insider could cover their tracks by soft-deleting the log of their access. The table uses `INSERT-only` patterns in application code, and the database user for the application should not have `DELETE` or `UPDATE` privileges on this table in production.

**No `updated_at` on `AuditLog`** for the same reason — audit events are immutable facts. The row represents "this action happened at this time" and that fact cannot be amended. The absence of `updated_at` is a deliberate signal to developers that this table is append-only.

**`ip_address` is stored for security forensics.** If a user's account is compromised and their health data is accessed by an attacker, the IP address provides the primary investigative lead: geolocation (is this login from the user's country?), ISP lookup (VPN, Tor exit node, cloud provider?), and cross-referencing with other breach events. Without stored IP addresses, breach investigations are blind. The field is typed as `INET` in PostgreSQL to support both IPv4 and IPv6 addresses.

---

## 4. Caching Architecture

### Cache Layers

The system uses three distinct cache layers, each with different scope, latency, and TTL characteristics:

**Layer 1 — Application (in-process)**
Application configuration and constants loaded from environment variables at startup. This includes `settings.JWT_SECRET_KEY`, `settings.ACCESS_TOKEN_EXPIRE_MINUTES`, and `settings.UPLOAD_DIR`. These are read once and live for the lifetime of the process. Because Cloud Run instances are stateless and frequently created/destroyed, this cache is ephemeral by design — it is not used for user data.

**Layer 2 — Redis (distributed)**
All user-specific, shared state that must be consistent across Cloud Run instances. Redis is the authoritative source for JWT blacklist entries, rate limit counters, and cached API responses. TTLs are set conservatively for mutable data (15 minutes for adherence, 1 hour for member profiles) and aggressively for immutable data (7 days for weekly summaries). The `CacheClient` wrapper in `cache/redis_client.py` implements graceful fallback: if Redis is unavailable, all cache operations silently no-op and the application falls back to database reads. This ensures a Redis outage degrades performance, not availability.

**Layer 3 — CDN (Cloud CDN)**
Meal photos are immutable once uploaded — a photo of a meal does not change. Cloud CDN intercepts photo GET requests at the nearest edge PoP and serves them without hitting Cloud Storage. TTL is 30 days. Cache-busting is not needed because the photo URL contains the UUID of the meal log — a new upload always gets a new UUID and thus a new cache key.

---

### What to Cache (with TTL Reasoning)

| Data | Cache Key | TTL | Invalidation Trigger |
|---|---|---|---|
| Member profile list | `members:user:{user_id}` | 1 hour | Member create / update / delete |
| Individual member | `member:{member_id}` | 1 hour | Member update / delete |
| Active programs for member | `programs:{member_id}` | 1 hour | Program create / update / status change |
| Program config (components) | `program:{program_id}` | 24 hours | Program update (rare) |
| Daily nutrition adherence | `adherence:{member_id}:nutrition:{date}` | 15 minutes | New meal log completed |
| Daily strength adherence | `adherence:{member_id}:strength:{date}` | 15 minutes | New workout session logged |
| Daily clinical adherence | `adherence:{member_id}:clinical:{date}` | 15 minutes | New health measurement logged |
| Rolling 7-day adherence | `adherence:rolling:{member_id}:{component}` | 15 minutes | Any new data logged |
| Full adherence report | `adherence:full:{member_id}:{date}` | 15 minutes | Any component update |
| Weekly summary | `summary:{program_id}:{week_number}` | 7 days | Never (immutable once generated) |
| Rate limit counter | `rate:{endpoint}:{ip}:{minute_bucket}` | 60 seconds | Auto-expires |
| JWT blacklist entry | `blacklist:token:{jti}` | Remaining token lifetime | Never (expire naturally) |

**TTL reasoning for 15-minute adherence cache:** Adherence changes only when new health data is logged. A typical user logs 3 meals, 1 workout, and 1 measurement per day — 5 writes. Between writes, adherence is constant. A 15-minute TTL means the worst-case stale read is 15 minutes, which is acceptable for a wellness dashboard (not a heart monitor). The cache is also proactively invalidated on every write, so in practice the TTL is rarely the expiry mechanism — explicit invalidation is.

**TTL reasoning for 7-day summary:** Weekly summaries are generated by AI at the end of each program week and are never updated. They are immutable facts. A 7-day TTL means the cache warms on first access and stays warm until the next week's summary is due. The `summary_service.py` validates the AI-generated JSON against a required schema before persisting, so cached summaries are guaranteed to be structurally valid.

---

### What NOT to Cache

**Real-time health measurements** (the "latest" blood pressure or weight) are always fetched from the database. The `GET /measurements/latest` endpoint specifically bypasses cache because this value is displayed on the clinical monitoring dashboard as "current status" — a stale cached value could show a blood pressure reading from yesterday when today's reading has already been logged.

**Audit logs** are never cached. Audit log writes are fire-and-forget via background task. Reads are not a supported API pattern (audit logs are for internal compliance review, not client consumption). Caching would add complexity with no benefit.

**Active authentication sessions** cannot be satisfied from cache alone because the JWT blacklist is the revocation mechanism. A token could be valid (passes signature verification) but revoked (jti in blacklist). The blacklist check is always a Redis read on every authenticated request — this is a deliberate trade-off of one Redis round-trip per request for the ability to immediately revoke tokens on logout or security events.

---

### Cache Invalidation Flow: User Logs a Meal Photo

```
1.  Client: POST /members/{id}/meals  [multipart photo]
2.  Server: validates JWT, ownership, file type
3.  Server: saves photo to disk / Cloud Storage
4.  Server: INSERT meal_log (extraction_status='pending')
5.  Server: HTTP 201 → client  [non-blocking return]
    ─── Background task fires ───────────────────────────
6.  Worker: UPDATE meal_log SET extraction_status='processing'
7.  Worker: calls Gemini Vision API with photo path
8.  Worker: receives { calories, protein_g, carbohydrates_g, fat_g, foods_identified }
9.  Worker: UPDATE meal_log SET extracted_nutrition={...}, extraction_status='completed'
10. Worker: cache.delete("adherence:{member_id}:nutrition:{today}")
11. Worker: cache.delete("adherence:rolling:{member_id}:nutrition")
12. Worker: cache.delete("adherence:full:{member_id}:{today}")
13. Worker: adherence_service.compute_nutrition_adherence(member_id, today)
            → queries DB: SUM(protein_g) for today
            → upserts adherence_metrics row (ON CONFLICT DO UPDATE)
            → stores result back in Redis with 15min TTL
```

Steps 10–13 ensure the cache is immediately consistent after a write. The next client request for adherence data will be a cache hit with the up-to-date value. The 15-minute TTL is a safety net for cases where the invalidation step fails (e.g., Redis momentarily unavailable).

---

### Handling Cache Stampede at 100K Users

**The Problem:** Redis key `adherence:full:{member_id}:{today}` expires at midnight. Ten thousand users open the app at 7am and simultaneously request their adherence dashboard. All 10,000 requests miss the cache and hit PostgreSQL concurrently, producing a "thundering herd" that can overwhelm the database.

**The Solution: Redis SETNX (Set if Not Exists) Lock**

```
Key expires → all requests miss cache simultaneously

Request A: SETNX lock:adherence:{member_id} 1 (TTL=5s) → SUCCESS (acquired lock)
Request A: queries PostgreSQL, computes adherence
Request A: SET adherence:full:{member_id}:{today} {data} (TTL=15min)
Request A: DEL lock:adherence:{member_id}

Requests B-9999: SETNX lock:adherence:{member_id} → FAIL (lock held)
Requests B-9999: sleep(100ms) → retry GET adherence:full:{member_id}:{today}
                → cache hit → return cached result

Result: 1 DB query instead of 10,000
```

The 5-second lock TTL is a dead-man switch — if Request A crashes during DB computation, the lock auto-expires and the next request can try. The 100ms sleep prevents a busy-wait. This pattern is implemented in the production version of `adherence_service.py` and reduces DB query amplification from O(N) users to O(1) per cache key.

**For 10K/100K Simultaneous Uploads:**
The Pub/Sub queue is the primary defense against upload spikes. Uploads publish messages to the queue at whatever rate users upload. Workers consume from the queue at a controlled rate bounded by their Cloud Run instance count and concurrency. The DB never sees 10,000 simultaneous write connections — it sees a steady stream from the worker pool. PgBouncer connection pooling (maximum 100 PostgreSQL connections shared across all Cloud Run instances) prevents connection exhaustion during peak traffic.

---

## 5. API Design

### Conventions

- **Base URL:** `/api/v1` — versioned prefix allows `v2` to coexist during migrations
- **Authentication:** `Authorization: Bearer {access_token}` on all protected endpoints
- **Pagination:** `?page=1&page_size=20` on all list endpoints; response wraps in `PaginatedResponse<T>` with `total`, `page`, `page_size`, `has_next`, `has_previous`
- **Dates:** ISO 8601 with timezone (`2024-01-15T10:30:00Z`) — clients must always send UTC
- **IDs:** UUID v4 — prevents sequential enumeration attacks
- **Errors:** Consistent envelope `{ "error": "ERROR_CODE", "detail": "human message", "status_code": N }`
- **Soft deletes:** Deleted resources return 404, not 410 — do not reveal resource existence to unauthorized callers

---

### All Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | No | Create new user account |
| `POST` | `/auth/login` | No | Exchange credentials for JWT access + refresh tokens |
| `POST` | `/auth/refresh` | No | Exchange refresh token for new access token |
| `POST` | `/auth/logout` | Yes | Blacklist current access token jti in Redis |
| `GET` | `/auth/me` | Yes | Return current authenticated user profile |
| `GET` | `/members` | Yes | List all family members for the authenticated user (paginated) |
| `POST` | `/members` | Yes | Create a new family member |
| `GET` | `/members/{member_id}` | Yes | Get single family member by ID |
| `PUT` | `/members/{member_id}` | Yes | Update family member profile |
| `DELETE` | `/members/{member_id}` | Yes | Soft-delete a family member |
| `GET` | `/members/{member_id}/programs` | Yes | List care programs for a member |
| `POST` | `/members/{member_id}/programs` | Yes | Create a new 90-day care program |
| `GET` | `/members/{member_id}/programs/{program_id}` | Yes | Get program with components and current day/phase |
| `PUT` | `/members/{member_id}/programs/{program_id}` | Yes | Update program metadata |
| `DELETE` | `/members/{member_id}/programs/{program_id}` | Yes | Soft-delete a program |
| `POST` | `/members/{member_id}/meals` | Yes | Upload meal photo (multipart); triggers async AI extraction |
| `GET` | `/members/{member_id}/meals` | Yes | List meal logs (paginated, filterable by date range) |
| `GET` | `/members/{member_id}/meals/{meal_id}` | Yes | Get single meal log with extracted nutrition |
| `GET` | `/members/{member_id}/meals/{meal_id}/status` | Yes | Poll AI extraction status |
| `POST` | `/members/{member_id}/workouts` | Yes | Log a workout session with exercises |
| `GET` | `/members/{member_id}/workouts` | Yes | List workout sessions (paginated) |
| `GET` | `/members/{member_id}/workouts/{session_id}` | Yes | Get single workout session with exercises |
| `POST` | `/members/{member_id}/measurements` | Yes | Log a health measurement (BP, weight, glucose) |
| `GET` | `/members/{member_id}/measurements` | Yes | List measurements (paginated, filterable by type) |
| `GET` | `/members/{member_id}/measurements/latest` | Yes | Get most recent measurement per type (dashboard) |
| `GET` | `/members/{member_id}/measurements/{measurement_id}` | Yes | Get single measurement |
| `GET` | `/members/{member_id}/adherence` | Yes | Get full weighted adherence report (nutrition 40% + strength 40% + clinical 20%) |
| `POST` | `/members/{member_id}/adherence/recompute` | Yes | Force recomputation of today's adherence (bypasses cache) |
| `GET` | `/members/{member_id}/adherence/nutrition/daily` | Yes | Get daily nutrition adherence for the past 30 days |
| `GET` | `/members/{member_id}/summaries` | Yes | List weekly AI summaries (metadata only) |
| `GET` | `/members/{member_id}/summaries/{summary_id}` | Yes | Get full weekly summary with AI insights |
| `POST` | `/members/{member_id}/summaries/generate` | Yes | Trigger async weekly summary generation (202 Accepted) |

---

### Detailed Example 1: Upload Meal Photo

**Request:**
```
POST /api/v1/members/550e8400-e29b-41d4-a716-446655440000/meals
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: multipart/form-data; boundary=----FormBoundary7MA4YWxk

------FormBoundary7MA4YWxk
Content-Disposition: form-data; name="file"; filename="lunch.jpg"
Content-Type: image/jpeg

[binary JPEG data]
------FormBoundary7MA4YWxk
Content-Disposition: form-data; name="meal_type"

lunch
------FormBoundary7MA4YWxk
Content-Disposition: form-data; name="logged_at"

2024-01-15T12:30:00Z
------FormBoundary7MA4YWxk
Content-Disposition: form-data; name="program_id"

550e8400-e29b-41d4-a716-446655440001
------FormBoundary7MA4YWxk--
```

**Response 201 (Created):**
```json
{
  "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "member_id": "550e8400-e29b-41d4-a716-446655440000",
  "meal_type": "lunch",
  "extraction_status": "pending",
  "photo_url": "/uploads/550e8400-e29b-41d4-a716-446655440000/7c9e6679.jpg",
  "logged_at": "2024-01-15T12:30:00Z",
  "created_at": "2024-01-15T12:30:01.423Z",
  "extracted_nutrition": null
}
```

**Response 400 (Wrong file type):**
```json
{
  "error": "MEAL_INVALID_FILE_TYPE",
  "detail": "Only jpg, jpeg, png files are allowed. Received: application/pdf",
  "status_code": 400
}
```

**Response 413 (File too large):**
```json
{
  "error": "MEAL_FILE_TOO_LARGE",
  "detail": "File size 12.4MB exceeds the 10MB limit",
  "status_code": 413
}
```

**Response 403 (Accessing another user's member):**
```json
{
  "error": "AUTH_INSUFFICIENT_PERMISSIONS",
  "detail": "You do not have access to this family member",
  "status_code": 403
}
```

---

### Detailed Example 2: Get Adherence Report

**Request:**
```
GET /api/v1/members/550e8400-e29b-41d4-a716-446655440000/adherence
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response 200:**
```json
{
  "member_id": "550e8400-e29b-41d4-a716-446655440000",
  "report_date": "2024-01-15",
  "overall_score": 78.3,
  "nutrition": {
    "adherence_rate": 87.5,
    "target_protein_g": 60,
    "actual_protein_g": 52.5,
    "target_calories": 2000,
    "actual_calories": 1750,
    "meals_logged": 2,
    "meals_target": 3,
    "met_count": 18,
    "partial_count": 6,
    "missed_count": 6
  },
  "strength": {
    "adherence_rate": 75.0,
    "sessions_completed": 3,
    "sessions_target": 4,
    "met_count": 12,
    "partial_count": 3,
    "missed_count": 6
  },
  "clinical": {
    "adherence_rate": 66.7,
    "measurements_taken": 2,
    "measurements_target": 3,
    "latest_bp": "122/80",
    "latest_weight_kg": 76.5,
    "met_count": 8,
    "partial_count": 4,
    "missed_count": 4
  },
  "rolling_adherence": {
    "trend": "improving",
    "last_3_days_avg": 82.1,
    "prior_4_days_avg": 71.4,
    "days_analyzed": 7
  }
}
```

---

### Detailed Example 3: Rate Limit Exceeded

**Request (6th attempt within 1 minute):**
```
POST /api/v1/auth/login
Content-Type: application/json

{"email": "demo@familyhealthos.com", "password": "WrongPassword"}
```

**Response 429:**
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "detail": "Too many login attempts. Try again in 1 minute.",
  "status_code": 429
}
```

**Response Headers:**
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1705315260
Retry-After: 47
Content-Type: application/json
```

The `X-RateLimit-Reset` value is a Unix timestamp — the exact second when the counter resets. The client can display a countdown. `Retry-After` is the seconds until the reset, for simpler clients.

---

### Rate Limiting Strategy

Rate limits are enforced in Redis using a sliding window counter. The key is `rate:{endpoint_slug}:{client_ip}:{minute_bucket}` where `minute_bucket = floor(timestamp / 60)`. On each request, the counter is incremented and checked. If it exceeds the limit, 429 is returned without touching the database. Counter TTL is 60 seconds, ensuring automatic cleanup.

| Endpoint | Limit | Window | Rationale |
|---|---|---|---|
| `POST /auth/login` | 5 requests | 1 minute | Brute force protection for credentials |
| `POST /auth/register` | 3 requests | 1 hour | Prevents mass account creation |
| `POST /members/*/meals` | 20 requests | 1 hour | AI processing has real cost; prevents abuse |
| `POST /members/*/workouts` | 50 requests | 1 hour | Reasonable for bulk logging scenarios |
| `GET /members/*/adherence` | 60 requests | 1 minute | Dashboard refresh rate limiting |
| All other GET endpoints | 100 requests | 1 minute | General protection |

Login rate limiting is per-IP, not per-account. Rationale: an attacker trying to brute force an account would change usernames but keep their IP. Per-account limiting can be circumvented by distributing across many targets; per-IP limiting hits the attacker's infrastructure directly.

---

## 6. Security Architecture

### Authentication Flow

```
Step 1:  Client → POST /auth/login {email, password}

Step 2:  Server → SELECT user WHERE email=:email
         Server → verify bcrypt.checkpw(password, stored_hash)
         [bcrypt cost=12 → ~300ms intentional delay, brute force resistant]

Step 3:  Server → generate access_token:
         {
           "sub": "user_id",
           "jti": "uuid4()",   [unique token ID for blacklisting]
           "exp": now + 30min,
           "type": "access"
         }
         Server → generate refresh_token:
         {
           "sub": "user_id",
           "exp": now + 7days,
           "type": "refresh"
         }

Step 4:  Server → HTTP 200 {access_token, refresh_token, user: {...}}

Step 5:  Client → stores both tokens in AsyncStorage (encrypted on iOS Keychain)

Step 6:  Client → every request: Authorization: Bearer {access_token}

Step 7:  Server middleware (get_current_user):
         a. Decode JWT, verify signature with SECRET_KEY
         b. Check token type == "access"
         c. Check exp > now (not expired)
         d. Check Redis: EXISTS blacklist:token:{jti} → if yes: 401
         e. SELECT user WHERE id=:sub AND is_active=true
         f. Inject user into request state

Step 8:  Access token expires after 30min:
         Client → POST /auth/refresh {refresh_token}
         Server → validates refresh_token signature and expiry
         Server → issues new access_token (new jti)
         Client → updates AsyncStorage

Step 9:  User logs out:
         Client → POST /auth/logout (with access_token)
         Server → SETEX blacklist:token:{jti} {remaining_ttl} "1"
         Server → all future requests with this jti return 401 immediately
```

---

### RBAC Model

The current system implements a single role (`ACCOUNT_OWNER`) with row-level security enforced via `user_id` filtering. A future multi-role design would look like:

**`ACCOUNT_OWNER` (current default role):**
- Read and write all family members linked to their user account
- Read and write all health data for their members
- Create and modify care programs for their members
- Cannot access data belonging to any other user account

**`MEMBER_SELF` (planned for teen/adult secondary accounts):**
- Read their own health data across all metric types
- Log their own meals, workouts, and measurements
- Cannot view other family members' data
- Cannot create or delete care programs (admin permission)
- Cannot modify program targets or components

**`CARE_PROVIDER` (planned for clinical integration):**
- Read-only access to specific members they are assigned to
- Cannot write health data directly (observational role)
- Access expires after a configurable period

---

### Member Data Isolation

Every service layer function that accesses family member data applies ownership filtering as the primary query condition:

```python
# CORRECT — ownership check is inside the DB query, not after
member = db.query(FamilyMember).filter(
    FamilyMember.id == member_id,
    FamilyMember.user_id == current_user.id,   # CRITICAL ownership check
    FamilyMember.deleted_at.is_(None)           # Exclude soft-deleted
).first()

if not member:
    # Return 403, not 404
    # 404 would reveal that the member_id exists but belongs to someone else
    # 403 reveals nothing about the existence of the resource
    raise HTTPException(
        status_code=403,
        detail="You do not have access to this family member"
    )
```

This pattern is enforced at the service layer, not the route layer. This means that even if an API route is introduced without an explicit ownership check, the service function will still enforce isolation. The 403-not-404 pattern is deliberate: returning 404 for an existing resource owned by another user would enable user enumeration attacks (an attacker could map out which member IDs exist by observing 403 vs 404 responses).

---

### PHI Data Protection

**Soft deletes only:** `deleted_at` is set on `FamilyMember`, `CareProgram`, `MealLog`, `WorkoutSession`, `HealthMeasurement`. Hard deletion is not implemented in application code and the database role for the application does not have `DELETE` privileges on PHI tables in production.

**Audit logging:** Every request that reads or writes PHI is logged to `audit_logs` via `AuditMiddleware`. The log includes: user ID, action type (READ_MEMBER, CREATE_MEAL_LOG, etc.), resource type, resource ID, IP address, and timestamp. The middleware wraps every response and logs asynchronously — audit failure never causes a 500 error for the user.

**Password hashing:** bcrypt with cost factor 12. At this cost factor, a single hash computation takes approximately 300ms on modern hardware. An attacker with a leaked database who can test 1,000 passwords/second would need 318 years to exhaust a 8-character alphanumeric password space. The 300ms overhead is imperceptible to users (login is a single operation) but catastrophic for offline attacks.

**JWT design:** 30-minute access tokens minimize the window of stolen token abuse. The `jti` (JWT ID) claim is a UUID4 generated per-token, stored in the Redis blacklist on logout. This enables immediate revocation — the standard approach of "just use short expiry" cannot revoke a valid token before expiry.

**Photo access via pre-signed URLs:** In production, `photo_url` fields return time-limited pre-signed URLs (`X-Goog-Signature` via Cloud Storage). URLs expire after 15 minutes. A URL shared externally becomes invalid within 15 minutes. A suspended account's photo URLs expire naturally without any database operations.

---

### Production Security (Not in Prototype)

- **TLS 1.3:** Terminated at the Cloud Load Balancer. All traffic between client and server is encrypted. Internal GCP traffic (Cloud Run → Cloud SQL) uses Private Service Connect over Google's private network.
- **VPC Private Networking:** Cloud SQL instance has no public IP. Cloud Run instances connect via VPC connector. Redis Memorystore is accessible only within the VPC. External internet cannot reach the database layer directly.
- **Field-Level Encryption:** PII columns (full_name, date_of_birth, email) are encrypted with AES-256 using Cloud KMS-managed keys before storage. The application decrypts on read. Key rotation does not require re-encrypting all data — envelope encryption means only the data encryption key is re-wrapped.
- **HIPAA BAA with GCP:** Google offers Business Associate Agreements for covered entities. Cloud SQL, Cloud Storage, Cloud Run, and Cloud Logging all appear on GCP's HIPAA-covered services list. The BAA must be signed before storing actual patient data.
- **WAF Rules via Cloud Armor:** OWASP CRS rule set blocks SQL injection patterns, cross-site scripting, and path traversal in all request fields. Custom rules block known bad actor IP ranges. Rate limiting at the WAF level provides a last-resort DDoS defense before traffic reaches Cloud Run.
- **Annual Penetration Testing:** Scope covers API authentication bypass, horizontal privilege escalation (can user A access user B's data), injection vulnerabilities, and insecure direct object references.
- **Data Residency:** Production deployment targets `asia-south1` (Mumbai) for Indian user data. Cloud SQL regional instance with automatic failover to secondary zone within the same region.

---

## 7. Scalability Plan

### Current State (Prototype, 100 Users)

The prototype runs entirely on a single machine via Docker Compose. All three services (FastAPI, PostgreSQL, Redis) share the host's CPU and memory. File uploads are stored to the host filesystem. There is no horizontal scaling — a single FastAPI process handles all requests sequentially (with asyncio concurrency). This is appropriate for a take-home demo but would fail at 500 concurrent users.

---

### 10K Users

**What changes:**

1. **Cloud Run** replaces the single Docker container. Cloud Run auto-scales from 0 to N instances based on request concurrency. Each instance handles 80 concurrent requests (FastAPI is async, so I/O-bound requests don't block each other). The application code requires zero changes — Cloud Run is a deployment target, not a code change.

2. **Redis Memorystore** replaces the local Redis container. This provides a shared Redis instance accessible from all Cloud Run instances. Without this change, each Cloud Run instance has its own in-process cache, meaning rate limits and JWT blacklists are not shared — a logged-out user's token would still be valid on the instance that doesn't have the blacklist entry.

3. **Cloud Storage** replaces local filesystem for photo uploads. At 10K users logging 3 meals/day with ~1MB photos each, storage grows at 30GB/day. Local disk on Cloud Run instances is ephemeral (cleared on instance restart) and limited. Cloud Storage provides infinite, durable storage with CDN integration.

4. **Pub/Sub** replaces `FastAPI BackgroundTasks` for AI extraction. BackgroundTasks run in-process — if the Cloud Run instance handling a request is shut down (e.g., scale-in), the background task is lost. Pub/Sub persists messages across instance lifecycle. Workers are separate Cloud Run instances that process jobs independently.

5. **Read replica for PostgreSQL.** Adherence queries (`GET /adherence`) are read-heavy — they aggregate data across 30-90 days of meal logs. Adding a read replica routes all `SELECT` queries from FastAPI to the replica, freeing the primary for writes only. SQLAlchemy supports this via separate `engine_read` and `engine_write` session factories.

6. **PgBouncer connection pooling.** PostgreSQL has a hard limit on concurrent connections (~100 for a small instance). Each Cloud Run instance maintains a pool of connections. Without pooling, 50 Cloud Run instances each holding 5 connections = 250 connections, exceeding PostgreSQL's limit. PgBouncer acts as a proxy that maintains a small pool of actual PostgreSQL connections and multiplexes thousands of application connections through them.

---

### 100K Users

**Additional changes beyond the 10K plan:**

1. **Table partitioning.** `meal_logs`, `workout_sessions`, and `adherence_metrics` will have accumulated hundreds of millions of rows. PostgreSQL declarative partitioning by month reduces the effective index size per partition from 100M rows to ~3M rows. Query planner automatically prunes irrelevant partitions. Archival: partitions older than 2 years can be moved to cheaper nearline storage.

2. **Read/write splitting in SQLAlchemy.** The `get_db()` dependency returns a write session (primary) by default. A separate `get_db_read()` dependency returns a read session (replica). Routes are annotated with which dependency they require. Heavy analytical queries (adherence reports, dashboard data) use read sessions exclusively.

3. **CDN for photo delivery.** Without CDN, each photo view hits Cloud Storage — at 100K users viewing meal history, egress costs and Cloud Storage API call costs become significant. Cloud CDN serves cached photos from the nearest edge PoP for free after the first request, with 30-day TTL. Cold miss rate approaches 0% because users frequently review the same meal logs.

4. **Multiple Pub/Sub subscribers.** At 100K users uploading 3 meals/day = 300K photos/day = 3.5 photos/second peak. Each AI extraction takes 2-5 seconds. To process in near-real-time: `throughput / processing_time = 3.5 / 3 ≈ 2 workers` at average load, scaling to 10-15 at peak. Pub/Sub automatically distributes messages across subscribers — adding workers is just scaling the Cloud Run worker service.

5. **Rate limiting at Cloud Armor (edge).** At 100K users, rate limit enforcement at the application layer (Redis) introduces a Redis read on every request. Cloud Armor can enforce rate limits before the request reaches Cloud Run, reducing compute cost for abusive traffic.

6. **Query optimization.** All hot queries undergo `EXPLAIN ANALYZE` review. Common issues: missing indexes on `WHERE` predicates, N+1 queries from ORM lazy loading (addressed via `joinedload`), and missing covering indexes (adding columns to index to avoid heap fetches).

---

### What Breaks First

At 10,000 concurrent meal uploads:

**PostgreSQL write throughput** is the first bottleneck. Each meal upload triggers: 1 `INSERT` into `meal_logs`, 1 `INSERT` into `audit_logs`, and (after AI extraction) 1 `UPSERT` into `adherence_metrics`. At 10,000 concurrent uploads, this is 30,000 writes/second. A standard Cloud SQL instance handles approximately 5,000-10,000 writes/second on an 8-core instance. The solution is a write queue: Pub/Sub buffers uploads, and a worker batch-inserts every 500ms using PostgreSQL's multi-row `INSERT INTO ... VALUES (...), (...), (...)` syntax, reducing 1,000 round trips to 1.

**Redis connection exhaustion** is the second bottleneck. Each cache read/write opens a connection from the connection pool. At 100 Cloud Run instances each holding a pool of 10 Redis connections = 1,000 connections. Redis's default `maxclients` is 10,000, so this is manageable, but monitoring connection count is critical.

---

### Performance Targets

| Operation | Target Latency | Current Prototype | Bottleneck if Missed |
|---|---|---|---|
| `GET` with cache hit | < 50ms | ~10ms | Redis latency or network |
| `GET` with cache miss | < 200ms | ~50ms | PostgreSQL query + Redis write |
| `POST` (write + cache invalidate) | < 500ms | ~100ms | PostgreSQL write + Redis delete |
| Photo upload (to storage) | < 2 seconds | ~500ms (local disk) | Network bandwidth, storage I/O |
| AI extraction (mock) | < 3 seconds | ~2s (sleep) | AI API latency |
| AI extraction (real Gemini) | < 10 seconds | N/A (mocked) | Gemini API P95 latency |
| Adherence report (cached) | < 50ms | ~10ms | Redis read latency |
| Adherence report (uncached) | < 500ms | ~200ms | PostgreSQL aggregation query |
| Weekly summary generation | < 15 seconds | ~3s (mock) | Gemini 1.5 Pro P95 latency |

---

## 8. Background Job Processing

### Which Operations Are Async

| Operation | Why Async | Mechanism (Prototype) | Mechanism (Production) |
|---|---|---|---|
| AI nutrition extraction | 2-10s Gemini API call — unacceptable to block HTTP response | `FastAPI BackgroundTasks` | Pub/Sub → Cloud Run Worker |
| Adherence recomputation | 100-500ms DB aggregation — can run after response | `FastAPI BackgroundTasks` | Pub/Sub (triggered by meal/workout write) |
| Weekly summary generation | 2-5s with AI, only needed weekly | Triggered on `POST /summaries/generate` | Cloud Scheduler → Pub/Sub → Worker |
| Audit log writes | Fire-and-forget, failure should not block response | `FastAPI BackgroundTasks` | Async DB write with retry |
| Photo validation and compression | CPU-intensive, not needed for 201 response | Not implemented | Pub/Sub Worker (separate from AI worker) |
| Push notifications (future) | Notification delivery is not user's problem | N/A | Pub/Sub → Firebase Cloud Messaging |

---

### Job Design (Production)

**Pub/Sub Message Schema for Nutrition Extraction:**
```json
{
  "job_type": "EXTRACT_NUTRITION",
  "meal_log_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "member_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "a3f8c9d1-1234-5678-abcd-ef0123456789",
  "image_path": "gs://praan-health-photos/550e8400.../7c9e6679.jpg",
  "meal_type": "lunch",
  "logged_at": "2024-01-15T12:30:00Z",
  "retry_count": 0,
  "created_at": "2024-01-15T12:30:01Z"
}
```

**Worker Processing Logic:**
```
1. Pull message from Pub/Sub subscription
2. UPDATE meal_log SET extraction_status='processing'
3. Download image from Cloud Storage (gs:// path)
4. Call Gemini Vision API with image + prompt template
5. Validate response schema (check all required nutrition fields present)

   On success:
   6a. UPDATE meal_log SET extracted_nutrition={...}, extraction_status='completed'
   6b. Invalidate adherence cache keys for this member + today
   6c. Recompute and store updated adherence metrics
   6d. ACK message (Pub/Sub deletes it)

   On failure (AI error, network timeout, invalid response):
   6e. If retry_count < 3:
         NACK message (Pub/Sub redelivers with exponential backoff: 10s, 60s, 300s)
         Increment retry_count in message
   6f. If retry_count >= 3:
         UPDATE meal_log SET extraction_status='failed'
         Forward to dead letter topic: praan-health-extraction-dlq
         Alert engineering via Cloud Monitoring
         ACK original message (stop retrying)
```

**Weekly Summary Cron Job:**
Cloud Scheduler fires `POST /api/v1/members/*/summaries/generate` at 23:00 IST every Sunday. For each active program that has completed a full week, the summary service: collects all adherence metrics for the week, computes average protein, sessions completed, and measurement compliance, passes the data to Gemini 1.5 Pro with a structured prompt requesting clinical observations, validates the JSON response, and stores the result in `program_summaries`. The job is idempotent — if it runs twice for the same week, the second run finds an existing summary and skips.

---

## 9. Edge Cases & Error Handling

| Scenario | What Could Go Wrong | Handling |
|---|---|---|
| Day 1 of program, no data logged yet | Adherence endpoint has nothing to compute | Returns `adherence_rate: 0`, `status: "missed"` — never null. The dashboard shows "0%" not an error. |
| Photo upload fails mid-upload (network drop) | `meal_log` row is written before photo is confirmed saved | Cleanup job runs every 6 hours: finds `meal_logs` with `extraction_status='pending'` older than 1 hour, deletes the orphaned DB row. Photos are stored with the meal log UUID in the path, enabling correlation. |
| AI extraction timeout (>30s) | Gemini API hangs, worker holds the message indefinitely | Worker has a 30-second timeout on the API call. On timeout, marks `extraction_status='failed'`, sends NACK to Pub/Sub for retry. After 3 retries, routes to dead letter queue. |
| Program reaches day 91 (expired) | Users attempt to log data after program ends | Program status auto-updates to `"completed"` via a daily Cloud Scheduler check. `POST /meals`, `/workouts`, `/measurements` all return 400 with `PROGRAM_COMPLETED` error code when the program is not `active`. The error message explains the program has ended and suggests starting a new one. |
| Simultaneous uploads from the same member | Two concurrent writes to `adherence_metrics` for the same (member, component, date) | `ON CONFLICT (member_id, component_type, metric_date) DO UPDATE SET ...` handles this atomically. PostgreSQL serializes the conflict resolution. The second writer's value wins, which is acceptable since both are computed from the same DB state (the difference is at most one meal log). |
| Member soft-deleted while request is in flight | Request starts, member is deleted mid-request by a concurrent call | All queries include `deleted_at IS NULL`. The mid-flight request will find the member (was not deleted when the query ran), and the deletion happens after. The subsequent request correctly returns 404. |
| Cache stampede at midnight (all TTLs reset) | 1,000 users hit adherence endpoint at midnight when daily cache keys expire | Redis SETNX lock pattern (described in Section 4). Only one request computes from DB; others wait 100ms and read from the freshly populated cache. |
| Invalid photo file type bypass | User manually constructs a multipart request with a PDF renamed to ".jpg" | File validation checks MIME type by reading file magic bytes, not file extension. A PDF renamed to `.jpg` has `%PDF-` as its first 4 bytes, which does not match JPEG (`FF D8 FF`) or PNG (`89 50 4E 47`) magic numbers. |
| Refresh token expired | Access token expires, refresh token also expired (user away for >7 days) | Refresh endpoint returns 401. Mobile client catches this in the axios response interceptor and redirects to LoginScreen. AsyncStorage is cleared. No data is lost — all data is server-side. |
| Program component config missing a required field | Nutrition component created without `daily_protein_target_g` | Pydantic schema `NutritionConfig` validates all required fields at the API boundary. The request is rejected with a 422 Unprocessable Entity before the service layer is reached. |
| Week 0 adherence (program created but not yet started) | Program has `start_date` in the future | Adherence endpoint checks `day_number < 1` and returns `HTTP 200` with an empty adherence report and `message: "Program starts in 2 days"`. Does not return 0% — distinguishes "not started" from "started and performing at 0%". |
| Member with no active program | User added a family member but hasn't created a program | Adherence endpoint returns `HTTP 404` with error code `ADHERENCE_NO_ACTIVE_PROGRAM` and `detail: "No active care program found for this member"`. The mobile client catches this and shows "Set up a care program to start tracking" CTA. |

---

## 10. Known Limitations & Production Readiness

### Shortcuts Taken (Honest Assessment)

**1. AI extraction is mocked.** `ai_service.py` returns hardcoded nutrition data from `MOCK_NUTRITION_DATA` with a 2-second sleep to simulate latency. A real implementation would call `google.generativeai.GenerativeModel("gemini-1.5-pro-vision")` with a structured prompt requesting JSON output in the `extracted_nutrition` schema. The mock is a deliberate scope decision — integrating a real AI API would require API key management, rate limit handling, retry logic for flaky responses, and prompt engineering, all of which are substantial work orthogonal to the architecture being demonstrated.

**2. Local file storage.** Photos are saved to `backend/uploads/{member_id}/` on the container filesystem. Cloud Run instance storage is ephemeral — restarting the container loses all photos. Production requires Cloud Storage with `google-cloud-storage` client library and IAM service account credentials. The `photo_key` column in `meal_logs` already stores the path format (`{member_id}/{uuid}.jpg`) that would be used as the Cloud Storage object key with zero schema changes.

**3. Synchronous AI processing via asyncio.sleep.** AI extraction runs in a FastAPI `BackgroundTask` in-process. If the Cloud Run instance serving the upload request is shut down during scaling, the background task is lost — the `meal_log` stays in `extraction_status='pending'` indefinitely. Production requires Pub/Sub to persist the job across instance lifecycle. The cleanup job (find `pending` rows older than 1 hour) partially mitigates this but with latency.

**4. No HTTPS in development.** The Docker Compose setup serves plain HTTP on port 8000. Mobile apps require HTTPS for production (App Transport Security on iOS, Network Security Config on Android). In production, HTTPS is terminated at the Cloud Load Balancer with a Google-managed SSL certificate — the FastAPI app itself never handles TLS.

**5. Simplified adherence calculations.** Strength adherence divides sessions completed by sessions target as a simple percentage. A production system would use a more nuanced model: sets completed, progressive overload achievement, rest interval compliance, and muscle group coverage. Clinical adherence similarly uses a simple count of measurements taken vs target, whereas production would incorporate measurement timing (was BP taken at the correct time of day?) and trend analysis (is BP trending toward or away from the target range?).

**6. No email verification.** Users can register with any email address, including non-existent ones. A production system sends a verification link on registration and blocks login until the email is confirmed. This prevents account enumeration via registration (an attacker cannot determine if an email is registered by watching for "email already in use" errors if all emails require verification before they become queryable).

**7. No background job worker process.** Background tasks run in FastAPI's in-process thread pool. This means AI extraction competes for CPU with API request handling. A production system runs a separate Cloud Run service (the "worker") that pulls from Pub/Sub and processes jobs without any HTTP serving overhead.

**8. No formal test suite.** Unit tests, integration tests, and end-to-end tests are not included. The architecture is designed for testability — services are dependency-injected, the database session is injectable for test overrides, and the cache client has a no-op test mode — but the tests themselves are not written. Production would require >80% line coverage with pytest, covering happy paths, auth failures, access control enforcement, and cache invalidation.

**9. No field-level PHI encryption.** Columns like `full_name`, `date_of_birth`, and extracted nutrition data are stored as plaintext in PostgreSQL. Production requires application-level encryption using Cloud KMS-managed keys before storing sensitive fields. This means a database breach does not expose PII in plaintext — an attacker with raw database access sees only encrypted bytes.

**10. No image resizing or compression pipeline.** Photos are stored at original resolution (potentially 4K from modern phones, 5-8MB). A production system would run a photo processing worker that generates multiple resolutions (thumbnail: 200px, medium: 800px, full: 1600px) and re-encodes to WebP for 60% smaller file size. The CDN then serves the appropriate resolution based on the client's screen density.

---

### Production Readiness Checklist

- [ ] Replace mock AI with Gemini Vision API (google-generativeai SDK)
- [ ] Move photo storage to GCP Cloud Storage with pre-signed URL generation
- [ ] Implement Pub/Sub message queue for AI extraction jobs
- [ ] Add PgBouncer connection pooling between Cloud Run and Cloud SQL
- [ ] Configure Cloud Run with minimum instances > 0 (eliminates cold start latency)
- [ ] Add TLS/HTTPS termination via Cloud Load Balancer with managed SSL certificate
- [ ] Implement field-level AES-256 encryption for PII columns via Cloud KMS
- [ ] Write comprehensive pytest test suite (>80% line coverage)
- [ ] Add Cloud Monitoring dashboards: request latency, error rate, cache hit rate, AI extraction success rate
- [ ] Configure alerting: P95 latency > 1s, error rate > 1%, extraction failure rate > 5%
- [ ] Sign HIPAA Business Associate Agreement with GCP
- [ ] Implement email verification on registration
- [ ] Add rate limiting at Cloud Armor edge layer
- [ ] Configure VPC private networking: Cloud SQL and Redis not publicly accessible
- [ ] Enable Cloud SQL automated backups (daily) and point-in-time recovery
- [ ] Set up Cloud Build CI/CD pipeline: lint → test → build → deploy to staging → deploy to production
- [ ] Performance test with k6: 10,000 concurrent users, all endpoint scenarios
- [ ] Security penetration test: OWASP Top 10, horizontal privilege escalation, JWT bypass
- [ ] Implement photo compression pipeline: multi-resolution WebP generation
- [ ] Add read replica to Cloud SQL for analytics/adherence queries
- [ ] Configure Pub/Sub dead letter queues with PagerDuty alerts
- [ ] Data residency: deploy to asia-south1 (Mumbai) for Indian user data
- [ ] Implement Cloud Scheduler weekly summary generation cron job
- [ ] Add Gemini 1.5 Pro integration for weekly AI summaries (production path already documented in summary_service.py)

---

*Document version: 1.0 — written at completion of Modules 1–10 (backend + mobile app)*
*Author: Founding Full-Stack Engineer take-home assignment*
*Stack: Python + FastAPI + PostgreSQL + Redis + React Native + GCP*
