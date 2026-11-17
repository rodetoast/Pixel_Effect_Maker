"""Launch an isolated Windows-Qt synthetic Inspector for native visual review.

No user project/artwork/QSettings is loaded or saved. Close the window to exit.
"""
import os
os.environ["QT_QPA_PLATFORM"] = "windows"
import argparse
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from tools.inspector_visual_probe import make_panel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=False)
    app = QApplication([]); QFontDatabase.addApplicationFont("C:/Windows/Fonts/malgun.ttf")
    app.setFont(QFont("Malgun Gothic", 9))
    panel, *_ = make_panel(args.output, "ko", 420, 1.25)
    panel.setWindowTitle("Pixel Effect Maker - Synthetic UX-2 Native QA")
    panel.resize(420, 1000)
    app.exec()


if __name__ == "__main__":main()
