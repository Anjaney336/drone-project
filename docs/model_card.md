# AERIS model cards

This document is the compact index for the model-specific validation reports. All
metrics below are held-out test-split metrics from local runs; they are not field
accuracy, certification, or a guarantee of safe autonomous operation.

## Infrastructure defect detection

| Field | Value |
|---|---|
| Registry key | `infrastructure_detection` |
| Checkpoint | `damage_detection_yolov8n_baseline` |
| Architecture | YOLOv8n |
| Task | Infrastructure defect object detection |
| Dataset | `damage_detection` (`data/manifests/damage_detection_manifest_v2.json`) |
| Metrics | mAP50 0.440; mAP50-95 0.258; precision 0.448; recall 0.496 |
| Status | READY for demonstration and controlled evaluation |
| Detailed report | [`yolo_baseline_diagnosis.md`](yolo_baseline_diagnosis.md) |

Known limitations include an unverified raw-data source/license, modest recall, and
domain shift between the local corpus and field imagery. Human review remains required.

## Crack segmentation

| Field | Value |
|---|---|
| Registry key | `crack_segmentation` |
| Checkpoint | `crack_segmentation_tinyunet_baseline` |
| Architecture | TinyUNet, 16 base channels |
| Task | Binary semantic segmentation |
| Dataset | `uav_crack_segmentation` (`data/manifests/uav_crack_segmentation_manifest_v2.json`) |
| Metrics | Mean IoU 0.501; mean Dice 0.637; precision 0.807; recall 0.600 |
| Status | READY for demonstration and controlled evaluation |
| Detailed report | [`crack_segmentation_validation.md`](crack_segmentation_validation.md) |

Thin, short, low-contrast cracks are a known weak case. A “no crack” output must not be
interpreted as proof that a structure is defect-free.

## Agriculture classification

| Field | Value |
|---|---|
| Registry key | `agriculture_uav_mobilenetv3_baseline` |
| Architecture | MobileNetV3-Small |
| Task | UAV crop-health classification |
| Dataset | MH-SoyaHealthVision UAV subset (CC BY 4.0) |
| Status | TRAINING / NOT READY until a measured held-out result and checkpoint are recorded |
| Detailed report | [`agriculture_model_selection.md`](agriculture_model_selection.md) |

No agriculture metric is claimed in this repository until training, evaluation, and
checkpoint integrity checks complete.

## Reproduce and verify

```powershell
.venv\Scripts\python.exe scripts\verify_datasets.py
pytest -q
```

Checkpoint paths, hashes, configs, and current status are tracked in
`data/manifests/models.json`. Generated checkpoints are intentionally ignored from Git;
the manifest is the auditable record of the local run.
