"""Explicit, bounded core suites. Test bodies remain owned by existing tests."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Check:
    name: str
    title: str
    purpose: str
    tests: tuple[str, ...]
    conditions: tuple[str, ...]
    timeout: float = 180
    version: int = 1

NATIVE = "tests/test_native_regression_repair.py::"
REGISTRY = {
    "ui": Check("ui", "UI Layout", "Logical control overlap, containment, disclosure and navigation (not native DPI QA)", (
        "tests/test_inspector_visual_quality.py",
        NATIVE+"test_lifetime_nested_controls_do_not_intersect",
        "tests/test_interactive_transform_proxy.py::test_gizmo_updates_only_changed_inspector_field_without_layout",
        "tests/test_v9_editor_lifecycle_integration.py::test_ui_navigation_state_does_not_dirty_project",
        "tests/test_lifecycle_prewarm_isolation.py",
        "tests/test_native_spinbox_buttons.py::test_mouse_press_hold_uses_qt_native_auto_repeat",
        "tests/test_spinbox_repeat_conditions.py",
    ), ("Qt offscreen", "KO/EN", "280/320/360 logical px", "font 100/125/150%; additional stress", "Fusion/windows11 style required", "Trail/Events/Lifetime, reveal/jump, A-B-A", "Gizmo changed-field sync: callback completion, 1000ms deadline", "Navigation Dirty0/Render0 after bounded idle completion; closed-window isolation", "SpinBox native repeat completion/release cancellation; local controlled style, not OS input QA"),version=4),
    "rotation": Check("rotation", "Rotation / FPS Sampling", "Source/Effect sampling, revolutions, seek and decoded PNG parity", tuple(NATIVE+name for name in (
        "test_rotation_quarters_resource_effect_actual_rgba", "test_change_effect_fps_12_to_24_regenerates_seek_pixels",
        "test_growing_effect_12_to_24_frames_does_not_reuse_short_base_cache", "test_particle_rotation_speed_is_source_sampling_not_angle_normalization",
    ))+("tests/test_fps_playback_semantics.py",), ("Synthetic asymmetric RGBA", "11/22 and 12/24 FPS", "360/720/-360 degrees", "Independent Resource/Effect FPS; source speed 0.5x/1x/2x", "Resource FPS Undo/Redo; source indices; pending/stale preview rejection", "Current/Full/Generated/Playback/PNG; reload"),version=2),
    "groups": Check("groups", "Group / Undo", "Domain selection, eligibility, Duplicate/Group/Ungroup and history", tuple(NATIVE+name for name in (
        "test_duplicate_multiselect_immediately_updates_group_button", "test_group_eligibility_matches_execution",
        "test_mouse_multiselect_group_state_uses_selection_not_current_index",
    )) + ("tests/test_resource_layer_group_workflow.py",), ("Synthetic root adjacency/lock/membership/transform-parent cases", "Ctrl/Shift QTest mouse", "Undo/Redo; Save/Reload")),
    "render": Check("render", "Render Parity", "Deterministic historical samples, random/reverse seek and cache dependencies", (
        "tests/test_particle_trail.py::test_parent_current_snapshot_system_surface_2_5d_parity_post_death_png",
        "tests/test_particle_trail.py::test_cache_invalidation_spawn_identity_no_rng",
        "tests/test_particle_sub_emitter.py::test_current_full_generated_playback_save_reload_png_and_transform",
        "tests/test_particle_sub_emitter.py::test_cyclic_periodicity_random_seek_and_unique_identity",
        "tests/test_particle_sub_emitter.py::test_target_dependencies_and_rename",
    ), ("Bounded synthetic Trail/Sub-emitter", "Repeat/random/reverse seek", "Decoded PNG RGBA; cache invalidation", "Elapsed time only, not a performance benchmark")),
}

# Explicit opt-in tools: inventories produce observations, not UI-quality PASS.
TOOLS = {
    "editor-inventory": ("tools/audit_editor_ux.py", "Legacy editor allocation/layout inventory (observational; saves images)"),
    "particle-workflow": ("tools/audit_particle_workflow.py", "Legacy workflow inventory/timing (observational; saves images)"),
    "capabilities": ("tools/recheck_post_v25_capabilities.py", "Extended post-v25 capability evidence; explicit, larger render audit"),
}

def select_checks(names):
    if not names or names == ["all"]:return tuple(REGISTRY.values())
    if "all" in names:raise ValueError("Use all alone or select named checks")
    if any(name not in REGISTRY for name in names):raise ValueError("Unknown check; use --list")
    return tuple(REGISTRY[name] for name in dict.fromkeys(names))
