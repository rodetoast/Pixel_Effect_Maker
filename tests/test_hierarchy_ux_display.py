import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtWidgets import QApplication

from app.models.layer_group import LayerGroup,group_node
from app.models.resource_composition import CompositionLayer,ResourceComposition
from app.ui.hierarchy_display import build_hierarchy_rows
from app.ui.resource_editor_v2.composition_timeline import CompositionTimeline

APP=QApplication.instance() or QApplication([])


def _composition():
    parent=CompositionLayer("Core","source_asset","a",0,1);child=CompositionLayer("Glow","source_asset","b",0,1,parent_id=parent.id);free=CompositionLayer("Free","source_asset","c",0,1)
    group=LayerGroup("Fire FX",children=[parent.id,child.id],locked=True)
    composition=ResourceComposition("C",16,16,12,2,layers=[parent,child,free],groups=[group],root_order=[group_node(group.id)])
    composition.root_order.append({"type":"layer","id":free.id});composition.sync_flat_order();return composition,group,parent,child,free


def test_group_indent_parent_badge_and_selection_are_independent():
    composition,group,parent,child,_free=_composition();rows=build_hierarchy_rows(composition.layers,composition.groups,composition.root_order,{group.id},{child.id},child.id,effective_locked=composition.effective_locked);by_id={row.identifier:row for row in rows}
    assert by_id[group.id].kind=="group" and by_id[group.id].depth==0 and by_id[group.id].child_count==2
    assert by_id[parent.id].depth==1 and not by_id[parent.id].parent_label
    assert by_id[child.id].depth==1 and by_id[child.id].parent_label=="Core"
    assert by_id[child.id].inherited_locked and by_id[child.id].primary and by_id[child.id].selected


def test_resource_timeline_rows_expose_group_parent_state_and_property_marker():
    composition,group,_parent,child,_free=_composition();child.add_property("rotation")
    timeline=CompositionTimeline();timeline.refresh(composition,child,0,{child.id},child.id,{group.id});headers=[timeline.table.verticalHeaderItem(row).text() for row in range(timeline.table.rowCount())]
    assert any("[G] Fire FX" in text for text in headers)
    assert any("[P: Core]" in text and "L*" in text and "▌" in text for text in headers)
    assert any("└ rotation" in text for text in headers)
    timeline.close()
