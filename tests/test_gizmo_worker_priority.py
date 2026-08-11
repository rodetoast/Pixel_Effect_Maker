import os
from threading import Event

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.services.effect_playback_service import EffectPlaybackManager
from app.services.interactive_gizmo_service import InteractiveGizmoRenderManager


APP = QApplication.instance() or QApplication([])


class RecordingPool:
    def __init__(self):
        self.calls = []

    def start(self, worker, priority=0):
        self.calls.append((worker, priority))


def test_interactive_current_frame_worker_uses_higher_priority_than_background_work():
    manager = InteractiveGizmoRenderManager(delay_ms=33)
    pool = RecordingPool()
    manager._pool = pool
    project = Project.create_default(width=8, height=8, fps=12, frame_count=1)
    manager.schedule(project, object(), 0, immediate=True)
    assert pool.calls[0][1] == 1
    manager.close()


def test_playback_invalidation_cooperatively_stops_remaining_frames(monkeypatch):
    project = Project.create_default(width=8, height=8, fps=12, frame_count=8)
    entered, release = Event(), Event()
    calls = []

    def slow_frame(_project, index, *_args):
        calls.append(index)
        entered.set()
        release.wait(2)
        return np.zeros((8, 8, 4), dtype=np.uint8), {}

    monkeypatch.setattr("app.services.effect_playback_service.render_exact_playback_frame", slow_frame)
    manager = EffectPlaybackManager()
    manager.prepare(project, 1)
    assert entered.wait(2)
    manager.invalidate()
    release.set()
    elapsed = 0
    while elapsed < 2000 and manager.collector.cancelled_workers == 0:
        APP.processEvents()
        QTest.qWait(10)
        elapsed += 10
    assert len(calls) < len(project.frames)
    assert manager.collector.cancelled_workers == 1
    assert manager.collector.cancelled_frames > 0
    manager.close()
