# Simplified hazard log

This is a research hazard analysis styled after MIL-STD-882E concepts; it is not a certification
artifact and no compliance claim is made.

| Hazard | Cause/failure mode | AERIS detection | Deterministic response | Residual risk / limitation |
|---|---|---|---|---|
| Misleading navigation | GNSS drift/bias or cross-sensor disagreement | NIS rejection and `cross_sensor_disagreement` in `SensorHealthMonitor.evaluate` | HOLD or RETURN_HOME recommendation in `SafetyEngine.decide` | thresholds are simulation-tuned; correlated/common-mode failure is not validated |
| Navigation source lost | GNSS or camera dropout | `sensor_unavailable` event and lower sensor trust | HOLD/RETURN_HOME recommendation | no real inertial dead-reckoning duration validation |
| Stale information | packet delay | `packet_timing` at configured delay threshold | HOLD/RETURN_HOME recommendation | host/network clock synchronization is not modeled |
| Implausible state | estimator velocity exceeds configured limit | `impossible_kinematics` | HOLD/RETURN_HOME recommendation | threshold is an engineering value, not airframe-specific assurance |
| Geofence departure | predicted position leaves configured boundary | `Geofence.contains` over predicted trajectory | REROUTE recommendation | constant-velocity prediction omits wind/dynamics |
| Loss of separation | predicted distance below configured minimum | collision component in `SafetyEngine.decide` | REROUTE recommendation | no independent collision ground truth or multi-agent intent model |
| Unsafe automation | recommendation interpreted as a hardware command | architecture contains no actuator/flight-control adapter | operator-facing recommendation only | human misuse remains possible; UI and docs must preserve this boundary |
| Unattributable verdict | a finding's review status is changed without an accountable reviewer | `REVIEW_TRANSITIONS` refuses illegal moves; CONFIRMED/REJECTED are terminal | `submit_human_review` raises; every verdict is appended to `human_reviews` with reviewer and timestamp | **the reviewer name is self-asserted, not authenticated** — the API has no login, so the audit trail records who *claimed* to review, not who provably did. Deploying beyond a prototype requires real authentication (see README, Evidence boundaries) |
| Fabricated finding | a model that is not READY is asked to analyse | `ModelAdapter._require_ready` checks `status.json` before every inference | `analyze()` raises RuntimeError; the API returns 409 and the UI disables analysis | a checkpoint present but silently corrupted is not detected; only its declared status is checked |
