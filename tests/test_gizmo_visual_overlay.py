"""Editor paint must not occlude sprite interiors or mutate exported RGBA."""
from types import SimpleNamespace
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from copy import deepcopy
import numpy as np
from PIL import Image
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage, QColor, QPainter
from PySide6.QtWidgets import QApplication
from app.ui.canvas_widget import CanvasWidget
from app.models.project import Project
from app.models.effect_resource_layer import EffectLayerTransform3D
from app.models.particle_emitter import ParticleEmitterSettings
from app.services.export_service import export_png_frames

APP = QApplication.instance() or QApplication([])


def test_resource_scale_frame_is_unfilled_hitbox_unchanged_and_export_identical(tmp_path, monkeypatch):
    project = Project.create_default(); project.frames = project.frames[:1]
    project.frames[0].layer_pixels[project.layers[0].id][:] = (11, 22, 33, 255)
    before = deepcopy(project.to_dict())
    expected = project.compose_frame(0).copy()
    canvas = CanvasWidget(); canvas.project = project
    canvas.set_resource_layer_transform("synthetic", EffectLayerTransform3D(), mode="scale")
    monkeypatch.setattr(canvas, "resource_transform_handle_positions", lambda: {"center": QPointF(100,100), "scale": QPointF(138,138)})
    image = QImage(220,220,QImage.Format.Format_RGBA8888); image.fill(QColor(121,83,47))
    painter = QPainter(image); painter.setBrush(QColor("#20242b"))  # Previously leaked from guide painting.
    original_brush = painter.brush()
    canvas._paint_resource_transform_gizmo(painter)
    assert painter.brush() == original_brush
    painter.end()
    assert image.pixelColor(100,100) == QColor(121,83,47)
    assert image.pixelColor(110,110) == QColor(121,83,47)
    assert canvas._hit_resource_transform(QPointF(148,138)) == "scale"  # Outside the smaller visual handle.
    canvas.set_effect_guides_visible(False)
    assert canvas._hit_resource_transform(QPointF(138,138)) is None
    assert project.to_dict() == before and np.array_equal(expected, project.compose_frame(0))
    png = export_png_frames(project, tmp_path / "png")[0]
    assert np.array_equal(np.asarray(Image.open(png).convert("RGBA")), expected)
    canvas.close()


def test_legacy_scale_and_particle_box_leave_their_interiors_clear(monkeypatch):
    canvas = CanvasWidget()
    monkeypatch.setattr(canvas, "_gizmo_center", lambda: (0,0))
    monkeypatch.setattr(canvas, "canvas_to_widget", lambda x,y: QPointF(100,100))
    canvas.gizmo_settings=SimpleNamespace(scale_x_start=1,scale_x_end=1,scale_y_start=1,scale_y_end=1)
    canvas.gizmo_mode="scale"
    for method in ("_paint_gizmo", "_paint_effect_guide"):
        if method == "_paint_effect_guide":
            canvas.effect_guide_settings = ParticleEmitterSettings(clip_asset_id="synthetic",spawn_shape="box",box_width=40,box_height=40)
            monkeypatch.setattr(canvas,"_guide_points",lambda:{"origin":QPointF(100,100),"endpoint":QPointF(150,100),"direction":QPointF(150,100)})
        image=QImage(220,220,QImage.Format.Format_RGBA8888);image.fill(QColor(101,72,43))
        painter=QPainter(image);painter.setBrush(QColor("#20242b"));brush=painter.brush()
        getattr(canvas,method)(painter)
        assert painter.brush()==brush
        painter.end()
        assert image.pixelColor(110,110)==QColor(101,72,43)
    canvas.close()
