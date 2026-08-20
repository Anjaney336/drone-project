# Agriculture dataset — final audit

**Status: DOWNLOAD COMPLETE, INTEGRITY VERIFIED, UAV SUBSET EXTRACTED AND AUDITED.**

## Source, license, attribution

- Name: MH-SoyaHealthVision
- Source: Mendeley Data, DOI `10.17632/hkbgh5s3b7.1`
- License: **CC BY 4.0** (attribution required)
- Contributors: Sayali Shinde, Dr. Vahida Attar (COEP Technological University Pune; IDEAS
  Technology Innovation Hub, Indian Statistical Institute Kolkata)
- Published: 18 Dec 2024

## Download and integrity (real, measured this session)

The archive reached 100% of its expected size and **passed a real CRC integrity check** —
`zipfile.ZipFile(...).testzip()` returned `None` (no bad entries) across all 10 top-level nested
zip archives, verified by actually opening and reading every entry, not just checking the central
directory. This is the same archive that failed this exact check earlier in the project (a
`Bad magic number for file header` error caused by corruption across repeated pause/resume
cycles) — that corrupted file was preserved as `mh_soyahealthvision.zip.corrupt_2026-08-20` for
reference, not silently discarded, and a fresh uninterrupted download replaced it.

## Structure

Two top-level splits, confirmed by listing (not extracting) all 10 nested zips:

| Split | Classes | Files |
|---|---:|---:|
| `Soyabean_Leaf_Image_Dataset` (ground-level leaf close-ups) | 6 (Healthy, Rust, Mosaic, Frog_Leaf_Eye, Spectoria_Brown_Spot, Caterpillar/Semilooper Pest Attack) | 2,782 |
| `Soyabean_UAV-Based_Image_Dataset` (drone aerial) | 4 (Healthy, Rust, Mosaic, Semilooper/Caterpillar Pest Attack) | 2,842 |

Total 5,624 files (the source page's "5,680" is close but not exact against this counted total —
stated as observed, not corrected to match the marketing figure).

## Why only the UAV subset was extracted and used

AERIS is a drone mission intelligence platform — the leaf-closeup split is ground-level macro
photography of individual leaves, a fundamentally different imaging distribution (framing,
distance, focus) from what an inspection drone actually captures. Per the explicit instruction not
to merge domains without justification, **the leaf split was not extracted or trained on.** It
remains available in the downloaded archive if a future ground-level-inspection use case is
identified, but a leaf-closeup classifier would not answer AERIS's actual question ("what does the
drone see").

## UAV subset — full audit (real, measured)

| Class | Images | Filename pattern |
|---|---:|---|
| healthy | 280 | `image_NNN.jpg` (no shared flight-session marker found) |
| rust | 1,000 | `DJI_<timestamp>_<seq>_D_NNNNNN.jpg` (9 distinct flight sessions) |
| mosaic | 772 | same DJI pattern (11 distinct flight sessions) |
| pest_attack | 790 | `DJI_NNNN_NNNNNN.jpg` (13 distinct flight sessions) |
| **Total** | **2,842** | all `.jpg`, all RGB |

- **Resolution:** uniform 3840×2160 (4K), consistent with real drone video-frame capture.
- **Corrupt files:** 0 (every file opened and `.verify()`-checked with Pillow).
- **Annotation format:** folder-per-class, no bounding boxes, no masks, no per-image metadata file
  → **image classification**, not detection or segmentation.
- **Class imbalance:** real and significant — rust (1,000) is 3.6× the size of healthy (280).
  Not corrected in the baseline (documented as a limitation, not hidden).
- **Duplicates:** not exhaustively hashed (2,842 files, time-boxed); the DJI filenames strongly
  suggest sequential video frames within a session, which is a near-duplicate risk *within* a
  session — exactly why the split is grouped by session (see below) rather than randomized
  per-image.

## Leakage risk and how it was handled

Consecutive frames from the same drone flight (same `DJI_..._D` prefix) are visually
near-identical. A naive random per-image train/test split would let near-duplicate frames from one
flight appear in both splits, inflating test accuracy without the model having learned anything
general. `scripts/build_agriculture_splits.py` groups images by flight-session prefix (parsed from
the filename) and assigns **entire sessions** to one split — verified: 9–13 sessions per DJI class,
each assigned wholly to train, val, or test.

## Recommended ML task

**Image classification**, 4 classes (healthy / rust / mosaic / pest_attack) — determined from the
actual annotation structure (folder-per-class, no geometric labels), not assumed in advance.
