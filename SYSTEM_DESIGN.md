# System Design Write-up

## Double-booking prevention

The guarantee is enforced at the database layer, not in application code, because application-level checks ("query then insert") race under concurrent load. Two **partial unique indexes** (Postgres) are the real safety net:

```sql
CREATE UNIQUE INDEX uq_doctor_active_start_time ON appointments (doctor_id, start_time)
  WHERE status NOT IN ('CANCELLED', 'RESCHEDULED');
CREATE UNIQUE INDEX uq_doctor_active_hold_start_time ON slot_holds (doctor_id, start_time)
  WHERE status = 'ACTIVE';
```

Only one *active* (non-cancelled/non-rescheduled) appointment, and one *active* hold, can exist per `(doctor_id, start_time)`. The partial `WHERE` clause lets a slot be reused after cancellation without violating uniqueness. `create_slot_hold()` still does an application-level pre-check (doctor on leave? already booked?) for a fast, friendly error — but the actual race is resolved by the `INSERT`: if two requests hit the same slot simultaneously, Postgres commits only one row and raises `IntegrityError` for the other, which the service turns into `409 Conflict` ("Slot no longer available"). Correctness holds even across multiple API server processes — no shared in-memory lock needed.

`confirm_booking()` additionally takes `SELECT ... FOR UPDATE` on the specific `slot_hold` row before converting it to an appointment, which serializes concurrent *confirm* calls against the *same* hold (e.g., a double-click), while the appointments table's own unique index is the final backstop against any other race. This was verified with a threading-based test (`test_double_booking.py`) that fires two simultaneous hold requests for the same doctor/time and asserts exactly one succeeds.

## Slot hold mechanism and expiration

Booking is two steps: (1) `POST /appointments/hold` reserves the slot for `SLOT_HOLD_MINUTES` (default 5) while the patient fills the symptom form, (2) `POST /appointments` converts the hold into a confirmed appointment. This prevents a slot from being shown as available to other patients while someone is mid-form, without permanently locking it if they abandon the flow. Holds carry `expires_at`; `confirm_booking()` checks it and rejects (409) an expired hold. Expiry is also swept proactively in two places: opportunistically at the start of every new hold attempt (`expire_stale_holds()`), and by a Celery beat task every 60 seconds, so abandoned holds free their slot even if no one else tries to book it.

## Doctor leave conflict handling

When an admin adds a `doctor_leaves` row for a date that already has `PENDING`/`CONFIRMED` appointments, the API responds immediately (leave is recorded) and enqueues `task_handle_doctor_leave` asynchronously. That task queries all affected appointments, sets their status to `CANCELLED` with an explicit `cancelled_reason` (never a silent delete — the row and its history stay queryable), then fires per-appointment cancellation emails to both patient and doctor and deletes any synced Google Calendar events. Because this runs in the background, marking a doctor on leave stays fast for the admin even with hundreds of affected bookings, and each notification failure is retried independently rather than blocking the whole batch.

## LLM failure handling

Both `generate_pre_visit_summary()` and `generate_post_visit_summary()` wrap the OpenAI call in specific `except` clauses for timeout, rate-limit, connection, and API-status errors, plus a catch-all for anything else (never let an LLM failure become an unhandled 500). The model is asked to return JSON, which is then validated against a strict Pydantic schema (`PreVisitLLMResult`/`PostVisitLLMResult`); a malformed or off-schema response is treated as a failure, not trusted data. Every path returns an `LLMResult(success, data, error)` — it never raises. The calling code always persists a summary row regardless of outcome: `status=SUCCESS` with the structured data, or `status=FAILED` with `raw_error` set. The booking/consultation flow itself never depends on the LLM call succeeding — symptoms and clinical notes are saved first, and the AI summary generation happens in a Celery task after, so a stuck OpenAI account never blocks a visit. The doctor UI shows "AI summary unavailable, please review the patient's original symptoms" and links back to the raw `symptom_forms` row. A separate beat task retries `FAILED` pre-visit summaries every 10 minutes.

## Notification failure handling

Every email attempt is persisted in `email_logs` (recipient, type, status, `attempt_count`, `last_error`) before and after sending — so a failure is never just a dropped exception. `send_notification_email()` never raises; a SendGrid error increments `attempt_count` and sets status to `RETRYING` (or `FAILED` once `MAX_EMAIL_RETRY_ATTEMPTS` is hit). A Celery beat task re-attempts `RETRYING`/`FAILED` logs every 5 minutes, giving natural exponential backoff since each retry only happens once per beat cycle. Permanently failed emails surface on `/admin/notifications` for manual follow-up. Google Calendar sync follows the identical pattern via `calendar_events.status` (`PENDING`/`SYNCED`/`FAILED`) with its own retry task — critically, calendar and email failures never roll back or invalidate the underlying appointment; they are independent, retryable side effects.

## Background job architecture

Celery (Redis broker) runs a worker for on-demand tasks (send confirmation, sync calendar, generate AI summary, create medication reminders) triggered right after the relevant DB transaction commits, plus Celery Beat for periodic sweeps (hold expiry, email/calendar retry, due medication reminders, 24h appointment reminders — deduplicated via a `notifications` row per user/appointment/type so beat re-runs never double-send).
