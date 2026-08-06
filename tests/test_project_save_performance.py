import json
import tracemalloc

import numpy as np

from app.frame_payload_codec import DEFAULT_FRAME_PAYLOAD_CODEC
from app.models.animation_clip import AnimationClipAsset
from app.models.project import Project
from app.models.source_asset import SourceAsset
from app.services.project_io import SavePerformanceCollector,save_project


def project_with_pixels(size=64,frames=3):
    project=Project.create_default("Performance",size,size);pixels=np.zeros((size,size,4),dtype=np.uint8);pixels[size//4:3*size//4,size//4:3*size//4]=[230,70,20,180]
    asset=SourceAsset("source",pixels.copy(),source_path="missing.png");clip=AnimationClipAsset("clip",[np.roll(pixels,index,axis=1) for index in range(frames)],frame_durations_ms=[50]*frames)
    project.source_assets.append(asset);project.animation_clips.append(clip);return project,asset,clip


def test_new_save_does_not_use_nested_pixel_lists(tmp_path):
    project,_,_=project_with_pixels();data=json.loads(save_project(project,tmp_path/"compact").read_text(encoding="utf-8"))
    assert isinstance(data["frames"][0]["layer_pixels"][project.layers[0].id],dict)
    assert isinstance(data["source_assets"][0]["pixels"],dict) and all(isinstance(item,dict) for item in data["animation_clips"][0]["frames"])


def test_unchanged_second_save_reuses_every_encoded_payload(tmp_path):
    codec=DEFAULT_FRAME_PAYLOAD_CODEC;codec.clear();codec.reset_stats();project,_,_=project_with_pixels();save_project(project,tmp_path/"first");assert codec.stats.encode_calls==5
    codec.reset_stats();save_project(project,tmp_path/"second")
    assert codec.stats.encode_calls==0 and codec.stats.cache_hits==5


def test_renaming_and_pivot_change_do_not_reencode_pixels(tmp_path):
    codec=DEFAULT_FRAME_PAYLOAD_CODEC;codec.clear();project,asset,_=project_with_pixels();save_project(project,tmp_path/"first");codec.reset_stats();asset.name="renamed";asset.pivot_x+=1;save_project(project,tmp_path/"second")
    assert codec.stats.encode_calls==0


def test_one_changed_clip_frame_reencodes_only_that_frame(tmp_path):
    codec=DEFAULT_FRAME_PAYLOAD_CODEC;codec.clear();project,_,clip=project_with_pixels();save_project(project,tmp_path/"first");codec.reset_stats();clip.frames[1][0,0]=[1,2,3,4];save_project(project,tmp_path/"second")
    assert codec.stats.encode_calls==1 and codec.stats.cache_hits==4


def test_save_collector_separates_pipeline_and_atomic_replace_once(tmp_path):
    project,_,_=project_with_pixels();collector=SavePerformanceCollector();save_project(project,tmp_path/"profile",collector)
    assert set(("project_to_dict","json_dumps","utf8_encode","temporary_write","flush","fsync","atomic_replace"))<=set(collector.calls)
    assert collector.calls["atomic_replace"]==1 and collector.output_bytes>0


def test_compact_save_peak_memory_and_file_are_below_legacy_representation(tmp_path):
    project,asset,_=project_with_pixels(128,1);legacy_bytes=len(json.dumps(asset.pixels.tolist(),separators=(",",":")).encode())
    tracemalloc.start();path=save_project(project,tmp_path/"compact");peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
    assert path.stat().st_size<legacy_bytes and peak<legacy_bytes*4


def test_save_serializes_no_runtime_cache_attributes(tmp_path):
    project,_,_=project_with_pixels();project._current_effect_frame=4;data=json.loads(save_project(project,tmp_path/"clean").read_text(encoding="utf-8"));text=json.dumps(data)
    for forbidden in ("preview_frames","QImage","QPixmap","interactive_transform_proxy","prewarm","worker_revision"):
        assert forbidden not in text
