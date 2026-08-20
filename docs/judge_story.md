# The judge story

## Problem

Government agencies increasingly fly drones over bridges, dams, roads, and structures. A single
mission produces thousands of images and telemetry records. That data collection alone does not
answer the question an engineer actually needs answered.

## Why existing drone imagery alone is insufficient

A model can flag "possible crack" in a frame. But the frame came from a real flight, with real
GNSS, real battery drain, real telemetry gaps. If the drone's navigation was degraded when that
frame was captured, the finding's location — or its very validity — is in question. Most drone
inspection tools show you a bounding box and stop there. None of them ask: *was the data that
produced this bounding box trustworthy in the first place?*

## AERIS intelligence

AERIS inserts a step every other system skips: **before** a finding reaches a human, it is
attached to a **mission reliability** assessment — a transparent, weighted score built from the
mission's own telemetry (GNSS/NIS consistency, sensor confidence, telemetry continuity, battery,
data completeness), never a black box.

## Drone health

Every mission's telemetry is scored per-dimension, with plain-language reasons, and — critically —
"not available" is a real, honestly-shown state, not silently defaulted to "healthy."

## Mission reliability

HIGH / MEDIUM / LOW, always with the *why*. A LOW-reliability mission's findings are visibly
qualified in the Human Review Queue — "treat as needing verification, not an actionable finding on
its own" — rather than presented with the same confidence as a HIGH-reliability mission's.

## AI analysis

A real YOLOv8n model, trained on a real (audited, honestly-imperfect) 1,500-image dataset, run
through the same registry that refuses to fabricate a prediction if the model isn't ready. Every
finding says "AI Flagged: Possible Defect" — never "Confirmed."

## Offline continuity

Field capture works with no connectivity: the record is saved locally, queued, and synced
explicitly and idempotently once connectivity returns — demonstrated for real this session, not
simulated for the judges.

## Human review

The AI is advisory, structurally. A reviewer's verdict — Confirmed, Rejected, Needs Reinspection,
Escalated — is the only thing that changes a finding's status, and every verdict is persisted with
an audit trail.

## Government prioritization

The Decision Center ranks assets by a transparent formula (severity, recurrence, criticality,
trend, geographic concentration), with the reasoning always visible — never an unexplained number.

## The one-sentence pitch

**AERIS doesn't just tell you what a drone saw — it tells you whether you should believe it, and
lets a human make the final call.**
