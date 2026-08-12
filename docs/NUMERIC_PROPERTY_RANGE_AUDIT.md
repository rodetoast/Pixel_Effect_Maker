# Numeric Property Range Audit

Audit scope: numeric controls in the Effect Resource Layer/Particle inspector and Resource Editor V2. All controls use bounded Qt SpinBoxes, so Arrow, keyboard, focused wheel, and programmatic `setValue` are clamped before a value signal reaches the model. JSON load passes through the listed model constructors; non-finite project numbers are rejected by project validation.

| Property group | UI widget | Min | Max | Step | Decimals | Model / serializer boundary |
|---|---|---:|---:|---:|---:|---|
| Effect Layer/Surface opacity | QDoubleSpinBox | 0 | 1 | .05 | 3 | `EffectLayerTransform3D` clamps 0..1 on construct/set/load |
| Effect Layer/Surface perspective | QDoubleSpinBox | 0 | 1 | .05 | 3 | `EffectLayerTransform3D` clamps 0..1 on construct/set/load |
| Particle opacity start/end | QDoubleSpinBox | 0 | 1 | .05 | 3 | `ParticleEmitterSettings` rejects outside 0..1 on construct/load |
| Motion local perspective | QDoubleSpinBox | 0 | 1 | .05 | 3 | `ParticleMotionSettings` rejects outside 0..1, including keyframes |
| Resource Composition opacity | QDoubleSpinBox (%) | 0 | 100 | 5 | 3 | divided by 100; canonical track value is 0..1 |
| Resource Composition perspective | QDoubleSpinBox | 0 | 1 | .05 | 3 | canonical `perspective_strength`; finite project validation |
| Effect position X/Y, pivot X/Y | QDoubleSpinBox | -8192 | 8192 | 1 | 3 | finite transform values |
| Effect position Z | QDoubleSpinBox | -4096 | 4096 | 1 | 3 | finite transform value |
| Effect rotation X/Y/Z | QDoubleSpinBox (°) | -36000 | 36000 | 1 | 3 | finite transform value |
| Effect scale X/Y | QDoubleSpinBox | .01 | 100 | .05 | 3 | model clamps minimum .01; finite |
| Particle output/start/duration | QSpinBox | 1/0/1 | 512/511/512 | 1 | 0 | model requires valid positive/frame ranges |
| Particle count min/max | QSpinBox | 0 | 4096 | 1 | 0 | model requires non-negative ordered range |
| Spawn positions/end points | QDoubleSpinBox | -4096 | 4096 | 1 | 3 | finite model values |
| Spawn radius/box size | QDoubleSpinBox | 0 | 4096 | 1 | 3 | model requires non-negative values |
| Spawn/direction angles | QDoubleSpinBox (°) | -3600 | 3600 | 1 | 3 | finite model values |
| Direction spread | QDoubleSpinBox (°) | 0 | 360 | 1 | 3 | model range 0..360 |
| Motion center/axis range | QDoubleSpinBox | -4096 | 4096 | 1 | 3 | finite model/keyframe values |
| Motion radius start/end | QDoubleSpinBox | 0 | 4096 | 1 | 3 | model/keyframes reject negative values |
| Motion ellipse X/Y | QDoubleSpinBox | 0 | 16 | 1 | 3 | model rejects negative values |
| Motion start angle | QDoubleSpinBox (°) | -36000 | 36000 | 1 | 3 | finite model/keyframe value |
| Motion turns | QDoubleSpinBox (turns/회) | -100 | 100 | 1 | 3 | finite model/keyframe value |
| Motion phase spread | QDoubleSpinBox (°) | 0 | 3600 | 1 | 3 | finite model value |
| Motion plane rotation | QDoubleSpinBox (°) | -3600 | 3600 | 1 | 3 | finite model value |
| Particle speed | QDoubleSpinBox | 0 | 1024 | 1 | 3 | model requires ordered non-negative range |
| Lifetime | QSpinBox | 1 | 512 | 1 | 0 | model requires ordered positive range |
| Particle scale / clip speed | QDoubleSpinBox | .01 | 16 | 1 | 3 | model requires ordered positive range |
| Particle rotation/angular velocity | QDoubleSpinBox (°) | -3600 | 3600 | 1 | 3 | finite ordered ranges |
| Start delay | QSpinBox | 0 | 512 | 1 | 0 | model requires ordered non-negative range |
| Seed | QSpinBox | -2147483647 | 2147483647 | 1 | 0 | integer serialization |
| Resource output/layer pivot | QDoubleSpinBox | -4096 | 4096 | 1 | 2/3 | finite composition values |
| Resource layer start/end | QSpinBox | 0 | 511 | 1 | 0 | layer model enforces end >= start |
| Resource position/rotation/scale track | QDoubleSpinBox | -4096 | 4096 | 1 | 3 | finite track values; scale display converts percent to canonical factor |

The central metadata in `NUMERIC_PROPERTY_SPECS` owns the four high-risk normalized/percentage domains: normalized opacity, normalized perspective, Resource opacity percent, and Resource perspective. Other established broad authoring ranges remain local to their existing panels to avoid an unrelated property-system rewrite.

Runtime log review for 2026-08-12 found no recorded 1.05/range `ValueError`. It did identify the actual uncaught MainWindow callback failure: Qt could not find `MainWindow::_undo_index_changed(int)`. The callback is now declared with `@Slot(int)` and has a meta-object regression test. This finding does not weaken the bounded-input fix: both UI clamping and model trust-boundary validation are tested independently.
