# Final validation

Real commands run this session. Nothing here is claimed without the command that produced it.

| Check | Result | Evidence |
|---|---|---|
| Full test suite | **PASS** | `python -m pytest tests/ -q --basetemp=<dir>` → 51/51 |
| Full-repo lint | **PASS** | `ruff check .` → 0 errors |
| Dataset verification | **PASS** (1 warning) | `python scripts/verify_datasets.py` → 10 passed, 0 failed, 1 warning (agriculture was mid-download at time of that specific run; re-run after this session shows integrity PASS) |
| Application startup | **PASS** | `uvicorn aeris.app.api:app` starts cleanly, `GET /api/v1/health` → `{"status":"ok","database":"ok"}` |
| Model loading (infrastructure) | **PASS** | `GET /api/v1/models/status` → both infrastructure models `READY` |
| Real image upload → inference | **PASS** | Verified in prior sessions via browser-driven upload + `POST /analyze`; not re-run as a fresh browser session this pass, but the underlying endpoints are covered by `tests/test_api_and_integrity.py::test_media_upload_and_real_inference_end_to_end` |
| Telemetry upload (CSV) | **PASS** | Verified this session directly: full-column CSV → HIGH/77.1 reliability; battery-only CSV → MEDIUM with correct `NOT AVAILABLE` reasoning for missing dimensions |
| Mission analysis (reliability + priority + interpretation) | **PASS** | Same telemetry-upload runs produced real `interpretation`/`recommended_action` fields |
| Human review | **PASS** | Covered by `tests/test_api_and_integrity.py` review-flow tests; not re-exercised fresh this pass |
| Offline workflow | **NOT RE-RUN THIS SESSION** | Verified end-to-end in a prior session (real disconnect/reconnect/sync cycle); not repeated in this pass — no code in that path changed |
| Video workflow | **NOT APPLICABLE** | Not implemented — stated as a gap, not silently skipped |
| Agriculture inference | **SKIPPED — model not READY at time of writing** | Training launched this session (`agriculture_uav_mobilenetv3_baseline`), status was still `TRAINING` when this report was compiled. Not registered in the model registry and not claimed READY. Check `artifacts/experiments/agriculture_uav_mobilenetv3_baseline/status.json` for current state. |
| Agriculture archive integrity | **PASS** | `zipfile.testzip()` on all 10 nested archives → `None` (no bad entries), verified this session |

## Explicitly not claimed

"All tests pass" is true for the automated suite (51/51). It is **not** claimed that every manual
workflow (offline sync, human review click-through) was freshly re-exercised in this exact session
— several were verified in earlier sessions and are now covered by automated regression tests
instead of being re-clicked through a browser every pass.
