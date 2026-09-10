"""Audit-only synthetic fixtures; never opens or rewrites a user's project.

Run from the repository: python tools/audit_effect_authoring.py
Temporary project/PNG files are scoped to a TemporaryDirectory in C:/Dev.
Numbers describe small synthetic workloads, not native GUI manual QA.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import statistics
import sys
from tempfile import TemporaryDirectory
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import numpy as np
from PIL import Image
from PySide6.QtWidgets import QApplication
from app.models.animation_clip import AnimationClipAsset
from app.models.effect_resource_layer import EffectResourceLayer
from app.models.particle_emitter import ParticleEmitter, ParticleEmitterSettings, ParticleMotionSettings
from app.models.project import Project
from app.models.resource_composition import AnimationTrack, Keyframe
from app.services.effect_resource_layer_render_service import apply_effect_resource_layer, render_effect_resource_layer, invalidate_effect_resource_layer_base
from app.services.export_service import export_png_frames
from app.services.particle_render_service import build_particle_instances, render_particle_frames
from app.services.project_io import load_project, save_project
from app.ui.particle_properties_panel import ParticlePropertiesPanel
from app.ui.timeline_multi_key import TimelineKey
from app.ui.timeline_snapping import collect_snap_targets
from app.ui.timeline_time_view import navigation_frame


def measure(fn, repetitions=3):
    samples = []
    for _ in range(repetitions):
        started = perf_counter()
        fn()
        samples.append((perf_counter() - started) * 1000)
    return round(statistics.median(samples), 3)


def sprite(name, grow=False, slash=False):
    # Baked source-frame artwork is a workaround, NOT a new lifetime feature.
    frames = []
    for index in range(8):
        image = np.zeros((9, 9, 4), dtype=np.uint8)
        radius = min(4, 1 + index // 2) if grow else max(1, 4 - index // 2)
        color = (255, max(50, 230 - index * 20), 80, 255)
        if slash:
            image[4, max(0, index - 2):min(9, index + 3)] = color
        else:
            image[4-radius:5+radius, 4-radius:5+radius] = color
        frames.append(image)
    return AnimationClipAsset(name, frames, fps=12, playback_mode="loop")


def add(project, clip, name, **overrides):
    values = dict(clip_asset_id=clip.id, output_frame_count=16,
                  particle_count_min=12, particle_count_max=12,
                  origin_x=32, origin_y=32, speed_min=.4, speed_max=1.5,
                  lifetime_min=8, lifetime_max=16, direction_spread_degrees=180,
                  rotation_min=-30, rotation_max=30, opacity_start=1, opacity_end=0,
                  seed=42)
    values.update(overrides)
    layer = EffectResourceLayer.from_particle_emitter(ParticleEmitter(name, ParticleEmitterSettings(**values)))
    project.effect_resource_layers.append(layer)
    return layer


def fixture(name):
    project = Project.create_default(width=64, height=64)
    clip = sprite(name, grow=name in {"Explosion", "Smoke"}, slash=name=="Sword Slash")
    project.animation_clips.append(clip)
    if name == "Hit Spark":
        add(project, clip, name, direction_mode="radial_outward")
    elif name == "Explosion":
        add(project, clip, "burst", direction_mode="radial_outward", speed_max=2)
        add(project, clip, "smoke", emission_mode="over_time", emission_duration=8, speed_max=.6, speed_min=.2, start_frame=3)
    elif name == "Smoke":
        add(project, clip, name, emission_mode="over_time", emission_duration=12,
            spawn_shape="box", box_width=10, box_height=4,
            direction_degrees=-90, direction_spread_degrees=12, speed_max=.7, speed_min=.2)
    elif name == "Magic Orbit":
        add(project, clip, name, motion=ParticleMotionSettings(mode="orbit", radius_start=14, radius_end=14, turns=1, phase_spread_degrees=360))
    elif name == "Sword Slash":
        layer = add(project, clip, name, particle_count_min=1, particle_count_max=1,
                    speed_min=0, speed_max=0, rotation_min=0, rotation_max=0)
        layer.layer_space_transform.tracks["rotation_z"] = AnimationTrack("rotation_z", 0, [Keyframe(0, -30), Keyframe(15, 30)])
    else:
        add(project, clip, "projectile", particle_count_min=1, particle_count_max=1,
            origin_x=10, speed_min=2, speed_max=2, direction_degrees=0, direction_spread_degrees=0)
        # Prearranged burst substitutes for an event; it does not follow collisions.
        add(project, clip, "scheduled impact", start_frame=12, origin_x=34, lifetime_min=4, lifetime_max=4)
    project.repair_effect_hierarchy()
    return project


def materialize(project):
    invalidate_effect_resource_layer_base()
    for layer in project.effect_resource_layers:
        apply_effect_resource_layer(project, layer)
    return [project.compose_frame(index) for index in range(len(project.frames))]


def run():
    results = {"conditions": "64x64 RGBA, 16 frames, 9x9 animated sprite; median of 3 unless noted", "fixtures": {}, "performance_ms": {}}
    with TemporaryDirectory(prefix="pem_capability_audit_", dir="C:/Dev") as temporary:
        root = Path(temporary)
        for name in ("Hit Spark", "Explosion", "Smoke", "Magic Orbit", "Sword Slash", "Projectile"):
            project = fixture(name)
            reference = materialize(project)
            assert sum(np.count_nonzero(frame[..., 3]) for frame in reference) > 0
            assert all(np.array_equal(a, b) for a, b in zip(reference, materialize(project), strict=True))
            loaded = load_project(save_project(project, root / (name + ".peffect.json")))
            restored = materialize(loaded)
            assert all(np.array_equal(a, b) for a, b in zip(reference, restored, strict=True))
            paths = export_png_frames(loaded, root / name)
            assert all(np.array_equal(frame, np.asarray(Image.open(path))) for frame, path in zip(reference, paths, strict=True))
            results["fixtures"][name] = {"frames": len(reference), "layers": len(project.effect_resource_layers), "replay_reload_export_exact": True}

        for count in (100, 500, 1000):
            project = fixture("Hit Spark")
            layer = project.effect_resource_layers[0]
            settings = layer.particle_settings
            settings.particle_count_min = settings.particle_count_max = count
            settings.lifetime_min = settings.lifetime_max = 16
            emitter = layer.as_particle_emitter()
            bench = {"instance_generation": measure(lambda: build_particle_instances(settings, 8)),
                     "uncached_16_frame_particle_render": measure(lambda: render_particle_frames(project, emitter))}
            materialize(project)
            bench["png_16_frames"] = measure(lambda: export_png_frames(project, root / ("perf" + str(count))))
            results["performance_ms"][f"particles_{count}"] = bench

        for count in (10, 50, 100):
            project = fixture("Hit Spark")
            project.effect_resource_layers.clear()
            for index in range(count):
                add(project, project.animation_clips[0], str(index), particle_count_min=1, particle_count_max=1)
            project.repair_effect_hierarchy()
            results["performance_ms"][f"layers_{count}"] = {
                "materialize_16_frames_cold_once": measure(lambda: materialize(project), 1),
                "compose_materialized_frame": measure(lambda: project.compose_frame(5)),
                "png_16_frames": measure(lambda: export_png_frames(project, root / ("layers" + str(count))), 1)}

    keys = {TimelineKey(f"layer-{index // 500}", "resource", "position_x", index % 500) for index in range(5000)}
    tracks = [AnimationTrack("position_x", 0, [Keyframe(frame, float(frame)) for frame in range(500)]) for _ in range(10)]
    results["performance_ms"]["keys_5000"] = {
        "snap_target_collection": measure(lambda: collect_snap_targets(keys, set(), 250, 512)),
        "next_navigation": measure(lambda: navigation_frame([key.frame for key in keys], 250, 1)),
        "evaluate_10_tracks": measure(lambda: [track.evaluate(250.5) for track in tracks])}
    application = QApplication.instance() or QApplication([])
    project = fixture("Hit Spark")
    emitter = project.effect_resource_layers[0].as_particle_emitter()
    emitter.settings.easing = "Ease In"
    panel = ParticlePropertiesPanel()
    panel.set_emitter(emitter, project)
    results["introspection"] = {"loaded_alpha_easing": emitter.settings.easing, "inspector_reconstructed_alpha_easing": panel.settings().easing}
    panel.close()
    application.processEvents()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    run()
