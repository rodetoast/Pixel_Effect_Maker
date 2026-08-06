# Resource Layer 2.5D Transform

## Scope

The final RGBA output of a Resource Layer is treated as one flat plane. This is not a mesh or volumetric 3D system. Single and Particle Emission keep their content controls; the common transform runs after either renderer and before Effect Composition.

## Coordinates and order

- X+ points right, Y+ points down, and Z+ points toward the viewer.
- Rotation Z keeps the existing positive screen-plane direction.
- Positive Rotation X tilts the bottom edge toward the viewer. Positive Rotation Y tilts the left edge toward the viewer under the Y-down convention.
- Local points use `T × Rz × Ry × Rx × S`, around the canvas center plus Pivot X/Y.
- Pivot is a static center-relative offset. Other common properties use the existing `AnimationTrack`, `Keyframe`, and easing types.

## Projection

Perspective Strength 0 is orthographic. Rotation X/Y still foreshortens the plane, but Position Z does not resize it. For `s > 0`:

```text
focal_length = max(canvas_width, canvas_height) × 2 / clamp(s, 0.000001, 1)
projected_x = x × focal_length / (focal_length - z)
projected_y = y × focal_length / (focal_length - z)
```

The renderer rejects corners at or behind `0.05 × focal_length`, clips work to the project canvas, and returns transparent output for a degenerate homography. Inverse mapping uses deterministic nearest-neighbor RGBA sampling. Identity returns the original array without resampling.

## Depth, editing, and limits

The Effect Inspector is responsive from an approximately 280px usable width. Transform modes use a two-column grid; numeric input occupies the remaining field width, while Easing and Keyframe controls sit on a second line. Single Path and Particle groups use the same shrinking two-column form policy. Horizontal scrolling is disabled only after the content minimum width is made smaller than the viewport; vertical scrolling remains available.

Resource Layers are stably sorted by evaluated Position Z per frame. Smaller Z composites first and larger Z appears in front; equal Z preserves timeline order. Degree values interpolate normally without shortest-angle wrapping, preserving full rotations.

The Inspector provides all common values, explicit keyframe buttons, and base-only Reset. Canvas controls provide Move XYZ (blue diagonal Z Depth Handle), Rotate XYZ, Scale, and Pivot. Shift snaps rotation to 15 degrees; Escape cancels a drag; a completed drag creates one Undo command. Single and Particle content-guide points share the renderer projection and inverse projection. Guides never enter Bake or export.

Particle Emission is simulated in 2D, then its whole RGBA result is transformed as one plane. Individual particles have no Z, Rotation X/Y, 3D velocity, or internal depth sorting. This common plane and animated Z are the basis for later Orbit/Helix motion.

## Interactive cache policy

Single/Particle settings, project canvas/FPS, project identity, and Resource Composition revisions key the base RGBA cache. Common Position/Rotation/Scale/Opacity/Pivot/Perspective values are deliberately excluded. A separate per-frame cache combines the base revision with evaluated 2.5D values.

Transform changes use a 33ms latest-wins request. During numeric input or gizmo drag the exact generated pixels remain untouched: a cropped Base QPixmap is mapped to the shared projected quad with `QTransform`, SmoothPixmapTransform disabled, and SourceOver composition. Particle simulation, Resource Composition rendering, other layer bases, and the Inspector widget tree remain warm.

The Canvas caches one alpha scan, crop copy, QImage, and QPixmap for each Layer/Base/Frame token. It also fixes all layers behind and in front of the selected layer into Underlay/Overlay pixmaps. Position Z only rebuilds these buffers when the before/after layer-ID signature changes. A repeated screen quad is quantized to 1/16 display pixel for paint suppression without rounding model values.

The union of old/new projected bounds and gizmo padding is passed to `QWidget.update(rect)`. Release, Escape, `editingFinished`, or a 120ms idle boundary runs one exact current-frame transform and removes the proxy. Playback, Save, Bake, and Export materialize exact CPU frames from the same Base cache. Guide projection math is shared; detailed Particle guides and Ghosts are deferred while the proxy is active.
