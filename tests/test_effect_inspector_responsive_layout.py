import os

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import pytest
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QAbstractSpinBox, QFormLayout, QLabel

from app.models.effect_resource_layer import EffectResourceLayer,PLACEMENT_PARTICLE
from app.models.project import Project
from app.models.resource_composition import ResourceComposition
from app.services.localization_service import LocalizationService
from app.services.settings_service import ShortcutSettingsService
from app.ui.composition_layer_properties_panel import CompositionLayerPropertiesPanel
from app.ui.main_window import MainWindow
from app.ui.particle_properties_panel import ParticlePropertiesPanel

APP=QApplication.instance() or QApplication([])


def context(mode="single"):
    project=Project.create_default();composition=ResourceComposition("Responsive Resource",width=16,height=16,frame_count=4);project.resource_compositions.append(composition)
    layer=EffectResourceLayer("Responsive Layer",composition.id,placement_mode=mode,end_frame=3)
    return project,layer


def localization(tmp_path,language):
    settings=QSettings(str(tmp_path/f"{language}.ini"),QSettings.Format.IniFormat);service=LocalizationService(settings,language);service.set_language(language);return service


def show_and_assert_fits(panel,width=280,font_scale=1.0):
    font=QFont(panel.font());font.setPointSizeF(max(1.0,font.pointSizeF()*font_scale));panel.setFont(font);panel.resize(width,640);panel.show();APP.processEvents()
    panel.widget().layout().activate();APP.processEvents()
    assert panel.horizontalScrollBarPolicy()==Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert panel.horizontalScrollBar().maximum()==0
    assert panel.widget().width()<=panel.viewport().width()
    for spin in panel.findChildren(QAbstractSpinBox):assert spin.width()>=1


def test_effect_inspector_has_no_horizontal_scrollbar_at_300px(tmp_path):
    project,layer=context();panel=CompositionLayerPropertiesPanel();panel.retranslate_ui(localization(tmp_path,"en"));panel.set_resource_layer(layer,project);show_and_assert_fits(panel,300)


def test_effect_inspector_content_fits_viewport_at_280px(tmp_path):
    project,layer=context();panel=CompositionLayerPropertiesPanel();panel.retranslate_ui(localization(tmp_path,"ko"));panel.set_resource_layer(layer,project);show_and_assert_fits(panel,280)


def test_transform_mode_buttons_fit_narrow_inspector(tmp_path):
    project,layer=context();panel=CompositionLayerPropertiesPanel();panel.retranslate_ui(localization(tmp_path,"en"));panel.set_resource_layer(layer,project);show_and_assert_fits(panel,280)
    panel.transform_panel.set_advanced_expanded(True);APP.processEvents()
    viewport_right=panel.viewport().rect().right();origin=panel.widget().mapTo(panel.viewport(),panel.transform_panel.pos())
    for button in panel.transform_panel.gizmo_buttons.values():assert origin.x()+button.geometry().right()<=viewport_right
    positions=[(button.geometry().x(),button.geometry().y()) for button in panel.transform_panel.gizmo_buttons.values()];assert len({x for x,_ in positions})==2 and len({y for _,y in positions})==3


def test_single_path_panel_fits_narrow_inspector(tmp_path):
    project,layer=context();panel=CompositionLayerPropertiesPanel();panel.retranslate_ui(localization(tmp_path,"en"));panel.set_resource_layer(layer,project);show_and_assert_fits(panel,280)
    assert all(widget.geometry().right()<=panel.widget().width() for widget,_ in panel._fields)


def test_particle_panel_fits_narrow_inspector(tmp_path):
    project,layer=context(PLACEMENT_PARTICLE);panel=ParticlePropertiesPanel();panel.retranslate_ui(localization(tmp_path,"en"));panel.set_resource_layer(layer,project);show_and_assert_fits(panel,280)
    assert all(group.width()<=panel.viewport().width() for _,group,_,_ in panel._group_records if group.isVisible())


@pytest.mark.parametrize("language",["ko","en"])
def test_effect_inspector_korean_and_english_fit(tmp_path,language):
    project,layer=context();panel=CompositionLayerPropertiesPanel();panel.retranslate_ui(localization(tmp_path,language));panel.set_resource_layer(layer,project);show_and_assert_fits(panel,280)


def test_effect_inspector_runtime_language_switch_reflows(tmp_path):
    project,layer=context();panel=CompositionLayerPropertiesPanel();panel.set_resource_layer(layer,project)
    for language in ("en","ko","en"):
        panel.retranslate_ui(localization(tmp_path,language));show_and_assert_fits(panel,280)


@pytest.mark.parametrize("scale",[1.25,1.5])
def test_effect_inspector_large_font_125_and_150_percent(tmp_path,scale):
    project,layer=context();panel=CompositionLayerPropertiesPanel();panel.retranslate_ui(localization(tmp_path,"en"));panel.set_resource_layer(layer,project);show_and_assert_fits(panel,300,scale)
    assert all(button.width()>0 for button in panel.transform_panel.gizmo_buttons.values())


def test_particle_inspector_large_font_150_percent(tmp_path):
    project,layer=context(PLACEMENT_PARTICLE);panel=ParticlePropertiesPanel();panel.retranslate_ui(localization(tmp_path,"en"));panel.set_resource_layer(layer,project);show_and_assert_fits(panel,300,1.5)


@pytest.mark.parametrize("panel_type,mode",[(CompositionLayerPropertiesPanel,"single"),(ParticlePropertiesPanel,PLACEMENT_PARTICLE)])
@pytest.mark.parametrize("language",["ko","en"])
@pytest.mark.parametrize("width",[280,300,320])
def test_every_effect_property_keeps_a_visible_text_label(tmp_path,panel_type,mode,language,width):
    project,layer=context(mode);panel=panel_type();panel.retranslate_ui(localization(tmp_path,language));panel.set_resource_layer(layer,project);show_and_assert_fits(panel,width,1.5)
    panel.transform_panel.set_advanced_expanded(True);APP.processEvents()
    forms=[panel.transform_panel.form]
    if isinstance(panel,CompositionLayerPropertiesPanel):forms.extend((panel.common_form,panel.form))
    else:forms.append(panel.common_form);forms.extend(record[2] for record in panel._group_records if record[1].isVisible())
    for form in forms:
        for row in range(form.rowCount()):
            label_item=form.itemAt(row,QFormLayout.ItemRole.LabelRole)
            if label_item is None:continue
            label=label_item.widget()
            assert isinstance(label,QLabel) and label.isVisible() and label.text().strip() and label.width()>0
            field_item=form.itemAt(row,QFormLayout.ItemRole.FieldRole)
            if field_item is not None and field_item.widget() is not None:
                editor=field_item.widget();label_rect=label.rect().translated(label.mapTo(panel.widget(),QPoint()))
                editor_rect=editor.rect().translated(editor.mapTo(panel.widget(),QPoint()))
                assert label_rect.left()>=0 and label_rect.right()<panel.widget().width()
                assert not label_rect.intersects(editor_rect)
    for label in panel.transform_panel.easing_labels.values():
        assert label.isVisible() and label.text().strip() and label.width()>0


def test_effect_inspector_keeps_vertical_scrolling(tmp_path):
    project,layer=context(PLACEMENT_PARTICLE);panel=ParticlePropertiesPanel();panel.retranslate_ui(localization(tmp_path,"en"));panel.set_resource_layer(layer,project);panel.resize(280,360);panel.show();APP.processEvents();assert panel.verticalScrollBar().maximum()>0 and panel.horizontalScrollBar().maximum()==0


@pytest.mark.parametrize("size",[(1024,768),(1280,800),(1308,1176),(1600,900)])
def test_effect_inspector_does_not_force_main_window_width(tmp_path,size):
    settings=QSettings(str(tmp_path/f"{size[0]}.ini"),QSettings.Format.IniFormat);window=MainWindow(ShortcutSettingsService(settings));window.resize(*size);window.show();window.editor_splitter.setSizes([210,max(300,size[0]-500),280]);APP.processEvents()
    assert (window.width(),window.height())==size;assert 280<=window.properties_stack.width()<=320;assert window.canvas.width()>window.properties_stack.width();assert window.effect_library.scroll_area.horizontalScrollBar().maximum()==0;window.dirty=False;window.close()
