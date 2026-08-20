# Prioritization engine validation

Two distinct, intentionally separate mechanisms exist — validated independently:

1. **Asset priority** (`src/aeris/app/priority.py`, `assess_priority`) — "how urgent is this
   asset", a transparent weighted formula over severity/confidence/criticality/recurrence/trend/
   geographic_impact. Unchanged this session; already explainable (returns `factors`, `formula`,
   `components`, never a bare number).
2. **Mission reliability** (`src/aeris/app/mission_reliability.py`) — "can we trust this mission's
   data", separate on purpose (see `docs/mission_reliability.md`).

## Real example (from this session's live backend, not constructed for this doc)

```
CRITICAL — 82.2/100 — BR-042 · Mahanadi East Bridge
Reasons:
• Severe observation recorded
• Repeated across 3 inspections
• High asset criticality
• Condition deterioration increased
• Located in a concentrated problem area
• Observation confidence unavailable; neutral value used for triage
```

Every priority-queue row carries this explanation — confirmed rendering correctly in-browser on
the Decision Center page this session (see `artifacts/frontend_api_failure_analysis.md`'s
validation section for the screenshot-equivalent page-text capture).

## Qualifying findings when mission reliability is LOW

Implemented in the Human Review Queue (`reviewQueuePage()` in `app.js`): each finding's row
carries its mission's reliability tag, and when that reliability is `LOW`, an explicit qualifying
line renders beneath it:

> ⚠ Data quality degraded — treat as needing verification, not an actionable finding on its own.

This was exercised earlier this session (previous turn) with a real LOW/39.0 reliability
assessment (two hand-constructed telemetry rows with a GNSS innovation excursion and two packet
gaps) attached to a real finding, and the review-queue correctly rendered the qualifying text next
to it — not a synthetic example built only for this document.

## What determines priority — no unexplained numbers

Asset priority currently draws on: AI/human-reported severity, confidence (explicitly neutral when
absent, never fabricated), asset criticality, recurrence count, condition trend, and geographic
concentration. It does **not** currently read `mission_reliability` or AI-finding confidence
directly into its formula — those are surfaced adjacently (in the review queue and Mission Detail
page) rather than folded into the same number, which keeps "how urgent" and "how trustworthy"
separately inspectable rather than collapsed into one opaque score. This is a deliberate design
choice carried over unchanged from the prior session's architecture (see
`docs/application_migration_plan.md`), not a gap introduced this pass.

## Limitation

Affected-area-based priority weighting (e.g. from the crack-segmentation model's predicted mask
area) is not yet wired into `assess_priority` — the crack segmentation model returns an
`affected_area_fraction` in its `ModelPrediction.regions`, but no code path currently feeds that
into a priority computation. Stated as a gap, not implemented silently as if it were complete.
