# Effect Playback Performance

## Scope and defaults

New Project uses 600×600, 12 FPS, and 12 Frames. New blank Resource Composition uses 300×300, inherits Project FPS, and starts with the same number of frames as FPS. In both dialogs, FPS keeps the initial one-second length linked only until Frames is edited directly.

This work changes preview scheduling and display only. App version remains 0.0.04, project format remains 8, and playback cache data is never serialized. Direct render, Scrub, Bake, PNG/sequence export, and Save retain deterministic exact output.

## Audited call paths

| Stage | Resource Editor | Effect Editor before cache | Effect Editor with cache |
| --- | --- | --- | --- |
| Timer | Fixed composition/asset interval | Incremented frame per callback | Polls elapsed-time target frame |
| Exact work | Composition render in paint | Dirty sequence materialization at Play and full effect composite in paint | Worker prepares exact RGBA snapshot frames |
| Particle/2.5D | Composition source lookup/transform | Current/full resource-layer render | Same deterministic exact renderer in worker |
| Display conversion | QImage/QPixmap in paint | QImage/QPixmap in paint | Once per prepared frame on GUI thread |
| Tick UI | Canvas/timeline | Canvas/timeline plus expensive paint | Cached pixmap, playhead, frame/status only |

The principal previous Effect cost was full float alpha composition on each Canvas paint. Play could also materialize dirty resource transform sequences on the UI thread. Resource Editor usually composites fewer/smaller layers and therefore appeared smoother.

## Runtime architecture

`EffectPlaybackManager` snapshots the current Project and queues current-frame-first exact preparation on the Qt global worker pool. Workers create contiguous RGBA only. The GUI thread converts each accepted, current-generation result to QImage/QPixmap once and installs it in a runtime LRU.

The key contains Project object identity, render revision, frame index, canvas size, relevant composition/resource-transform/motion/layer visibility/opacity state, and preview identity. The cache has a 256MB hard accounting limit and evicts least-recently-used frames. A 600×600 RGBA frame is about 1.44MB; RGBA plus display-copy accounting is about 2.88MB per cached entry.

Preparation orders the current frame followed by later frames, giving a four-frame conceptual ready-ahead target without waiting for the whole sequence. Playback begins immediately. On a miss, Canvas retains the most recent ready exact frame; it never blocks the UI thread with an exact render.

Starting any Effect gizmo stops Playback, invalidates its cache generation, and sets a cooperative cancellation event. The Playback worker checks it around every exact frame, so obsolete ready-ahead work stops before consuming the rest of the sequence. Direct-manipulation current-frame workers run at Qt pool priority `+1`; Playback and idle Prewarm run at `-1`.

`QElapsedTimer` maps actual elapsed milliseconds to `floor(elapsed × FPS)`. Late callbacks skip obsolete preview frames so playback duration does not stretch. Non-loop playback stops at the final frame. Frame dropping exists only in preview display, never in render/export/save paths.

Render-affecting edits stop playback and invalidate revision/cache: pixels, composition/layers, particle/motion/2.5D, opacity, visibility, keyframes, canvas size, and timeline render properties. Selection, focus, Pan, Zoom, guide visibility, Help, and metadata-only Save do not invalidate it. Project transitions always clear it.

## Measurements

Offscreen Windows diagnostic, Python 3.13/PySide6, 600×600, 12 FPS, 12 Frames. Values are observations, not CI thresholds.

| Scenario | Exact frame generation |
| --- | ---: |
| 1 visible static layer | 23.57ms |
| 3 visible static layers | 66.72ms |
| 5 visible static layers | 104.66ms |
| Particle count 0 | 42.65ms |
| Particle count 50 | 54.50ms |
| Particle count 100 | 63.20ms |
| Resource Editor one-layer composition | 14.47ms |

Particle 100 split was approximately 20.68ms particle exact render and 42.19ms layer alpha composite. Five static layers spent approximately 105.38ms in layer alpha composite. Full NumPy→QImage→QPixmap conversion averaged 0.48ms. A direct warm QPixmap draw averaged 0.14–0.21ms, while the complete 700×700 `CanvasWidget.paintEvent` (background, checkerboard, border, and cached 600×600 frame) averaged 3.39ms.

| Playback rate | Budget | Result |
| --- | ---: | --- |
| 12 FPS | 83.33ms | 1–3 static layers and measured particles fit generation budget; 5 layers exceed it, but cached display fits easily |
| 24 FPS | 41.67ms | 1 layer fits; 3–5 layers and measured particle scenarios require ahead preparation/drop tolerance |
| 30 FPS | 33.33ms | Only the measured 1-layer static exact generation fits |
| 60 FPS | 16.67ms | Measured exact scenarios exceed budget; cached display remains far below budget |

Cache-hit tests assert zero additional effect/particle render calls and zero additional QImage/QPixmap creation. Exact RGBA tests compare cached frames with direct current-frame render, full Bake, and PNG export. Interactive 2.5D proxy tests continue to assert no full-sequence materialization during Play or drag.

## Native/GPU decision

Cached display is not the bottleneck, so the Python/PySide UI and current Canvas architecture should remain. Exact generation is the next optimization boundary: float layer alpha composite is the clearest native/vectorized candidate, followed by particle sprite raster/composite and perspective/2.5D warp for heavier projects. A renderer-only C++/Rust/GPU experiment is justified if 24–60 FPS cold generation becomes a requirement. The measurements do not justify a whole-engine rewrite.
