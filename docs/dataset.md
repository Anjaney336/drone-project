# Dataset and provenance

## Inventory

| Dataset | Origin | Local samples | Modality | Intended use |
|---|---:|---:|---|---|
| AERIS demonstration dataset | demonstration | 10 assets, 4 missions, 7 seeded observations | product entities | reproducible SIH workflow only |
| `damage_detection_local` | public dataset, unverified source | 1,500 images (70/15/15, seed 20260820) | RGB image + YOLO boxes | **trains the shipped YOLOv8n detector** |
| `uav_crack_segmentation_local` | public dataset, unverified source | 315 images (70/15/15, seed 20260820) | RGB image + binary mask | **trains the shipped TinyUNet segmenter** |
| AERIS synthetic sensor v1 | synthetic / synthetic fault | generated per split | truth, IMU, GNSS-like, detector outputs | statistical supporting-data validation |
| AERIS seeded scenarios | simulation | generated per run | position/velocity/GNSS-like measurements | estimation baselines |
| AERIS fault injection | synthetic fault | generated per run | drift, dropout, noise, timing, loss, bias, degradation, disagreement | resilience tests only |
| Real flight telemetry | measured | 0 | camera/GNSS/IMU/barometer/telemetry | not yet available |

The two `_local` datasets above are what the shipped models were actually trained on; their
manifests are `data/manifests/damage_detection_manifest.json` and
`data/manifests/uav_crack_segmentation_manifest.json`. The machine-readable inventory is
`data/manifests/datasets.yaml`.

## Datasets considered and not used

Three public benchmarks were evaluated during an earlier, drone-detection-oriented phase of
this project and are **not** part of the inspection product. They are recorded here so the
decision is auditable, not as roadmap items:

| Dataset | Why it was dropped |
|---|---|
| VisDrone 2019 DET | Aerial detection of ground objects (pedestrians, vehicles). Not infrastructure defects, and never present in the workspace or wired into any pipeline. |
| Anti-UAV300 | Detecting drones *in the sky*. That is a counter-UAV task, not an inspection task. The 5.6 GB archive never completed download and was excluded from every reported metric. |
| EuRoC MAV | Stereo + IMU with ground-truth pose, useful only for visual-inertial estimator replay. No local archive was ever validated. |

No metric anywhere in this repository is derived from any of them. `aeris.data.synthetic`
cites a published VisDrone YOLOv8-M result as the *provenance of a noise parameter*; that is a
citation, not a dependency on the dataset.

Unknown values in the telemetry schema are nullable. Origin, source, scenario ID, and
injected-fault label accompany every simulation row.

## Product demonstration dataset

`data/demo/aeris_demo_seed_2026.json` is the authoritative product seed. Generate it with
`scripts/export_demo_dataset.py`. Its fixed source is `aeris.demo.seed.v1`, seed is 2026, and
generation timestamp is fixed so byte output is reproducible. SHA-256 for this revision is
`bbccb2e42181940ab12d317541ec955524fe50e6f6fbc3d3a0a6aab340908b87`.

Reproducibility is enforced, not just asserted. `scripts/export_demo_dataset.py --check`
regenerates the dataset and fails if the committed file differs; CI runs it on every push.
Three things make the hash stable:

- the export runs against a throwaway database, so nothing the app or the test suite wrote
  into `artifacts/aeris_product.db` can leak into it;
- the file is written as bytes with explicit LF newlines, so it does not change when
  generated on Windows;
- `.gitattributes` marks `data/**` as binary for end-of-line purposes, so `text=auto`
  cannot rewrite the newlines on checkout and invalidate the hash.

The locations are intentionally demonstration records for the prototype. Evidence URIs are
labelled demonstration references, not downloadable photographs. Observation confidence is null
on the seeded observations because they were authored as demonstration records, not produced by
a model — a real AI finding always carries the confidence its model reported.

## Limitations

- no licensed, repository-tracked real drone flight telemetry;
- no local flight-controller ground truth;
- no hardware time synchronization or calibration record;
- no validated RGB/thermal pairing;
- no real anomaly or adversarial-attack measurements;
- no evidence that the training imagery represents a particular Indian deployment site;
- **the upstream source and licence of both training datasets were not retained** when the raw
  folders were downloaded, and the detector's class ids 0/1 remain anonymous — findings are
  surfaced as `class_0_unverified` / `class_1_unverified` rather than as named defect types.
