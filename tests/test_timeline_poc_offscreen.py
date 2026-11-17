"""POC Qt checks run in fresh processes, never sharing production QApplication."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    output = tmp_path_factory.mktemp("timeline-poc")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run([sys.executable, "-m", "tools.timeline_poc", "--verify", "--output", str(output)],
        cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-1000:]
    data = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert data["status"] == "PASS"
    return output, data


@pytest.mark.parametrize("scale", [1, 1.25, 1.5])
def test_fresh_dpr_qtest_and_completion_cleanup(report, scale):
    output, data = report
    probe = next(p for p in data["probes"] if p["requested_scale"] == scale)
    assert probe["dpr"] == pytest.approx(scale)
    assert len(probe["checks"]) == 3 and all(c["status"] == "PASS" for c in probe["checks"])
    qt_input = next(c for c in probe["checks"] if c["id"] == "qt_input")
    assert qt_input["observed"]["zoom_anchor_error_dip"] <= 0.500001
    assert probe["application_top_level_widgets_after_cleanup"] == 0
    assert probe["environment"]["qt_platform"] == "offscreen"


@pytest.mark.parametrize("scale", [1, 1.25, 1.5])
def test_font_language_palette_screenshots_and_geometry(report, scale):
    output, data = report
    probe = next(p for p in data["probes"] if p["requested_scale"] == scale)
    assert len(probe["screenshots"]) == 12
    for item in probe["screenshots"]:
        image = output / f"scale-{round(scale * 100)}" / item["file"]
        assert image.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
        assert item["resolved_font"]
        assert item["physical_width"] > 0 and item["row_height_dip"] >= 28
    assert {i["font_scale"] for i in probe["screenshots"]} == {1, 1.25, 1.5}
    assert {i["language"] for i in probe["screenshots"]} == {"en", "ko"}
    assert {i["theme"] for i in probe["screenshots"]} == {"light", "dark"}


@pytest.mark.parametrize("frames", [12, 120, 1000, 10000])
def test_viewport_cost_is_bounded_by_visible_rows_and_frames(report, frames):
    _, data = report
    for probe in data["probes"]:
        for item in (m for m in probe["metrics"] if m["frames"] == frames):
            stats = item["paint"]
            assert item["qwidget_descendants"] < 12
            assert item["qtable_descendants"] == 0
            assert item["hit_test_queries"] == sum(item["hit_target_counts"].values()) == 1000
            assert stats["frame_headers"] <= 24
            assert stats["row_headers"] <= 14
            assert stats["keys_drawn"] <= stats["frame_headers"] * stats["row_headers"]
            assert stats["per_cell_objects"] == stats["raster_cache_bytes"] == 0
            assert item["grab_median_ms"] >= 0


def test_verify_cli_refuses_existing_output_without_modifying_it(tmp_path):
    sentinel = tmp_path / "keep.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    result = subprocess.run([sys.executable, "-m", "tools.timeline_poc", "--verify", "--output", str(tmp_path)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=10)
    assert result.returncode == 2 and sentinel.read_text(encoding="utf-8") == "preserve"


def test_invalid_synthetic_counts_fail_before_native_window():
    result = subprocess.run([sys.executable, "-m", "tools.timeline_poc", "--frames", "0"],
        cwd=Path(__file__).resolve().parents[1], env=dict(os.environ, QT_QPA_PLATFORM="offscreen"),
        capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
