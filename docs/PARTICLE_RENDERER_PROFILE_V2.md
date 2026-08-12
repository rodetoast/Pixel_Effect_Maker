# Particle Renderer Profile V2

## Scope and Checkpoint

This is a measured CPU-only optimization pass. It does not add a Particle feature, change Playback architecture, alter project format, add a dependency, or implement GPU/native rendering.

The v9 Architecture and Integrated QA state was first committed locally as:

```text
0867107 Finalize v9 architecture and integrated stability
724 passed
Pixel Effect Maker v0.0.04
FORMAT_VERSION 9
```

The user's untracked `테스트소스.png` was excluded. The Particle changes documented below remain uncommitted and unstaged.

## Fixed Fixture and Method

All before/after values use the same deterministic fixtures:

- Canvas: 600×600, 12 FPS, 12 frames.
- Sprite: directional asymmetric 28×28 RGBA with transparent margin.
- Particle cases: 10 Linear; 100 Linear; 100 Orbit; 100 Helix.
- Resource 2.5D case: Particle 100 Orbit plus non-zero Resource X/Y tilt, local Z spin and Perspective.
- Fixed seed, lifetime, count, scale/rotation ranges and frame 6.

Cold measurements invalidate Resource, composition and spawn caches before each of 7 samples. Warm measurements discard one warm-up then collect 100 samples for Particle 10 and 60 for Particle 100. The report records median, average, min and max; wall-clock values are informational, never test thresholds. `cProfile` covers 30 warm Particle-100 Orbit frames. `tracemalloc` records one representative frame.

## Baseline

| Fixture | Cold median / average / min / max (ms) | Warm median / average / min / max (ms) |
|---|---:|---:|
| Particle 10 Linear | 2.923 / 2.966 / 2.576 / 3.719 | 2.473 / 2.617 / 2.377 / 3.629 |
| Particle 100 Linear | 24.847 / 24.971 / 23.848 / 26.218 | 23.821 / 23.748 / 22.064 / 26.674 |
| Particle 100 Orbit | 24.669 / 24.467 / 22.995 / 25.458 | 25.361 / 25.386 / 22.435 / 29.912 |
| Particle 100 Helix | 27.173 / 27.258 / 25.885 / 29.354 | 26.621 / 26.855 / 24.434 / 31.521 |
| Particle 100 Resource 2.5D | 31.742 / 31.736 / 30.161 / 32.775 | 27.127 / 27.359 / 24.320 / 32.842 |

Previous like-for-like 600×600 cold prebuffer smoke: 324.639 ms wall, 34.799 ms Particle stage.

## Baseline Hotspots

The following are cumulative profile shares of the 1,419.654 ms 30-frame profile and therefore overlap where a child is included in a parent:

| Rank | Stage | Calls | Cumulative time | Share |
|---|---|---:|---:|---:|
| 1 | Per-particle `render_transformed_source` | 3,000 | 980.139 ms | 69.0% |
| 2 | Particle ROI `_source_over` | 3,000 | 278.223 ms | 19.6% |
| 3 | System Space single-point projection | 3,000 | 277.498 ms | 19.5% |
| 4 | Homography construction/solve | 3,000 | 133.673 ms | 9.4% |
| 5 | Destination corner geometry | 3,000 | 106.601 ms | 7.5% |

Call-count audit for one Particle-100 Orbit frame:

```text
source-frame resolve:       100
transformed sprite render:  100
destination corners:        100
homography solve:            100
matrix inverse:              100
alpha composite:             100
```

Resource/spawn reuse was already effective: one cold miss followed by 60 hits for both caches. The expensive Resource Composition/Resource 2.5D appearance was frame-level work, not repeated 100 times. No new cache was justified.

Allocation evidence matched the call profile: 3,000 meshgrids, stacked homogeneous point grids, sampled RGBA temporaries, float alpha-composite temporaries, 45,000 `np.array` calls, and repeated transform dataclass construction. Representative traced peak was 1,689,758 bytes. PIL/QImage conversion was not in this renderer path.

## Accepted Optimization A — Frame Evaluation and Batched Projection

Root cause: Motion perspective and the same Layer Space transform were evaluated for every particle. Each center was wrapped in a one-point NumPy array and passed through several allocation-heavy projection layers.

Change:

- Evaluate Motion and Layer Space once per effect frame.
- Preserve the existing scalar motion evaluator but provide its evaluated Motion value.
- Collect visible local centers and project them in one call through the existing shared Layer Space math.

Warm median after A: Linear 21.569 ms, Orbit 20.299 ms, Helix 19.810 ms, Resource 2.5D 20.254 ms. Improvement against baseline: 9.5%, 20.0%, 25.6%, and 25.3%. All 60 saved baseline frames remained byte-exact; the related 32-test semantics subset passed.

## Accepted Optimization B — Translation Nearest Sampler

Root cause: unrotated, unit-scale particles at fractional positions still built a quadrilateral, solved/inverted a homography, allocated a 2D meshgrid and stacked homogeneous coordinates. For translation, U and V are independent 1D axes.

Change:

- Keep the existing integer-aligned identity blit.
- Add a translation-only nearest path using one X vector and one Y vector.
- Retain the original projective sampler as an explicit exact fallback/reference.

Particle 100 Linear warm median fell from 23.821 to 9.732 ms after B (59.1%). Orbit/Helix still rotated particles and correctly stayed on the general path at this stage. Baseline RGBA remained byte-exact.

## Accepted Optimization C — Analytic Affine Inverse

Root cause: ordinary particle rotation and scale are affine but paid for an 8-coefficient projective solve, 3×3 inverse, meshgrid and stacked points for every particle.

Change:

- For zero tilt/perspective, derive U/V from the two destination axes and one scalar determinant.
- Allocate broadcast X/Y vectors instead of meshgrid + stacked XYZ.
- Retain projective sampling unchanged for actual tilt/perspective.

The affine/translation paths were compared byte-for-byte with the prior projective path for 1,000 deterministic randomized cases covering source sizes, pivot outside/inside bounds, position, rotation, scale, opacity, canvas edges and partial offscreen placement. Failures: 0.

## Final Performance

| Fixture | Final cold median / average / min / max (ms) | Final warm median / average / min / max (ms) | Warm median improvement |
|---|---:|---:|---:|
| Particle 10 Linear | 1.411 / 1.480 / 1.185 / 1.940 | 1.126 / 1.275 / 1.058 / 3.836 | 54.5% |
| Particle 100 Linear | 10.015 / 10.087 / 9.867 / 10.593 | 9.561 / 9.802 / 9.146 / 11.996 | 59.9% |
| Particle 100 Orbit | 14.382 / 14.612 / 13.562 / 16.021 | 13.832 / 13.782 / 12.679 / 16.244 | 45.5% |
| Particle 100 Helix | 14.023 / 14.015 / 13.813 / 14.302 | 13.786 / 14.097 / 12.689 / 19.278 | 48.2% |
| Particle 100 Resource 2.5D | 19.032 / 19.452 / 18.268 / 20.987 | 14.227 / 14.376 / 13.079 / 17.095 | 47.6% |

Final like-for-like 600×600 cold prebuffer smoke: 174.737 ms wall and 14.715 ms Particle stage, reductions of 46.2% and 57.7%. Cached frame installation remained a GUI/cache operation (0.322 ms in this run), outside the changed Particle raster path.

The final profile made 100 transformed-sprite and alpha-composite calls per frame but zero homography solves/inverses for the representative Orbit fixture. Representative traced peak was 1,649,871 bytes, 2.4% below baseline.

## Cache and Memory

No new cache was added, so there is no new key, lock, eviction path, budget or byte counter. Existing Resource/spawn caches remain project/revision/settings aware and bounded by entry count. Existing composition, Effect base/transform, Playback, composite and image byte budgets are unchanged. Project-switch and cache byte-counter tests remain part of the full suite.

A Particle-500 Resource-2.5D smoke retained one Resource entry and one spawn entry against the existing 16/32 entry limits. Its representative traced peak was 2,284,222 bytes; no cache budget or byte counter was exceeded.

## Correctness

Hard regressions cover:

- Identity direct blit including transparent RGB.
- Integer and fractional translation.
- Rotation, non-uniform scale and opacity.
- Four partial-offscreen edges.
- 1,000 randomized affine-vs-projective exact cases.
- Animated Resource plus Resource X/Y, local Z and Perspective.
- Linear, Orbit and Helix current/full/playback parity.
- Existing current-frame, access-order, Resource-coordinate independence, Bake, PNG and PNG Sequence suites.

Nearest-only sampling, half-open source bounds, destination coordinate conventions, outside transparency, `Ry @ Rx @ Rz` Resource local-Z semantics, particle coordinates and stable depth ordering are unchanged.

## Race and Final Verification

Because this pass changed neither cache ownership nor worker architecture, the requested reduced race policy was used. The final clean subset contained prewarm, latest-wins, revision/generation, current-frame, gizmo overlay and the six new exact renderer tests:

```text
81 tests/run × 5 runs = 405 passed
failures = 0
```

During a separate longer exploratory repeat, the existing Inspector test once missed its fixed 40 ms QTimer deadline after eight clean runs (`records=[]`). There was no model/RGBA mismatch, the Renderer path is unrelated, and no UI production code was changed. The bounded final run and complete suite both passed.

```text
pytest:                    730 passed in 49.80s
app.main --version:       Pixel Effect Maker v0.0.04
FORMAT_VERSION:           9
app.main --check:         exit 0 (sandbox AppData logging fallback reported)
run_app.bat --check:      exit 0
git diff --check:         clean (line-ending warnings only)
checkpoint HEAD:          0867107
optimization staged:      0
optimization commit:      0
push / tag / build:       0 / 0 / 0
```

## Rejected or Deferred Candidates

- Sprite-appearance cache: rejected because existing Resource Composition/clip caching already produced 60 hits after one miss, while the profile located the cost in particle-level affine placement.
- Grid-shape cache: rejected because analytic translation/affine sampling removed the large grid construction without adding a shared cache or thread-safety burden.
- Depth-sort rewrite: rejected; it was not a leading hotspot at Particle 100.
- Float-composite semantic change: rejected; exact straight-alpha rounding remains unchanged.
- Conservative pre-transform offscreen culling: deferred because the measured gain was already substantial and aggressive bounds risk visible-edge errors.

## GPU and Native Decision

GPU is not currently required. Measured CPU duplication was removable with small NumPy/Python changes, producing roughly 46–60% representative improvement without changing architecture. A native renderer is also not justified for the current Particle-100 production target. The largest remaining measured hotspot is per-particle affine sampling plus exact straight-alpha ROI composition; it should be revisited only if future real projects exceed the current scale after Keyframe Editing is stabilized.

## Next Priority

The next product task is Keyframe Editing normalization. Long Sequence Playback, additional format stabilization, Early Preview #2 and release/build work remain deferred.
