# Healthcare Appointment & Follow-up Manager

A full-stack clinic platform with separate portals for **patients**, **doctors**, and **admins** — appointment booking with race-safe slot holds, AI pre-visit and post-visit summaries, medication reminders, email notifications, and Google Calendar sync.

## Features

- **Patients**: register/login, search doctors by specialization, book/cancel/reschedule appointments, submit symptoms before a visit, view AI post-visit summaries and prescriptions, connect Google Calendar.
- **Doctors**: view today's/upcoming appointments, see the AI-generated pre-visit summary (urgency, chief complaint, suggested questions), submit consultation notes + prescription, which auto-generates a patient-friendly post-visit summary.
- **Admins**: create/manage doctor profiles (specializations, working hours, slot duration), mark doctor leave (auto-cancels & notifies affected patients), view all appointments, view failed notifications.
- **Reliability**: DB-level double-booking prevention, slot holds with expiry, LLM failures never block booking, email retries with backoff, Google Calendar sync failures never invalidate an appointment.

## Architecture

```
frontend/   Next.js 14 (App Router) + TypeScript + Tailwind
backend/    FastAPI + SQLAlchemy + Alembic + Celery + Redis
postgres    Primary datastore
redis       Celery broker/result backend
```

Request flow: `Frontend -> FastAPI (sync request/response) -> Celery (async: email, calendar, AI, reminders)`.
Business logic lives in `app/services/*`, not in route handlers — routers only validate/authorize and call services.

## Tech Stack

| Layer      | Choice                                                              |
|------------|----------------------------------------------------------------------|
| Frontend   | Next.js 14, TypeScript, Tailwind CSS, React Hook Form, Axios         |
| Backend    | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, JWT (python-jose), bcrypt |
| Database   | PostgreSQL                                                            |
| Background | Celery + Redis (worker + beat)                                       |
| AI         | OpenAI API (JSON-mode, Pydantic-validated)                           |
| Email      | SendGrid                                                              |
| Calendar   | Google Calendar API, OAuth 2.0                                       |

## Folder Structure

```
backend/
  app/
    api/v1/        route handlers (auth, doctors, patients, appointments, admin, google)
    core/           config, database session, security (JWT/bcrypt), exceptions
    models/         SQLAlchemy models (one file per domain area)
    schemas/        Pydantic request/response schemas
    services/       business logic: booking, slot generation, llm, email, calendar
    workers/        celery_app.py (schedule) + tasks.py (async jobs)
    utils/          medication frequency parser
    tests/          pytest suite
  alembic/          migrations (0001_initial_schema.py has the full schema)
  seed.py           admin/doctors/patient/sample-appointment seed data
frontend/
  app/              route pages (public, patient/*, doctor/*, admin/*)
  components/       Navbar, ProtectedRoute, StatusBadge
  hooks/useAuth.tsx JWT auth context (login/register/logout)
  services/api.ts   axios client with auth interceptor
  types/            shared TypeScript types
docker-compose.yml  postgres + redis + backend + celery worker + celery beat + frontend
SYSTEM_DESIGN.md    800-word design write-up (conflicts, holds, leave, notifications)
```

## Local Setup

### Prerequisites
Python 3.11+, Node 18+, PostgreSQL 14+, Redis 6+ (or use `docker-compose up` for all infra).

### 1. Database
```bash
createdb healthcare_db
# or via docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16-alpine
```

### 2. Redis
```bash
# docker run -d -p 6379:6379 redis:7-alpine
```

### 3. Backend
```bash
cd backend
python -m venv .venv
.venv/Scripts/activate       # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env         # fill in DATABASE_URL, OPENAI_API_KEY, SENDGRID_API_KEY, GOOGLE_*
alembic upgrade head
python -m app.seed           # creates admin, 3 doctors, 1 patient, 1 sample appointment
uvicorn app.main:app --reload
```
API docs: `http://localhost:8000/docs` (Swagger) and `/redoc`.

Seeded logins (see `app/seed.py`):
| Role    | Email                  | Password       |
|---------|-------------------------|----------------|
| Admin   | admin@clinic.com        | Admin@12345    |
| Doctor  | dr.sharma@clinic.com    | Doctor@12345   |
| Patient | patient@example.com     | Patient@12345  |

### 4. Celery worker + beat (separate terminals, same venv)
```bash
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```
Beat drives: slot-hold expiry (every 60s), medication reminder dispatch (60s), email retry (5 min), calendar-sync retry (5 min), appointment reminders (every 30 min), pre-visit-summary retry (10 min).

### 5. Frontend
```bash
cd frontend
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_BASE_URL
npm run dev
```
App: `http://localhost:3000`.

### 6. All-in-one with Docker
```bash
docker-compose up --build
```

## Environment Variables

See `backend/.env.example` and `frontend/.env.example` for the full list. Key ones:

- `OPENAI_API_KEY` / `OPENAI_MODEL` — LLM summaries. If unset, the app still runs; AI summaries are stored as `FAILED` with a clear reason and the doctor/patient sees "AI summary unavailable".
- `SENDGRID_API_KEY` / `SENDGRID_FROM_EMAIL` — outbound email.
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` — Calendar OAuth.
- `SLOT_HOLD_MINUTES` — how long a slot hold is valid (default 5).
- `MAX_EMAIL_RETRY_ATTEMPTS` — after this many failures, an email is marked permanently `FAILED` and surfaces on `/admin/notifications`.

## Google Cloud / Calendar Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create/select a project.
2. Enable the **Google Calendar API** (APIs & Services → Library).
3. APIs & Services → Credentials → Create Credentials → **OAuth client ID** → Application type **Web application**.
4. Add an authorized redirect URI matching `GOOGLE_REDIRECT_URI` in your `.env`, e.g. `http://localhost:8000/api/v1/google/callback`.
5. Copy the generated Client ID/Secret into `backend/.env`.
6. In the app, a logged-in patient/doctor visits `/patient/calendar` or `/doctor/calendar` → "Connect Google Calendar" → Google consent screen → redirected back and tokens are stored in `calendar_connections`.
7. While the app is in "Testing" publishing status in Google Cloud, only test users you add under OAuth consent screen can authorize it.

## Database Schema (summary)

`users` (role: PATIENT/DOCTOR/ADMIN) → `patients` / `doctors` (1:1) → `doctor_specializations`, `doctor_working_hours`, `doctor_leaves` (1:many). `appointments` links a patient and doctor; `slot_holds` is a short-lived pre-booking reservation. Clinical data: `symptom_forms` → `pre_visit_summaries` (AI), `consultation_notes` + `prescriptions` → `prescription_medications` → `post_visit_summaries` (AI) and `medication_reminders`. Delivery tracking: `notifications` (idempotency for reminders), `email_logs` (retry state), `calendar_connections` (OAuth tokens), `calendar_events` (sync state per attendee). Full DDL: [`backend/alembic/versions/0001_initial_schema.py`](backend/alembic/versions/0001_initial_schema.py).

Two **partial unique indexes** are the crux of the whole system:
```sql
CREATE UNIQUE INDEX uq_doctor_active_start_time ON appointments (doctor_id, start_time)
  WHERE status NOT IN ('CANCELLED', 'RESCHEDULED');
CREATE UNIQUE INDEX uq_doctor_active_hold_start_time ON slot_holds (doctor_id, start_time)
  WHERE status = 'ACTIVE';
```

## LLM Prompts

**Pre-visit** (`app/services/llm_service.py::PRE_VISIT_PROMPT`):
> Analyse these symptoms and return: 1. urgency level (Low / Medium / High) 2. chief complaint 3. three suggested questions for the doctor. Symptoms: `<symptoms>`

**Post-visit** (`POST_VISIT_PROMPT`):
> Convert these clinical notes into a patient-friendly summary with a medication schedule and follow-up steps. Use ONLY information present in the notes — do not invent medications, diagnoses, or facts. Clinical notes: `<notes>`

Both request strict JSON, validated against a Pydantic model before being trusted; on any failure (timeout, rate limit, bad key, network, malformed JSON, schema mismatch) the appointment/consultation flow **continues unaffected** and the summary row is stored with `status=FAILED` plus the error reason — see [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) for the full failure-handling story.

## API Documentation

Full interactive docs at `/docs` once the backend is running. Representative endpoints:

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/doctors?specialization=
GET    /api/v1/doctors/{id}
GET    /api/v1/doctors/{id}/availability?date=YYYY-MM-DD
POST   /api/v1/appointments/hold          { doctor_id, start_time }
POST   /api/v1/appointments               { hold_id }
GET    /api/v1/appointments
PATCH  /api/v1/appointments/{id}/cancel
PATCH  /api/v1/appointments/{id}/reschedule
POST   /api/v1/appointments/{id}/symptoms
GET    /api/v1/appointments/{id}/symptoms
GET    /api/v1/appointments/{id}/pre-visit-summary
POST   /api/v1/appointments/{id}/consultation
GET    /api/v1/appointments/{id}/post-visit-summary
POST   /api/v1/google/connect
GET    /api/v1/google/callback
POST   /api/v1/admin/doctors
PATCH  /api/v1/admin/doctors/{id}
POST   /api/v1/admin/doctors/{id}/leave
DELETE /api/v1/admin/doctors/{id}/leave
```

Errors follow a consistent shape:
```json
{ "success": false, "message": "...", "error_code": "CONFLICT", "details": {} }
```
`409` is used specifically for slot conflicts (already booked / hold lost the race / hold expired).

## Running Tests

```bash
cd backend
pytest -v
```
Covers: register/login, role authorization (patient blocked from admin routes), slot generation (working hours/leave/booked-slot exclusion), **double-booking under concurrent threads**, hold expiry, doctor-leave conflict, reschedule, LLM failure modes (timeout/malformed JSON/unexpected exception never propagate), email retry/backoff/permanent-failure, medication reminder frequency parsing.

All 24 tests pass (verified on Python 3.14 / Windows, SQLite backend for test isolation — the concurrency test uses a temp-file-backed SQLite DB so each thread gets its own connection, genuinely racing for the same slot, same as two separate API processes would against Postgres):
```
24 passed in 17.10s
```

## Known Simplifications

- All appointment/working-hour times are treated as UTC; a production clinic app would add a per-doctor timezone field and convert at the edges.
- Google OAuth `state` is kept in an in-memory dict (`app/api/v1/google.py`) for simplicity — swap for a Redis-backed store before running more than one backend instance.
- The frontend covers every route from the spec; a few lower-traffic admin views (e.g. editing working hours after creation) call the same `PATCH /admin/doctors/{id}` style endpoints but keep the UI minimal — extend as needed.

## Deployment

- **Frontend → Vercel**: import the repo, set root directory to `frontend/`, add `NEXT_PUBLIC_API_BASE_URL` pointing at the deployed backend.
- **Backend → Render**: new Web Service from `backend/`, build command `pip install -r requirements.txt`, start command `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add a Render **Background Worker** for `celery -A app.workers.celery_app worker` and one for `celery -A app.workers.celery_app beat`.
- **Postgres → Neon/Supabase/Render Postgres**: copy the connection string into `DATABASE_URL`.
- **Redis → Upstash/Render Redis**: copy the connection string into `REDIS_URL` / `CELERY_BROKER_URL`.
- Update `GOOGLE_REDIRECT_URI` and the Google Cloud OAuth client's authorized redirect URI to the deployed backend URL, and `BACKEND_CORS_ORIGINS`/`FRONTEND_URL` to the deployed frontend URL.
