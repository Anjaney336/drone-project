# Independent SIH engineering evaluation — AERIS

Rated as a Smart India Hackathon / national-level engineering submission, against what a strong
finalist/winner typically demonstrates: a clear problem, a usable working prototype, real
technical depth, honest evidence, and a demonstration a judge can follow in minutes.

## Overall score: **6.5 / 10**

Not inflated. AERIS is a genuinely working, evidence-backed prototype with a differentiated
core idea (mission reliability, not just detection) — that is rare among hackathon drone
projects and is the strongest asset here. It is held back from a higher score by baseline model
accuracy, the absence of a second domain (agriculture) actually working, and a demo that is not
yet a single reproducible script a judge could run unsupervised.

## Category scores

| # | Category | Score /10 | Why |
|---|---|---:|---|
| 1 | Problem relevance | **9** | Genuinely underserved gap: most drone-inspection hackathon projects stop at "detect defect." AERIS's four questions (healthy? trustworthy? observed? urgent?) map directly to how a real government asset-management workflow actually needs to work. |
| 2 | Innovation | **7** | Mission Reliability as a first-class, explainable signal *decoupled from* detection confidence is the genuinely novel piece. Detection itself (YOLO+segmentation) is standard, not novel. |
| 3 | Technical complexity | **7** | Real training pipelines, a working model registry with honest state machine, SQLite schema with 11 real tables, EKF/NIS-derived reliability scoring reused from a real prior research prototype. Not novel algorithmically, but genuinely non-trivial engineering, not a wrapper around one API call. |
| 4 | AI/ML quality | **5** | This is the honest weak point. mAP50=0.44, recall=0.50 (YOLO) and IoU=0.50 (segmentation) are real, disclosed, and diagnosed — but they are modest. A judge who checks the numbers will see a legitimate baseline, not a strong model. The diagnosis work (docs/yolo_baseline_diagnosis.md) is a real asset that partially offsets this — it shows scientific maturity even where the number is unimpressive. |
| 5 | Robotics relevance | **6** | Telemetry/EKF/NIS concepts are real robotics engineering, reused honestly from prior sensor-fusion work. No actual flight-controller integration or live drone connection exists — this is data-model and scoring depth, not hardware-in-the-loop robotics. |
| 6 | Government applicability | **8** | District/asset/priority-queue/decision-workflow modeling is specific and plausible for an actual state PWD/irrigation-department use case, not generic. Demonstration data uses real Indian districts (Cuttack, Puri, Khordha) rather than placeholder cities. |
| 7 | Real-world feasibility | **6** | CPU-only inference is honest and demo-practical, but the underlying model quality (see AI/ML quality) means it is not yet field-deployable as an autonomous decision-maker — appropriately, the system positions AI as advisory with mandatory human review, which is the right feasibility posture, not a weakness to hide. |
| 8 | Scalability | **6** | SQLite is explicitly documented as a prototype choice with a stated Postgres/PostGIS migration path (`docs/architecture.md`). Reasonable for a hackathon, correctly not oversold as production-scale. |
| 9 | Offline capability | **7** | Real, verified, end-to-end (queue → disconnect → preserved → reconnect → sync → verified in backend). Honestly scoped as `localStorage`, not IndexedDB, with stated size limits — the honesty here is itself a point in AERIS's favor with a technical judge. |
| 10 | Product usability | **6** | Clean, coherent single-page app with real navigation and a genuinely connected Mission Detail page. Image analysis still requires a server-side file path rather than a browser upload — a judge trying to click through independently would hit this friction immediately. |
| 11 | Demo quality | **5** | Every step of the flagship workflow is individually real and verified, but there's no single push-button demo script — running it live in front of judges currently means either clicking through the UI carefully or knowing the right `curl` sequence. This is a correctable gap, not a fundamental one. |
| 12 | Data quality | **6** | Datasets are real, audited, honestly documented including their flaws (unverified class semantics, 55:1 imbalance, no pretrained encoder). This transparency is good engineering practice but the datasets themselves are modest (1,500 and 315 images) and of unconfirmed public provenance. |
| 13 | Explainability | **9** | The strongest category. Every score in the system — priority, reliability, review status — ships with a plain-language reason list, not a bare number. This is executed consistently, not just in one showcase feature. |
| 14 | Human-in-the-loop design | **8** | Correctly implemented as mandatory, not optional — AI never auto-confirms a defect, terminology consistently says "AI Flagged," and the review verdict genuinely changes system state (audit trail, queue removal). |
| 15 | Differentiation from a basic drone dashboard | **8** | Mission Reliability + the explicit separation of "what AI saw" from "can we trust what AI saw" is the clearest differentiator from the many drone-defect-detection hackathon projects that stop at a bounding box. |

## What would move this from 6.5 toward 9

See `docs/road_to_10.md` for the prioritized list. In one sentence: **raise AI/ML quality
credibly (or reframe it honestly as "baseline, diagnosed, with a clear improvement path"), ship
agriculture as a second real working domain, and make the flagship demo a single reproducible
script** — those three changes address the three lowest-scoring categories (AI/ML quality, demo
quality, and indirectly data quality/product usability) without touching what already works.
