from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def classify(relative: str) -> tuple[str, str, str, str, str]:
    lower = relative.lower()
    if any(token in lower for token in ("__pycache__", ".pytest_cache", ".ruff_cache")):
        return "tool cache", "generated artifact", "no", "yes", "none"
    if lower.startswith(".legacy_backup/"):
        return (
            "pre-rebuild asset",
            "quarantined legacy",
            "no",
            "review before deletion",
            "active AERIS tree",
        )
    if lower.startswith("data/raw/visdrone"):
        return "public perception benchmark", "dataset", "manifest only", "no", "data/raw/visdrone"
    if lower.endswith((".mp4", ".csv", ".png", ".jpg", ".pt")):
        return (
            "data/model/media asset",
            "artifact or dataset",
            "unknown",
            "manifest dependent",
            "data layout or artifacts",
        )
    if lower.startswith("src/aeris"):
        return "AERIS runtime module", "production prototype code", "yes", "no", "self"
    if lower.startswith("tests/"):
        return "AERIS validation", "test", "pytest", "no", "self"
    if lower.startswith("docs/") or lower.endswith(".md"):
        return "project documentation", "documentation", "human", "no", "self"
    return "support/configuration", "configuration or support", "possible", "review", "self"


def main() -> None:
    output = ROOT / "artifacts" / "repository_audit.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    excluded = {".git", ".venv"}
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "file",
                "purpose",
                "classification",
                "referenced_by_active_code",
                "safe_to_delete",
                "replacement",
            ]
        )
        for path in sorted(ROOT.rglob("*")):
            relative = path.relative_to(ROOT).as_posix()
            if path.is_dir() or any(part in excluded for part in path.parts):
                continue
            writer.writerow([relative, *classify(relative)])
    print(output)


if __name__ == "__main__":
    main()
