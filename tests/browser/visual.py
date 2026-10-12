"""Screenshot comparison for the visual tests.

A screenshot is compared with its baseline in tests/browser/baselines/. A
pixel differs when any channel moves by more than PIXEL_THRESHOLD; the shot
fails when more than MAX_DIFF_RATIO of its pixels differ. Measured in October
2026: the same machine renders identically every time, and the pinned
Playwright image CI uses differs from it by at most 7 pixels a shot beyond 8
levels, antialiasing at a few edges. So a full-width hairline, a missing
icon, or a color token moved by more than 8 levels fails. On failure the new
shot and a diff (differences in red over a faded baseline) are written to
tests/browser/visual-diffs/, which CI uploads.

    UPDATE_BASELINES=1 pytest tests/browser/test_visual.py   # accept new looks

A missing baseline is written and the test skipped, so a new shot (or a new
app from the template) starts its own; in CI a missing baseline fails.
"""

import io
import os
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BASELINES = HERE / "baselines"
DIFFS = HERE / "visual-diffs"
PIXEL_THRESHOLD = 8
MAX_DIFF_RATIO = 0.0001


def compare(png: bytes, name: str) -> None:
    from PIL import Image, ImageChops

    baseline_path = BASELINES / f"{name}.png"
    if os.environ.get("UPDATE_BASELINES") or not baseline_path.exists():
        missing = not baseline_path.exists()
        BASELINES.mkdir(exist_ok=True)
        baseline_path.write_bytes(png)
        if missing and os.environ.get("CI"):
            pytest.fail(f"no baseline for {name}; run the visual tests locally and commit it")
        if missing:
            pytest.skip(f"wrote a new baseline for {name}; look at it and commit it")
        return

    actual = Image.open(io.BytesIO(png)).convert("RGB")
    baseline = Image.open(baseline_path).convert("RGB")
    if actual.size != baseline.size:
        _write_failure(name, actual, None)
        pytest.fail(f"{name}: size {actual.size} differs from the baseline's {baseline.size}")

    delta = ImageChops.difference(actual, baseline).split()
    worst = ImageChops.lighter(ImageChops.lighter(delta[0], delta[1]), delta[2])
    mask = worst.point(lambda v: 255 if v > PIXEL_THRESHOLD else 0)
    changed = mask.histogram()[255]
    total = actual.size[0] * actual.size[1]
    if changed > total * MAX_DIFF_RATIO:
        _write_failure(name, actual, (baseline, mask))
        pytest.fail(
            f"{name}: {changed} of {total} pixels differ ({changed / total:.3%}); "
            f"see {DIFFS.relative_to(HERE.parent.parent)}/{name}.diff.png"
        )


def _write_failure(name, actual, diff) -> None:
    from PIL import Image

    DIFFS.mkdir(exist_ok=True)
    actual.save(DIFFS / f"{name}.actual.png")
    if diff:
        baseline, mask = diff
        faded = Image.blend(baseline, Image.new("RGB", baseline.size, "white"), 0.7)
        faded.paste(Image.new("RGB", baseline.size, (230, 0, 0)), mask=mask)
        faded.save(DIFFS / f"{name}.diff.png")
