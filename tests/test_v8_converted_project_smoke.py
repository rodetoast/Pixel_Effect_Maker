from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from app.models.project import FORMAT_VERSION
from app.services.project_io import load_project, save_project


ROOT=Path(__file__).resolve().parents[1]
PROJECTS=(ROOT/"projects"/"test0805_v8.peffect.json",ROOT/"projects"/"test0806_v8.peffect.json")


def file_hash(path):
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest()


@pytest.mark.parametrize("source",PROJECTS,ids=lambda path:path.stem)
def test_converted_v8_project_read_only_smoke(source,tmp_path):
    if not source.exists():pytest.skip(f"local converted fixture is unavailable: {source}")
    before=file_hash(source);project=load_project(source)
    assert project.format_version==FORMAT_VERSION==11
    source_ids={item.id for item in project.source_assets};clip_ids={item.id for item in project.animation_clips};composition_ids={item.id for item in project.resource_compositions};layer_ids={item.id for item in project.layers}
    for composition in project.resource_compositions:
        for layer in composition.layers:
            assert layer.source_id in (source_ids if layer.source_type=="source_asset" else clip_ids)
    for layer in project.effect_resource_layers:
        assert not layer.resource_composition_id or layer.resource_composition_id in composition_ids
        assert layer.generated_layer_id is None or layer.generated_layer_id in layer_ids
        if layer.placement_mode=="particle":assert layer.particle_settings.motion.mode=="linear"
    samples=sorted({0,len(project.frames)//2,len(project.frames)-1})
    rendered={index:project.compose_frame(index) for index in samples}
    target=save_project(project,tmp_path/source.name)
    reloaded=load_project(target)
    assert reloaded.format_version==11
    assert all(np.array_equal(rendered[index],reloaded.compose_frame(index)) for index in samples)
    assert file_hash(source)==before
