# Fault-model register

All active benchmark faults are **synthetic-fault injections**, not measured failures or attacks.
The code source of truth is `aeris.simulation.fault_injection` and scenario composition is in
`aeris.simulation.scenarios`.

| Fault | Active model | Parameter basis |
|---|---|---|
| Baseline GNSS noise | independent 1.5 m Gaussian per axis | engineering estimate; not receiver-calibrated |
| GNSS drift | `[2.5, -0.8, 0] × severity × elapsed` m | engineering stress-test profile; not claimed as ionospheric or spoofing characterization |
| GNSS bias/disagreement | fixed vector, severity scaled | engineering estimate selected to exceed the 3-D NIS consistency gate |
| GNSS dropout | measurement becomes unavailable | structural failure mode; 5 s duration is engineering estimate |
| Packet loss | Bernoulli probability based on severity | engineering estimate |
| Communication latency | 0.4 s × severity | engineering estimate; DJI publishes approximately 120 ms minimum link latency, which is not used as a fault distribution |
| IMU bias | `[0.8, -0.4, 0.2] × severity` m/s² | engineering injected step, intentionally distinct from nominal BMI088 stochastic bias |
| Camera degradation/occlusion | increased observation error/lower confidence, or unavailable observation | engineering detector-output fault; no pixels are generated |
| Impossible kinematics | speed above 60 m/s detector threshold | engineering safety threshold, not a Mini 4 Pro limit |

The supporting dataset generator uses the same fault labels and the same
`synthetic_fault` provenance class, but its DOP/multipath regimes are not silently substituted for
the benchmark configuration. DJI's [Mini 4 Pro specification](https://www.dji.com/mini-4-pro/specs)
and Bosch's [BMI088 specification](https://www.bosch-sensortec.com/en/products/motion-sensors/imus/bmi088/)
are scope anchors; every parameter not numerically supported by them is labelled above as an
engineering estimate.
