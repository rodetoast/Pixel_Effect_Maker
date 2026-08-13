# 2.5D Transform Architecture

Pixel Effect Maker exposes three deliberately separate transform stages.

| Stage | Editor / UI | What it changes | Perspective meaning |
|---|---|---|---|
| Resource Sprite 2.5D | Resource Editor, primary | Sprite appearance: X/Y tilt, local-plane Z spin, scale and pivot | Perspective of the Resource Sprite plane only; particle paths are unchanged |
| System Space Transform | Effect Editor, Advanced | The complete Resource Layer coordinate system: particle spawn positions, Motion/Orbit/Helix paths, axes and depth | Perspective of system coordinates and particle centers |
| Surface Transform | Effect Editor, Advanced / Compatibility | The flat RGBA layer after rasterization, before final Effect composition | Post-raster plane perspective retained for existing project compatibility |

For Particle placement, the conceptual order is:

```text
Resource Sprite appearance
→ local Particle Motion
→ System Space projection and depth
→ particle/resource rasterization
→ compatibility Surface Transform
→ Effect composition
```

Use Resource Sprite 2.5D for ordinary art tilt. Use System Space only when spawn positions and paths must move as one coordinate system. Surface Transform is not the default workflow for new content.

The UI hierarchy is not project data. Opening or closing Advanced does not dirty the project, invalidate playback, render frames or change FORMAT_VERSION 9 serialization.

Integrated v9 QA verifies that Resource Sprite transforms change rendered sprite RGBA without changing particle-local spawn, Orbit or Helix coordinates. System Space changes projected particle coordinates and depth; Surface Transform remains the final post-raster compatibility stage. These roles survive metadata-only save/reload and remain byte-exact across direct current-frame rendering, playback preparation, bake and PNG sequence export.
## Effect Advanced enable / bypass

Advanced ON evaluates the Effect Resource Layer's System Space and Surface Compatibility transforms. Advanced OFF evaluates both transforms as identity for rendering, guides, depth ordering and gizmos, while preserving every stored value, revision, easing and keyframe. Re-enabling Advanced restores the previous evaluated result. The optional v9 `advanced_transform_enabled` field defaults to `true` for existing projects.
