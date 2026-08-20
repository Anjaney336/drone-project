# Research method

AERIS maintains a six-dimensional position/velocity state. IMU acceleration drives prediction. Camera-derived tracks and GNSS positions update the estimator with modality-specific measurement covariance.

For measurement dimension 3, the normalized innovation squared is `νᵀS⁻¹ν`. A threshold of 11.345 corresponds to a 99% chi-square boundary. In the proposed adaptive method, threshold crossing is anomaly evidence—not automatic rejection. Instantaneous trust decays exponentially with normalized NIS, an EWMA stabilizes trust over time, and effective covariance is `R / trust²`. The hard-rejection variant is retained only as a comparator.

The benchmark uses paired seeds and identical observations for raw inverse-variance fusion, fixed EKF, hard-rejection EKF, and AERIS adaptive EKF. Offline evaluators compare estimates and predictions with simulator truth; runtime algorithms never receive future truth. Metrics include position and velocity RMSE, median and p95 error, precision/recall/F1, FPR/FNR, time-to-detect, NIS statistics, ADE/FDE, latency, and FPS. The 100-trial report aggregates mean, median, standard deviation, p95, and normal-approximation 95% confidence intervals.

Ablations remove visual input, adaptive trust, NIS evidence, or trajectory prediction one factor at a time. Simulation results establish software behavior under controlled conditions; they do not establish flightworthiness.
