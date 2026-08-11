# Effect Renderer Throughput

## Exact call graph

`render_exact_playback_frame` orders visible Effect slots, calls `render_effect_resource_layer_current_frame`, dispatches Single to `render_effect_composition_layer_current_frame` or Particle to `render_particle_frame`, applies `transform_rgba_frame`, then composites ordered project layers with `composite_rgba8_over_float32` and performs one final float32→RGBA8 conversion. Particle frames resolve cached clips/spawn state, evaluate motion, stable-sort by `(local_z, generation_order)`, map each sprite through `render_transformed_source`, and round each `_source_over` result to RGBA8.

## Profile and allocation findings

Profiling used `perf_counter`, existing render collectors, deterministic 600×600 fixtures, allocation sizes, and call counters. The former final layer compositor converted every 600×600 source to float32 and created multiple full-canvas alpha/RGB temporaries per layer. Five layers therefore processed 1.8 million source pixels per frame even when only a small Effect region was visible. Particle sprite mapping and common 2.5D warp already clipped mesh grids, homography sampling, and compositing to their bounding rectangles; neither created a 600×600 temporary per particle.

## Optimizations

The Effect compositor scans uint8 alpha and runs the historical float32 operation order only on inclusive non-zero-alpha bounds. Transparent results and zero-opacity sources are skipped. The representative 12-frame fixture processed 4,167 ROI pixels out of 17,280,000 possible non-skipped source pixels. A direct float32 opaque assignment was rejected because randomized profiling found possible intermediate ULP differences; reference arithmetic is retained.

Particle `_source_over` uses a verified alpha ROI. Because that stage rounds to uint8 after every sprite, fully opaque sprite ROIs can be copied exactly. Off-canvas transformed bounds already return before grid allocation. Clip and deterministic spawn caches remain unchanged; exact transform values are not quantized, and no speculative transform cache was added.

A worker-shared 64MB cache lasts for one Playback preparation only. It caches one exact frame for Single layers only when the Resource Composition has one frame, placement covers the sequence, start/end positions are equal, and the common transform has no keyframes. Animated, Particle, Motion, or keyed layers are excluded. Static intermediate composites were not cached because changing float32 grouping/order is not proven bit-exact.

Scratch/out= prototypes were not retained: ROI removal eliminated the dominant allocations, while changing expression grouping risked exact rounding and added complexity without a measured need. Alpha bounds are not persisted across edits because project pixel arrays can be mutated in place; the inexpensive scan is repeated safely.

## Before and after

Windows offscreen diagnostics, 600×600; wall time is observational rather than a CI threshold.

| Scenario | Before | After |
| --- | ---: | ---: |
| 1 sparse visible layer | 23.57ms | 5.17ms |
| 3 sparse visible layers | 66.72ms | 8.10ms |
| 5 sparse visible layers | 104.66ms | 11.10ms |
| Particle 0 | 42.65ms | 5.87ms |
| Particle 50 | 54.50ms | 16.31ms |
| Particle 100 | 63.20ms | 26.46ms |
| 12-frame five-layer Particle-100 Prebuffer | 949.52ms | 348.18ms |
| Worker 1 / Worker 2 Prebuffer | 1458 / 916ms | 414 / 354ms |

Under two-worker load, the representative exact frame averaged 52.85ms: Particle 37.61ms and final layer composite 15.24ms. Identity/Rotation Z/Rotation X-Y/Perspective common transforms measured 0.007/6.326/3.828/3.575ms for a 120×130 alpha region. Cached Canvas paint remains about 3.39ms.

## Exactness and remaining candidates

Five hundred deterministic float32 Effect composite pipelines and 500 uint8 Particle composite pipelines match the reference final RGBA exactly. Existing Direct, current/full sequence, Playback, Bake, PNG, Orbit, Helix, 2.5D, Save, Gizmo, and Prebuffer regressions also pass. First-loop miss and drop counts remain zero.

Particle raster/composite is now the largest representative cost, so a future native sprite renderer is more valuable than native final alpha composition. Native SIMD for layer ROI composition is lower priority at roughly 15ms under parallel load. Projected-quad warp is already ROI-bounded and below 7ms in the measured cases, so GPU warp is not justified. No evidence supports an application or engine rewrite.

Paused Timeline access now calls the same one-frame Particle evaluator for every Particle Resource Layer instead of trusting persisted Generated Layer pixels. This adds one current-frame render per visible Particle layer and zero full-sequence renders. ROI placement, static-layer eligibility, Spawn cache keys, stable sort, and composite arithmetic are unchanged.
