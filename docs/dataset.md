# Dataset and provenance

## Inventory

| Dataset | Origin | Local samples | Modality | Intended use |
|---|---:|---:|---|---|
| AERIS demonstration dataset | demonstration | 10 assets, 4 missions, 7 seeded observations | product entities | reproducible SIH workflow only |
| VisDrone 2019 DET | public benchmark candidate | 0 validated local files | RGB image + detection annotation | future small-object perception evaluation only |
| AERIS synthetic sensor v1 | synthetic / synthetic fault | generated per split | truth, IMU, GNSS-like, detector outputs | statistical supporting-data validation |
| AERIS seeded scenarios | simulation | generated per run | position/velocity/GNSS-like measurements | estimation baselines |
| AERIS fault injection | synthetic fault | generated per run | drift, dropout, noise, timing, loss, bias, degradation, disagreement | resilience tests only |
| Real flight telemetry | measured | 0 | camera/GNSS/IMU/barometer/telemetry | not yet available |
| Anti-UAV300 | public benchmark candidate | download initiated; not validated locally | RGB/thermal UAV video + boxes/visibility | dedicated UAV detection/tracking |
| EuRoC MAV | public benchmark candidate | not validated locally | stereo, IMU, pose ground truth | visual-inertial ingestion and timing |

The machine-readable manifest is `data/manifests/datasets.yaml`. VisDrone is not present in the
active workspace and is not evidence for GNSS, IMU, telemetry, navigation anomalies, or current
detector performance. Users must verify upstream terms before any future download/redistribution.

## Relevance decision

VisDrone is relevant only for aerial-view small-object perception engineering. Its canonical classes are ground objects; it is **not** a dedicated airborne-drone detection dataset and cannot validate AERIS navigation resilience. Anti-UAV300 is the appropriate complementary perception benchmark because its official release contains RGB and thermal UAV sequences with dense boxes and visibility flags. EuRoC MAV is appropriate for visual-inertial adapter validation because it provides stereo at 20 FPS, IMU at 200 Hz, calibration, and external ground truth. Neither dataset alone validates the full AERIS safety claim.

The Anti-UAV300 browser transfer was initiated from the official Google Drive release on 2026-08-20. The 5.6 GB archive was not complete at audit time and is therefore excluded from all reported metrics. A partial browser download is not treated as a dataset. EuRoC's official archive is also multi-gigabyte and remains excluded until a complete archive, license review, checksum, and ingestion QA are recorded.

Official references: Anti-UAV repository: https://github.com/ZhaoJ9014/Anti-UAV ; EuRoC MAV: https://ethz-asl.github.io/datasets/euroc-mav/ and DOI https://doi.org/10.3929/ethz-b-000690084 .

Unknown values in the telemetry schema are nullable. Origin, source, scenario ID, and injected-fault label accompany every simulation row.

## Product demonstration dataset

`data/demo/aeris_demo_seed_2026.json` is the authoritative product seed. Generate it with
`scripts/export_demo_dataset.py`. Its fixed source is `aeris.demo.seed.v1`, seed is 2026, and
generation timestamp is fixed so byte output is reproducible. SHA-256 for this revision is
`db0e2e7d6d23115cae030560d9660ae67ed98503f01f1d479ca11795e0c7503f`.

The locations are intentionally demonstration records for the prototype. Evidence URIs are
labelled demonstration references, not downloadable photographs. Observation confidence is null
because no trained/evaluated infrastructure model is present.

## Limitations

- no licensed, repository-tracked real drone flight telemetry;
- no local flight-controller ground truth;
- no hardware time synchronization or calibration record;
- no validated RGB/thermal pairing;
- no real anomaly or adversarial-attack measurements;
- no evidence that public perception benchmarks represent a particular Indian deployment site.
