"""Real event-loop/timer regressions, isolated from production QApplication."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    output = tmp_path_factory.mktemp("poc15-navigation")
    result = subprocess.run([sys.executable, "-m", "tools.timeline_poc", "--verify", "--output", str(output)],
        cwd=Path(__file__).resolve().parents[1], env=dict(os.environ, QT_QPA_PLATFORM="offscreen"),
        capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-1000:]
    data = json.loads((output / "report.json").read_text(encoding="utf-8"))
    assert data["status"] == "PASS" and len(data["probes"]) == 3
    return data


@pytest.mark.parametrize("name", [
    "wheel_zoom_resize", "bounds_edge_exit", "shell_tooltip", "large_selection", "pan_scrub_exclusion", "playhead_handle",
    "edge_right_frames", "edge_left_frames", "edge_right_cells", "edge_left_cells",
    "edge_down_cells", "edge_up_cells", "edge_right_down_cells", "edge_left_up_cells",
    "stop_escape", "stop_focus", "stop_capture", "stop_hide", "stop_close", "edge_zoom_8", "edge_zoom_160",
])
def test_navigation_regression_across_actual_dpr_processes(report, name):
    for probe in report["probes"]:
        assert probe["status"] == probe["navigation"]["status"] == "PASS"
        check = next(c for c in probe["navigation"]["checks"] if c["id"] == name)
        assert check["status"] == "PASS"
        observed = check["observed"]
        if name.startswith("edge_"):
            assert observed["stationary_ticks"] >= 3
            assert observed["tick_median_ms"] >= 0
        if name == "large_selection":
            assert observed["logical_cells"] == 2_000_000
            assert observed["frame_intervals"] == 1 and observed["cell_range_fields"] == 4
            assert observed["qwidget_descendants"] == 5
            assert observed["visible_paint"]["frame_headers"] < 25
        if name == "wheel_zoom_resize":
            assert observed["roundtrip50_error_dip"] < 1e-7
        assert probe["application_top_level_widgets_after_navigation"] == 0


def test_auto_scroll_is_not_simulated_by_direct_callback_calls():
    source = (Path(__file__).resolve().parents[1] / "tools/timeline_poc/navigation_probe.py").read_text(encoding="utf-8")
    assert "._auto_tick(" not in source
    assert "registeredTimers(view.auto_timer)" in source
