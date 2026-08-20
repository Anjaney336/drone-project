# Code quality

## Before → after (this session)

| | Before | After |
|---|---:|---:|
| `ruff check .` (full repo) | 107 errors | **0 errors** |

## Breakdown of the 107 original issues

All 107 were in this session's own newly-written source (training pipelines, API endpoints, audit
scripts) — none were pre-existing debt in code from earlier sessions, and none were in generated or
third-party files.

| Category | Count (approx.) | Classification |
|---|---:|---|
| `E501` line too long | ~95 | (A) Automatically fixable via `ruff format`, or (B) manual reflow for long string literals the formatter won't safely rewrap |
| `I001` unsorted imports | 2 | (A) Automatically fixable via `ruff check --fix` |
| `F401` unused import | 1 | (A) Automatically fixable |
| `F841` unused local variable | 1 | (B) Manual — removed the unused `results =` assignment in `train.py` |
| `B905` `zip()` without `strict=` | 2 | (A) Auto-fixable via `--unsafe-fixes` (adds explicit `strict=False`, preserving existing truncating behavior) |

## What was NOT done

- No directory was excluded from linting.
- No rule was disabled in `pyproject.toml`'s `[tool.ruff.lint]` config.
- No blanket `# noqa` was added anywhere.
- No line-length limit was raised to make violations disappear — every long line was actually
  reflowed or shortened.

## Verification

```powershell
ruff check .
# All checks passed!
```
