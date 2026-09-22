# Pixel Effect Maker — Effect Authoring Capability Audit

## 기준과 결론

- Audited: **v0.0.15 / FORMAT_VERSION 12**, 2026-09-08 시작, 2026-09-10 보고 마무리.
- Project: `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`.
- HEAD: `1bfd865c6396565b9c43d541613b5a58ef590cd9`, main.
- Working tree: Resource Clip / Overscan 변경이 있는 상태를 감사했다. 해당 변경은 수정하지 않았다.
- 이 문서의 최초 감사 산출물은 이 문서와 `tools/audit_effect_authoring.py`였고 `baff65b`에 checkpoint됐다. 아래 matrix와 결론은 v0.0.19 Gravity 구현 결과에 맞춰 갱신했다.
- 코드 추적, 기존 자동 테스트, 합성 fixture, offscreen Inspector introspection을 사용했다. **실제 GUI 수동 제작/시각 QA는 수행하지 않았다.** 외부 제품의 기능 수를 목표로 삼지 않았으며 외부 reference는 사용하지 않았다.

제품 정의: 2D/Pixel Art/Sprite 기반 게임용 이펙트를 Animation·Particle·Layer로 조합하고 엔진에 가져갈 이미지로 출력하는 제작툴. 범용 영상 편집기나 Full 3D 엔진이 아니다.

현재는 **레이어 애니메이션 편집 기반은 강하고, 절차적 Particle 표현력은 중간 단계**다. v0.0.16 uniform Scale, v0.0.17 RGB Color over Lifetime, v0.0.18 Normal/Additive에 이어 v0.0.19에서 signed constant Gravity를 추가했다. 남은 큰 표현력 병목은 (1) Drag와 Noise/Turbulence, (2) multi-point lifetime curve, (3) trail/orientation이다. 별도의 납품 병목은 Sprite Sheet/engine metadata 부재다.

v0.0.19의 **Gravity**는 각 Particle의 실제 0-based frame age에 `0.5 × g × age²`를 적용하는 analytic local-Y contribution이다. Linear/Orbit/Helix base path 뒤, 기존 Layer/Parent 2.5D와 Surface 변환 전에 합성되며 direct seek와 export가 상태 이력 없이 동일하다. 정의한 constant Gravity end-to-end 경로는 COMPLETE지만 Natural Motion 전체는 Drag와 Noise/Turbulence가 없어 PARTIAL이다.

## 판정 방법 / 증거 인덱스

상태: COMPLETE(명시한 좁은 범위의 end-to-end 경로와 테스트 확인), PARTIAL(범위/접근/검증 제한), MISSING(모델·UI·실행 경로 없음), BUGGY(재현 결함), UI_ONLY, MODEL_ONLY(UI에 없는 모델/실행 지원 포함), RENDER_ONLY, EXPORT_GAP, NOT_APPLICABLE. 이번 감사에서 UI_ONLY/RENDER_ONLY/EXPORT_GAP에 억지로 기능을 배정하지 않았다. 의도적인 Solo/guide/Overscan 제외는 EXPORT_GAP이 아니다.

Matrix 기호: `Y` 해당 경로 있음, `—` 해당 없음, `0` 없음, `P` 부분 지원/아래 제한 참조, `V` editor/view 전용. Save는 프로젝트 저장이며 엔진용 metadata가 아니다. Keyframe `0`은 static 설정 자체를 부정하지 않는다. COMPLETE는 모든 매개변수의 모든 조합을 보증한다는 뜻이 아니다. UI 테스트 통과는 네이티브 수동 QA를 대신하지 않는다.

각 행의 Area 뒤 증거 ID는 다음 **Model → UI → Mutation/Undo → Render → Save → Export → Tests** 경로를 참조한다. 공통 경로를 중복하지 않고, 세부 의미와 예외는 후속 절에 명시한다.

| ID | 실제 코드 경로 및 테스트 근거 |
| --- | --- |
| P | `app/models/particle_emitter.py`: ParticleEmitterSettings/ParticleInstance/build용 필드 및 to_dict/from_dict. `app/ui/particle_properties_panel.py`: set_emitter, settings, _changed, seed randomize. `app/ui/main_window.py`: update_particle_draft → EditorValueCommand(resource_layer_settings), apply_undo_value; _sync_resource_layer_adapters. `app/services/particle_render_service.py`: build_particle_instances, _spawn_position, render_particle_frame(s). `tests/test_particle_pipeline.py`, `test_numeric_edit_commit_semantics.py`, `test_resource_layer_v6.py`. |
| M | 같은 모델의 ParticleMotionSettings/MOTION_TRACK_PROPERTIES; Inspector _motion_control_map/_add_motion_keyframe; MainWindow motion key callbacks → resource_layer_settings undo; particle_render_service.evaluate_particle_motion/particle_motion_guide. `test_particle_orbit_motion.py`, `test_particle_helix_motion.py`, `test_motion_inspector_ui.py`, `test_motion_save_regression.py`, `test_particle_motion_output_consistency.py`. |
| R | `app/models/resource_composition.py`: CompositionLayer/ResourceComposition/AnimationTrack. `app/ui/resource_editor_v2/resource_editor_widget.py`, composition_inspector.py, composition_timeline.py: _push_value → EditorValueCommand / apply_undo_value. `app/services/resource_composition_render_service.py`. `test_resource_composition.py`, `test_resource_composition_editor.py`, `test_resource_multi_image_layers.py`, `test_resource_editor_v2.py`. |
| E | `app/models/effect_resource_layer.py`: Single/Particle, System/Surface transforms. `app/ui/main_window.py`: select_resource_layer, transform updates, multi-transform, _push_effect_batch; `resource_layer_transform_panel.py`. `app/services/effect_resource_layer_render_service.py`: current/full/apply; layer_space_transform_service.py / layer_parenting_service.py. `test_effect_multi_resource_layers.py`, `test_layer_space_transform_v9.py`, `test_resource_layer_transform_3d.py`, `test_resource_2_5d_particle_semantics.py`, `test_resource_identity_pixel_exact.py`. |
| H | `app/models/layer_group.py` / layer_parenting.py, ResourceComposition/Project hierarchy methods; ResourceEditor V2 and MainWindow group/parent/state/multi callbacks; logical-to-generated layer mapping; renderer effective visibility and world affines. `test_layer_groups.py`, `test_layer_group_persistence.py`, `test_layer_parenting_v12.py`, `test_layer_parenting_workflow.py`, `test_layer_lock_workflow.py`, `test_layer_solo_workflow.py`, `test_layer_multiselect.py`, `test_layer_batch_commands.py`, `test_layer_duplicate_workflow.py`, `test_layer_drag_reorder.py`. |
| T | AnimationTrack/Keyframe; `app/ui/timeline_multi_key.py`, timeline_time_view.py, timeline_snapping.py, timeline_widget.py and V2 composition_timeline.py; Resource/MainWindow batch commands, stable layer/property/frame identity; tracks consumed by R/E/M. `test_timeline_multi_key_model.py`, `test_timeline_multi_key_editing.py`, `test_timeline_multi_key_clipboard.py`, `test_timeline_multi_key_alt_duplicate.py`, `test_timeline_navigation_reveal.py`, `test_timeline_snapping.py`, `test_undo_integrity.py`, `test_undo_index_changed_ctrl_wheel_regression.py`. |
| A | `app/models/source_asset.py`, animation_clip.py; `app/services/resource_import_service.py`, aseprite service; V2 asset_browser_panel.py, asset_inspector_widget.py; MainWindow import_resource/reimport_resource/delete_resource/update_resource_pivot. `test_resource_foundation.py`, `test_resource_editor_flow.py`, `test_resource_multi_image_layers.py`, `test_resource_pivot_visualization.py`. |
| C | `app/services/alpha_composite_service.py`, effect_render_service.py, resource_composition_render_service.py, `app/models/project.py:compose_frame`; `test_alpha_composite_optimization.py`, `test_resource_multi_image_layers.py:test_three_layer_composite_matches_independent_straight_alpha_expected`. |
| S | `app/services/project_io.py:save_project/load_project`, `app/models/project.py:to_dict/from_dict` FORMAT_VERSION 12, embedded asset/clip pixels and logical layers. Atomic temporary file + flush/fsync + replace. Rebuilds compatibility adapters. `test_motion_save_regression.py`, `test_layer_group_persistence.py`, `test_layer_parenting_v12.py`, fixture roundtrips in audit script. |
| X | MainWindow.export_frames → _materialize_resource_transform_sequences → `app/services/export_service.py:export_png_frames` → Project.compose_frame → PIL PNG. Separate `preview_export_service.py:export_preview_sequence`; MainWindow.export_particle_preview requires current preview session. `test_particle_motion_output_consistency.py:test_motion_direct_preview_bake_and_exports_match`, `test_resource_2_5d_particle_semantics.py:test_resource_2_5d_current_full_bake_and_png_export_parity`, `test_resource_composition_clip.py`, audit script. |
| V | MainWindow playback/timeline actions; V2 resource_editor_widget.py toggle_play/_advance; `app/ui/canvas_widget.py`, V2 composition_canvas.py; preview/cache/prebuffer services. `test_playback_controls.py`, `test_playback_shortcut_regressions.py`, `test_playback_status.py`, `test_effect_playback_prebuffer.py`, `test_resource_editor_overscan.py`, `test_particle_motion_gizmo.py`. |
| L | Legacy `app/models/effect_generator.py:TransformEmitterSettings`, `app/services/emitter_service.py`, effect_render_service.py; old generator Inspector/MainWindow compatibility. New creation control hidden in active Effect library; legacy settings are not unified Particle capability. |

Missing-feature 판정은 위 dataclass/serializer/Inspector/renderer dispatch/export entry point를 대조한 결과다. 로드맵 문구, reserved deformation, cache prewarm, NewProject의 canvas-size preset은 해당 effect 기능의 구현 증거로 세지 않는다.

## Master Capability Matrix

| Area | Capability | Status | Model | UI | Render | Keyframe | Undo | Save | Export | Priority |
| ---- | ---------- | ------ | ----- | -- | ------ | -------- | ---- | ---- | ------ | -------- |
| Emission P/S/X | Count fixed/min-max, one burst | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Emission P | Rate particles/sec | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Emission P | Over-time finite count distribution | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Emission P | Burst schedule/multiple burst counts | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Emission P | Start frame + per-instance delay min/max | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Emission P/L | Independent spawn interval | PARTIAL | P | P | P | 0 | P | Y | Y | A |
| Emission P | Emission duration / output duration | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Emission P/V | Infinite emitter loop / steady state | PARTIAL | P | P | P | 0 | P | P | P | A |
| Emission P | One-shot finite emission | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Emission P | Lifetime fixed / random min-max | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Seed P/S/X | Fixed per-emitter / per-instance reproducibility | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Seed P/V | Randomize seed then replay | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Seed P/V | Automatically randomize every replay | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Emission P | Simulation prewarm | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Spawn P | Point | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Spawn P | Line uniform sample | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Spawn P | Box filled XY random | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Spawn P | Circle (filled disk) | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Spawn P | Ring circumference / arc via Circle | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Spawn P | Ring thickness / shape fill-edge switch | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Spawn P | Cone-like angular spread | PARTIAL | P | P | Y | 0 | Y | Y | Y | B |
| Spawn P | Image bounds / alpha mask sample | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Spawn P | Custom path | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Spawn P/M | Independent random Z | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Spawn P/E | Shape rotation / 2.5D via System | PARTIAL | P | Y | Y | P | Y | Y | Y | 유지 |
| Initial P | Position / direction / velocity / speed range | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Initial P | Rotation / angular velocity range | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Initial P | Uniform scale min/max | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Initial P | Independent scale X/Y random | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Initial P | Opacity fixed shared start | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Initial P | Per-particle opacity random | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Initial P | Color/tint fixed/random range/palette | MISSING | 0 | 0 | 0 | 0 | — | — | — | S |
| Initial P/A | Random animation start frame | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Initial P/A | Positive clip speed fixed/range | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Initial P | User-defined discrete variations (except frame) | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Lifetime P | Alpha start → end with four easings | COMPLETE | Y | Y | Y | — | Y | Y | Y | 유지 |
| Lifetime P | Alpha easing retained by Inspector | COMPLETE | Y | Y | Y | — | Y | Y | Y | 유지 |
| Lifetime P | RGB color multiplier start/end/easing | PARTIAL | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Lifetime P | Multi-stop color gradient / HSV curve | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Lifetime P | Uniform scale multiplier start/end/easing | PARTIAL | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Lifetime P | Multi-point scale / independent X/Y | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Lifetime P | Rotation = initial + angular velocity × age | COMPLETE | Y | Y | Y | — | Y | Y | Y | 유지 |
| Lifetime P | Variable angular velocity curve | MISSING | 0 | 0 | 0 | — | — | — | — | B |
| Lifetime P/M | Speed/velocity curve (linear mode) | MISSING | 0 | 0 | 0 | — | — | — | — | A |
| Color R/E/P | Layer tint / particle start-end tint | MISSING | 0 | 0 | 0 | 0 | — | — | — | S |
| Color R/E/P | Source artwork color + opacity | COMPLETE | Y | Y | Y | P | Y | Y | Y | 유지 |
| Color C | Straight RGBA alpha handling | COMPLETE | Y | — | Y | — | — | Y | Y | 유지 |
| Color C | User premultiplied input/output mode | MISSING | 0 | 0 | 0 | — | — | — | — | B |
| Blend C | Normal at Resource / Effect / particle / generated / final | COMPLETE | Y | — | Y | — | — | Y | Y | 유지 |
| Blend C | Additive at all above units | MISSING | 0 | 0 | 0 | 0 | — | — | — | S |
| Blend C | Multiply / Screen | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Blend C | Custom blend | MISSING | 0 | 0 | 0 | 0 | — | — | — | C |
| Motion P | Linear direction/speed/initial velocity | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Motion M | Orbit / Helix lifetime trajectory | COMPLETE | Y | Y | Y | P | Y | Y | Y | 유지 |
| Motion M | Center XYZ/radius start-end/angle/turns/axis/perspective tracks | COMPLETE | Y | Y | Y | Y | Y | Y | Y | 유지 |
| Motion M | Ellipse XY/phase spread/plane rotation tracks | MODEL_ONLY | Y | 0 | Y | Y | 0 | Y | Y | B |
| Motion P | Radial outward velocity | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Motion P/M | Signed constant Gravity | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Motion P/M | Drag / damping | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Motion P/M | Noise / turbulence | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Motion P/M | Random walk / random per-particle force | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Motion P/M | Attraction / repulsion / target follow | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Sprite A/P/R | Animated Resource / per-instance sprite animation | COMPLETE | Y | Y | Y | P | Y | Y | Y | 유지 |
| Sprite A/P | Loop | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Sprite A/P | Imported clip once / hold selection | MODEL_ONLY | Y | P | Y | 0 | P | Y | Y | A |
| Sprite A/P | Reverse / ping-pong | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Sprite A/P | Lifetime-synchronized duration | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Orientation P | Fixed / random / angular rotation | COMPLETE | Y | Y | Y | 0 | Y | Y | Y | 유지 |
| Orientation P | Face velocity / outward / inward / path tangent | MISSING | 0 | 0 | 0 | 0 | — | — | — | A |
| Orientation P/E | Screen-plane billboard-like sprites | PARTIAL | P | P | Y | P | Y | Y | Y | 유지 |
| Trail P | Trail / ribbon / per-particle history | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Trail P | Width / lifetime / color / alpha / texture | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Event P | Spawn / death / end / timeline sub-emitter | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Event P | Collision sub-emitter | NOT_APPLICABLE | 0 | 0 | 0 | 0 | — | — | — | Later |
| Composition R/E/H | Multi resource/image/effect layers | COMPLETE | Y | Y | Y | Y | Y | Y | Y | 유지 |
| Composition H | One-level organizational groups | COMPLETE | Y | Y | Y | — | Y | Y | Y | 유지 |
| Composition H | Arbitrarily nested group hierarchy | MISSING | 0 | 0 | 0 | — | — | — | — | C |
| Composition H | Visibility / lock / solo | COMPLETE | Y | Y | Y | — | Y | Y | P | 유지 |
| Composition H | Order / duplicate / multi-selection | COMPLETE | Y | Y | Y | — | Y | Y | Y | 유지 |
| Composition H/E | Parenting / Keep World | COMPLETE | Y | Y | Y | Y | Y | Y | Y | 유지 |
| Composition R/E | 2.5D / System / Surface / pivot | COMPLETE | Y | Y | Y | P | Y | Y | Y | 유지 |
| Composition E/H | World/local multi-transform (supported axes) | COMPLETE | Y | Y | Y | Y | Y | Y | Y | 유지 |
| Composition R | Resource position Z authoring | MODEL_ONLY | Y | 0 | Y | Y | 0 | Y | Y | B |
| Composition R/E | Opacity / timing / rotation revolutions | COMPLETE | Y | Y | Y | Y | Y | Y | Y | 유지 |
| Timeline T | Key / multi-key / marquee / drag / delete | COMPLETE | Y | Y | Y | Y | Y | Y | Y | 유지 |
| Timeline T | Copy-paste / Alt duplicate / nudge / batch easing | COMPLETE | Y | Y | Y | Y | Y | Y | Y | 유지 |
| Timeline T | Zoom / pan / fit / reveal / key navigation | COMPLETE | V | Y | V | — | — | — | — | 유지 |
| Timeline T | Snapping to keys/playhead/bounds | COMPLETE | V | Y | Y | Y | Y | Y | Y | 유지 |
| Timeline T/V | Work Area / Loop Range | MISSING | 0 | 0 | 0 | — | — | — | — | A |
| Timeline T | Markers / timeline search | MISSING | 0 | 0 | 0 | — | — | — | — | B |
| Timeline T | Key timing distribute / scale keys | MISSING | 0 | 0 | 0 | Y | — | — | — | B |
| Easing R/T/M | Linear / Ease In / Ease Out / Ease In-Out | COMPLETE | Y | Y | Y | Y | Y | Y | Y | 유지 |
| Easing T | Step/Hold segment interpolation | MISSING | 0 | 0 | 0 | 0 | — | — | — | B |
| Easing T | Custom Bezier / graphs / tangent handles | MISSING | 0 | 0 | 0 | 0 | — | — | — | C |
| Easing T | Bounce / Elastic | MISSING | 0 | 0 | 0 | 0 | — | — | — | C |
| Preview V | Play/pause / step / restart / full loop | COMPLETE | V | Y | Y | — | — | P | — | 유지 |
| Preview V | Resource one-shot stop | COMPLETE | Y | Y | Y | — | Y | Y | P | 유지 |
| Preview V | FPS / clip playback speed | COMPLETE | Y | Y | Y | P | Y | Y | P | 유지 |
| Preview V | Independent global preview speed multiplier | PARTIAL | P | P | P | — | — | P | — | B |
| Preview V | Checkerboard / output frame | COMPLETE | V | Y | V | — | — | — | — | 유지 |
| Preview V | Custom backdrop / adjustable color | PARTIAL | P | P | V | — | — | P | — | B |
| Preview V/R | Resource editor-only Overscan | COMPLETE | V | Y | V | — | — | — | — | 유지 |
| Spatial V/E/M | Move/rotate/scale/pivot and 2.5D guides/bounds | COMPLETE | V | Y | Y | P | Y | Y | Y | 유지 |
| Spatial V/H/M | Parent / motion / Orbit / Helix guides | PARTIAL | V | Y | V | — | — | — | — | 유지 |
| Spatial V | Canvas pixel grid | PARTIAL | V | P | V | — | — | — | — | B |
| Spatial V | User guides / center / layer-to-layer snap | MISSING | 0 | 0 | 0 | — | — | — | — | B |
| Export X | PNG single frame via one-frame project | PARTIAL | Y | P | Y | — | — | — | Y | A |
| Export X | PNG sequence RGBA fixed canvas | COMPLETE | Y | Y | Y | — | — | — | Y | 유지 |
| Export X | Sprite Sheet / Atlas | MISSING | 0 | 0 | 0 | — | — | — | 0 | A |
| Export X | Rows/cols/padding/spacing/fixed-cell packing | MISSING | 0 | 0 | 0 | — | — | — | 0 | A |
| Export X | Trim / POT / texture limit / border options | MISSING | 0 | 0 | 0 | — | — | — | 0 | A |
| Export X | GIF / APNG | MISSING | 0 | 0 | 0 | — | — | — | 0 | B |
| Export X | Engine JSON / pivot / FPS / loop / frame durations | MISSING | P | 0 | — | — | — | P | 0 | A |
| Export X/R/E/P | Supported exact transform/motion/alpha/seed/timing | COMPLETE | Y | Y | Y | Y | Y | Y | Y | 유지 |
| Resource A/S | PNG / GIF import, embedded portable pixels | PARTIAL | Y | Y | Y | — | P | Y | Y | A |
| Resource A | Aseprite import | PARTIAL | Y | Y | Y | — | P | Y | Y | B |
| Resource A | Replace/reimport existing source | PARTIAL | Y | Y | Y | — | 0 | Y | Y | A |
| Resource A/R/E | Rename layers/compositions; source asset name editing | PARTIAL | Y | P | Y | — | P | Y | Y | A |
| Resource A | Delete with in-use protection | PARTIAL | Y | Y | Y | — | 0 | Y | Y | A |
| Resource A/S | Missing external path / duplicate names / portability | PARTIAL | Y | Y | Y | — | P | Y | Y | A |
| Reuse H | Duplicate layers/groups inside project | COMPLETE | Y | Y | Y | Y | Y | Y | Y | 유지 |
| Reuse H/S | Duplicate entire effect via Save As | PARTIAL | Y | P | Y | Y | — | Y | Y | A |
| Reuse A/S | Presets/emitter/layer/template library, save/import presets | MISSING | 0 | 0 | 0 | — | — | — | — | A |
| Reuse A/T | Cross-project complete layer/effect transfer | MISSING | 0 | 0 | 0 | — | — | — | — | A |
| Performance P/E/T | 10/50/100 layers; 100/500/1000 particles; 5000 keys | PARTIAL | Y | P | Y | Y | P | Y | Y | A |
| Product | Audio/video/camera tracking/full 3D/roto/text suite/plugins | NOT_APPLICABLE | — | — | — | — | — | — | — | Not Planned |

## 의미와 제한 — 이름이 아닌 실제 동작

### Emission / Spawn / initial variation

Count는 emitter마다 seed로 **한 번** min/max 중 결정한다. 이후 instance마다 수명·속도·크기·회전·angular velocity·delay·clip speed 등을 독립적으로 샘플링한다. emitter 전체 값을 한 번 랜덤화하는 것과 다르다. 같은 seed와 같은 설정/소스에서 재현되지만 설정을 바꾸면 RNG 소비 순서도 달라질 수 있으므로 특정 particle ID의 모든 난수가 영구 고정된다는 계약은 없다.

Burst는 전체 count를 같은 기본 시작에 놓는다. over_time은 `round(i * (emission_duration-1)/(count-1))`로 유한 count의 birth를 분배한다. 여기에 start_frame과 각 delay를 더한다. rate/sec·독립 interval·여러 burst schedule이 아니며 여러 particle이 같은 frame에 태어날 수 있다. TransformEmitter의 emission_interval을 unified Particle interval로 잘못 세지 않는다.

Emission duration은 분배 구간, particle lifetime은 태어난 뒤의 생존 frame 수, output_frame_count는 렌더할 전체 길이, Layer start/end는 배치의 유효 구간, Resource frame_count/FPS는 source animation 시간이다. 범위 밖의 생존 particle은 output 끝에서 잘릴 수 있다. 반복 preview는 이미 생성한 유한 시퀀스를 돌리므로 경계가 자동으로 seamless해지지 않는다. Explosion/단발 Projectile Burst에는 충분하지만 지속 Smoke/Aura는 수작업 중첩/시작·끝 관리가 필요하며 간헐 Spark는 지연과 레이어 복제로 근사한다.

Point=한 점, Line=두 점 사이 균일 t, Box=중심±폭/높이 절반에서 독립 XY 표본. Circle은 고정 radius의 **둘레** 표본이며 angle 범위로 Arc가 된다. 원 내부 면적 표본·두께 있는 Ring·mask/path·random Z는 없다. Cone-like는 방향 spread이지 부피 shape가 아니다. shape 자체의 크기/각도는 static; System transform animation으로 전체를 움직이거나 회전/2.5D 투영하는 것은 가능하다. 방향은 fixed 또는 radial_outward이며 center에서 radial은 무작위 방향이다. 원점/속도 direction과 sprite orientation은 별개다.

Initial fixed는 min=max로 설정할 수 있다. scale은 uniform scalar뿐이고 velocity XY는 direction+speed에서 유도된다(독립 XY min/max UI 아님). random frame은 모든 frame 중 정수 선택; 사용자 지정 discrete palette/list는 없다. opacity_start는 모든 particle이 공유하는 시작 alpha이고 Random Range 그룹 안에 있다고 random alpha가 아니다. Color는 artwork에 이미 있는 RGBA만 사용한다.

### Lifetime와 Timeline은 다른 시간축

Alpha는 `age/(lifetime-1)`를 사용하고 lifetime<=1이면 amount=1이다. start/end 선형 fade는 있고 여러 stop/curve UI는 없다. 회전은 initial rotation + constant angular velocity × age다. Linear speed/velocity는 고정이다.

Orbit/Helix는 radius/angle/axis를 **age/lifetime** 기반으로 평가하므로 마지막 살아 있는 frame이 1.0에 정확히 도달하지 않는다. 반면 그 trajectory의 center/radius/turns 등의 track은 **Effect의 절대 frame**에서 평가한다. 이것을 임의의 particle size/color curve로 간주하지 않는다. motion 모델의 numeric track은 14개, Inspector keyframe map은 10개다. ellipse XY/phase spread/plane rotation은 static UI는 있지만 해당 track 작성 UI는 없다.

v0.0.16 unified Particle에는 `LifetimeScalarModulation` 기반의 uniform Scale over Lifetime이 있다. 각 instance base scale에 Start→End multiplier를 곱하고 네 easing을 지원한다. 개별 X/Y와 multi-point curve, emitter timeline keyframe은 없으므로 전체 판정은 **PARTIAL**이다. legacy TransformEmitter의 별도 scale_x/y_start/end 보간과 Resource 내부 artwork animation은 이 채널로 세지 않는다.

### RESOLVED IN v0.0.16 — Alpha easing 보존 실패

`ParticleEmitterSettings.easing="Ease In"`을 `ParticlePropertiesPanel.set_emitter` 후 `settings()`로 읽으면 **Linear**가 되던 원인은 settings()가 easing을 전달하지 않아 dataclass 기본값으로 재구성했기 때문이다. refresh signal 자체가 model을 바꾼 것이 아니었다.

최초 재현은 audit script의 `introspection`: loaded_alpha_easing=`Ease In`, inspector_reconstructed_alpha_easing=`Linear`였다. v0.0.16은 Alpha Easing control을 명시적으로 binding하고 loading guard 안에서 exact 복원하며 `settings()`에 값을 전달한다. MainWindow는 no-op을 push하지 않는다. 네 easing의 refresh/selection/save/Undo 테스트를 추가했고, 공용 alpha evaluator의 누락됐던 Ease In/Out 계산도 고쳤다.

### Color / Blend / Motion / Sprite

모든 합성 단위(Resource 내부, Effect, particle instance, generated layer, final)는 Normal source-over다. straight RGBA를 alpha-weighted 계산 후 다시 straight로 나누어 출력한다. 이 내부 수학은 사용자가 선택하는 premultiplied blend mode가 아니다. Additive/Multiply/Screen/custom은 모델 필드·UI·renderer 분기 모두 없다. PNG로 구워 넣은 밝은 sprite는 Additive와 같지 않으며 배경과 겹쳤을 때 결과도 다르다.

v0.0.17의 RGB lifetime channel은 source artwork RGB에 encoded 8-bit component-wise multiplier를 적용하며 Alpha를 포함하지 않는다. Start/End/Easing으로 Fire, Heal, Poison, Magic의 2-point 색 진행을 직접 만들 수 있다. static base tint, random palette, multi-stop gradient, HSV/HSL interpolation은 아직 없다.

Motion은 linear/orbit/helix base path와 signed constant Gravity contribution을 제공하지만 범용 force stack은 아니다. radial은 initial direction 옵션이며 random initial direction은 random walk가 아니다. Drag/noise/turbulence/attraction/follow는 없다. Smoke/Fire/Dust/Fog/wisps/electric/Snow는 source 애니메이션·다층·Orbit·Gravity 조합에 의존하며 자연스러운 감속과 불규칙 흐름은 아직 부족하다.

Particle마다 animated clip 또는 완료된 Resource Composition을 재생한다. clip speed min/max는 양수이고 최소/최대 invariant 및 Undo 회귀 테스트가 있다. GIF frame durations를 소비한다. once는 source 종료 후 sprite 없음, loop는 modulo, hold는 마지막 frame 유지다. imported AnimationClip의 playback_mode는 모델/renderer가 지원하지만 V2 asset Inspector에 once/hold 선택 control이 없다(일부 import가 hold를 정한다). Resource loop checkbox와 imported clip playback mode를 구분한다. asset preview는 자체 modulo 재생이므로 runtime once/hold의 정확한 검토 도구는 아니다. reverse/ping-pong/lifetime sync는 없다.

Fixed/random/angular rotation은 있지만 face velocity/outward/inward/path tangent 정렬은 없다. screen-plane sprite 투영은 billboard-like이나 full camera-facing 모드 선택기가 아니다. X/Y/Z 2.5D는 flat artwork의 projection이며 full 3D scene이 아니다.

Trails/ribbon에는 history, width, lifetime, color, alpha fade, texture, per-particle 관리가 모두 없다. slash/streak/comet/laser/fast spark/missile은 긴 source sprite나 baked animation을 대체재로 사용한다. Spawn/death/end/timeline event가 다른 emitter를 실제 생성하는 시스템도 없다. 시작 frame을 맞춘 복수 layer는 choreography일 뿐 sub-emitter가 아니다. collision event는 현재 충돌 시스템이 없는 offline authoring 제품의 후순위다.

### Layer / Timeline / Preview / 공간 편집

Flash/Smoke/Spark/Ring/Glow/Debris를 각각 레이어로 구성하는 기반은 강하다. hierarchy group은 조직/visibility/lock/solo 단위이고 parenting은 별도의 transform dependency다. 무제한 중첩 group이나 group 자체 transform으로 확대 해석하지 않는다. Parent Keep World는 reparent 순간 보존이며 전체 시간대의 world animation을 자동 rebake하는 기능이 아니다. multi-transform은 지원된 Move/Rotate Z/Scale 흐름을 말하며 모든 3D 축 batch 조작을 보증하지 않는다.

System transform은 particle 배치/공간에, Surface transform은 완성된 결과에 적용하는 구분이 있고, Resource sprite 2.5D는 내부 artwork에 적용한다. transform advanced bypass, rotation revolution, pivots 및 parent offsets가 저장/렌더된다. Resource position_z는 모델/renderer에 있으나 active property registry에 사용자 추가 항목이 없으므로 MODEL_ONLY다.

Visibility는 final에도 적용한다. Lock은 편집 제한이지 보이지 않음이 아니다. **Solo는 preview-only**로 final export가 모든 visible layer를 포함하는 것이 정상이다. Bounds/parent/motion guide는 단순화된 편집 안내이며 모든 particle의 실시간 궤적을 보여주지 않는다.

Timeline multi-key/clipboard/Alt-drag/nudge/snap/reveal은 이미 구현되어 있다. AnimationTrack easing은 Linear, quadratic Ease In, Ease Out, Ease In/Out의 네 가지다. 첫/마지막 키 밖에서 값이 유지되는 것은 Step/Hold segment interpolation과 다르다. custom Bezier/value/speed graph/tangent/broken handles/bounce/elastic은 없다. property search/filter는 timeline 전체 검색이 아니다. Work Area/Loop Range/markers/key distribute/time-scale 없음.

임의의 같은 10-frame 구간을 비파괴적으로 고정 반복하는 직접 workflow는 없다. scrubbing/restart/step으로 수동 확인하거나 Resource 총 길이를 바꾸어 근사해야 하는데 후자는 문서를 바꾸므로 대체 권장하지 않는다. 고정 seed replay는 안정적이며 randomize는 버튼으로 새 seed를 저장한 뒤 replay한다. 매 재생마다 자동 seed 변경은 없다. FPS 변경은 출력 시간의 변경이며 독립 preview 속도 조절과 다르다. prebuffer/proxy prewarm은 성능 cache일 뿐 simulation prewarm이 아니다.

Checkerboard/output frame/Overscan은 editor 표시다. Overscan은 Resource canvas에서만 출력 영역 밖 작업을 돕고 dim 처리한다. final clip은 계속 strict하다. pixel 좌표 반올림/화면 grid와 user guide/center/layer-to-layer snap은 서로 다른 기능이며 후자는 없다. 임의 backdrop 선택/독립 preview speed/모든 grid control의 네이티브 사용성은 이번 감사에서 완결 검증하지 않았으므로 PARTIAL로 유보했다.

### Export / Resource / Reuse

최종 exporter는 고정 canvas 크기의 RGBA PNG sequence 하나다. sanitized 이름 + 번호로 저장한다. PNG 단일 frame은 한-frame project라는 우회만 확인했고 현재-frame 전용 export UI는 없다. sheet/atlas, rows/cols/padding/spacing/trim/fixed-cell/POT/max texture/transparent-border option 없음. GIF/APNG import 가능성과 export 가능성을 혼동하지 않는다.

Engine용 JSON/pivot/FPS/loop/frame durations metadata는 없다. `.peffect.json`은 editor 전체 프로젝트이며 engine animation metadata가 아니다. output pixels에 pivot transform은 반영되지만 pivot 숫자는 PNG에 담지 않는다. 따라서 Unity/Godot/custom engine에 PNG들을 넣고 프레임 속도·loop·pivot·sheet packing을 사용자가 별도 설정해야 한다. 특정 엔진 플러그인보다 일반 sheet+metadata가 적합하다.

Export는 현재 frame cache를 그대로 믿는 것이 아니라 MainWindow의 materialize 경로를 거친다. 서비스 export_png_frames만 호출하는 외부 코드는 먼저 materialize해야 한다. audit fixture는 이를 명시적으로 수행했다. transform/parenting/2.5D/particle/motion/opacity/sprite/seed/timing/revolutions/strict clip parity는 X의 개별 회귀로 확인한다. editor proxy 저해상도 표시, solo, guides, overscan은 final에 포함하지 않는다. 구현되지 않은 color/blend를 일치 검증했다고 주장하지 않는다.

PNG/GIF는 embedded pixel 데이터라 원본 절대 경로가 없어도 저장된 project 렌더가 가능하다. 재가져오기는 원본이 없으면 경로 선택이 필요하다. ASE/ASEPRITE는 외부 executable 의존성이 있으므로 portable project와 import tool portability는 별개다. 동일 이름은 ID로 구분되지만 browser에서 식별성이 떨어질 수 있다. 이름 변경은 layer/composition에 있고 asset rename UI는 제한적이다. reimport는 ID/name/pivot을 보존하고 cache를 갱신하지만 import/reimport/delete에는 일관된 undo transaction이 확인되지 않아 PARTIAL이다. delete는 사용 중 참조 보호가 있으며 resource_layer adapters까지 동기화한 정상 MainWindow 흐름을 기준으로 판정한다.

통합 Particle는 `_sync_resource_layer_adapters()`가 legacy `project.particle_emitters`를 채운다. 따라서 refresh/revert가 그 목록을 검색한다는 이유만으로 죽은 UI라고 판정하면 안 된다. export preview는 refresh한 최신 session이 필요하다. 자동으로 final materialize하는 전체 PNG export와 다른 workflow다. 이 경로는 광범위 조합의 수동 QA가 남아 있다.

같은 프로젝트의 layer/group duplicate는 완성되어 있으나 전체 project의 Save As 복제와 독립 emitter/layer/effect preset library는 다르다. project 사이 key clipboard 지원을 완전한 asset dependency transfer로 세지 않는다. preset/import template/cross-project complete effect transfer는 없다.

## 대표 Effect 재구성 — 실행된 코드 fixture

`tools/audit_effect_authoring.py`는 64×64, 16 frames, 9×9 8-frame artwork를 만들어 current API만 호출한다. 6종 전부 nonempty, same-seed rerender, 실제 compact save/load 후 rematerialize, PNG decode 비교를 assert했다. 저장본 generated pixels만 비교한 것이 아니라 logical layers에서 다시 렌더했다. 각 fixture는 시각적으로 완성된 제품 preset이 아닌 **가능 범위와 우회를 확인하는 최소 구조**다.

| Fixture | 판정 | 실제 구성 / 제한 |
| --- | --- | --- |
| Hit Spark | POSSIBLE WITH WORKAROUNDS | burst, radial velocity, random rotation, alpha fade. source 8-frame 크기 감소로 scale fade 대체. lifetime random과 완벽히 동기화되지 않음. |
| Explosion | POSSIBLE WITH WORKAROUNDS | radial burst + 지연된 over-time smoke, 2 layers, random life. source 성장/색 변화 사용. 개별 scale/color module와 additive는 없음. |
| Smoke | LIMITED | box 분포, finite over-time, 느린 upward spread, alpha fade, source growth. noise/drag·지속 emission·seamless loop 불충족. |
| Magic Orbit | POSSIBLE WITH WORKAROUNDS | phase spread orbit + animated colored sprite + alpha. 실제 source color 편집은 외부 artwork, glow는 Normal artwork 근사. |
| Sword Slash | POSSIBLE WITH WORKAROUNDS | 1-instance animated slash sprite + System Z rotation keys + alpha/timing. ribbon을 baked animation으로 대체, 임의 이동 경로의 자동 trail 아님. |
| Projectile | LIMITED | 1-instance linear looping sprite + frame 12 사전 배치 impact layer. trail 없음, 도착/충돌 event가 impact를 생성하지 않음. |

필수 조건 전체를 native procedural 기능으로 충족하는 FULLY POSSIBLE 판정은 주지 않았다. 정해진 offline 연출은 우회 가능하므로 전부 NOT PRACTICAL이라고도 하지 않는다. Fire/Heal/Poison/Magic 색 전환은 같은 artwork 우회, Dust/Impact Burst/Spawn/Teleport/Charge는 다층 timing으로 비교적 용이하다. Magic Circle/Aura/Orbit/Helix는 기존 강점을 직접 활용한다. Electric/Lightning은 손그린 sequence 의존, Rain/Snow/Ambient는 유한 반복 및 자연 운동 한계, Buff Glow는 additive 한계를 공유한다. Sword Trail/Projectile Trail은 가장 직접적으로 trail 부재의 영향을 받는다.

## 성능 / 규모

합성 microbenchmark, 이 머신/이번 실행 수치. 64×64 RGBA, 16 frames, 9×9 8-frame source. particle workload는 lifetime=16과 100/500/1000 instances. 3회 median, layer cold materialization/레이어 export만 1회. OS cache/다른 프로세스 영향이 있어 절대 성능 약속이 아니다.

| Workload | instance build ms | uncached particle render 16f ms | materialized PNG 16f ms |
| --- | ---: | ---: | ---: |
| 100 particles | 0.637 | 156.561 | 11.855 |
| 500 particles | 2.465 | 790.599 | 12.322 |
| 1000 particles | 5.162 | 1643.842 | 12.950 |

| Logical layers (1 particle each) | Cold materialize 16f ms | Already materialized compose 1f ms | PNG 16f ms |
| --- | ---: | ---: | ---: |
| 10 | 72.052 | 1.609 | 34.266 |
| 50 | 365.283 | 7.583 | 127.221 |
| 100 | 856.778 | 15.546 | 252.158 |

5000 keys = 10 tracks × 500 frames(0..499), 실제 512 frame 범위 안. snap target collection 0.918 ms, next navigation 0.401 ms, 10 track evaluations 0.157 ms. 이는 키 그림 그리기·5000-key undo snapshot·전체 UI layout 비용이 아니다.

Particle 수가 늘 때 spawn simulation보다 sprite transform/composite 처리량이 지배적이다. 1000 particles의 cold 평균은 약 103 ms/frame이라 매 frame cold 재렌더로 실시간 재생할 수 있다고 말할 수 없다. prebuffer/cache는 이를 가리거나 준비 비용으로 옮기지만 cold interaction 한계가 사라지는 것은 아니다. 100 layers의 compose만 약 15.5 ms이므로 UI·렌더·업로드까지 더하면 60 FPS 보장은 어렵다. PNG 수치는 **이미 materialized** 데이터이며 full export latency에는 필요한 rebuild가 추가된다.

기존 interaction/prebuffer/current-frame consistency/performance 테스트도 전체 회귀에 포함한다. 다만 이 7개 규모에 대해 네이티브 mouse drag latency/p95/RSS/대형 canvas/큰 transparent sprite/모든 hierarchy depth를 측정하지 않았다. production ceiling 판정은 PARTIAL. 다음 성능 audit은 cold/warm을 나누고 256/512 canvas, transformed sprite bounds, p95 interaction, memory와 rebuild+export 총량을 측정해야 한다.

## Gap 점수와 Roadmap

I=Production Impact, F=Frequency, W=Workaround Cost, R=Implementation Risk(클수록 위험), A=Architecture Fit. 각 0..5. 경험적 제품 판단이지 사용자 통계가 아니다. 합계를 사용하지 않는다. 같은 구현 계약에 속한 부족 항목은 함께 점수를 주되 하위 항목을 명시했다.

| Gap (matrix의 부족 항목 포함) | I | F | W | R | A | Priority/Tier | 이유 / 재사용 / 변경면 |
| --- | -: | -: | -: | -: | -: | --- | --- |
| Lifetime multi-point / independent X/Y scale | 3 | 3 | 2 | 3 | 5 | Medium/A | v0.0.16 uniform start/end로 핵심 grow/shrink 가능. 필요성 검증 뒤 scalar foundation 확장. |
| Tint/start-end color/gradient/random palette | 5 | 5 | 4 | 4 | 4 | High/S | Fire/Heal/Poison. RGBA 경로 재사용; tint cache key/alpha/color-space 계약 필요; M/R/UI/S/X, lifetime foundation 의존. |
| Additive | 5 | 5 | 4 | 4 | 4 | High/S | Glow/energy. composition boundary 재사용; transparent export 합성 의미를 먼저 정의; M/R/UI/S/X 전체. |
| Rate/interval/burst schedule/continuous loop/prewarm | 4 | 4 | 3 | 4 | 4 | High/A | Ambient 반복. seeded birth planner 재사용; seek와 warmup 정의, rate FPS 단위, cache/save migration. |
| Disk fill/ring thickness/fill-edge toggle | 3 | 3 | 2 | 2 | 5 | Medium/A | _spawn_position 확장, seed sampling/면적분포 테스트; shape animation 별도. |
| Gravity/acceleration/constant force/drag/velocity curves | 4 | 4 | 4 | 4 | 4 | High/A | Debris/Smoke. age 기반 analytic motion 우선; scrub 독립성 보존; M/R/UI/S/X. |
| Noise/turbulence | 4 | 3 | 4 | 4 | 3 | Medium/A | 자연 운동; particle seed 재사용 가능, 상태형 RNG walk 금지; deterministic time sampling 필요. |
| Opacity random / multi-stop alpha curve | 3 | 4 | 2 | 2 | 5 | Medium/A | Lifetime foundation와 P Inspector 재사용; source alpha 유지. |
| Sprite once/hold UI, lifetime sync | 4 | 4 | 3 | 3 | 5 | High/A | clip evaluator/positive speed invariant 재사용; Resource/GIF 시간 단위와 완료 의미 정리. |
| Face velocity/outward/inward/tangent | 3 | 4 | 3 | 3 | 5 | Medium/A | 현재 velocity/trajectory derivative + rotation; zero speed/2.5D axis 정의. |
| Multiply/Screen | 3 | 3 | 3 | 3 | 4 | Medium/A | Additive contract 뒤 shared compositor 확장; PNG bake 기준. |
| Work Area/Loop Range | 4 | 5 | 3 | 2 | 5 | High/A | timeline navigation/prebuffer 재사용; 문서 길이/키를 바꾸지 않는 editor state. |
| Sheet/atlas/basic pack options/single-frame export | 5 | 4 | 3 | 3 | 5 | High/A | PNG renderer 재사용; fixed cells 먼저, trim/atlas 뒤; image placement+metadata 일치. |
| Trim/POT/size/padding/spacing/border | 3 | 3 | 3 | 3 | 4 | Medium/A | exporter 위 packing 단계; trim offset과 pivot 동시 검증. |
| Engine JSON/pivot/FPS/loop/durations | 5 | 4 | 4 | 3 | 5 | High/A | S의 timing/pivot 참조하되 editor JSON 그대로 노출 금지; metadata schema 분리. |
| Asset rename/reimport/delete Undo & portability UX | 4 | 4 | 3 | 3 | 5 | High/A | stable IDs+EditorValueCommand 재사용; asset blob/revision/cache invalidation 포함. |
| Presets/templates/save-import/cross-project effect copy | 4 | 4 | 3 | 4 | 4 | Medium/A | group duplicate+serializer 재사용; ID remap/asset closure/versioning/relative paths. |
| Cold performance/large-scale validation | 4 | 4 | 4 | 4 | 4 | High/A | existing collectors/prebuffer/proxy/renderer cache 재사용; correctness 먼저. |
| Arbitrary path/image bounds/shape animation | 3 | 2 | 3 | 3 | 3 | Medium/B | spawn sampler 확장; path ownership/alpha sampling/track semantics 추가. |
| Random Z/independent scale XY/discrete choices | 2 | 3 | 2 | 2 | 4 | Medium/B | seeded initial state 확장, existing serialization/Inspector. |
| Extra motion tracks + Resource Z UI | 2 | 2 | 2 | 2 | 5 | Medium/B | 모델/renderer 이미 존재; registry/control/undo 테스트, 불필요한 모델 재작성 금지. |
| Variable angular speed / reverse / ping-pong | 3 | 3 | 2 | 2 | 4 | Medium/B | lifetime/clip evaluator; negative speed invariant를 깨지 않는 명시 mode 선호. |
| Trails/ribbon/all width-life-color-alpha-texture controls | 4 | 3 | 4 | 5 | 3 | Medium/B | logical/generated layer mapping 재사용; deterministic history reconstruction+export/memory 필요. |
| Spawn/death/end/timeline events/subemitters | 3 | 2 | 3 | 5 | 3 | Medium/B | birth planner/IDs 재사용; DAG/recursion limits/seed derivation/duration bounding 필요. |
| Attraction/follow/random walk/random force | 2 | 2 | 3 | 4 | 3 | Medium/B | analytic motion 확장, arbitrary-seek 재현 우선. |
| Auto random replay/global preview speed/backdrop/grid UX | 2 | 3 | 1 | 2 | 4 | Medium/B | editor state+seed/playback controls; export timing과 분리. |
| Canvas guides/center/layer snap | 3 | 3 | 2 | 3 | 4 | Medium/B | gizmo world/local coordinate pipeline 재사용; timeline snap과 별도. |
| Markers/search/distribute/time-scale keys | 3 | 3 | 2 | 3 | 4 | Medium/B | multi-key batch/visible key snapshots 재사용; collision+undo policy. |
| Step/Hold easing | 3 | 3 | 2 | 2 | 5 | Medium/B | AnimationTrack enum/evaluator/UI/S; source hold와 별개. |
| GIF/APNG output / explicit premult mode | 2 | 2 | 2 | 3 | 3 | Medium/B | PNG sequence pipeline reuse; palette/alpha/timing fidelity 별도. |
| Graph/Bezier/tangent/value-speed graph/Bounce/Elastic | 2 | 2 | 3 | 5 | 3 | Low/C | lifetime evaluator와 interpolation contract 후; global track editor 확대는 나중. |
| Nested groups / custom blend | 2 | 2 | 3 | 4 | 3 | Low/C | hierarchy/compositor 확장; current invariants 영향 큼. |
| Collision events | 1 | 1 | 3 | 5 | 1 | Low/C | runtime 엔진에 더 자연스러움; offline 최소 필요 입증 전 보류. |
| Audio/video/tracking/expression/full3D/grading/roto/text/plugins | 0 | 0 | 1 | 5 | 0 | Not Planned | 제품 목적 밖. 기존에 없다고 core gap으로 점수 올리지 않음. |

### Already Strong

레이어/그룹 조직, visibility/lock/preview solo, stable-ID duplicate/reorder, parenting/Keep World, System/Surface/Resource 2.5D 의미 분리, world/local multi-transform, 누적 rotation revolution, Orbit/Helix, multi-key/clipboard/Alt duplicate/snap/reveal, 조건부 auto-key와 numeric commit/Undo 회귀 기반, deterministic scrub/render, embedded compact save, editor Overscan과 final clip 분리. 이 기반을 새 module에서도 재사용해야 한다.

### Dependencies / 고위험 경계

```text
Normalized-age 계약 + scalar curve
  ├─ Scale over Lifetime (uniform → XY)
  ├─ 기존 Alpha 계약 정렬 → multi-stop alpha
  └─ Color representation → Tint/Color Lifetime → optional graph UI

RGBA/transparent compositing contract → Additive → Multiply/Screen
Deterministic motion/seek contract → Force/Drag → Noise
Seeded birth schedule → emission rate/loop/prewarm → bounded events
History reconstruction + seek/memory limits → trails → export parity
Canonical final render → fixed-cell sheet + metadata → trim/atlas
Timeline view state + playback/prebuffer bounds → Work Area
ID/dependency closure → portable preset/cross-project transfer
```

고위험: premultiplied/straight 혼합과 Additive transparent PNG 의미, normalized-age endpoint 변경, FPS 단위, stateful simulation의 scrub 순서 의존, cache key 누락, trim pivot drift, recursive events, trail memory, preset ID 충돌. v0.0.17은 RGB-only persistent channel 추가로 FORMAT 14를 사용하며 FORMAT <=13은 disabled white identity로 migration한다. 이후 blend/force/emission/preset도 FORMAT 변경 후보이고, Work Area가 editor settings에만 있으면 FORMAT 변경이 불필요할 수 있다.

### 다음 5개 작업 (한 번에 구현하지 않을 분리된 제안)

| 순서 | 범위 | 이유/사용자 체감 | 선행 조건 | 위험 |
| --- | --- | --- | --- | --- |
| 1 | Additive 최소 blend contract + end-to-end | Glow/energy/light 겹침 표현 | intermediate/final alpha 계약과 reference image test | High: 모든 compositor와 transparent export |
| 2 | Fixed-cell Sprite Sheet + engine-neutral metadata | PNG 재조립/속도·pivot 수작업 감소 | canonical final render, metadata schema | Medium: rows/cols/offset/timing |
| 3 | Work Area / Loop Range | 임의 10-frame 구간을 비파괴 반복 확인 | view-state, playback/prebuffer bounds | Low-medium: 범위 boundary/Undo와 분리 |
| 4 | Deterministic Gravity/Force/Drag | Debris·Smoke의 자연 운동 표현 | analytic seek contract, performance budget | High: scrub/cache/Orbit·Helix isolation |
| 5 | Multi-point Scale/Color lifetime curve | grow-then-shrink와 3색 진행 | 현재 2-point channel semantics | Medium-high: curve UI/serialization/Undo |

Force/Drag/Noise는 표현력 병목 상위이지만 deterministic seek/현재 성능을 지키는 비용이 커서 위 5개 다음의 별도 motion pass로 권장한다. 자연 운동 중심 사용자가 늘면 4/5보다 앞당길 수 있다. 범용 Graph Editor는 scale lifetime의 선행조건이 아니다.

## 최종 검증

| 검증 | 실제 결과 |
| --- | --- |
| Full pytest | **1138 passed in 79.59s, 0 failed**, 지정된 `--basetemp=C:\Dev\pixel_effect_maker_pytest_temp` 사용 |
| Diagnostic fixtures | 6/6 nonempty + same-seed rerender + save/load/rematerialize + PNG decode exact 통과 |
| Inspector introspection | Ease In → Linear 변환 재현; BUG FOUND로 기록, 미수정 |
| `python -m compileall app` | exit 0 |
| `python -m app.main --version` | exit 0, Pixel Effect Maker v0.0.15 |
| `python -m app.main --check` | exit 0; 아래 logging 권한 경고 있음 |
| `run_app.bat --check` | exit 0; 이번 shell의 `PIXEL_EFFECT_PYTHON=C:\Dev\pixel_effect_test_venv\Scripts\python.exe` 지정, 같은 logging 경고 |
| `git diff --check` | exit 0; 기존 파일 LF→CRLF 안내만 있음 |
| 시작 diff + 사용자 PNG 비교 | `git diff --binary`와 PNG SHA256 출력이 저장한 시작 출력과 완전히 동일 |
| 최종 Git | main, HEAD 동일, staged 0; local main은 기존대로 origin/main보다 31 commits ahead(네트워크 fetch 안 함) |

`--check`의 경고는 이 실행 환경에서 AppData 아래 `Pixel Effect Maker/logs/pixel_effect_maker.log` 쓰기가 거부된 것이다. logging 초기화가 불가했지만 점검 프로세스는 exit 0이었다. 정상 설치 환경의 로그 저장까지 성공했다고 주장하지 않는다. launcher default interpreter 자동 발견은 별도로 보증하지 않는다.

사용자 `테스트소스.png` SHA256: `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`. 이름·내용·stage 상태 보존. 기존 Overscan tracked diff도 그대로다. 이번에 추가한 것은 이 문서와 `tools/audit_effect_authoring.py`뿐이며 둘 다 unstaged다. 독립 fixture temporary files는 도구가 만든 `C:/Dev/pem_capability_audit_*` 내부에서 생성·정리되어 사용자 프로젝트에 남지 않는다. 실제 사용자 파일은 삭제하지 않았다.

## 요청한 1–147 완료 보고

1. 프로젝트: `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`.
2. HEAD: `1bfd865c6396565b9c43d541613b5a58ef590cd9`.
3. Version: v0.0.15 유지.
4. FORMAT_VERSION: 12 유지.
5. 시작: Overscan 관련 tracked 5개 수정, audit/test 3개 untracked, 테스트소스.png untracked; stage 0.
6. Full pytest: 실행 결과 아래 검증 기록 참조.
7. 핵심 정의: pixel/sprite 게임용 effect authoring/export.
8. 주요 사례: Hit/Slash/Explosion/Fire/Smoke/Dust/Projectile/Magic Circle/Aura/Lightning/Heal/Poison/Trail/Impact/Teleport/Charge/Glow/Ambient/Orbit/Helix.
9. 범위 밖: 범용 audio/video/full3D/tracking/roto/text/grading/expression/plugin suite.
10. Count: fixed/min-max, emitter당 한 번 샘플.
11. Rate: 독립 rate 없음, finite count over_time.
12. Burst: 한 번의 count burst; schedule 없음.
13. Delay: start frame + 개별 min/max.
14. Interval: unified 없음, legacy만 별도 interval.
15. Lifetime: 개별 fixed/min-max frames.
16. Loop: finite output replay, continuous emitter loop 아님.
17. Seed: per-emitter 고정/수동 randomize.
18. Prewarm: simulation 없음; cache 준비와 구분.
19. Point: 지원.
20. Line: uniform t 지원.
21. Box: XY area sample 지원.
22. Circle: disk fill 없음.
23. Ring: Circle이 circumference 역할.
24. Arc: angle 범위 지원.
25. Random Area: box 지원, circle fill/random Z 없음.
26. Custom Path: 없음.
27. Position: shape 기반 seeded instance sample.
28. Rotation: fixed/min-max.
29. Scale: uniform min-max, random XY 없음.
30. Velocity: direction/speed에서 유도.
31. Speed: positive min-max.
32. Lifetime: random min-max.
33. Color: source artwork만, tint/random 없음.
34. Sprite frame: random starting frame.
35. Lifetime Color: v0.0.17 RGB start/end/easing 지원(PARTIAL); multi-stop/HSV/Alpha 결합 없음.
36. Lifetime Alpha: start/end와 네 easing 지원; v0.0.16에서 Inspector 보존 회귀 및 Ease In/Out 평가 수정. multi-stop은 없음.
37. Lifetime Scale: v0.0.16 uniform start/end/easing 지원(PARTIAL); 개별 X/Y와 multi-point는 없음.
38. Lifetime Rotation: constant angular velocity.
39. Lifetime Speed: linear speed curve 없음.
40. Lifetime Velocity: 일반 curve 없음; Orbit/Helix trajectory 별도.
41. Tint: Particle lifetime RGB multiplier만 지원; static/random Layer/Particle base tint는 없음.
42. Opacity: Resource/Effect/keyframe/particle fade 지원.
43. Normal: source-over 지원.
44. Additive: 없음.
45. Multiply: 없음.
46. Screen: 없음.
47. Particle blending: Normal 고정.
48. Linear: 지원.
49. Orbit: 지원, 일부 absolute-frame motion tracks.
50. Helix: 지원, axis/radius/angle lifetime trajectory.
51. Gravity: COMPLETE — signed local-Y constant acceleration, actual particle frame age, analytic direct-seek evaluator.
52. Force: 없음.
53. Drag: 없음.
54. Noise: 없음.
55. Turbulence: 없음.
56. Radial: outward initial velocity 지원.
57. Animated source: clip/Resource composition 지원.
58. Loop: source loop 지원.
59. Once: clip model/render, active selector 제한.
60. Ping-pong: 없음.
61. Random start: 지원.
62. Playback speed: 양수 지원.
63. Playback random: min/max per-instance.
64. Initial rotation: 지원.
65. Random rotation: 지원.
66. Rotation over life: linear angular 지원.
67. Face velocity: 없음.
68. Path alignment: 없음.
69. Trail: 없음; baked sprite 우회.
70. Trail Width: 없음.
71. Trail Lifetime: 없음.
72. Trail Color: 없음.
73. Trail Alpha: 없음.
74. On Spawn: 없음.
75. On Death: 없음.
76. On End: 없음.
77. Sub-Emitter: 없음; scheduled layers와 구분.
78. Layer: multi image/resource/effect 지원.
79. Group: one-level organizational hierarchy 지원.
80. Parenting: local/world/Keep World 지원.
81. 2.5D: Resource/System/Surface flat projection.
82. Multi-Transform: 지원된 Move/Rotate Z/Scale.
83. Blend: Normal 고정.
84. Timing: layer/source/life 구분, frame 기반.
85. Keyframe: conditional auto-key 포함 지원.
86. Multi-Key: marquee/drag/delete/easing/nudge 지원.
87. Copy/Paste: typed key clipboard 지원.
88. Alt Duplicate: 지원.
89. Navigation: zoom/pan/fit/key navigation 지원.
90. Reveal: 지원.
91. Snapping: timeline targets 지원.
92. Work Area: 없음.
93. Curve/Graph: preset easing만, custom graph 없음.
94. Preview Loop: 전체 범위 지원.
95. Work Range: 없음.
96. Restart: 지원.
97. Fixed Seed Replay: fixture exact.
98. Random Seed Replay: 수동 randomize 후 replay.
99. FPS: project/resource timing; PNG metadata 없음.
100. Overscan: Resource editor-only, final strict clip.
101. PNG: RGBA; dedicated current-frame UI 제한.
102. PNG Sequence: 지원.
103. Sprite Sheet: 없음.
104. Trim: 없음.
105. Pivot: project/render 있음, engine metadata 없음.
106. FPS metadata: 없음.
107. Loop metadata: 없음.
108. JSON: editor project만; engine metadata 아님.
109. Export correctness: supported canonical paths tests + 6 fixtures exact; proxy/solo/guides 의도적으로 제외.
110. Hit Spark: POSSIBLE WITH WORKAROUNDS.
111. Explosion: POSSIBLE WITH WORKAROUNDS.
112. Smoke: LIMITED.
113. Magic Orbit: POSSIBLE WITH WORKAROUNDS.
114. Sword Slash: POSSIBLE WITH WORKAROUNDS.
115. Projectile: LIMITED.
116. 강점: Already Strong 절 참조.
117. Tier S: 완료된 최소 Additive. uniform lifetime scale과 2-point RGB lifetime도 완료.
118. Tier A: emission/forces/natural motion, sheet/metadata, Work Area, asset reliability, presets, performance.
119. Tier B: trails/events/orientation/shape/path/specialized editing.
120. Tier C: graphs/custom blend/nested groups/collision later.
121. Not Planned: 범용 영상/3D suite.
122. Reuse: evaluator, seeded instances, compositor, stable-ID commands, final renderer.
123. Dependency graph: 위 계약→module→UI/export 순서 참조.
124. High risk: alpha contract/stateful seek/cache/recursive events/history memory.
125. FORMAT: v0.0.19 Gravity 영속화로 16; FORMAT 15 이하는 Gravity OFF/0 identity로 migration.
126. 다음 5개: deterministic Gravity/Force/Drag → Sheet/metadata → Work Area → multi-point lifetime curve → Trail/Orientation.
127. 이유: 표현 공백 우선, 이어서 엔진 납품과 반복 속도.
128. 선행 dependency: normalized age / alpha / canonical output / view bounds.
129. 체감: 아트 재제작 감소, glow 표현, 납품 자동화, 부분 반복.
130. 위험: 순서별 Medium / Medium-high / High / Medium / Low-medium.
131. 추가 test: standalone diagnostic assertions 6 fixtures + performance + Inspector introspection; production pytest 파일 추가 없음.
132. Full pytest: 검증 기록 참조.
133. compileall: 검증 기록 참조.
134. --version: 검증 기록 참조.
135. --check: 검증 기록 참조.
136. run_app.bat: 검증 기록 참조.
137. git diff --check: 검증 기록 참조.
138. 최종 HEAD: 시작 HEAD 유지.
139. staged: 0 유지.
140. commit: 0.
141. tag/push/build/PyInstaller/ZIP: 0.
142. Animation Editor 성숙도: 강한 기반/넓은 자동 회귀, 네이티브 전체 QA 보증은 아님.
143. Effect Authoring Tool 성숙도: layer/sprite 중심 강점, procedural particle 표현은 중간 단계.
144. 게임 Effect 충실도: 정해진 baked 연출은 우회 가능, 자연/발광/trail/event 계열은 제한.
145. 표현 병목 3개: natural forces/noise, multi-point lifetime curves, trails/orientation.
146. 1순위: deterministic Gravity/Force/Drag의 최소 seek-safe contract.
147. Work Area보다 먼저: 예. 없는 표현을 여는 기능을 먼저, 반복 확인 최적화는 후속.
