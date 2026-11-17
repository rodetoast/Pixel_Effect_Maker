"""Run with python -m tools.timeline_poc; --verify never opens a native window."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def parser():
    result = argparse.ArgumentParser(description="Synthetic Timeline POC (no project loading)")
    result.add_argument("--verify", action="store_true", help="offscreen checks, fresh DPR subprocesses, JSON/PNG")
    result.add_argument("--probe", action="store_true", help=argparse.SUPPRESS)
    result.add_argument("--output", type=Path, help="new/empty diagnostics output directory")
    result.add_argument("--compare-table", action="store_true", help="bounded synthetic QTableWidget cost baseline")
    result.add_argument("--frames", type=int, default=120)
    result.add_argument("--tracks", type=int, default=24)
    result.add_argument("--language", choices=("en", "ko"), default="ko")
    result.add_argument("--theme", choices=("light", "dark"), default="dark")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.verify or args.probe:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        output = args.output or Path(tempfile.mkdtemp(prefix="pem_timeline_poc_"))
        if output.exists() and any(output.iterdir()):
            parser().error("diagnostics output directory must be new or empty")
        output.mkdir(parents=True, exist_ok=True)
        if args.verify:
            probes = []
            for scale in (1.0, 1.25, 1.5):
                env = dict(os.environ, QT_SCALE_FACTOR=str(scale), QT_FONT_DPI="96",
                           QT_SCALE_FACTOR_ROUNDING_POLICY="PassThrough")
                env.pop("QT_SCREEN_SCALE_FACTORS", None)
                command = [sys.executable, "-m", "tools.timeline_poc", "--probe", "--output",
                           str(output / f"scale-{round(scale * 100)}")]
                if args.compare_table and scale == 1:
                    command.append("--compare-table")
                try:
                    child = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
                    report = json.loads(child.stdout)
                    report["requested_scale"] = scale
                    if child.returncode != 0 or abs(report.get("dpr", 0) - scale) > 0.01:
                        report["status"] = "FAIL"
                except (subprocess.TimeoutExpired, ValueError):
                    report = {"status": "ERROR", "requested_scale": scale, "reason": "probe timeout or invalid JSON"}
                probes.append(report)
            report = {"schema_version": 1, "kind": "timeline-poc-phase1.5", "synthetic_only": True,
                      "production_registry_modified": False,
                      "status": "PASS" if all(p["status"] == "PASS" for p in probes) else "FAIL",
                      "probes": probes}
        else:
            from .diagnostics import run_probe
            report = run_probe(output, compare_table=args.compare_table)
        (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=True))
        return 0 if report["status"] == "PASS" else 1

    from PySide6.QtWidgets import QApplication
    from .adapter import SyntheticTimelineAdapter

    try:
        adapter = SyntheticTimelineAdapter(args.frames, args.tracks)
    except ValueError as error:
        parser().error(str(error))
    app = QApplication.instance() or QApplication([])
    window = create_demo(adapter, args.language, args.theme)
    window.show()
    window.timeline.setFocus()
    return app.exec()


def create_demo(adapter, language_code="ko", theme_code="dark"):
    """Build the same shell for manual use and isolated offscreen QTest."""
    from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget
    from .paint import LABELS
    from .view import TimelineViewport

    window = QWidget()
    window.setWindowTitle("Pixel Effect Maker · Synthetic Timeline POC")
    layout = QVBoxLayout(window)
    title, notice, help_label, status = QLabel(), QLabel(), QLabel(), QLabel()
    title.setStyleSheet("font-weight:600")
    help_label.setWordWrap(True)
    notice.setWordWrap(True)
    row = QHBoxLayout()
    language, theme = QComboBox(), QComboBox()
    window.language_selector, window.theme_selector = language, theme
    language.addItems(["KO", "EN"])
    theme.addItems(["Dark", "Light"])
    language.setAccessibleName("Language / 언어")
    theme.setAccessibleName("Theme / 테마")
    language.setCurrentIndex(0 if language_code == "ko" else 1)
    theme.setCurrentIndex(0 if theme_code == "dark" else 1)
    row.addWidget(title, 1)
    row.addWidget(language)
    row.addWidget(theme)
    layout.addLayout(row)
    layout.addWidget(notice)
    view = TimelineViewport(adapter, language=language_code, theme=theme_code)
    window.timeline = view
    tools = QHBoxLayout()
    mode = QComboBox()
    mode.addItem("Frame range", "frames")
    mode.addItem("Cell range", "cells")
    mode.setAccessibleName("Selection mode / 선택 모드")
    window.selection_mode = mode
    tools.addWidget(mode)
    tools.addStretch()
    zoom_buttons = []
    for text, callback in (("−", lambda: view.zoom_step(-1)), ("+", lambda: view.zoom_step(1)),
                           ("Fit", view.fit_frames), ("Reset", view.reset_zoom)):
        button = QToolButton()
        button.setText(text)
        button.clicked.connect(callback)
        tools.addWidget(button)
        zoom_buttons.append(button)
    window.zoom_controls = zoom_buttons
    layout.addLayout(tools)
    window.setFont(view.font())
    layout.addWidget(view, 1)
    layout.addWidget(help_label)
    layout.addWidget(status)

    def update_status():
        labels = LABELS[view.language]
        status.setText(f'{labels["playhead"]}: {view.selection.playhead + 1} / {adapter.frame_count}  ·  '
                       f'{labels["selection"]}: {len(view.selection.frames)}  ·  '
                       f'{labels["zoom"]}: {view.geometry_state.frame_width / 32:.0%}'
                       + (f"  ·  F{view.selection.cells.bounds[0]+1}–{view.selection.cells.bounds[1]} / "
                          f"T{view.selection.cells.bounds[2]+1}–{view.selection.cells.bounds[3]}"
                          if view.selection.active_domain == "cells" and view.selection.cells else ""))

    def update_labels():
        selected_language = "ko" if language.currentIndex() == 0 else "en"
        selected_theme = "dark" if theme.currentIndex() == 0 else "light"
        view.set_labels(selected_language)
        view.set_theme(selected_theme)
        labels, colors = LABELS[selected_language], view.colors
        title.setText(labels["title"])
        notice.setText(labels["synthetic"])
        help_label.setText(labels["help"])
        mode.setItemText(0, labels["frame_mode"])
        mode.setItemText(1, labels["cell_mode"])
        zoom_buttons[2].setText(labels["fit"])
        zoom_buttons[3].setText(labels["reset"])
        for button in zoom_buttons:
            button.setToolTip(f'{labels["zoom"]} · {button.text()}')
            button.setAccessibleName(button.toolTip())
        zoom_buttons[2].setToolTip(zoom_buttons[2].toolTip() + " · 8–160 DIP/frame")
        mode.setToolTip(labels["cell_mode"] + ": " + ("본체에서만 2차원 범위 선택" if selected_language == "ko"
                                                      else "2D body selection only"))
        if mode.currentData() == "cells":
            help_label.setText("본체 빈 셀 드래그: 2차원 선택 · 가장자리: 자동 스크롤 · Esc: 취소"
                              if selected_language == "ko" else "Drag empty body cells: 2D range · Edge: auto-scroll · Esc: cancel")
        window.setStyleSheet(f"QWidget {{background:{colors.background};color:{colors.text};}}")
        update_status()

    language.currentIndexChanged.connect(update_labels)
    theme.currentIndexChanged.connect(update_labels)
    view.state_changed.connect(update_status)
    def change_mode():
        view.set_body_mode(mode.currentData())
        if mode.currentData() == "cells":
            help_label.setText(("본체 빈 셀 드래그: 2차원 선택 · 가장자리: 자동 스크롤 · Esc: 취소"
                              if view.language == "ko" else "Drag empty body cells: 2D range · Edge: auto-scroll · Esc: cancel"))
        else:
            help_label.setText(LABELS[view.language]["help"])
    mode.currentIndexChanged.connect(change_mode)
    update_labels()
    window.resize(1050, 570)
    return window


if __name__ == "__main__":
    raise SystemExit(main())
