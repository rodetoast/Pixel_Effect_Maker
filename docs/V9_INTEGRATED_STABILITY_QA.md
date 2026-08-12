# v9 Integrated Production Workflow Stability QA

## QA Scope

This pass connects existing v9 production features without adding a feature, renderer, project format, build or release artifact. Automation is split between deterministic model/service integration, offscreen QTest editor integration, and repeated race/cache stress. Real Windows visual interaction remains in `MANUAL_TEST_CHECKLIST.md` and is not claimed here.

Baseline: `main` at `c19685d`, Pixel Effect Maker `v0.0.04`, `FORMAT_VERSION = 9`, 703 tests passed. Existing Architecture/UI edits and the user's untracked `테스트소스.png` were preserved; tests use generated files under pytest temp directories only.

## Representative Projects

- Static Resource: imported 28×28 RGBA PNG with transparent margins, asymmetric directional pixels, exact alpha and center pivot.
- Animated Resource: deterministic 12-frame, 12 FPS RGBA clip with per-frame color and marker movement.
- Effect: deterministic 12-frame project; integrated output uses a compact 72×72 canvas for fast exact tests, while performance smoke uses the production 600×600 canvas.
- Particle: fixed seed/count/lifetime with deterministic Linear, Orbit and Z-axis Helix settings, local perspective and diagnostics for spawn, age, local/projected XYZ, source frame and depth key.

## Integrated Workflows

The new integration tests cover:

1. PNG import → Source Asset → identity Resource Composition, with source, current Resource frame and `composition_as_clip` byte-exact.
2. Resource X/Y tilt, local Z animation and Resource Perspective across static and animated sources without changing particle-local spawn or motion coordinates.
3. Single and Particle Linear/Orbit/Helix direct-frame rendering in sequential, reverse and random access order.
4. Resource Sprite → System Space → raster → Surface compatibility → Effect composition, including transformed projected position/depth and preserved local diagnostics.
5. Direct current frame = full Resource Layer sequence; exact Playback = baked project composite = decoded PNG Sequence after save/reload.
6. Resource and Effect edits across one undo stack, Advanced/selection/zoom/pan navigation without project dirtying, and New/Open cache/transient cleanup.

## Round-trip Results

- Metadata-only save invoked one serialization and one atomic replace, with zero new full-sequence or current-frame particle renders.
- Motion metadata saved over deliberately stale generated pixels reloads with exact current-frame rendering independent of access order.
- Resource keyframes, System Space tracks/values and Surface compatibility values survive v9 save/reload with exact RGBA on all 12 frames.
- v8 `layer_transform` maps to v9 `surface_transform`; `layer_space_transform` starts at identity. Representative RGBA is byte-exact before/after v9 Save As, and the original v8 SHA-256 remains unchanged.
- Invalid JSON, non-object payloads, future format and non-finite JSON numeric input are rejected through existing `ProjectIOError` policy.

## Race Stress

Five existing worker/current-frame/gizmo suites were repeated 20 times:

```text
75 tests/run × 20 runs = 1,500 test executions
failures = 0
```

The subset includes proxy prewarm, latest-wins, request revision/generation, current-frame order, delayed worker installation, overlay persistence, frame-change rejection, Escape and 100-move gizmo paths.

## Cache and Lifecycle Results

- A/B projects were opened alternately 20 times in one MainWindow. Playback cache cleared on each transition; direct paused display matched exact render and transform cache keys belonged only to the active project layer.
- New Project stopped playback and cleared Playback, Resource base/transform and transient proxy state.
- Existing byte ceilings remain enforced for Playback, composition, transform, composite, base-image and static-render caches.
- Save does not materialize the Resource/Particle sequence.

## Performance Smoke

Wall-clock values are observations, not hard pass/fail thresholds, and are compared only with like fixtures.

| Fixture | Result |
|---|---:|
| 28×28 projective Resource transform | 0.249 ms average |
| 300×300 projective Resource transform | 12.019 ms average |
| 600×600, five-layer ROI composite | exact sparse ROI test passed |
| Particle 100 exact frame during prebuffer | 34.799 ms average |
| 600×600, 12-frame cold prebuffer | 324.639 ms wall clock |
| Cached frame install | 0.246 ms average |
| 100 gizmo moves | one latest request/current-frame render, zero full-sequence renders |

The cold prebuffer completed with zero first-loop cache misses and zero frame drops in the existing assertion path.

## Issues Found and Fixes

Two P2 existing-function regressions were found; no P0, P1 or P3 issue remains from automated QA.

1. Transform cache byte accounting retained bytes for entries removed after a Resource/base-key revision. The removal path now subtracts each evicted frame's actual byte size. A regression asserts counter equality with live cache contents and the configured budget.
2. Selecting an Effect Resource Layer called preview cleanup that invalidated warm Playback cache even when no preview existed. Cleanup now invalidates only when an active preview or preview frame set is present. Preview behavior and render-affecting invalidation remain covered.

## Automated Test Files

- `tests/test_v9_integrated_workflow.py`: 9 tests.
- `tests/test_v9_project_roundtrip_integration.py`: 8 tests.
- `tests/test_v9_editor_lifecycle_integration.py`: 4 tests.

The pass adds 21 integration tests. Skip/XFail was not used to hide a failure.

## Final Verification

```text
pytest:                    724 passed in 48.12s
race subset:              75 × 20 = 1,500 passed, failures 0
app.main --version:       Pixel Effect Maker v0.0.04
FORMAT_VERSION:           9
app.main --check:         exit 0
run_app.bat --check:      exit 0
git diff --check:         clean (line-ending warnings only)
HEAD:                     c19685d
staged / commit / tag:    0 / 0 / 0
push / build:             0 / 0
```

The sandboxed `app.main --check` could not open the normal per-user AppData log file and reported the existing logging-unavailable fallback, but the application check itself completed with exit code 0.

## Remaining Manual QA

Manual validation is still recommended for real file dialogs and application restart, Save/Discard/Cancel decisions, visible first-loop smoothness, prolonged physical mouse drag, Windows DPI 100/125/150%, Korean/English clipping/tooltips, and actual GIF/Aseprite import. See `docs/MANUAL_TEST_CHECKLIST.md`.

## Stability Judgment

Automated v9 integration is stable across Asset → Resource → Effect → Particle → Playback → Save → Reload → Bake/Export. Resource Sprite appearance, Effect System coordinates and post-raster Surface compatibility remain separated through serialization and exact rendering. The next recommended step is the bounded real-Windows manual pass, not a feature or format expansion.
