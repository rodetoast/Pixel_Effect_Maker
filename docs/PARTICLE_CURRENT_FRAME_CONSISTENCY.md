# Particle Current-frame Consistency

## Symptom and reproduction

Playback was correct, but paused Timeline clicks could show some particles at an old Spawn/origin position. A deterministic reproduction bakes an Orbit layer with radius zero, changes only Motion metadata, saves without sequence materialization, reloads, and compares all 24 persisted frames with direct exact frames. Frame 0 agrees while later moving frames diverge.

## Root cause

Particle math, Spawn RNG/cache, ROI placement, and Playback were correct. Ordinary Save intentionally persists Motion metadata without materializing a Particle sequence. Persisted Generated Layer pixels are therefore cache/bake artifacts and can represent an earlier Motion revision. The paused Canvas composed those buffers and only repaired layers listed in the session-local `_dirty_particle_motion_layers`; that set is not serialized and is empty after reload.

This predates the current Renderer Throughput ROI/static-cache pass. Particle layers are explicitly excluded from the static Playback cache, and the exact Particle ROI destination is calculated from the evaluated center.

## Frame and state semantics

Timeline columns and `current_frame` use 0-based indices internally; labels display `index + 1`. `birth_frame` is also 0-based. For a visible particle, `age = effect_frame - birth_frame` and motion receives `normalized_age = age / lifetime`; these established semantics are unchanged.

Spawn cache values are tuples of frozen `ParticleInstance` objects. Its key is the serialized Particle settings excluding Motion and output frame count, plus clip length: Motion never alters spawn randomness, and output duration does not alter a particle identity. Evaluation writes only local values. An optional diagnostic collector records immutable particle ID/order, spawn/lifetime/age, normalized age, source frame, projected XYZ, rotation, scale, opacity, and depth key; production calls pay only a `None` branch.

## Current-frame invariant

On paused Timeline selection, MainWindow directly evaluates one requested frame for every Particle Resource Layer and installs those exact pixels before Canvas composition. It never renders another frame or materializes a sequence. Linear, Orbit, and Helix direct frames are swept against full sequence and independently rendered Playback RGBA for frames 0–23. Sequential, reverse, fixed-seed random/jump, and repeated access return identical RGBA.

## Cache and worker audit

| Cache/state | Key / policy | Frame safe | Mutation safe |
| --- | --- | --- | --- |
| Spawn state | settings without Motion/output count + clip length | Frame-independent by design | frozen tuple/items |
| Resource clip | project/resource identity + source identity or composition revision | clip contains all source frames | read-only evaluation |
| Resource base | layer + settings/project/resource revisions | full sequence or direct API separation | render outputs not mutated by evaluator |
| Transform | layer/base key + frame + exact transform values | yes | output-owned |
| Playback | project/revision/frame/canvas/relevant revisions/preview | yes | snapshot + owned RGBA |
| Static Playback layer | Single-only conservative settings/resource/transform key | Particle is never eligible | preparation lifetime |
| Gizmo proxy/prewarm | project/layer/frame/base/resource/transform/depth revisions | request frame rechecked | latest-wins |

Timeline movement cancels pending Gizmo work. Result installation also requires both the same Project identity and current requested frame, so out-of-order completion cannot install an old frame. No Playback cache pixels are copied into paused state.

## Regression coverage

Automated offscreen tests cover all-frame direct/full/Playback parity for Linear, Orbit, and Helix; order independence; repeated frames; immutable Spawn state; spawn/lifetime boundary ages; Particle diagnostic fields; metadata round-trip reproduction; real Timeline cell selection and Canvas RGBA; zero full-sequence fallback; and stale Gizmo result rejection. Existing ROI, static-cache exclusion, Playback/Bake/PNG, Save, and Gizmo performance suites remain authoritative for their respective boundaries.
