# Licensing and redistribution

This file is a release gate, not legal advice. Confirm the upstream terms before
redistributing any data or model artifact.

## Repository code

The AERIS source is released under the repository license in [`LICENSE`](../LICENSE).
Contributions must preserve attribution and the applicable third-party notices.

## Third-party data

| Asset | Current disposition | License/provenance |
|---|---|---|
| Damage Detection | Not redistributed; sample only | Source and license unconfirmed |
| UAV crack segmentation | Not redistributed; sample only | Source and license unconfirmed |
| MH-SoyaHealthVision | Download-only; manifest and script committed | CC BY 4.0, Mendeley DOI `10.17632/hkbgh5s3b7.1`; attribution required |
| Light-field `.npy` collection | Quarantined and ignored | Origin and license unknown; do not publish |
| VisDrone / Anti-UAV / EuRoC candidates | Not active; no raw data committed | Review each upstream dataset's current terms before use |

The samples under `data/samples/` are included for deterministic engineering tests. They
must not be treated as a blanket grant to redistribute the corresponding full datasets.

## Model weights

`yolov8n.pt` is an Ultralytics-derived base weight and is subject to its upstream
license/notice. Fine-tuned checkpoints are generated under `artifacts/` and are not
committed. See `data/manifests/models.json` for hashes and provenance fields.

## Before a release

1. Confirm each dataset's canonical source and license in writing.
2. Record the source URL/DOI, version/date, attribution, and checksum in the dataset
   register and manifest.
3. Remove any raw or generated artifact whose terms or provenance are unresolved.
4. Re-run `scripts/verify_datasets.py` and review the final Git diff before publishing.
