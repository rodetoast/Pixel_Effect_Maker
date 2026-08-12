# 2.5D Architecture Decision Review

> Prototype review document. This is not a final product decision and does not authorize removal of the current v9 Layer Space implementation.

## Problem

Two distinct user intentions were represented by one broad idea of “2.5D rotation”:

- System-space transformation: rotate Particle spawn, motion, guides, depth and the rendered sprites as one local coordinate system.
- Sprite appearance transformation: tilt the Resource Sprite plane while leaving Particle spawn and motion coordinates unchanged.

The current v9 Effect Layer Space implements the first intention. This prototype implements the second in Resource Editor so both can be compared in the same worktree.

## Current v9 Effect Layer Space

The Particle path is `Particle Local XYZ -> Effect Layer Space XYZ -> fixed-camera projection -> depth sort -> camera-facing billboard -> Surface Transform`. Rotation X/Y therefore changes spawn markers, Linear/Orbit/Helix paths, particle centers and transformed depth. This is coherent as a system-space tool but is not a sprite-orientation control.

Primary affected files/subsystems (13):

1. `app/models/effect_resource_layer.py` — two transform stages and serialization.
2. `app/models/project.py` — format v9 and migration gate.
3. `app/services/layer_space_transform_service.py` — shared XYZ/projection math.
4. `app/services/particle_render_service.py` — local-to-layer projection and depth sort.
5. `app/services/effect_resource_layer_render_service.py` — Single/Particle render ordering.
6. `app/services/particle_preview_service.py` — preview snapshots.
7. `app/services/effect_playback_service.py` — revision/cache relevance.
8. `app/services/interactive_gizmo_service.py` — latest-wins exact rendering.
9. `app/ui/canvas_widget.py` — projected axes, rings, guides and handles.
10. `app/ui/resource_layer_transform_panel.py` — Effect inspector.
11. `app/ui/interactive_transform_proxy.py` — Single proxy.
12. `app/ui/interactive_proxy_prewarm.py` — proxy cache/prewarm.
13. `app/ui/main_window.py` — interaction, undo and render scheduling.

Surface Transform remains a separate compatibility warp after Layer Space.

## Resource Editor Sprite 2.5D Prototype

The Resource Composition layer retains its canonical `rotation` track as Rotation Z and adds renderer/UI use of existing `rotation_x`, `rotation_y`, and `perspective_strength` track IDs. The path is:

`Source frame -> source-local plane at its pivot -> scale -> canonical local Rz spin -> Rx/Ry tilt -> fixed-camera projection -> nearest-neighbor raster -> Resource Composition`

The math uses column vectors. Effect Layer Space keeps its established `Rz @ Ry @ Rx` system-space convention. Resource Sprite 2.5D deliberately uses `Ry @ Rx @ Rz`: the rightmost local Z spin is applied first, then X/Y tilt. Consequently changing Resource Z does not change the tilted plane normal, while its local X/Y axes and sprite pixels rotate within that plane. With X=Y=0 this reduces to the legacy 2D Z rotation.

That final Composition frame becomes the Particle sprite source through `composition_as_clip()`. Particle motion evaluation never sees the Resource layer transform.

Prototype app changes are restricted to six files/subsystems:

1. `app/models/property_registry.py` — searchable Resource properties.
2. `app/services/resource_composition_render_service.py` — sprite-plane transform and raster.
3. `app/ui/resource_editor_v2/composition_canvas.py` — projected quad/axes/rings and direct manipulation.
4. `app/ui/resource_editor_v2/composition_inspector.py` — controls and X/Y/Z tool buttons.
5. `app/ui/resource_editor_v2/resource_editor_widget.py` — mode routing and undo merge IDs.
6. `app/services/localization_service.py` — labels and tooltips.

The Resource model and project serializer already support these AnimationTrack IDs, so no new storage class is required.

## A/B Semantic Difference

| Observation | A — Effect Layer Space | B — Resource Sprite 2.5D |
|---|---|---|
| Sprite appearance | Changes | Changes |
| Spawn screen position | Rotates/projects | Unchanged |
| Particle center | Rotates/projects | Unchanged |
| Motion guide | Rotates/projects | Unchanged |
| Orbit center/path | Rotates/projects | Unchanged |
| Helix center/axis/path | Rotates/projects | Unchanged |
| Depth ordering | Uses transformed Layer Space Z | Motion/system depth unchanged |
| Gizmo meaning | System coordinate frame | Selected sprite plane |
| Typical user intent | Rotate the entire effect system | Aim/tilt the art used by particles |

Automated tests compare the particle diagnostic coordinates before/after Resource X/Y/Z/Perspective and require exact equality while requiring Resource RGBA to change.

## Code Complexity

A crosses Particle evaluation, projection, depth, guides, Effect gizmo, playback caches, serializer/migration and Surface ordering. B is upstream of Particle creation and stays within Resource Composition rendering and editing. B therefore has the smaller semantic blast radius for sprite orientation.

## UX Complexity

A exposes Motion Local Perspective, Layer Space Perspective and Surface Perspective in one Effect workflow. Each changes a different coordinate stage. B allows the common workflow to read as “Resource Appearance Perspective + Particle Motion.” This is easier to predict because appearance is authored where the Resource is built.

A remains valuable for users intentionally rotating an entire effect coordinate system, especially when Orbit/Helix/depth should rotate together. It should not be described as a sprite tilt.

## Serialization Impact

- `FORMAT_VERSION` remains 9.
- Existing `rotation` remains canonical Rotation Z; existing projects keep the exact legacy 2D raster path when X/Y/Perspective are inactive.
- `rotation_z` is not exposed as a second Resource rotation and is not read by the Resource renderer.
- `rotation_x`, `rotation_y`, and `perspective_strength` already serialize inside Composition Layer `tracks`.
- No migration or new top-level key is required.

## Renderer Impact

Legacy Resource layers stay on the original one-pass 2D renderer. A layer enters the prototype path only when X/Y, Position Z, or Perspective is active. The prototype builds a local RGBA plane, reuses v9's rotation matrix/fixed-camera/homography math, and source-over composites it. Sampling remains nearest-neighbor. Output remains cropped to the existing fixed Resource Composition canvas; no automatic resize is introduced.

`horizontal_tilt` and `vertical_tilt` are not reused. They are asymmetric 2D quadrilateral approximations in `effect_render_service._destination_corners`, not the canonical Rx/Ry fixed-camera projection, and would give the Resource and Effect gizmos different mathematics.

## Particle Impact

`particle_render_service.py` and Particle settings are unchanged by this prototype. `composition_as_clip()` supplies already-oriented RGBA frames; spawn, motion center, Orbit/Helix local coordinates, layer-space depth and lifetime remain independent. Direct current-frame, full sequence, bake, preview PNG and project PNG paths are covered with the transformed Composition.

## Gizmo Impact

Resource Editor now exposes Rotate X, Rotate Y, and canonical Rotate Z buttons. The selection quad, pivot, projected XYZ axes and rotation rings all use the same `layer_space_transform_service` projection as the Resource renderer. Interaction state remains owned by Resource Editor, with its existing transient update, undo and Escape flow; it is not shared with Effect Editor.

The Resource Z ring is sampled in the transformed local plane, so X/Y tilt projects it as an ellipse. Its plane normal is invariant as Z changes. The Effect gizmo retains system-space semantics and remains a separate A/B path.

## Effect Interaction Paint and Async Install

The Effect Canvas paint order is `base exact pixmap -> interactive transform proxy -> selection/pivot overlays -> Motion guide -> Resource transform gizmo/active handle`. Gizmo and guide geometry are lightweight GUI-thread overlays and are never embedded in, or hidden by, an exact worker frame.

Exact current-frame results carry layer, frame, generation, and transform revision. If an exact result arrives before its matching underlay/overlay prewarm, the newest matching result is retained and retried immediately after prewarm installation. Older revisions remain rejected. Installing a base frame or proxy result requests repaint but does not clear the active tool, handle, transient transform, projected axes/rings, or guide; only release, Escape, project/layer changes, or the existing interaction-cancel policy may do so.

## Compatibility

- Existing Rotation Z (`rotation`) rendering is asserted pixel-exact against the old direct renderer.
- Existing animation tracks remain valid.
- Multi-frame Resource animations receive the same plane transform per frame while their source content advances.
- Transparent bounds and fixed-canvas clipping retain the current policies.
- Current v9 Layer Space, Surface Transform, migration, transformed depth and Effect gizmo remain present for A/B comparison.

## Resource Pixel Identity and Pivot

Resource pixel geometry uses source-local outer-edge coordinates. A `W × H` source occupies `[0, W) × [0, H)` as pixel cells bounded by the geometric rectangle `[0, W] × [0, H]`; a 28×28 center pivot is therefore `(14, 14)`. Alpha bounds are half-open, so opaque indexes 2..26 produce `[2, 27)`. Selection quads use those outer edges.

An unrotated, unit-scale, zero-perspective source whose `position - pivot` is integer-aligned bypasses homography and uses a clipped direct blit. This is an accuracy path: it preserves source RGBA bytes and prevents the unit-square inverse sampler from duplicating right/bottom edge samples. Rotation Z and every non-identity projective path retain their established nearest-neighbor behavior and Local Z order.

The Resource Pivot marker is a Canvas-only overlay at the projected world position of the source-local pivot. Changing local pivot coordinates preserves established Position semantics: the pivot remains at the layer position while the sprite and selection footprint move relative to it. X/Y tilt, Local Z, scale, zoom, and pan all reuse the same projected pivot math.

Non-identity rasterization projects the half-open alpha outer-edge quad, scans a half-open destination bbox at destination pixel centers, and inverse-maps only normalized coordinates in `[0,1)`. Outside samples are transparent rather than clamped to an edge texel. This keeps nearest-neighbor pixel art exact without extending right or bottom border colors. The selection quad represents the alpha outer-edge footprint; transparent source margins are intentionally not opaque raster content.

Before a Resource exists, Asset Preview displays the same source-local pivot as a Canvas-only overlay. Preview Fit/zoom/pan are camera state and do not mutate the Asset, Project dirty state, renderer, or rotation order.

In Effect Editor Move XYZ mode, the red X handle is the Resource Layer Space `position_x` control, not a Particle ellipse or Motion property. Resource transform hit-testing has priority where it visibly overlaps a Motion Guide handle. The handle moves the layer and its projected guide together; Motion-only handles retain their existing behavior elsewhere.

## Manual A/B Scenarios

1. **Slash:** A uses Effect Layer Rotation Y 45°. B uses Resource Rotation Y 45° with Effect Layer identity. Compare sprite silhouette and confirm B spawn/guide positions do not move.
2. **Animated Fire:** A uses Effect Rotation X 60°. B uses Resource Rotation X 60°. Scrub all source frames and compare the stable plane orientation.
3. **Orbit:** use the same Resource and Orbit settings. A should rotate the Orbit path; B must retain the original center/path and alter only each sprite's appearance.
4. **Helix:** A should rotate/project the Helix coordinate system. B must preserve center, axis and path while tilting the sprite frames.

For each scenario compare current frame, playback, bake and PNG output, then inspect the Resource and Effect gizmos to confirm their different meanings.

## Recommendation

Recommend **F — Resource Editor Sprite 2.5D as the default appearance workflow, with Effect System Space retained as an explicitly Advanced feature**.

Reasoning: B directly matches the common “tilt the particle art” intent with fewer affected subsystems and fewer simultaneous perspective concepts. A remains technically coherent and useful when the user truly wants spawn, Orbit/Helix, depth and guides to rotate as a system. The two should use distinct names and UI grouping.

## Final Product Decision

Decision F is now reflected in the product hierarchy:

- **Resource Editor Sprite 2.5D** is the primary appearance workflow. X/Y tilt, local-plane Z spin, scale, pivot and Sprite Perspective change how the resource image looks without moving particle centers or paths.
- **Effect Editor System Space Transform** remains available under the collapsed Advanced section. It transforms the full layer coordinate system, including particle spawn positions, Motion paths, axes and depth.
- **Surface Transform (Compatibility)** remains under Advanced for post-raster v8/v9 compatibility. A non-identity value is indicated even while Advanced is collapsed.

This decision changes labels, help and Inspector hierarchy only. FORMAT_VERSION remains 9; serializer keys, transform evaluation order, particle simulation and renderer output are unchanged.
