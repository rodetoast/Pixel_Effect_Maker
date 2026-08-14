from copy import deepcopy

from app.models.project import Project
from app.models.resource_composition import CompositionLayer, ResourceComposition
from app.models.source_asset import SourceAsset
import numpy as np


def test_parent_v12_roundtrip_and_dangling_repair():
    a=CompositionLayer("a","source_asset","a",0,0);b=CompositionLayer("b","source_asset","b",0,0,parent_id=a.id)
    project=Project.create_default();project.source_assets=[SourceAsset("a",np.zeros((1,1,4),dtype=np.uint8),id="a"),SourceAsset("b",np.zeros((1,1,4),dtype=np.uint8),id="b")];project.resource_compositions=[ResourceComposition("c",8,8,12,1,layers=[a,b])]
    data=project.to_dict();loaded=Project.from_dict(deepcopy(data));assert loaded.resource_compositions[0].layers[1].parent_id==a.id
    data["resource_compositions"][0]["layers"][1]["parent_id"]="missing"
    assert Project.from_dict(data).resource_compositions[0].layers[1].parent_id is None
