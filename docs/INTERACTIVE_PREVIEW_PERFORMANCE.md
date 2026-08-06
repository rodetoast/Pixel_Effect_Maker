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

## Exact-output boundary

Mouse Release, Escape, SpinBox `editingFinished`, and 120ms idle run one exact current-frame CPU render. Playback, Save, Bake, PNG Export, and Preview Sequence Export use the exact CPU sequence path. Proxy images never enter Project frames, serialization, or exports.
