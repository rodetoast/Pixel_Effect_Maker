# Effect Gizmo Performance

## Interaction contract

Effect Editor 2.5D, Single path, Particle emission, Orbit, and Helix handles share one rule: input and guide geometry update first; a transient layer snapshot is rendered at most once per 33ms; the Project model is committed once on release. Escape drops the snapshot without Undo or exact rendering. Release, Undo, and Redo install one deterministic exact current frame.

The worker renders only the selected Resource Layer's current frame. It never renders a full sequence and never recomposites unrelated layers. Cached Underlay/Overlay pixmaps provide the stable depth partitions. A cold miss keeps the handle live while low-priority Prewarm produces those buffers; it does not fall back to GUI-thread composition.

## Scheduling order

| Work | Qt pool priority | Cancellation / coalescing |
| --- | ---: | --- |
| Current interactive frame | +1 | 33ms latest-wins revision |
| Release exact current frame | +1 | immediate, latest revision |
| Playback ready-ahead | -1 | cooperative event per exact frame |
| Idle proxy Prewarm | -1 | cooperative event between Base and composites |

Inspector value synchronization is limited to one 33ms update and reuses existing widgets. Canvas invalidation uses the union of old/new selected bounds, guide, and gizmo padding; it does not request a full repaint from the Resource Layer drag path.

## Regression evidence

The automated interaction fixture exercises 100 consecutive 2.5D mouse moves and verifies transient model state, one Undo command, one release exact render, unchanged Particle simulation/full-sequence counters, one cached Base QImage/QPixmap, and bounded proxy paint/apply counts. Orbit/Helix composite tests verify stable spawn-cache misses, reused Underlay/Overlay objects, and a dirty rectangle smaller than the Canvas. Worker tests verify `+1` interactive priority and that invalidating Playback stops remaining exact frames.

The earlier 600×600/five-layer diagnostic identified the old cold press at 100.089ms, almost entirely synchronous depth composition, while a warm press was 0.346ms. The optimized cold path no longer performs that work on press; cold and warm presses now differ only in whether an already prepared proxy can be painted immediately. Timing values remain diagnostics rather than CI thresholds because offscreen Qt scheduling varies by host.

## Rotation identifier regression

The visible and hit-test handle identifiers are `rotate_x`, `rotate_y`, and `rotate_z`, while the model fields are `rotation_x`, `rotation_y`, and `rotation_z`. The original 2.5D interaction assigned the handle identifier directly with `setattr`, creating unused dynamic attributes; Mouse Move and signals ran, but the Inspector, evaluated transform, and Proxy continued reading zero. One shared handle-to-property mapping now owns the translation and changed-field list. If a current-frame key already exists, Rotation edits that key, matching the Inspector policy; otherwise it edits the base property.

This bug existed before `6b79b37 Optimize effect editor gizmo interaction`; the transient optimization preserved rather than introduced it. X/Y can also become exactly edge-on, where Qt legitimately cannot build an invertible projective mapping. That one intermediate proxy pose is skipped safely instead of raising from `None.isInvertible()`; subsequent pointer positions continue normally.

Offscreen QTest presses the painted handle and sends the full Canvas input path for all three axes. Each 100-move run records 100 canonical rotation updates with zero Particle current/full renders, zero new Base QImage/QPixmap, zero Inspector rebuild, and zero Timeline rebuild. Release commits once, adds one Undo command, and installs one exact current frame; Escape commits and renders nothing.

## Exact boundaries

Interactive RGBA is runtime-only. Save and project JSON never include it. Playback, Bake, PNG export, and sequence export continue to use exact CPU renderers. App version remains `0.0.04` and project format remains `8`.
