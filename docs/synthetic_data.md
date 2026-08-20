# Defensible synthetic sensor data

The generator emits exact kinematic truth, BMI088-grounded IMU noise, DOP-scaled GNSS-like
measurements, and detector-output records. It emits **no pixels and no synthetic imagery**.
Detection statistics are grounded in published aerial-detection literature; underlying imagery is
not real and is not used.

## Source and estimate register

| Model element | Value/model | Basis |
|---|---|---|
| Airframe envelope | 16 m/s horizontal; 5 m/s vertical | [DJI Mini 4 Pro specifications](https://www.dji.com/mini-4-pro/specs) |
| IMU white noise | 175 µg/√Hz accelerometer; 0.014 °/s/√Hz gyro | [Bosch BMI088 specification BST-BMI088-DS001](https://www.bosch-sensortec.com/en/products/motion-sensors/imus/bmi088/) |
| IMU bias | first-order Gauss–Markov, 0.003 m/s² stationary sigma, 100 s correlation | engineering estimate; BMI088 source does not publish these two parameters |
| GNSS geometry | coordinate error sigma multiplied by HDOP/VDOP | DOP is the geometry mapping described by the [GPS SPS Performance Standard](https://www.gps.gov/technical/ps/2020-SPS-performance-standard.pdf); chosen ranges are engineering estimates |
| Open-sky GNSS scale | 0.5 m base sigma | engineering estimate anchored to DJI's stated ±0.5 m GNSS hovering accuracy; not claimed as a Gaussian datasheet sigma |
| Urban multipath | biased Student-t horizontal error | distribution parameters are engineering estimates; a separate biased/heavy-tail regime follows the observed distinction between LOS/NLOS/urban errors in [Chen et al. (2018)](https://doi.org/10.3390/s18041149) |
| GNSS outage | 2 s discrete loss | engineering estimate |
| Clear-view detector target | precision 0.534; recall 0.420 | reported YOLOv8-M VisDrone result in [Remote Sensing 18(9), 1394](https://doi.org/10.3390/rs18091394) |
| Range/occlusion falloff | logistic range curve and explicit occlusion multiplier | engineering estimate; VisDrone includes occlusion annotations and identifies scale/occlusion as challenges in [Zhu et al.](https://arxiv.org/abs/1804.07437) |

Temperature dependence and scale-factor errors are omitted because this pass lacks applicable,
verified parameterization. The flight truth contains straight, waypoint, loiter, evasive, and
landing segments at 50 Hz. It is deterministic and noiseless. GNSS drift, IMU bias jump and
communication delay reuse constants from `aeris.simulation.fault_injection`; DOP, urban multipath,
outage and occlusion remain separately documented supporting-data regimes.

## Split discipline and evidence

`scripts/generate_synthetic_data.py` fixes tuning seed 20261 and untouched held-out seed 20262.
Each file has a separate manifest with hash, parameters, citations, seed, and record-level
`synthetic`/`synthetic_fault` origin. Only the held-out split is eligible for reported evaluation.
This synthetic dataset is supporting validation input; the headline fusion result continues to
come from the corrected equal-stream scenario protocol in `artifacts/benchmark.json`.

`scripts/validate_synthetic_data.py` recomputes short-interval Allan deviation, checks open-sky
GNSS error/DOP scaling, checks clear-view precision and recall, and verifies provenance. Its
machine-readable result is `artifacts/synthetic_data_validation.json`.
