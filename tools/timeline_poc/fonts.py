"""Read installed fonts when Windows offscreen QPA has no font database.

No font files are copied/bundled, and the shared QApplication font is not changed.
"""

import os
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase


def timeline_font():
    families = QFontDatabase.families()
    if not families and os.name == "nt":
        directory = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for name in ("malgun.ttf", "segoeui.ttf"):
            path = directory / name
            if path.is_file():
                QFontDatabase.addApplicationFont(str(path))
        families = QFontDatabase.families()
    for preferred in ("Malgun Gothic", "맑은 고딕", "Noto Sans CJK KR", "Segoe UI", "DejaVu Sans"):
        if preferred in families:
            return QFont(preferred, 9)
    return QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
