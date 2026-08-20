# Methodology

The filter propagates a six-state position/velocity model with measured IMU acceleration as control input. Position updates compute innovation `y = z - Hx`, residual covariance `S = HPH^T + R`, and normalized innovation squared `y^T S^-1 y`. A 3-D 99% chi-square threshold (11.345) marks inconsistent evidence. In AERIS it does not automatically discard the measurement: instantaneous trust decays with normalized NIS, cross-modal agreement can corroborate a measurement against a faulty prediction, and effective covariance is inflated by inverse squared trust. Trust degrades immediately and recovers through an EWMA. Hard rejection is a separate comparator.

The trajectory baseline extrapolates constant velocity and propagates a conservative covariance trace. The safety engine checks predicted minimum separation, geofence containment, anomaly severity, uncertainty, sensor trust, and communication delay in deterministic priority order. Every recommendation includes evidence and an auditable weighted risk breakdown.

Scenarios are deterministic for a seed and record scenario ID, config hash, model version, dataset version, and timestamp. Faults have explicit type, LOW–EXTREME severity, start time, duration, affected sensor, and recovery; they are labelled `synthetic_*`.
