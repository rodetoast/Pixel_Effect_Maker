from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtWidgets import QApplication

from tests.test_timeline_multi_key_editing import _close,_effect_window


APP=QApplication.instance() or QApplication([])


def test_effect_library_prioritizes_resource_layer_space(tmp_path):
    window,_single,_particle=_effect_window(tmp_path);window.resize(1280,720);window.show();APP.processEvents();library=window.effect_library
    assert library.asset_list.maximumHeight()<=92 and library.clip_list.maximumHeight()<=104
    assert library.composition_group.minimumHeight()>=250 and library.composition_list.minimumHeight()>=150
    assert library.composition_group.height()>=library.clip_group.height()
    assert library.add_composition_button.property("commandRole")=="primary"
    assert library.composition_top_separator is None
    assert library.remove_composition_button.property("commandRole")=="danger"
    assert library.lock_composition_button.property("commandRole")=="toggle"
    _close(window)


def test_resource_information_has_grouped_metadata_and_separate_cta(tmp_path):
    window,_single,_particle=_effect_window(tmp_path);inspector=window.resource_editor.composition_inspector
    assert inspector.metadata_group.objectName()=="resourceInformationSection"
    assert inspector.metadata_group.isAncestorOf(inspector.info) and inspector.metadata_group.isAncestorOf(inspector.name)
    assert not inspector.metadata_group.isAncestorOf(inspector.use)
    assert inspector.use.property("commandRole")=="primary" and inspector.center.property("commandRole")=="secondary"
    _close(window)


def test_effect_inspector_density_keeps_full_help_in_tooltips(tmp_path):
    window,single,particle=_effect_window(tmp_path);window.select_resource_layer(particle.id);APP.processEvents();panel=window.particle_properties
    margins=panel.layout.contentsMargins();assert max(margins.left(),margins.top(),margins.right(),margins.bottom())<=6
    assert all(form.verticalSpacing()<=4 for _title,_group,form,_records in panel._group_records)
    transform=panel.transform_panel
    assert len(transform.description.text())<len(transform.description.toolTip())
    assert len(transform.surface_warning.text())<len(transform.surface_warning.toolTip())
    window.select_resource_layer(single.id);APP.processEvents();composition=window.composition_layer_properties
    assert composition.form.verticalSpacing()<=4 and composition.common_form.verticalSpacing()<=4
    _close(window)


def test_representative_window_sizes_keep_splitter_children_non_overlapping(tmp_path):
    window,_single,_particle=_effect_window(tmp_path);window.show()
    for width,height in ((1280,720),(1600,900),(1920,1080)):
        window.resize(width,height);APP.processEvents();children=[window.effect_library,window.canvas,window.properties_stack]
        assert all(child.geometry().width()>0 and child.geometry().height()>0 for child in children)
        assert all(left.geometry().right()<right.geometry().left() for left,right in zip(children,children[1:]))
    _close(window)
