# Effect Playback Prebuffer

## State machine

Effect playback uses `STOPPED → PREPARING → PLAYING`. Play first submits exact RGBA preparation; the `QElapsedTimer` starts only when the required keys are present. Preparation wait time therefore never advances the animation. Stop, render edits, project transitions, window close, and Effect gizmo input cancel the worker generation cooperatively and reject late results.

## Buffer policy

Sequences of at most 30 frames use full prebuffer when `width × height × 4 × 2 × frames` fits the 256MB LRU accounting budget. Every frame is ready before Clock start, including Frame 0 across a loop boundary. The short-sequence timer displays cached frames sequentially, giving the first loop zero cache underruns and zero frame drops.

Longer or over-budget sequences require `clamp(ceil(FPS × 0.5), 4, 15)` frames beginning at the current frame. Looping order wraps through Frame 0; non-loop playback stops on the last frame. Remaining frames continue rendering ahead. An underrun holds the most recent exact pixmap and never invokes an exact renderer on the GUI thread.

## Scheduling and installation

Two low-priority Qt pool workers share one read-only Project snapshot. Before Renderer ROI optimization, the 600×600/five-layer/Particle-100 diagnostic measured about 950ms; the same fixture now measures about 348ms. Worker 1/2 totals improved from 1458/916ms to about 414/354ms. A preparation-lifetime 64MB static Single-layer cache is shared by both workers. Playback and Prewarm remain priority `-1`.

The GUI poll installs at most four completed frames per pass. Timeline status reports `Preparing playback… n / total` or `재생 준비 중… n / total`. Cache-ready checks use direct key membership rather than scanning the LRU.

## Cache and exact output

Stop preserves already installed matching frames, so a warm replay starts immediately and schedules zero renders. Selection, Pan, Zoom, Guide visibility, focus, Help, and metadata-only Save retain the cache. Pixel, composition, Resource Layer, Particle, Motion, 2.5D, opacity, visibility, keyframe, and canvas changes invalidate it.

Playback cache frames remain identical to the direct exact renderer, Bake, and PNG export. Cache, state, progress, and frame-drop diagnostics are runtime-only and never enter project JSON. App version remains `0.0.04`; project format remains `8`.
