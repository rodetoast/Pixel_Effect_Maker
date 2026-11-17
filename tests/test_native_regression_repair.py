"""User-path regressions: sampled rotation, nested point geometry, selection commands."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from copy import deepcopy
from itertools import combinations
import numpy as np
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QApplication, QWidget, QStyleFactory
from app.models.project import Project
from app.models.source_asset import SourceAsset
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.effect_resource_layer import EffectResourceLayer, PLACEMENT_PARTICLE
from app.services.resource_composition_render_service import render_composition_frame
from app.services.effect_resource_layer_render_service import render_effect_resource_layer_current_frame, render_effect_resource_layer
from tools.inspector_visual_probe import make_panel

APP = QApplication.instance() or QApplication([])

def settle():
    for _ in range(6): APP.processEvents()

def rotation_project(resource_fps=11, effect_fps=11, turns=1, loop=True):
    p = Project.create_default(width=24, height=24, frame_count=121, fps=effect_fps)
    pixels = np.zeros((6, 6, 4), dtype=np.uint8)
    pixels[0:2, 1:5] = (255, 40, 10, 255)
    pixels[2:6, 1:3] = (20, 210, 255, 255)
    a = SourceAsset("asymmetric", pixels, pivot_x=3, pivot_y=3)
    c = ResourceComposition("spin", 24, 24, resource_fps, 61, loop)
    sprite = CompositionLayer("sprite", "source_asset", a.id, 0, 60, pivot_x=3, pivot_y=3)
    track = sprite.add_property("rotation"); track.set_keyframe(0, 0); track.set_keyframe(60, 360*turns)
    c.layers.append(sprite); c.repair_hierarchy(); p.source_assets.append(a); p.resource_compositions.append(c)
    layer = EffectResourceLayer("spin", c.id, placement_mode=PLACEMENT_PARTICLE, end_frame=120)
    s = layer.particle_settings
    s.output_frame_count=121; s.count_min=s.count_max=1; s.lifetime_min=s.lifetime_max=121
    s.origin_x=s.origin_y=12; s.speed_min=s.speed_max=0
    s.scale_min=s.scale_max=1; s.rotation_min=s.rotation_max=0
    s.angular_velocity_min=s.angular_velocity_max=0; s.opacity_start=s.opacity_end=1
    s.clip_speed_min=s.clip_speed_max=1
    p.effect_resource_layers.append(layer); p.repair_effect_hierarchy()
    return p, c, sprite, layer

@pytest.mark.parametrize("effect_fps", [11, 22])
@pytest.mark.parametrize("turns",[1,2,-1])
@pytest.mark.parametrize("mode",["single","particle"])
def test_rotation_quarters_resource_effect_actual_rgba(effect_fps,turns,mode,tmp_path):
    from app.services.effect_resource_layer_render_service import apply_effect_resource_layer
    from app.services.effect_playback_service import render_exact_playback_frame
    from app.services.export_service import export_png_frames
    from PIL import Image
    p,c,sprite,layer=rotation_project(effect_fps=effect_fps,turns=turns)
    if mode=="single":
        layer.placement_mode="single";layer.start_x=layer.end_x=12;layer.start_y=layer.end_y=12
    full=render_effect_resource_layer(p,layer)
    generated=apply_effect_resource_layer(p,layer,full)
    loaded=Project.from_dict(p.to_dict())
    paths=export_png_frames(p,tmp_path/"png")
    for index in (0,15,30,45,60):
        frame=index*effect_fps//c.fps
        assert sprite.value("rotation",index)==index*6*turns
        expected=render_composition_frame(p,c,index)
        np.testing.assert_array_equal(render_effect_resource_layer_current_frame(p,layer,frame),expected,err_msg=f"current resource={index} effect={frame}")
        np.testing.assert_array_equal(full[frame],expected,err_msg=f"full resource={index} effect={frame}")
        np.testing.assert_array_equal(p.frames[frame].layer_pixels[generated.id],expected)
        np.testing.assert_array_equal(render_exact_playback_frame(p,frame)[0],expected)
        np.testing.assert_array_equal(np.asarray(Image.open(paths[frame]).convert("RGBA")),expected)
        np.testing.assert_array_equal(render_effect_resource_layer_current_frame(loaded,loaded.effect_resource_layers[0],frame),expected)

@pytest.mark.parametrize("via_dialog",[False,True])
def test_change_effect_fps_12_to_24_regenerates_seek_pixels(tmp_path,via_dialog):
    from PySide6.QtCore import QSettings
    from app.services.settings_service import ShortcutSettingsService
    from app.ui.main_window import MainWindow
    from tests.test_effect_layer_group_workflow import _close
    from tests.test_project_settings import values_for
    p,c,sprite,_=rotation_project(12,12)
    p.effect_resource_layers=[];p.repair_effect_hierarchy()
    win=MainWindow(ShortcutSettingsService(QSettings(str(tmp_path/"fps.ini"),QSettings.Format.IniFormat)),p)
    try:
        layer=win.create_resource_layer_from_resource(c.id)
        draft=win.particle_preview_manager.ensure_draft(layer.as_particle_emitter());draft.settings.seed=987;draft.is_dirty=True
        before_tracks=deepcopy(sprite.to_dict())
        if via_dialog:assert win.apply_project_settings(values_for(win,fps=24))
        else:win.set_fps(24)
        assert sprite.to_dict()==before_tracks
        assert win.particle_preview_manager.drafts[layer.id].settings.seed==987
        for frame in (0,30,60,90,120):
            expected=render_effect_resource_layer_current_frame(p,layer,frame)
            np.testing.assert_array_equal(p.frames[frame].layer_pixels[layer.generated_layer_id],expected,err_msg=f"generated seek frame {frame}")
    finally:_close(win)

def test_growing_effect_12_to_24_frames_does_not_reuse_short_base_cache():
    p,c,sprite,layer=rotation_project(12,12)
    p.frames=p.frames[:12];layer.placement_mode="single";layer.end_frame=11
    layer.start_x=layer.end_x=layer.start_y=layer.end_y=12
    assert len(render_effect_resource_layer(p,layer))==12
    for _ in range(12):p.add_frame()
    full=render_effect_resource_layer(p,layer)
    assert len(full)==24
    for frame in range(24):np.testing.assert_array_equal(full[frame],render_effect_resource_layer_current_frame(p,layer,frame))

@pytest.mark.parametrize("speed",[.5,2])
def test_particle_rotation_speed_is_source_sampling_not_angle_normalization(speed):
    p,c,sprite,layer=rotation_project(12,12)
    layer.particle_settings.clip_speed_min=layer.particle_settings.clip_speed_max=speed
    for source_frame in (0,15,30,45,60):
        frame=int(source_frame/speed)
        # At 2x, source frame 15 would require effect frame 7.5: discrete
        # seek at 7 correctly samples 14, not an interpolated 90-degree image.
        sampled=int(frame*speed)%c.frame_count
        np.testing.assert_array_equal(render_effect_resource_layer_current_frame(p,layer,frame),render_composition_frame(p,c,sampled))

def point_geometry_issues(editor):
    controls=[editor.title,editor.list,editor.time,editor.color if editor.channel=="color" else editor.value,editor.easing,editor.add,editor.remove,editor.status]
    controls += [editor.form.labelForField(w) for w in (editor.time,editor.color if editor.channel=="color" else editor.value,editor.easing)]
    controls=[w for w in controls if w.isVisibleTo(editor) and (not hasattr(w,"text") or w.text())]
    rect=lambda w: QRect(w.mapToGlobal(QPoint()),w.size())
    issues=[f"overlap:{a.objectName() or type(a).__name__}/{b.objectName() or type(b).__name__}" for a,b in combinations(controls,2) if rect(a).intersects(rect(b))]
    issues += ["outside:"+type(w).__name__ for w in controls if not rect(editor).contains(rect(w))]
    issues += ["empty:"+type(w).__name__ for w in controls if w.width()<8 or w.height()<8]
    return issues

@pytest.mark.parametrize("language", ["ko","en"])
@pytest.mark.parametrize("width", [280,320,360])
@pytest.mark.parametrize("scale", [1,1.25,1.5])
@pytest.mark.parametrize("style", ["Fusion","windows11"])
def test_lifetime_nested_controls_do_not_intersect(tmp_path,language,width,scale,style):
    p,project,a,b=make_panel(tmp_path,language,width,scale)
    # Do not restyle every surviving widget from unrelated tests in QApplication.
    visual_style=QStyleFactory.create(style);visual_style.setParent(p)
    for widget in (p,*p.findChildren(QWidget)):widget.setStyle(visual_style)
    settle()
    try:
        settings=deepcopy(a.particle_settings)
        settings.scale_over_lifetime.enabled=settings.color_over_lifetime.enabled=True
        p.set_settings(settings);p.workflow.jump("look");settle()
        for points in range(2,9):
            for editor in p._point_editors:
                assert not point_geometry_issues(editor), (editor.channel,points,point_geometry_issues(editor))
                if points<8:editor.add_point()
            settle()
        p.workflow.sections["look"].set_expanded(False);settle()
        p.resize(360,1100);p.workflow.jump("look");settle()
        font=p.font();font.setPointSizeF(18);p.setFont(font);p.resize(280,700);settle()
        for editor in p._point_editors:
            editor.status.setText("Rejected: check endpoints, value range, and strictly increasing neighbor times. "*2)
        settle()
        for editor in p._point_editors:assert not point_geometry_issues(editor), point_geometry_issues(editor)
        for enabled in (False,True):
            p.scale_lifetime_enabled.setChecked(enabled);p.color_lifetime_enabled.setChecked(enabled);settle()
            for editor in p._point_editors:
                if editor.isVisibleTo(p):assert not point_geometry_issues(editor)
        p.workflow.sections["look"].set_expanded(False);settle()
        p.workflow.jump("look",p.scale_point_editor.time);settle()
        p.set_resource_layer(b,project);p.set_resource_layer(a,project);p.workflow.jump("look",p.opacity_point_editor);settle()
        for editor in p._point_editors:
            if editor.isVisibleTo(p):assert not point_geometry_issues(editor)
    finally:p.close();p.deleteLater();settle()

def test_duplicate_multiselect_immediately_updates_group_button(tmp_path):
    from tests.test_effect_layer_group_workflow import _window,_close
    win=_window(tmp_path)
    try:
        win.select_resource_layer(win._effect_ui_root_ids()[0])
        win.duplicate_selected_effect_layers();settle()
        ids=win._effect_ui_root_ids()
        win.select_effect_layers_with_modifiers(ids[0])
        win.select_effect_layers_with_modifiers(ids[1],Qt.KeyboardModifier.ControlModifier)
        assert len(win.effect_layer_selection.selected_ids)==2
        assert win.effect_library.group_composition_button.isEnabled()
        assert win.effect_library.composition_selection_label.text()
        order=deepcopy(win.project.effect_root_order)
        transforms={item.id:(item.parent_id,item.parent_offset,deepcopy(item.layer_transform.to_dict())) for item in win.project.effect_resource_layers}
        rgba=win.project.compose_frame(0).copy()
        win.application_undo_stack.clear()
        win.effect_library.group_composition_button.click();settle()
        assert len(win.project.effect_layer_groups)==1
        group=win.project.effect_layer_groups[0]
        assert set(group.children)==set(ids[:2])
        assert win.effect_library.ungroup_composition_button.isEnabled()
        assert transforms=={item.id:(item.parent_id,item.parent_offset,item.layer_transform.to_dict()) for item in win.project.effect_resource_layers}
        np.testing.assert_array_equal(win.project.compose_frame(0),rgba)
        loaded=Project.from_dict(win.project.to_dict());assert loaded.effect_group_by_id(group.id).children==group.children
        np.testing.assert_array_equal(loaded.compose_frame(0),rgba)
        win.effect_library.ungroup_composition_button.click();settle()
        assert not win.project.effect_layer_groups and win.project.effect_root_order==order
        win.application_undo_stack.undo();assert len(win.project.effect_layer_groups)==1
        win.application_undo_stack.undo();assert not win.project.effect_layer_groups and win.project.effect_root_order==order
        win.application_undo_stack.redo();win.application_undo_stack.redo()
        assert not win.project.effect_layer_groups and win.project.effect_root_order==order
    finally:_close(win)

@pytest.mark.parametrize("condition",["one","nonadjacent","locked","member","mixed_groups","group","hidden_solo","transform_parent"])
def test_group_eligibility_matches_execution(tmp_path,condition):
    from tests.test_effect_layer_group_workflow import _window,_close
    from app.services.effect_group_service import effect_group_reasons
    win=_window(tmp_path)
    try:
        ids=win._effect_ui_root_ids();selected=ids[:2]
        if condition=="one":selected=ids[:1]
        elif condition=="nonadjacent":selected=[ids[0],ids[2]]
        elif condition=="locked":next(l for l in win.project.effect_resource_layers if l.id==ids[0]).locked=True
        elif condition in {"member","mixed_groups","group"}:
            win.select_effect_layers_with_modifiers(ids[0]);win.select_effect_layers_with_modifiers(ids[1],Qt.KeyboardModifier.ControlModifier)
            group=win.create_effect_group_selected()
            selected=[group.id] if condition=="group" else ids[:2] if condition=="member" else [ids[0],ids[2]]
        elif condition=="hidden_solo":
            for l in win.project.effect_resource_layers:l.visible=False;l.solo=True
        elif condition=="transform_parent":win.set_effect_layer_parent(ids[0],ids[2])
        win._refresh_effect_panels()
        win.select_effect_layers_with_modifiers(selected[0])
        for identifier in selected[1:]:win.select_effect_layers_with_modifiers(identifier,Qt.KeyboardModifier.ControlModifier)
        reasons=effect_group_reasons(win.project,selected)
        assert win.effect_library.group_composition_button.isEnabled()==(reasons[0] is None)
        assert win.effect_library.ungroup_composition_button.isEnabled()==(reasons[1] is None)
        if reasons[0]:
            before=win.project.to_dict();assert win.create_effect_group_selected() is None;assert win.project.to_dict()==before
            assert win.effect_library.group_composition_button.toolTip()
        else:assert win.create_effect_group_selected()
    finally:_close(win)

@pytest.mark.parametrize("modifier",[Qt.KeyboardModifier.ControlModifier,Qt.KeyboardModifier.ShiftModifier])
def test_mouse_multiselect_group_state_uses_selection_not_current_index(tmp_path,modifier):
    from tests.test_effect_layer_group_workflow import _window,_close
    from PySide6.QtTest import QTest
    win=_window(tmp_path)
    try:
        win.resize(1200,850);win.show();settle()
        view=win.effect_library.composition_list
        win.effect_library.scroll_area.ensureWidgetVisible(view);settle()
        for row,mods in ((0,Qt.KeyboardModifier.NoModifier),(1,modifier)):
            point=view.visualItemRect(view.item(row)).center();point.setX(max(70,point.x()))
            QTest.mouseClick(view.viewport(),Qt.MouseButton.LeftButton,mods,point);settle()
        assert len(win.effect_layer_selection.selected_ids)==2
        assert win.effect_library.group_composition_button.isEnabled()
    finally:_close(win)
