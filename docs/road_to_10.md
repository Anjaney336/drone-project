# Road to 10 — highest-impact improvements

Prioritized by (impact on score) ÷ (implementation cost), not by part-number order. Each item
states the category it moves and by roughly how much, based on `docs/sih_engineering_evaluation.md`.

## Tier 1 — do these first (large impact, already partially underway)

1. **Finish and honestly report the YOLO resolution experiment.** Moves: AI/ML quality (+0.5–1
   if it measurably improves recall on the small-object class), Technical complexity (+0.5, shows
   real scientific method, not just training a bigger model and hoping). Cost: none — already
   running, just needs to complete and be evaluated on the untouched test split.
2. **Ship a single-command flagship demo script.** Moves: Demo quality (+2–3), Product usability
   (+1). This is the single highest-leverage remaining gap: every workflow step is real, but a
   judge cannot currently press one button and watch mission→inference→reliability→review→
   priority happen. Cost: low — it's orchestration of already-working API calls, not new logic.
3. **Browser-based image upload**, replacing the server-filesystem-path requirement for
   `/analyze`. Moves: Product usability (+1–2), Demo quality (+1). Cost: moderate — a multipart
   upload endpoint plus a file-picker in the Mission Detail/Missions page.

## Tier 2 — meaningful if time allows

4. **Agriculture as a second real working domain**, once the download completes and is honestly
   audited. Moves: Problem relevance (+0.5, broadens the government use case beyond one
   department), Data quality (+1), Differentiation (+0.5 — "one platform, two ministries" is a
   stronger story than "one platform, one department"). Cost: high — full audit, task
   formulation, training, registry integration. Only pursue if the download finishes with enough
   time remaining; do not rush it to protect the "not fabricated" guarantee that is currently one
   of AERIS's real strengths.
5. **Fold mission reliability into the priority score itself** (not just displayed adjacently).
   Moves: Explainability (+0.5, already strong, this closes the one gap noted in
   `docs/priority_engine_validation.md`), AI/ML quality perception (+0.5 — "a LOW-reliability
   finding is automatically down-weighted, not just annotated" is a more sophisticated story).
   Cost: low-moderate — `assess_priority` needs one new input and one new documented weight.
6. **Video/frame-sampling pipeline**, scoped exactly as instructed — frame extraction, existing
   image model per frame, temporal timeline, explicitly not claiming a video model. Moves:
   Innovation (+0.5), Robotics relevance (+0.5), Demo quality (+0.5, judges respond well to a
   video timeline). Cost: moderate-high — real engineering, not a documentation exercise.

## Tier 3 — polish, do last

7. Drone Health as a structured status/reason/evidence/action model per dimension (currently
   reliability-derived but not broken into the NAVIGATION/SENSORS/POWER/TELEMETRY/DATA-QUALITY
   taxonomy requested). Moves: Robotics relevance (+0.5), Explainability (+0.5, already high).
8. Map/geographic filtering by domain, priority, and review status on top of the existing static
   map. Moves: Government applicability (+0.5), Product usability (+0.5).
9. Visual/typographic polish pass once the functional gaps above are closed — polish on top of a
   thin workflow reads as "trying to distract," polish on top of a complete workflow reads as
   "professional."

## What NOT to do

- Do not chase a higher mAP by training longer without evidence it will help beyond what
  `docs/yolo_baseline_diagnosis.md` already identified (resolution as the primary lever) — more
  epochs alone without addressing the small-object/resolution root cause is unlikely to move the
  needle and risks looking like undirected tuning to a technical judge.
- Do not add agriculture, video, or any new capability by faking results to hit a deadline — the
  project's current 9/10 explainability and human-in-the-loop scores exist *because* nothing in
  the repo is fabricated; one discovered fake number would cost far more credibility than any
  single feature gains.
- Do not rebuild the offline layer onto IndexedDB "to sound more advanced" — `localStorage` with
  honestly documented limits is defensible; the risk/reward of a rewrite this late is poor.
