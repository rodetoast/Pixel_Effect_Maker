"""Post-v25 audit artifacts only. No collision/ribbon/force/variation implementation.

Creates fresh synthetic evidence outside the repository. Production APIs are the
only renderers. Contact crossing scans are measurements, never effect behavior.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from PIL import Image, ImageDraw
from app.models.particle_emitter import (
    ParticleMotionSettings as Motion, ParticleTrailSettings as Trail,
    LifetimeScalarModulation as Scalar, LifetimeScalarPoint as S,
    LifetimeColorModulation as Color, LifetimeColorPoint as C,
)
from app.models.project import FORMAT_VERSION
from app.version import __version__ as APP_VERSION
from app.services import particle_render_service as r
from app.services.particle_sub_emitter_service import (
    iter_invocations, template_settings, render_layer_particles,
)
from app.services.particle_trail_render_service import render_particle_trails
from app.services.effect_resource_layer_render_service import (
    render_effect_resource_layer, render_effect_resource_layer_current_frame,
    apply_effect_resource_layer, invalidate_effect_resource_layer_base,
)
from app.services.effect_playback_service import render_exact_playback_frame
from app.services.lifetime_modulation_service import (
    evaluate_lifetime_scalar, evaluate_lifetime_color_component,
)
from app.services.project_io import save_project, load_project
from app.services.export_service import export_png_frames
from tools.benchmark_lifetime_multi_point import fixture, multi
from tools.benchmark_particle_sub_emitter import make

NAMES = (
    "Hit Spark", "Explosion", "Smoke", "Fire Ember", "Magic Comet",
    "Projectile", "Sword Slash", "Area Dust", "Ring Burst", "Rain Snow",
    "Firework", "Debris Smoke",
)
# Finite named goals, not subjective scores or user-frequency statistics.
# Basic archetypes are separate from their advanced reusable variants.
GOALS = {
    "contact_projectile": ("Projectile", "Collision", "variable-height flat-ground impact"),
    "contact_rain": ("Rain Snow", "Collision", "variable-height ground splash"),
    "contact_debris": ("Debris Smoke", "Collision", "landing-triggered dust"),
    "contact_spark": ("Hit Spark", "Collision", "spark dies on ground contact"),
    "strip_comet": ("Magic Comet", "Ribbon", "continuous curved tail"),
    "strip_projectile": ("Projectile", "Ribbon", "continuous long tail"),
    "strip_slash": ("Sword Slash", "Ribbon", "procedural continuous arc sweep"),
    "flow_smoke": ("Smoke", "Force", "spatial curl-driven circulation"),
    "flow_fire": ("Fire Ember", "Force", "spatial vortex-driven plume"),
    "flow_dust": ("Area Dust", "Force", "spatial attractor/repulsor field"),
}
IMPROVEMENTS = {
    "Variation": ["Explosion", "Firework", "Debris Smoke"],
    "Collision": [], "Ribbon": [],
    "Force": ["Smoke", "Fire Ember", "Area Dust", "Magic Comet", "Rain Snow"],
    "Graph": list(NAMES),
    "Inheritance": ["Projectile", "Explosion", "Firework", "Debris Smoke"],
    "Spawn": [],
}


def configure(name):
    events = name in {"Explosion", "Projectile", "Firework", "Debris Smoke"}
    if events:
        project, layer, target = make("death", 12 if name in {"Explosion", "Debris Smoke"} else 1, 6)
        target.name = "Smoke template" if name != "Firework" else "Radial sparks"
        cs = target.particle_settings
        cs.origin_x = cs.origin_y = 0
        cs.direction_degrees = -90
        cs.direction_spread_degrees = 35 if name != "Firework" else 360
        cs.blend_mode = "normal" if name != "Firework" else "additive"
        if name != "Firework": multi(cs, "Smoke")
    else:
        base = {"Fire Ember": "Cyclic Fire", "Magic Comet": "Magic Wisp", "Area Dust": "Smoke"}.get(name, name)
        project, layer = fixture(base)
    layer.name = name
    s = layer.particle_settings
    s.output_frame_count = 24
    s.origin_x = s.origin_y = 48
    if name in {"Hit Spark", "Ring Burst", "Explosion", "Debris Smoke"}:
        s.spawn_shape = "circle"; s.radius = 8 if name != "Ring Burst" else 20
        s.direction_mode = "radial_outward"; s.direction_spread_degrees = 0
    if name in {"Explosion", "Debris Smoke"}:
        s.lifetime_min = 5; s.lifetime_max = 12
        s.speed_min = 1; s.speed_max = 2
        s.gravity_enabled = True; s.gravity_strength = .08
    if name in {"Smoke", "Fire Ember", "Area Dust", "Rain Snow"}:
        s.emission_cycle_mode = "cyclic_steady"; s.emission_period_frames = 12
        s.emission_mode = "over_time"; s.emission_duration = 12
        s.spawn_shape = "box"; s.box_width = 52; s.box_height = 12
        s.direction_degrees = 90 if name == "Rain Snow" else -90
        s.direction_spread_degrees = 20; s.noise_enabled = True; s.noise_strength = 2
        s.gravity_enabled = True; s.gravity_strength = .035 if name == "Rain Snow" else -.025
        s.drag_enabled = True; s.drag_strength = .04
        if name == "Rain Snow": s.origin_y = 15; s.speed_min = 1; s.speed_max = 2
        if name == "Area Dust": s.box_height = 52; s.speed_min = .1; s.speed_max = .4
        if name == "Rain Snow":
            s.blend_mode = "normal"
            s.color_over_lifetime = Color(True, (210, 230, 255), (180, 210, 255))
            s.scale_over_lifetime = Scalar(True, .4, .6)
    if name in {"Magic Comet", "Sword Slash"}:
        s.particle_count_min = s.particle_count_max = 1
        s.motion = Motion(mode="orbit", center_x=0, center_y=0,
                          radius_start=25, radius_end=25, turns=.75)
        s.gravity_enabled = s.drag_enabled = False
        s.trail = Trail(True, 12, 2, .8)
        if name == "Sword Slash":
            clip = r._resolve_particle_clip(project, s)
            clip.frames = [np.full((3, 13, 4), 255, np.uint8)]
            clip.pivot_x = 6; clip.pivot_y = 1
            s.angular_velocity_min = s.angular_velocity_max = -12
    if name in {"Projectile", "Firework"}:
        s.origin_x = 20 if name == "Projectile" else 48
        s.origin_y = 48 if name == "Projectile" else 70
        s.direction_degrees = 0 if name == "Projectile" else -90
        s.speed_min = s.speed_max = 3
        s.gravity_enabled = s.drag_enabled = False
        s.trail = Trail(True, 10, 2, .8)
    if name == "Hit Spark": s.trail = Trail(True, 8, 2, .7)
    return project, layer


def digest(value):
    return hashlib.sha256(value).hexdigest()


def materialize(project):
    invalidate_effect_resource_layer_base()
    for layer in project.effect_resource_layers: apply_effect_resource_layer(project, layer)
    return [project.compose_frame(t) for t in range(len(project.frames))]


def evidence(project, layer, target):
    target.mkdir()
    invalidate_effect_resource_layer_base()
    raw = render_effect_resource_layer(project, layer)
    output = materialize(project)
    generated = next(x for x in project.layers if x.id == layer.generated_layer_id)
    for t in range(len(project.frames)):
        assert np.array_equal(raw[t], render_effect_resource_layer_current_frame(project, layer, t))
        assert np.array_equal(raw[t], project.frames[t].layer_pixels[generated.id])
        assert np.array_equal(output[t], render_exact_playback_frame(project, t)[0])
    for t in reversed(range(len(project.frames))):
        assert np.array_equal(raw[t], render_effect_resource_layer_current_frame(project, layer, t))
    saved = save_project(project, target / "fixture.peffect.json")
    loaded = load_project(saved)
    rebuilt = materialize(loaded)  # Do not merely trust saved Generated pixels.
    assert all(np.array_equal(a, b) for a, b in zip(output, rebuilt))
    pngs = export_png_frames(loaded, target / "frames")
    assert len(pngs) == 24
    assert all(np.array_equal(a, np.asarray(Image.open(p))) for a, p in zip(output, pngs))
    nonempty = [int(np.count_nonzero(a[..., 3])) for a in output]
    assert max(nonempty) > 0
    cyclic = layer.particle_settings.emission_cycle_mode == "cyclic_steady"
    if cyclic:
        period = layer.particle_settings.emission_period_frames
        for t in (0, 3, 11, 100000):
            assert np.array_equal(render_layer_particles(project, layer, t),
                                  render_layer_particles(project, layer, t + period))
    return output, dict(raw_current_full_generated_exact=True, playback_exact=True,
                        reload_rematerialized_png_exact=True, alpha_pixels=nonempty,
                        rgba_sha256=digest(b"".join(a.tobytes() for a in output)),
                        cyclic_periodic=cyclic, dimensions=[96, 96], frames=24)


def sheet(rows, path, frames=(0, 3, 7, 10, 16, 23)):
    image = Image.new("RGB", (130 + 96 * len(frames), 112 * len(rows)), (22, 24, 28))
    draw = ImageDraw.Draw(image)
    for row, (label, sequence) in enumerate(rows):
        y = row * 112
        draw.text((4, y + 24), label, fill="white")
        for col, t in enumerate(frames):
            x = 130 + col * 96
            tile = Image.fromarray(sequence[t])
            image.paste(tile, (x, y + 16), tile)
            draw.text((x, y), f"f{t}", fill="white")
    image.save(path)


def repetition(root):
    results = {}; rows = []
    for name, kind, cyclic, random_life in (
        ("Explosion smoke", "death", False, False),
        ("Debris smoke", "death", False, True),
        ("Firework bursts", "death", False, False),
        ("Birth Puff", "birth", False, False),
        ("Cyclic Death", "death", True, False),
    ):
        project, parent, target = make(kind, 12, 6, cyclic, True)
        s = parent.particle_settings
        s.spawn_shape = "circle"; s.radius = 32; s.origin_x = s.origin_y = 48
        s.speed_min = s.speed_max = 0
        s.gravity_enabled = s.drag_enabled = s.noise_enabled = False
        if random_life: s.lifetime_min = 4; s.lifetime_max = 12
        cs = target.particle_settings
        cs.random_start_frame = True
        if "smoke" in name:
            multi(cs, "Smoke"); cs.blend_mode = "normal"
            cs.direction_degrees = -90; cs.direction_spread_degrees = 70
        elif name == "Firework bursts":
            cs.direction_spread_degrees = 360; cs.speed_min = 1.5; cs.speed_max = 3
        clip = r._resolve_particle_clip(project, cs)
        # Synthetic animation; canonical random clip start now has a real range.
        clip.frames.extend([np.full((5, 5, 4), (255, 150, 80, 255), np.uint8),
                            np.full((5, 5, 4), (100, 180, 255, 200), np.uint8)])
        cs = template_settings(cs)
        children = r.particle_spawn_states(cs, len(clip.frames))
        parents = r.particle_spawn_states(s, len(clip.frames))
        hashes = []; signatures = []; origins = []; normalized = []
        for p in parents:
            event_frame = p.birth_frame + (p.lifetime if kind == "death" else 0)
            invocation = next(i for i in iter_invocations(parent.id, s, parents, kind, children, cs, event_frame + 2)
                              if i.key[3] == p.particle_id and i.key[2] == 0)
            assert all(c.canonical is children[c.particle_id] for c in invocation.children)
            copies = tuple(replace(c, event_origin=r.ParticleMotionPosition(48, 48, 0)) for c in invocation.children)
            frame = render_particle_trails(project, parent.as_particle_emitter(), event_frame + 2,
                                           clip, (), None, None, None, streams=[(cs, clip, copies)])
            hashes.append(digest(frame.tobytes())); normalized.append(frame)
            signatures.append([asdict(c.canonical) for c in invocation.children])
            origins.append(asdict(invocation.origin))
        assert len(set(hashes)) == 1
        assert all(value == signatures[0] for value in signatures)
        sequence = [render_layer_particles(project, parent, t) for t in range(24)]
        rows.append((name, sequence))
        # Equal-age, origin-normalized child-only images expose the repetition.
        sheet([(f"{name} slots", normalized * 2)], root / (name.replace(" ", "_") + "_normalized.png"), (0, 1, 2, 3, 4, 5))
        results[name] = dict(invocations=len(parents), unique_normalized_rgba=len(set(hashes)),
                             unique_origins=len({json.dumps(o, sort_keys=True) for o in origins}),
                             sampled_child_fields=signatures[0], origins=origins,
                             repeated="direction/speed/lifetime/rotation/clip start/speed/scale/Noise ID; local-age curves",
                             structurally_usable=True, naturalness="not automatically judged")
    sheet(rows, root / "repetition_contact_sheet.png")
    return results


def contact_diagnostic():
    rows = []
    for archetype, gravity in (("Projectile", 0), ("Rain", .1), ("Debris", .25)):
        for label, height, speed, ground in (("tuned", 20, 2, 40), ("start height", 10, 2, 40),
                                              ("velocity", 20, 3, 40), ("ground height", 20, 2, 30)):
            _, layer = fixture("Hit Spark"); s = layer.particle_settings
            s.particle_count_min = s.particle_count_max = 1
            s.origin_y = height; s.direction_degrees = 90; s.direction_spread_degrees = 0
            s.speed_min = s.speed_max = speed; s.lifetime_min = s.lifetime_max = 40
            s.gravity_enabled = gravity > 0; s.gravity_strength = gravity
            s.drag_enabled = s.noise_enabled = False
            instance = r.build_particle_instances(s, 1)[0]
            positions = [r.evaluate_particle_motion(s, instance, a / 40, particle_age=a).y for a in range(40)]
            crossing = next(a for a, y in enumerate(positions) if y >= ground)
            if label == "tuned": tuned_age = crossing
            death_y = positions[tuned_age]  # Same fixed L=tuned_age+1 workaround.
            rows.append(dict(effect=archetype, variant=label, start_y=height, speed=speed,
                             ground_y=ground, first_sample_at_or_below_ground=crossing,
                             fixed_lifetime=tuned_age + 1, death_event_frame=tuned_age + 1,
                             death_origin_y=death_y, ground_error_y=death_y - ground))
    assert all(abs(row["ground_error_y"]) > 0 for row in rows if row["variant"] != "tuned")
    return dict(method="Read-only integer-position crossing measurement, not collision implementation",
                cases=rows, arbitrary_terrain=False, moving_target=False, reusable_fixed_death=False)


def ribbon_diagnostic(root):
    rows = []; results = []
    for path in ("Curved Projectile", "Orbit", "Slash"):
        for interval in (1, 2, 4):
            project, layer = fixture("Sword Slash")
            s = layer.particle_settings
            s.particle_count_min = s.particle_count_max = 1
            s.scale_over_lifetime = Scalar(False); s.opacity_over_lifetime = Scalar(True, 1, 1)
            s.gravity_enabled = s.drag_enabled = s.noise_enabled = False
            s.trail = Trail(True, 16, interval, .9)
            s.angular_velocity_min = s.angular_velocity_max = 25 if path == "Slash" else 0
            if path == "Curved Projectile":
                s.origin_x = 12; s.origin_y = 20; s.direction_spread_degrees = 0
                s.speed_min = s.speed_max = 3; s.gravity_enabled = True; s.gravity_strength = .25
            else: s.motion = Motion(mode="orbit", center_x=0, center_y=0, radius_start=25, radius_end=25, turns=1)
            name = f"{path} I{interval}"
            output, parity = evidence(project, layer, root / name.replace(" ", "_"))
            values = []; render_layer_particles(project, layer, 12, diagnostics=values)
            centers = np.array([(v.local_x, v.local_y) for v in values])
            gaps = np.linalg.norm(np.diff(centers, axis=0), axis=1)
            instance = r.build_particle_instances(s, 1)[0]
            positions = [r.evaluate_particle_motion(s, instance, float(a) / instance.lifetime, particle_age=float(a))
                         for a in np.linspace(0, 12, 193)]
            mask = output[12][..., 3] > 0
            covered = [bool(mask[round(p.y), round(p.x)]) for p in positions]
            results.append(dict(path=path, interval=interval, **parity, stamp_count=len(values),
                                max_neighbor_center_distance=float(max(gaps, default=0)),
                                separated_beyond_5x5_diagonal=int(sum(gaps > np.sqrt(50))),
                                centerline_samples=len(covered), uncovered_centerline_samples=covered.count(False),
                                rotations=[v.rotation for v in values], continuous_geometry=False))
            rows.append((name, output))
    sheet(rows, root / "trail_interval_contact_sheet.png")
    return results


def force_and_graph():
    force = {}
    for name in ("Smoke", "Fire Ember", "Area Dust", "Rain Snow", "Magic Comet"):
        _, layer = configure(name); s = layer.particle_settings
        instance = r.build_particle_instances(s, 1)[0]
        off = replace(s, gravity_enabled=False, drag_enabled=False, noise_enabled=False)
        before = r.evaluate_particle_motion(off, instance, 10 / instance.lifetime, particle_age=10)
        after = r.evaluate_particle_motion(s, instance, 10 / instance.lifetime, particle_age=10)
        force[name] = dict(age=10, gdn_off=asdict(before), gdn_on=asdict(after),
                           positional_difference=before != after, force_field=False)
    curves = {
        "bell": Scalar(True, points=(S(0, 0), S(.5, 1), S(1, 0))),
        "hold": Scalar(True, points=(S(0, 0), S(.2, 1), S(.8, 1), S(1, 0))),
        "pulse": Scalar(True, points=(S(0, 0), S(.25, 1), S(.5, 0), S(.75, 1), S(1, 0))),
    }
    graph = {}
    for name, curve in curves.items():
        curve.validate()
        knots = [(p.time, evaluate_lifetime_scalar(curve, p.time)) for p in curve.points]
        assert all(v == p.value for (_, v), p in zip(knots, curve.points))
        graph[name] = dict(knots=knots, samples=[evaluate_lifetime_scalar(curve, t / 20) for t in range(21)])
    color = Color(True, points=(C(0, (255, 255, 255)), C(.5, (255, 255, 0)), C(1, (255, 0, 0))))
    color.validate()
    rgb = [tuple(round(evaluate_lifetime_color_component(color, t, c) * 255) for c in range(3)) for t in (0, .5, 1)]
    assert rgb == [(255, 255, 255), (255, 255, 0), (255, 0, 0)]
    graph["white_yellow_red"] = rgb
    return force, graph


def run(root):
    root.mkdir(parents=True, exist_ok=False)
    start = perf_counter()
    result = dict(version=APP_VERSION, format=FORMAT_VERSION, platform=platform.platform(),
                  native_gui_manual="수행하지 않음", production_feature_changes=0,
                  representative_fixture_count=len(NAMES), representatives={})
    rows = []
    for name in NAMES:
        project, layer = configure(name)
        output, info = evidence(project, layer, root / name.replace(" ", "_"))
        result["representatives"][name] = info; rows.append((name, output))
    sheet(rows, root / "representative_contact_sheet.png")
    result["repetition"] = repetition(root)
    result["contact"] = contact_diagnostic()
    result["ribbon"] = ribbon_diagnostic(root)
    result["force"], result["graph"] = force_and_graph()
    result["named_advanced_goals"] = GOALS
    result["candidate_impact"] = {
        candidate: dict(newly_practical_goals=[k for k, (_, c, _) in GOALS.items() if c == candidate],
                        newly_practical_count=sum(c == candidate for _, c, _ in GOALS.values()),
                        major_improvement_archetypes=names, major_improvement_count=len(names))
        for candidate, names in IMPROVEMENTS.items()
    }
    result["elapsed_seconds"] = round(perf_counter() - start, 3)
    (root / "report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k in {
        "version", "format", "representative_fixture_count", "candidate_impact", "elapsed_seconds"
    }}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
