# Requirements traceability matrix

This matrix includes only behavior present in code and exercised by a named test.

| ID | Verifiable requirement | Implementation | Verification |
|---|---|---|---|
| REQ-PER-01 | Labelled simulator observations shall pass through detector and tracker interfaces. | `SimulationObservationDetector.detect`; `run_scenario` | `test_simulator_camera_enters_detector_and_tracker` |
| REQ-FUS-01 | The estimator shall expose innovation, NIS, covariance and sensor trust. | `ConstantVelocityEKF.update_position` | `test_prediction_and_update_expose_innovation_and_nis` |
| REQ-FUS-02 | Adaptive fusion shall soft-weight rejected measurements; hard rejection shall remain a distinct comparator. | `ConstantVelocityEKF.update_position` | `test_outlier_is_soft_weighted_and_reduces_trust`; `test_hard_rejection_is_a_distinct_comparator` |
| REQ-ANOM-01 | Missing, inconsistent and delayed measurements shall create evidence-backed events. | `SensorHealthMonitor.evaluate` | `test_innovation_and_packet_timing_events_are_evidence_backed`; `test_missing_sensor_is_reported_without_using_fault_labels` |
| REQ-PRED-01 | The predictor shall emit a time-indexed constant-velocity path. | `ConstantVelocityPredictor.predict` | `test_tracking_velocity_and_prediction` |
| REQ-SAFE-01 | Boundary risk shall produce a deterministic recommendation and recovery dwell. | `SafetyEngine.decide` | `test_geofence_risk_produces_explainable_reroute`; `test_state_machine_enters_recovery_after_anomaly_clears` |
| REQ-DATA-01 | Telemetry shall carry required origin/source lineage; missing live hardware data shall not be fabricated. | `TelemetryRecord`; `LiveHardwareAdapter.records` | `test_typed_mission_api_and_unavailable_invariant`; `test_live_mode_reports_unavailable_instead_of_faking_data` |
| REQ-BENCH-01 | All comparators shall consume the same immutable sample stream per scenario/seed. | `run_benchmark`; `sensor_stream_digest` | `test_paired_variants_receive_byte_identical_immutable_stream` |
| REQ-API-01 | Unknown request fields shall fail and the benchmark route shall expose only the authoritative artifact. | Pydantic `MissionCreate`; `get_benchmark` | `test_unknown_api_fields_are_rejected`; `test_benchmark_endpoint_reads_only_authoritative_artifact` |
| REQ-SYN-01 | Synthetic data shall be deterministic, speed-bounded and explicitly tagged. | `aeris.data.synthetic.generate` | `test_synthetic_generator_is_reproducible_and_provenance_is_complete`; `test_synthetic_trajectory_respects_documented_speed_limit` |
