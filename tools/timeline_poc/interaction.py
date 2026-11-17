"""Pure pointer state machine. Drag selects/scrubs/pans; never moves data."""

from copy import deepcopy
from dataclasses import dataclass

from .geometry import HitTarget
from .selection import CellRange, FrameIntervals, TimelineSelection


@dataclass
class TimelineInteraction:
    selection: TimelineSelection
    mode: str = "idle"
    start: tuple[float, float] = (0, 0)
    start_frame: int = 0
    origin_scroll: tuple[float, float] = (0, 0)
    before: object = None
    ctrl: bool = False
    start_row: int = 0

    def press(self, hit: HitTarget, x, y, *, button="left", shift=False, ctrl=False, scroll=(0, 0)):
        self.cancel()
        self.before = deepcopy(self.selection)
        self.start = (x, y)
        self.ctrl = ctrl
        self.origin_scroll = scroll
        if button == "middle":
            self.mode = "pan"
        elif button == "left" and hit.kind == "ruler":
            self.mode = "scrub"
            self.selection.playhead = hit.frame
        elif button == "left" and hit.kind == "cell_range":
            self.mode = "pressed_cells"
            self.start_frame, self.start_row = hit.frame, hit.row
            self.selection.cells = CellRange(hit.frame, hit.row, hit.frame, hit.row)
            self.selection.active_domain = "cells"
        elif button == "left" and hit.kind in {"frame", "cell"}:
            self.mode = "pressed_frames"
            self.start_frame = self.selection.anchor if shift and self.selection.anchor is not None else hit.frame
            self.selection.select_frame(hit.frame, shift=shift, ctrl=ctrl)
        elif button == "left" and hit.kind == "key":
            self.selection.select_key(hit.row, hit.frame, ctrl=ctrl)
            self.mode = "key_click_only"
        elif button == "left" and hit.kind == "layer":
            self.selection.select_layer(hit.row, ctrl=ctrl)
            self.mode = "layer_click_only"
        else:
            self.mode = "idle"
            self.before = None

    def move(self, x, y, geometry, threshold):
        distance = abs(x - self.start[0]) + abs(y - self.start[1])
        if self.mode == "pan":
            return (self.origin_scroll[0] - x + self.start[0],
                    self.origin_scroll[1] - y + self.start[1])
        if self.mode == "scrub":
            self.selection.playhead = geometry.frame_at(x, clamp=True)
        elif self.mode == "drag_frames" or self.mode == "pressed_frames" and distance >= threshold:
            self.mode = "drag_frames"
            frame = geometry.frame_at(x, clamp=True)
            values = FrameIntervals(((min(self.start_frame, frame), max(self.start_frame, frame) + 1),))
            self.selection.frames = self.before.frames | values if self.ctrl else values
            self.selection.primary, self.selection.anchor = frame, self.start_frame
        elif self.mode == "drag_cells" or self.mode == "pressed_cells" and distance >= threshold:
            self.mode = "drag_cells"
            self.selection.cells = CellRange(self.start_frame, self.start_row,
                geometry.frame_at(x, clamp=True), geometry.row_at(y, clamp=True))
        return None

    def finish(self):
        self.mode, self.before = "idle", None

    def cancel(self):
        if self.before is not None:
            self.selection.__dict__.update(deepcopy(self.before.__dict__))
        self.finish()

    def key(self, name, frame_count, *, shift=False):
        if name == "escape":
            self.cancel()
            return True
        if name not in {"left", "right", "home", "end"}:
            return False
        if self.mode != "idle":
            self.cancel()
        current = self.selection.primary if shift and self.selection.primary is not None else self.selection.playhead
        target = {"home": 0, "end": frame_count - 1,
                  "left": current - 1, "right": current + 1}[name]
        target = max(0, min(frame_count - 1, target))
        if shift:
            if self.selection.anchor is None:
                self.selection.anchor = current
            self.selection.select_frame(target, shift=True)
        else:
            self.selection.seek(target, frame_count)
        return True
