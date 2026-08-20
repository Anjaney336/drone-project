# Agriculture dataset audit — MH-SoyaHealthVision

**Status: DOWNLOAD IN PROGRESS. Audit not yet possible.**

Per the accuracy rule for this phase, this dataset is NOT described as "downloaded" until all of
the following are true. Current state against each:

| Requirement | Status |
|---|---|
| Full archive download completed | ✗ NOT MET — partial file, see below |
| Expected size reasonably verified | ✗ NOT MET — cannot verify against a partial file |
| Archive integrity verified | ✗ NOT MET — `zipfile.ZipFile()` raises `BadZipFile` on the partial download (expected) |
| Archive can be opened/extracted | ✗ NOT MET |
| Expected files present | ✗ NOT MET |
| Image/sample counts audited | ✗ NOT MET |
| UAV split and leaf-image split identified | ✗ NOT MET (folder structure is only known from the source page description, not verified locally) |
| License/provenance metadata stored | **partially met** — recorded below from the verified source page, not yet re-confirmed against extracted files |

## What is verified (from the source page, not yet from local files)

- Source: Mendeley Data, DOI `10.17632/hkbgh5s3b7.1`, published 18 Dec 2024, contributors Sayali
  Shinde and Dr. Vahida Attar (COEP Technological University Pune; IDEAS Technology Innovation
  Hub, Indian Statistical Institute Kolkata).
- License: **CC BY 4.0** (attribution required).
- Claimed size: 9.75 GB. Claimed content: 5,680 images total — a leaf-image split (6 folders:
  healthy + 4 disease types + pest attack) and a UAV/aerial split (4 folders: healthy + 2 disease
  types + pest attack).
- Download URL: `https://data.mendeley.com/public-api/zip/hkbgh5s3b7/download/1` (direct,
  scriptable, no authentication observed).

## Current download state (last checked 2026-08-20 22:40 IST)

```
5,281,894,400 / 9,750,000,000 bytes ≈ 54.2%
```

Still `DOWNLOAD IN PROGRESS`. The transfer is resumable (`curl -C -`) and has run continuously in
the background since it was restarted (see below); rate has varied roughly 250 KB/s–1 MB/s. It was
restarted once early in this work after an earlier `--max-time` cap would have killed it
mid-transfer; the resume worked correctly (verified by the file size continuing to grow from the
pre-restart byte count rather than resetting to zero). Per the accuracy rule for this dataset, it
has **not** been marked downloaded, audited, or integrated into any pipeline, and no agriculture
model has been selected or trained.

## What happens next, once complete

This document will be replaced with the real audit once the archive opens successfully:
per-split image counts, class distribution for both the leaf and UAV splits, image dimensions,
duplicate/near-duplicate check, and a task-suitability decision. Per the phase instructions, the
UAV/aerial split will be prioritized over the leaf-closeup split for the AERIS MVP because it
aligns with the drone-mission platform; the two splits will not be merged into one classifier
without a technically justified reason, consistent with `docs/model_selection.md`'s
no-shared-multi-domain-model decision for the infrastructure datasets. **No training will start
on this dataset until that real audit exists.**
