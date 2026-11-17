"""Viewport-only timeline painting. No per-cell objects or persistent image cache."""

from dataclasses import dataclass
from .geometry import ruler_steps

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPen, QPolygonF


LABELS = {
    "en": {"title": "PIXEL EFFECT MAKER · TIMELINE LAB", "layer": "Layer / Track",
           "ruler": "Scrub", "frames": "Frames", "help": "Frame drag: select · Ruler: scrub · Ctrl-wheel: zoom · MMB: pan",
           "selection": "Selected", "playhead": "Playhead", "synthetic": "SYNTHETIC ONLY · No document editing",
           "frame_mode": "Frame range", "cell_mode": "Cell range", "fit": "Fit", "reset": "Reset", "zoom": "Zoom"},
    "ko": {"title": "PIXEL EFFECT MAKER · 타임라인 실험", "layer": "레이어 / 트랙",
           "ruler": "탐색", "frames": "프레임", "help": "프레임 드래그: 범위 선택 · 눈금: 탐색 · Ctrl-휠: 확대 · 가운데 버튼: 이동",
           "selection": "선택", "playhead": "재생 헤드", "synthetic": "합성 데이터 전용 · 문서 편집 없음",
           "frame_mode": "프레임 범위", "cell_mode": "셀 범위", "fit": "맞춤", "reset": "기본", "zoom": "확대"},
}


@dataclass(frozen=True)
class TimelinePalette:
    background: str
    panel: str
    alternate: str
    grid: str
    text: str
    muted: str
    selection: str
    selection_edge: str
    key: str
    playhead: str

    @classmethod
    def for_theme(cls, theme):
        if theme == "light":
            return cls("#fafcff", "#eaf0f7", "#f0f4f9", "#d2dce8", "#15283e",
                       "#52647b", "#d4e6fb", "#275d92", "#1c625c", "#8c4900")
        if theme != "dark":
            raise ValueError("theme must be light or dark")
        return cls("#19212d", "#222e3e", "#1d2735", "#344459", "#edf3fb",
                   "#afbed1", "#2b4d70", "#94c9ff", "#8fd9c9", "#ffd166")


class TimelinePaint:
    def draw(self, painter, geometry, adapter, selection, palette, language, focused=False):
        g, p = geometry, palette
        labels = LABELS[language]
        frames, rows = g.visible_frames(), g.visible_rows()
        fm = painter.fontMetrics()
        stride, major = ruler_steps(fm.horizontalAdvance(str(g.frame_count)) + 12, g.frame_width)
        stats = {"visible_frame_start": frames.start, "visible_frame_stop": frames.stop,
                 "visible_row_start": rows.start, "visible_row_stop": rows.stop,
                 "frame_headers": 0, "row_headers": 0, "key_queries": 0,
                 "keys_drawn": 0, "grid_lines": 0, "per_cell_objects": 0,
                 "raster_cache_bytes": 0, "label_stride": stride, "major_stride": major,
                 "cell_range_rects": 0, "frame_labels_drawn": 0}
        painter.fillRect(QRectF(0, 0, g.width, g.height), QColor(p.background))
        painter.save()
        painter.setClipRect(QRectF(g.header_width, g.body_top, g.body_width, g.body_height))
        for row in rows:
            if row % 2:
                painter.fillRect(QRectF(g.header_width, g.row_y(row, False), g.body_width, g.row_height), QColor(p.alternate))
        for frame in frames:
            if frame in selection.frames:
                painter.fillRect(QRectF(g.frame_x(frame, False), g.body_top, g.frame_width, g.body_height), QColor(p.selection))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(p.selection_edge), 1.5, Qt.PenStyle.DashLine))
        for a, b in selection.frames.intervals:
            if b > frames.start and a < frames.stop:
                painter.drawRect(QRectF(g.frame_x(a, False), g.body_top,
                                       (b - a) * g.frame_width, g.body_height - 1))
        if selection.cells is not None:
            a, b, c, d = selection.cells.bounds
            x1, x2 = max(g.header_width, g.frame_x(a, False)), min(g.width, g.frame_x(b, False))
            y1, y2 = max(g.body_top, g.row_y(c, False)), min(g.height, g.row_y(d, False))
            if x2 > x1 and y2 > y1:
                tint = QColor(p.selection_edge)
                tint.setAlpha(45)
                painter.fillRect(QRectF(x1, y1, x2 - x1, y2 - y1), tint)
                painter.setPen(QPen(QColor(p.selection_edge), 2, Qt.PenStyle.DashLine))
                painter.drawRect(QRectF(x1 + 1, y1 + 1, x2 - x1 - 2, y2 - y1 - 2))
                # Endpoint corner squares differ from the solid playhead handle.
                painter.setBrush(QColor(p.selection_edge))
                for f, r in ((selection.cells.anchor_frame, selection.cells.anchor_row),
                             (selection.cells.active_frame, selection.cells.active_row)):
                    painter.drawRect(QRectF(g.frame_x(f) - 3, g.row_y(r) - 3, 6, 6))
                stats["cell_range_rects"] = 1
        painter.setPen(QPen(QColor(p.grid), 1))
        for frame in range(frames.start, frames.stop + 1) if frames else ():
            x = g.frame_x(frame, False)
            painter.setPen(QPen(QColor(p.grid), 1.5 if frame % major == 0 else 0.7))
            painter.drawLine(QPointF(x, g.body_top), QPointF(x, g.height))
            stats["grid_lines"] += 1
        for row in range(rows.start, rows.stop + 1) if rows else ():
            y = g.row_y(row, False)
            painter.drawLine(QPointF(g.header_width, y), QPointF(g.width, y))
            stats["grid_lines"] += 1
        for row in rows:
            keys = adapter.keys_in(row, frames.start, frames.stop)
            stats["key_queries"] += 1
            for frame in keys:
                x, y = g.frame_x(frame), g.row_y(row)
                selected = (row, frame) in selection.keys
                painter.setPen(QPen(QColor(p.text if selected else p.key), 2 if selected else 1))
                painter.setBrush(QColor(p.selection_edge if selected else p.key))
                radius = 5
                painter.drawPolygon(QPolygonF([QPointF(x, y - radius), QPointF(x + radius, y),
                                                QPointF(x, y + radius), QPointF(x - radius, y)]))
                if selected:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(QRectF(x - 8, y - 8, 16, 16))
                stats["keys_drawn"] += 1
        painter.restore()

        painter.fillRect(QRectF(0, 0, g.width, g.body_top), QColor(p.panel))
        painter.fillRect(QRectF(0, g.body_top, g.header_width, g.body_height), QColor(p.panel))
        painter.save()
        painter.setClipRect(QRectF(g.header_width, 0, g.body_width, g.body_top))
        for frame in frames:
            x = g.frame_x(frame, False)
            rect = QRectF(x, g.ruler_height, g.frame_width, g.frame_header_height)
            selected = frame in selection.frames
            if selected:
                painter.fillRect(rect, QColor(p.selection))
                painter.setPen(QPen(QColor(p.selection_edge), 1))
                painter.drawRect(rect.adjusted(1, 1, -1, -1))
            if frame % stride == 0 and rect.left() >= g.header_width and rect.right() <= g.width:
                painter.setPen(QColor(p.text))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(frame + 1))
                stats["frame_labels_drawn"] += 1
            major_label = f"{frame + 1}f"
            if frame % major == 0 and x + 4 >= g.header_width and x + 4 + fm.horizontalAdvance(major_label) <= g.width:
                painter.setPen(QColor(p.muted))
                painter.drawText(QRectF(x + 4, 0, major * g.frame_width, g.ruler_height),
                                 Qt.AlignmentFlag.AlignVCenter, major_label)
            painter.setPen(QPen(QColor(p.muted), 1))
            tick = 7 if frame % major == 0 else 3
            painter.drawLine(QPointF(g.frame_x(frame), g.ruler_height - tick),
                             QPointF(g.frame_x(frame), g.ruler_height))
            stats["frame_headers"] += 1
        painter.restore()

        painter.save()
        painter.setClipRect(QRectF(0, g.body_top, g.header_width, g.body_height))
        for row in rows:
            rect = QRectF(0, g.row_y(row, False), g.header_width, g.row_height)
            if row in selection.layers:
                painter.fillRect(rect, QColor(p.selection))
                painter.fillRect(QRectF(0, rect.top(), 3, rect.height()), QColor(p.selection_edge))
            painter.setPen(QColor(p.text))
            text = fm.elidedText(adapter.row_label(row, language), Qt.TextElideMode.ElideRight,
                                 max(0, int(g.header_width - 24)))
            painter.drawText(rect.adjusted(12, 0, -12, 0), Qt.AlignmentFlag.AlignVCenter, text)
            painter.setPen(QColor(p.grid))
            painter.drawLine(QPointF(0, rect.bottom()), QPointF(g.header_width, rect.bottom()))
            stats["row_headers"] += 1
        painter.restore()
        painter.setPen(QColor(p.muted))
        painter.drawText(QRectF(10, 0, g.header_width - 20, g.ruler_height),
                         Qt.AlignmentFlag.AlignVCenter, labels["ruler"])
        painter.setPen(QColor(p.text))
        painter.drawText(QRectF(10, g.ruler_height, g.header_width - 20, g.frame_header_height),
                         Qt.AlignmentFlag.AlignVCenter, labels["layer"])
        painter.setPen(QPen(QColor(p.grid), 1))
        painter.drawLine(QPointF(g.header_width, 0), QPointF(g.header_width, g.height))
        painter.drawLine(QPointF(0, g.body_top), QPointF(g.width, g.body_top))

        painter.save()
        painter.setClipRect(QRectF(g.header_width, 0, g.body_width, g.height))
        x = g.frame_x(selection.playhead)
        painter.setPen(QPen(QColor(p.playhead), 2))
        painter.drawLine(QPointF(x, 13), QPointF(x, g.height))
        painter.setBrush(QColor(p.playhead))
        painter.drawPolygon(QPolygonF([QPointF(x - 6, 2), QPointF(x + 6, 2), QPointF(x + 6, 9),
                                       QPointF(x, 15), QPointF(x - 6, 9)]))
        painter.restore()
        # Continuation markers describe selected ranges beyond the visible body.
        extents = [(a, b, 0, g.row_count) for a, b in selection.frames.intervals]
        if selection.cells is not None:
            extents.append(selection.cells.bounds)
        painter.save()
        painter.setClipRect(QRectF(g.header_width, g.body_top, g.body_width, g.body_height))
        painter.setPen(QPen(QColor(p.selection_edge), 2))
        for a, b, c, d in extents:
            if a >= frames.stop or b <= frames.start or c >= rows.stop or d <= rows.start:
                continue
            y = min(g.height - 10, g.body_top + 12)
            if g.frame_x(a, False) < g.header_width:
                painter.drawText(QPointF(g.header_width + 4, y), "◀")
            if g.frame_x(b, False) > g.width:
                painter.drawText(QPointF(g.width - 18, y), "▶")
            if selection.cells is not None and (a, b, c, d) == selection.cells.bounds:
                if g.row_y(c, False) < g.body_top:
                    painter.drawText(QPointF(g.header_width + 20, g.body_top + 14), "▲")
                if g.row_y(d, False) > g.height:
                    painter.drawText(QPointF(g.header_width + 20, g.height - 5), "▼")
        painter.restore()
        if focused:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(p.selection_edge), 1, Qt.PenStyle.DotLine))
            painter.drawRect(QRectF(1, 1, g.width - 2, g.height - 2))
        return stats
