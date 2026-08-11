# Interactive 2.5D Preview Performance

## Measured bottleneck

The checkpoint renderer was measured with an offscreen 600×600 project and five visible layers. Values are diagnostic observations, not CI thresholds.

| Stage | Calls | Average | Maximum |
| --- | ---: | ---: | ---: |
| Full-canvas alpha bounds scan | 100 | 0.970ms | 1.310ms |
| Shared projected quad | 500 | 0.018ms | 0.215ms |
| Exact NumPy transform, 130×110 alpha content | 30 | 3.458ms | 4.615ms |
| Full RGBA → QImage → QPixmap | 50 | 0.439ms | 1.975ms |
| Five-layer exact composite | 20 | 94.682ms | 97.542ms |
| Canvas paint including exact composite | 10 | 102.924ms | 105.271ms |

The repeated full project composite, not projection geometry, was the dominant interaction cost.

## Proxy path

Interaction state is UI-only. On first use it obtains the cached untransformed Base RGBA, scans alpha once, owns one cropped RGBA copy, and creates one QImage/QPixmap. The exact renderer's `projected_quad()` supplies all geometry. QPainter maps the crop with projective `QTransform`, nearest display sampling, SourceOver composition, and no SmoothPixmapTransform.

Other visible layers are composited once into Underlay and Overlay buffers. Their ordered ID signature is retained; Position Z rebuilds these buffers only after the selected layer crosses a real depth-order boundary. Detailed Particle guides are paused until finalize.

Requests are latest-wins at 33ms. Old and new projected bounds plus gizmo padding form the dirty rectangle. Screen-identical quads use 1/16-pixel comparison to suppress redundant paint, while the model retains exact floats.

## After proxy

Using the same 600×600/five-layer diagnostic:

| Stage | Calls | Average | Maximum |
| --- | ---: | ---: | ---: |
| One-time alpha/QImage/depth-buffer preparation | 1 | 84.826ms | — |
| Proxy geometry apply | 100 | 0.129ms | 0.406ms |
| Proxy full-canvas paint | 30 | 3.927ms | 7.095ms |
| 136×140 dirty-region paint | 30 | 3.117ms | 3.937ms |

The session created one Base QImage, one Base QPixmap, and one depth-buffer set. The one-time preparation is moved to interaction start; subsequent input avoids Particle Simulation, exact Homography/Sampling, full project composition, and NumPy image conversion.

## Idle prewarm completion

Resource Layer selection and final frame navigation now debounce for 80ms, then submit alpha cropping and prefix/suffix composition to the existing Qt global worker pool. A request revision makes completion latest-only. Project/layer/frame/canvas/placement/base/resource/transform/render/visibility/depth tokens are rechecked before both payload creation and GUI installation. A mouse press cancels pending work and never waits for an active worker.

The composite LRU key excludes the selected layer transform but includes the exact before/after render-array identities, opacity, visibility, and stable depth signature. It is capped at 64MB; the separate cropped-base LRU is capped at 32MB. Prewarm installation creates GUI images only on the GUI thread and does not request a repaint.

Offscreen diagnostic, 600×600 with five visible Resource Layers (one run; timings are observations, not CI limits):

| Stage | Calls | Average | Maximum / result |
| --- | ---: | ---: | ---: |
| Idle debounce | 1 | 80ms configured | — |
| Payload/layer-cache snapshot | 1 | 0.237ms | — |
| Base alpha crop | 1 | 0.986ms | — |
| Underlay alpha composite (3 layers) | 1 | 61.069ms | — |
| Overlay alpha composite (2 layers) | 1 | 40.746ms | — |
| Underlay/Overlay NumPy → QImage | 2 | 0.206ms | 0.208ms |
| Underlay/Overlay QImage → QPixmap | 2 | 0.656ms | 1.202ms |
| Proxy state installation | 1 | 2.269ms | — |
| Prewarm ready after selection | 1 | 207.107ms including debounce/poll | — |
| First mouse press, Prewarm Hit | 1 | 0.346ms | 0 composite, 0 QImage, 0 QPixmap |
| First mouse press, cold Miss | 1 | 100.089ms | 1 depth-buffer pair, 1 Base QImage/Pixmap |
| First proxy paint | 20 | 3.998ms | 10.298ms |

The cold prefix/suffix alpha composite remains the largest preparation cost, but it is now paid during idle on a worker. The synchronous cache-hit press is below the 10ms diagnostic target and performs no particle simulation, exact NumPy transform, full-layer composite, or image conversion. A miss keeps the previous synchronous fallback so input can start without waiting for stale background work.

## Exact-output boundary

Mouse Release, Escape, SpinBox `editingFinished`, and 120ms idle run one exact current-frame CPU render. Playback, Bake, PNG Export, and Preview Sequence Export use the exact CPU frame/sequence path. Ordinary Save/Save As serializes Motion metadata and existing pixels without invoking particle current/full rendering. Proxy images never enter Project frames, serialization, or exports.

Effect playback now has a separate runtime exact-frame preparation/cache path; it never stores proxy pixels in the model. Interactive press/move/release behavior and its zero-full-sequence drag guarantees remain unchanged. See `EFFECT_PLAYBACK_PERFORMANCE.md` for playback-specific measurements and invalidation rules.
