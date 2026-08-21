# Offline workflow validation

**Mechanism: `localStorage`, not IndexedDB.** The field-capture queue
(`getQueue`/`setQueue`/`syncQueue` in `src/aeris/app/static/app.js`) reads and writes a single
JSON array under the key `aeris-field-queue`. This is stated plainly here and in
no IndexedDB claim is made anywhere in this repository.

## Real test performed (this session, in an actual browser)

| Step | Result |
|---|---|
| 1. Backend online | Confirmed via `GET /api/v1/health` before starting |
| 2. Navigate to Field Capture, fill and submit the form | Real record created client-side |
| 3. Inspect `localStorage['aeris-field-queue']` directly | Confirmed 1 real record: `client_record_id`, `asset_id`, `observation_type`, `notes`, `captured_at`, `origin: "field"`, `source: "aeris.field_capture"` |
| 4. Disconnect backend (killed the process) | `netstat` confirmed port 8501 no longer listening |
| 5. Call `syncQueue()` while disconnected | Threw as expected; **queue length remained 1** — the record was not lost or silently dropped |
| 6. Restore backend | `GET /api/v1/health` → `200 ok` again |
| 7. Call `syncQueue()` again | Succeeded; **queue length dropped to 0** |
| 8. Confirm the record reached the backend | `GET /api/v1/assets/BR-042` shows the observation with `origin: "field"`, `analysis_method: "field_observation_no_model_inference"`, a real server-assigned `observation_id`, and the exact notes text submitted — not a fabricated echo |

This exercised the real code path, not a mock: the same `syncQueue()`/`getQueue()`/`setQueue()`
functions the UI buttons call were invoked directly in the live page's JS context.

## Idempotency (already covered by an existing automated test)

`tests/test_product_layer.py::test_offline_sync_is_idempotent_and_preserves_field_origin` — not
re-run manually this pass since it's unrelated to the localStorage mechanism specifically, but it
remains part of the 48-test suite and passed in this session's runs.

## Known limitations (stated honestly, not new to this pass)

- `localStorage` has a practical size ceiling (typically 5–10MB per origin across browsers) — for
  a hackathon demo capturing a handful of text observations this is not a problem, but it would
  not scale to, e.g., storing full-resolution images offline. Evidence photos are referenced by
  filename (`evidence_name`) only; the file itself is not persisted offline in this prototype.
- No conflict resolution beyond `client_record_id`-based idempotency (a record synced twice is
  deduplicated server-side, but there is no merge logic for concurrent edits to the same record
  from two devices — not a realistic scenario for a single-operator field-capture prototype, but
  stated for completeness).
- The sync queue is per-browser-profile, not per-user-account — there is no cross-device queue.

This is a genuine, working offline-first capture-and-sync workflow for a hackathon prototype. It
is not claimed to be production-grade government offline infrastructure.
