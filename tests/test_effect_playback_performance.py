import os

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.models.project import Project
from app.services.settings_service import ShortcutSettingsService
from app.ui.main_window import MainWindow


APP=QApplication.instance() or QApplication([])


class FakeClock:
    def __init__(self):self.ms=0
    def start(self):self.ms=0
    def elapsed(self):return self.ms


def make_window(tmp_path,frames=12):
    project=Project.create_default(width=16,height=16,fps=12,frame_count=frames)
    return MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"clock.ini"),QSettings.Format.IniFormat)),project)


def finish(value):
    value.set_playing(False);value.dirty=False;value._non_undo_dirty=False;value.close();APP.processEvents()


def test_playback_timer_uses_elapsed_time_and_late_tick_skips_frames(tmp_path):
    value=make_window(tmp_path);clock=FakeClock();value._playback_clock=clock;value.set_playing(True)
    clock.ms=260;value._advance_playback(False)
    assert value.frame_index==3
    clock.ms=510;value._advance_playback(False)
    assert value.frame_index==6
    finish(value)


def test_playback_clock_does_not_advance_again_without_elapsed_frame(tmp_path):
    value=make_window(tmp_path);clock=FakeClock();value._playback_clock=clock;value.set_playing(True)
    clock.ms=170;value._advance_playback(False);first=value.frame_index
    clock.ms=180;value._advance_playback(False)
    assert first==2 and value.frame_index==2
    finish(value)


def test_non_loop_elapsed_time_stops_at_last_frame(tmp_path):
    value=make_window(tmp_path,5);value.project.loop=False;clock=FakeClock();value._playback_clock=clock;value.set_playing(True)
    clock.ms=1000;value._advance_playback(False)
    assert value.frame_index==4 and not value.play_timer.isActive()
    finish(value)


def test_playback_tick_updates_only_frame_ui_not_effect_inspector(tmp_path,monkeypatch):
    value=make_window(tmp_path);clock=FakeClock();value._playback_clock=clock;calls=[]
    monkeypatch.setattr(value,"_refresh_effect_panels",lambda:calls.append("panel"));value.set_playing(True)
    clock.ms=90;value._advance_playback(False)
    assert value.frame_index==1 and calls==[]
    finish(value)


def test_playback_start_does_not_materialize_project_sequences(tmp_path,monkeypatch):
    value=make_window(tmp_path);calls=[];monkeypatch.setattr(value,"_materialize_resource_transform_sequences",lambda:calls.append("materialize"))
    value.set_playing(True)
    assert calls==[]
    finish(value)


def test_playback_paint_skips_editing_guides_and_gizmos(tmp_path,monkeypatch):
    from PySide6.QtGui import QImage,QPixmap
    value=make_window(tmp_path);calls=[]
    value.canvas.effect_guide_id="guide";value.canvas.effect_guide_settings=object()
    value.canvas.resource_transform_id="resource";value.canvas.resource_transform=object()
    monkeypatch.setattr(value.canvas,"_paint_effect_guide",lambda painter:calls.append("guide"))
    monkeypatch.setattr(value.canvas,"_paint_resource_transform_gizmo",lambda painter:calls.append("gizmo"))
    pixmap=QPixmap.fromImage(QImage(16,16,QImage.Format.Format_RGBA8888));value.canvas.set_playback_frame(pixmap,0);value.canvas.begin_playback()
    target=QImage(value.canvas.size(),QImage.Format.Format_RGBA8888);value.canvas.render(target)
    assert calls==[]
    finish(value)
