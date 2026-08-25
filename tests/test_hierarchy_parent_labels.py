from app.models.layer_group import LayerGroup
from app.models.resource_composition import CompositionLayer
from app.ui.hierarchy_display import layer_display_labels,parent_display_labels


def test_duplicate_parent_names_prefer_group_paths_then_short_ids():
    first=CompositionLayer("Core","source_asset","a",0,1);second=CompositionLayer("Core","source_asset","b",0,1);child_a=CompositionLayer("A","source_asset","c",0,1,parent_id=first.id);child_b=CompositionLayer("B","source_asset","d",0,1,parent_id=second.id);groups=[LayerGroup("Fire",children=[first.id,child_a.id]),LayerGroup("Smoke",children=[second.id,child_b.id])]
    labels=parent_display_labels([first,second,child_a,child_b],groups)
    assert labels[child_a.id]=="Fire / Core" and labels[child_b.id]=="Smoke / Core"


def test_same_path_duplicate_falls_back_to_short_stable_id_and_rename_refreshes():
    first=CompositionLayer("Core","source_asset","a",0,1);second=CompositionLayer("Core","source_asset","b",0,1);labels=layer_display_labels([first,second],[])
    assert labels[first.id].endswith(first.id[:4]) and labels[second.id].endswith(second.id[:4])
    first.name="Main Core";renamed=layer_display_labels([first,second],[]);assert renamed[first.id]=="Main Core" and renamed[second.id]=="Core"
