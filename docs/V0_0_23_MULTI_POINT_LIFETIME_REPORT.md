# v0.0.23 Multi-point Lifetime Foundation — completion evidence

## 기준과 Git 경계

작업 루트: `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`.
시작 HEAD `d91f9582984b3d63904c0666d5d76c700bf40b5d`, version 0.0.22, format 19.
실제 baseline 전체 pytest **1410 passed / 88.13s**. compileall/version/direct check/batch check 및 diff check가 정상이고 staging contamination이 없음을 확인한 뒤
`Add deterministic cyclic emission` 커밋 **73af974542e2b50a51a8ca57e12373149986865b**을 만들었다.
직후 main ahead 41, staged 0, 보호 PNG만 untracked였다. 기존 v22 cyclic golden/prewarm/periodicity/direct seek/parity/safety 테스트도 이 실행에 포함됐다.

v23은 **unstaged/uncommitted**로 남긴다. Tag/Push/Build/PyInstaller/ZIP/Release 수행 0.
사용자 프로젝트와 보호 PNG를 변경하지 않았다. PNG SHA256:
`8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`.

### v22 explicit checkpoint whitelist (52)

`git add -A`는 사용하지 않았다. 실제 포함 파일은 다음과 같다.

```text
CHANGELOG.md
README.md
app/models/particle_emitter.py
app/models/project.py
app/services/effect_playback_service.py
app/services/localization_service.py
app/services/particle_render_service.py
app/ui/main_window.py
app/ui/particle_properties_panel.py
app/version.py
docs/EFFECT_AUTHORING_CAPABILITY_AUDIT.md
docs/MANUAL_TEST_CHECKLIST.md
tests/test_2_5d_inspector_architecture.py
tests/test_editor_state_hardening.py
tests/test_effect_advanced_bypass.py
tests/test_effect_multi_resource_layers.py
tests/test_keyframe_editing_foundation.py
tests/test_layer_group_persistence.py
tests/test_layer_groups.py
tests/test_layer_multiselect.py
tests/test_layer_parenting_v12.py
tests/test_layer_solo_workflow.py
tests/test_layer_space_transform_v9.py
tests/test_particle_additive_blend.py
tests/test_particle_color_lifetime_serialization.py
tests/test_particle_drag_serialization.py
tests/test_particle_gravity_serialization.py
tests/test_particle_noise_serialization.py
tests/test_particle_pipeline.py
tests/test_particle_scale_over_lifetime.py
tests/test_preview_build_notice.py
tests/test_project_format_v8.py
tests/test_project_save_source_roundtrip.py
tests/test_resource_2_5d_particle_semantics.py
tests/test_resource_composition.py
tests/test_resource_foundation.py
tests/test_resource_layer_v6.py
tests/test_resource_multi_image_layers.py
tests/test_rotation_revolution_display.py
tests/test_runtime_diagnostics.py
tests/test_source_assets_and_migration.py
tests/test_timeline_multi_key_clipboard.py
tests/test_timeline_multi_key_editing.py
tests/test_v8_converted_project_smoke.py
tests/test_v9_integrated_workflow.py
tests/test_v9_project_roundtrip_integration.py
tests/test_version.py
app/services/particle_cyclic_emission_service.py
docs/V0_0_22_CYCLIC_EMISSION_REPORT.md
tests/test_particle_cyclic_emission.py
tests/test_particle_cyclic_emission_serialization.py
tools/benchmark_cyclic_emission.py
```

제외: `테스트소스.png`, 사용자 project, C:\Dev evidence, build/dist/exe/ZIP/cache/log/temp/backup/pytest temp.

## 구현 전 architecture audit — 13 질문

| 번호 | 확인 내용 / 코드 근거 |
|---|---|
| 1 | `particle_emitter.py`의 LifetimeScalarModulation은 enabled/start/end/easing을 저장했다. |
| 2 | LifetimeColorModulation은 enabled/start_rgb/end_rgb/easing, RGB-only였다. |
| 3 | Opacity는 기존 ParticleEmitterSettings의 flat 필드로 구현되어 별도 재사용 모델이 없었다. 역사적 구조이며 별도 시간 의미는 아니었다. |
| 4 | 모두 resource_composition.EASINGS의 Linear/Ease In/Ease Out/Ease In/Out을 사용했다. |
| 5 | Scale disabled=1, Color disabled=(1,1,1). |
| 6 | Opacity 기본은 1→0 Linear, neutral은 1→1. |
| 7 | render_particle_frame에서 실제 age를 normalized_lifetime_age(age,L)에 전달; L>1은 age/(L−1), L≤1은1. Motion age/L과 구분했다. |
| 8 | Color는 encoded sRGB 각 채널 lerp 후 /255. linear-light/HSV 변환 없음. |
| 9 | lifetime uniform scale은 instance/motion/perspective/inherited base X/Y 양쪽에 동일하게 곱했다. |
| 10 | source alpha × lifetime opacity가 sprite raster blend에 전달되고 layer opacity가 뒤에 적용됨. Parent/System/Surface 경로는 그대로였다. |
| 11 | Cyclic wrapper의 absolute birth로부터 actual age를 계산하므로 prewarm도 같은 evaluator를 탔다. |
| 12 | ParticlePropertiesPanel.set_settings → settings → _changed, MainWindow.update_particle_draft → EditorValueCommand 경로. |
| 13 | set_settings가 s.easing을 alpha_easing에 복원하고 settings가 이를 alpha 전용 필드로 재구성했다. 신규 UI는 해당 easing을 opacity points에서 직접 보존한다. |

## 새 canonical 모델과 평가

Version **0.0.23**, FORMAT_VERSION **20**. Scalar/RGB point는 frozen dataclass, curve points는 tuple다.
각 채널 JSON은 enabled + points만 저장한다. Opacity의 과거 flat 필드는 InitVars(생성자 호환)와 같은 points를 수정하는 properties다. Scale/Color도 같은 point-backed endpoint adapters를 유지했다. 독립 writable start/end state는 없다.

2..8 points, finite times, strictly increasing, endpoints exactly0/1. Scalar Scale 0..16, Opacity0..1, RGB 정확히3 int0..255(no bool/alpha). Invalid/ambiguous payload는 거부하고 silent sort/repair는 하지 않는다. Format20 root는 canonical point payload를 요구한다. <=19의 legacy Start/End/Easing은 정확히 두 endpoints와 첫 outgoing easing으로 읽는다. Load는 원본을 rewrite하지 않는다.

선택 segment의 u=(t−ti)/(tj−ti)에 기존 easing을 적용하여 lerp한다. 공개 evaluator는 endpoint/clamp와 internal knot에서 저장값을 직접 반환한다. **2-point raster adapter**는 legacy endpoint 계산 순서를 유지한다. 예: alpha `.8 + (.1−.8)*1`과 literal `.1`은 1 ULP 차이로 uint8 half-even rounding이 달라질 수 있다. 이 호환 경로는 canonical points에서 계산하며 별도 상태를 저장하지 않는다. Multi-point는 정확한 knots를 사용한다.

Color는 artwork RGB 곱셈 tint이며 Alpha는 별개다. Cyclic copy actual age와 RNG/Noise canonical identity, G/D/N의 시간 의미, Layer/Parent/System/Surface/2.5D/revolution/clip 의미를 바꾸지 않았다.

Evaluator sample당 QColor/dict/deepcopy/sort/serialization/filesystem/spline/point collection 생성은 없다. 기존 frame-level settings/cache key 직렬화와 depth sorting은 그대로지만 point evaluation 안에서는 하지 않는다. Spawn cache key는 모든 lifetime 채널을 제외한다. Render key 및 playback lifetime revision은 curve 변경을 포함한다. Existing MainWindow command가 preview/generated invalidation과 Undo refresh를 수행한다.

## UI/Undo

Over Lifetime의 compact list에서 지점을 선택하고 아래 time/value/RGB/easing을 편집한다. Graph canvas는 없다. 시간은 %,4 decimals/0.1% step, scalar는6 decimals. 0/100% time은 locked, final easing은 disabled, 끝점은 삭제 불가다. 내부 time duplicate/crossing은 상태 문구와 함께 revert한다.

Add는 largest gap midpoint + current evaluated value + **Linear outgoing easing**, ties는 첫 gap. 전체 curve shape 보존을 보장하지 않는다. Remove는 선택된 internal only. RGB picker cancel/no-op은 mutation0; Alpha control 없음. KO/EN captions/tooltips/easing captions을 제공한다.

Hidden legacy controls는 기존 callers/tests의 endpoint adapter일 뿐 active UI에는 중복 Start/End 입력이 없다. settings()는 editor의 canonical points를 deepcopy하므로 숫자 display precision/selection/scrub/localization이 curve를 재구성하거나 잘라내지 않는다.

각 accepted Add/Remove/Time/Value/RGB/Easing/Enabled action은 Undo1(merge ID−1). No-op/reject/cancel/refresh는 Undo/dirty/revision0. Lifetime edit는 Composition timeline/Auto-Key tracks를 만들지 않는다.

## 검증과 성능

신규 focused3 files **127 passed / 3.40s**. 전체 **1537 passed / 93.52s** 확인 후 최종 재실행을 수행했다(아래 갱신). Compileall, --version, --check, run_app.bat --check, git diff --check exit0. Direct/batch check에서 sandbox의 AppData log write PermissionError warning이 있었으며 권한/로그 경로를 변경하지 않았다. 이는 실제 GUI 수동 실행 검증이 아니다.

v22 frozen renderer와 원래 lifetime helper를 read-only git show로 로드해 4easing×2blend×2cycle mode pixel exact를 검증했다. 레퍼런스의 공통 서비스와 model adapters는 현재 workspace를 공유한다. Raw Current/Full/Generated stage와 Final Playback/Compositor/PNG stage를 각각 exact 비교했으며 compositor의 기존 alpha rounding을 stage 혼동으로 오인하지 않았다.

Evidence: `C:\Dev\pem_v23_lifetime_20261001_serial_verified`.
6합성 dot fixtures ×24 decoded PNGs, JSON project roundtrip, contact sheet, report.json을 생성했다. 이는 애플리케이션 build/ZIP이 아니다. Contact sheet를 시각적으로 검사했고 peak/fade/growth/3-stop tint/prewarm이 보인다. 합성 fixtures는 production artwork quality나 자연스러움을 보장하지 않는다.

동일96×96 canvas/5×5 source, 3 warm samples의 median. 아래 evaluator 수치는 전체5scalar/RGB samples per particle을 합친 Python workload다. 5000 samples는 독립 evaluation만 수행하고 actual renderer는 기존4096 limit에 의해 명시적으로 거부했다. Limit을 해제하거나 particles를 잘라내지 않았다.

| Count | Scenario | Curve samples ms | Warm render ms | Canonical / active |
|---:|---|---:|---:|---|
| 100 | legacy_2_point | 0.4015 | 10.9138 | 100 / 100 |
| 100 | scale_3_point | 0.4249 | 9.9815 | 100 / 100 |
| 100 | opacity_4_point | 0.4201 | 9.9507 | 100 / 100 |
| 100 | color_3_point | 0.373 | 10.334 | 100 / 100 |
| 100 | all_curves | 0.3986 | 9.9227 | 100 / 100 |
| 100 | cyclic_full_stack | 0.394 | 23.6421 | 100 / 200 |
| 500 | legacy_2_point | 2.1556 | 49.6463 | 500 / 500 |
| 500 | scale_3_point | 2.0766 | 49.3354 | 500 / 500 |
| 500 | opacity_4_point | 2.0895 | 49.769 | 500 / 500 |
| 500 | color_3_point | 1.953 | 50.3648 | 500 / 500 |
| 500 | all_curves | 1.9814 | 48.4891 | 500 / 500 |
| 500 | cyclic_full_stack | 2.0366 | 105.9395 | 500 / 1000 |
| 1000 | legacy_2_point | 4.0971 | 98.1932 | 1000 / 1000 |
| 1000 | scale_3_point | 4.1405 | 99.524 | 1000 / 1000 |
| 1000 | opacity_4_point | 4.2283 | 98.3179 | 1000 / 1000 |
| 1000 | color_3_point | 3.8498 | 99.5578 | 1000 / 1000 |
| 1000 | all_curves | 4.0808 | 100.0178 | 1000 / 1000 |
| 1000 | cyclic_full_stack | 4.1754 | 213.9068 | 1000 / 2000 |
| 5000 | legacy_2_point | 20.2341 | safety reject | — / — |
| 5000 | scale_3_point | 20.9983 | safety reject | — / — |
| 5000 | opacity_4_point | 21.0707 | safety reject | — / — |
| 5000 | color_3_point | 18.7312 | safety reject | — / — |
| 5000 | all_curves | 20.1808 | safety reject | — / — |
| 5000 | cyclic_full_stack | 20.1272 | safety reject | — / — |

2-point renderer v23/v22 ratios: 100: 1.0845 (10.9138/10.0634ms); 500: 0.985 (49.6463/50.3998ms); 1000: 0.9939 (98.1932/98.7952ms).
약±측정 노이즈 수준의 renderer 비용을 확인했지만 standalone evaluator는 point lookup/adapter 비용이 늘었다. 2000 active full-stack은 약214ms 수준이며60FPS 보장은 하지 않는다. Cyclic benchmark는 P24/L36/frame5에서 previous-cycle copies를 실제 포함한다.

## 범위와 남은 QA

좁은 Multi-point Lifetime Scale/Opacity/RGB Color end-to-end는 자동 검증 기준 COMPLETE. 전체 Curve System은 PARTIAL. Bezier, graph editor, tangents, per-axis Scale, HSV, randomized curve, Timeline curve animation, Trail/Ribbon, Sub-emitter는 구현하지 않았다. 다음 후보는 사용자 GUI 승인 후 최소 Trail/Ribbon foundation이다.

**Windows native GUI manual: 수행하지 않음.** 실제 사용자 승인용 체크리스트는 MANUAL_TEST_CHECKLIST.md 상단15(+responsive) 항목에 남겼다. v23 staged/commit0, tag/push/build0.

## 요청 완료 보고 172항목 매핑

| # | 항목 | 결과/근거 |
|---:|---|---|
| 1 | 시작 HEAD | d91f9582984b3d63904c0666d5d76c700bf40b5d |
| 2 | 시작 Version | 0.0.22 |
| 3 | 시작 FORMAT | 19 |
| 4 | 시작 pytest | 1410 passed / 88.13s |
| 5 | Cyclic checkpoint | 73af974542e2b50a51a8ca57e12373149986865b |
| 6 | 포함 파일 | 아래 explicit whitelist 52 files |
| 7 | 제외 | 보호 PNG, 사용자 프로젝트, C:\Dev evidence, build/dist/log/cache/temp/ZIP |
| 8 | checkpoint 후 Git | main ahead 41; 보호 PNG만 untracked; staged 0 |
| 9 | 기존 Scale | enabled/start/end/easing LifetimeScalarModulation |
| 10 | 기존 Color | enabled/start_rgb/end_rgb/easing LifetimeColorModulation |
| 11 | 기존 Opacity | ParticleEmitterSettings.opacity_start/opacity_end/easing |
| 12 | normalized age | age/(lifetime−1), clamp; lifetime≤1 → 1 |
| 13 | easing helper | emitter_service.ease / eased_lifetime_amount, 공통 EASINGS 4종 |
| 14 | 기존 Scale evaluator | evaluate_lifetime_scalar: disabled 1, eased lerp |
| 15 | 기존 Color evaluator | RGB component arithmetic /255; disabled 1 |
| 16 | 기존 Opacity evaluator | render_particle_frame의 start+(end−start)*ease(age) |
| 17 | Alpha integrity | set_settings에서 s.easing 복원, settings에서 alpha_easing을 독립 저장; 신규 points 유지 |
| 18 | Inspector reconstruction | ParticlePropertiesPanel.set_settings/settings/_changed |
| 19 | serialization | legacy nested models + flat alpha; 새 canonical points로 교체 |
| 20 | Version | 0.0.23 |
| 21 | FORMAT_VERSION | 20 |
| 22 | scalar point | LifetimeScalarPoint(time,value,easing_to_next), frozen |
| 23 | color point | LifetimeColorPoint(time,rgb3,easing_to_next), frozen |
| 24 | canonical | 각 channel enabled + points; model points tuple, JSON points array |
| 25 | legacy adapters | start/end/easing 및 start_rgb/end_rgb properties; Opacity InitVars + point-backed properties; 별도 writable state 없음 |
| 26 | minimum | 2 |
| 27 | maximum | 8 |
| 28 | endpoints | 0/1 필수; UI 시간 수정·삭제 불가 |
| 29 | internal times | unique finite strictly increasing 0<t<1, crossing reject |
| 30 | easing ownership | point i가 i→i+1 소유; 마지막 저장값은 보존하되 미사용/편집 비활성 |
| 31 | Scale mapping | (0,start)/(1,end) |
| 32 | Scale easing mapping | 첫 outgoing easing=legacy easing |
| 33 | Color mapping | 0=start_rgb,1=end_rgb,첫 easing 보존 |
| 34 | Opacity mapping | 0=opacity_start,1=opacity_end,첫 easing=legacy alpha easing |
| 35 | load rewrite | 없음; byte sentinel 검증 |
| 36 | legacy render | 4 easing × 2 blend × 2 cycle mode, v22 frozen renderer+helpers exact |
| 37 | segment lookup | bounded index scan≤8; 2-point render fast path |
| 38 | local u | (t−left.time)/(right.time−left.time) |
| 39 | easing | 기존 ease(), enum 변경 없음 |
| 40 | scalar lerp | left.value+(right.value−left.value)*ease(u) |
| 41 | RGB lerp | encoded sRGB 각 channel lerp /255 |
| 42 | endpoints | 공개 evaluator는 clamp 후 정확한 endpoint; 2-point raster는 legacy float arithmetic |
| 43 | internal knot | 정확한 point value/RGB 직접 반환 |
| 44 | float robustness | finite/strict gaps 검증; no silent sort; UI display rounding이 canonical points를 덮지 않음 |
| 45 | Scale semantics | 수명 내 uniform multiplier |
| 46 | base X/Y ratio | 동일 factor를 base X/Y에 곱함; ratio 테스트 |
| 47 | Scale disabled | identity 1; 기존 픽셀 유지 |
| 48 | Scale peak | 0.2→1.3→0 합성 fixture |
| 49 | Opacity semantics | 항상 활성 scalar curve 0..1 |
| 50 | source alpha | 원본 alpha × lifetime opacity, 기존 raster blend 유지 |
| 51 | layer opacity | raster 후 Layer opacity, 기존 Parent/System/Surface pipeline 유지 |
| 52 | color isolation | RGB points에 alpha 없음 |
| 53 | Alpha Easing migration | legacy easing 첫 outgoing segment로 정확히 변환 |
| 54 | RGB-only | 정확히 int3, bool/alpha/추가 채널 거부 |
| 55 | interpolation space | encoded sRGB, 기존 방식 |
| 56 | tint semantics | source RGB × lifetime tint; 검정 source를 밝히지 않음 |
| 57 | alpha isolation | Color 변경 전후 alpha exact 테스트 |
| 58 | Color disabled | RGB identity (1,1,1), points 보존 |
| 59 | Over Lifetime | 기존 영역, 3 compact list+selected point editor |
| 60 | Scale editor | Enabled + time/value/easing/Add/Remove |
| 61 | Opacity editor | time/value/easing/Add/Remove, enabled toggle 없음 |
| 62 | Color editor | Enabled + time/RGB picker/easing/Add/Remove |
| 63 | time UI | 0..100%, 4 decimals, step 0.1%; endpoints disabled |
| 64 | value UI | Scale 0..16, Opacity 0..1, 6 decimals |
| 65 | color picker | QColorDialog RGB만 읽음; alpha control 없음 |
| 66 | segment easing UI | KO/EN captions + invariant data; final disabled |
| 67 | Add | largest gap midpoint, evaluated value, Linear; first gap wins ties |
| 68 | Remove | 선택된 internal only; endpoint/no selection disabled |
| 69 | endpoint lock | model validation + UI |
| 70 | invalid time | 명시적 상태 문구 + revert; Undo 0 |
| 71 | KO | 제목/필드/버튼/보간/tooltip/거부 문구 |
| 72 | EN | 동일 계약 영문 |
| 73 | refresh integrity | sentinel A/B, 언어/scrub/load/Undo refresh에서 canonical 그대로 |
| 74 | Add Undo | 1 |
| 75 | Remove Undo | 1 |
| 76 | Time Undo | 1 |
| 77 | Scalar Undo | 1 |
| 78 | RGB Undo | 1 |
| 79 | Easing Undo | 1 |
| 80 | no-op | Undo/dirty/revision 0 |
| 81 | picker cancel | mutation/Undo 0 |
| 82 | refresh Undo | 0 |
| 83 | prewarm Scale | copy actual age normalized |
| 84 | prewarm Opacity | 동일 actual age |
| 85 | prewarm Color | 동일 actual age |
| 86 | F(t+P) | static/local Linear/Orbit/Helix × Normal/Additive exact |
| 87 | canonical identity | curve edits는 spawn key에서 제외; slot object cache 유지 |
| 88 | copy age | frame−absolute copy birth; gate라고 time0 재시작 안 함 |
| 89 | Gravity | actual age² 유지 |
| 90 | Drag | analytic effective motion age 유지 |
| 91 | Noise | actual age + canonical particle ID 유지 |
| 92 | Linear | 시간 의미 변경 없음 |
| 93 | Orbit | 기존 motion path 유지 |
| 94 | Helix | 기존 motion path 유지 |
| 95 | Normal | 기존 blend 유지 |
| 96 | Additive | 기존 blend 유지 |
| 97 | full stack | Cyclic/G/D/N/3 curves/Additive 합성·테스트 |
| 98 | FORMAT19 defaults | Scale/Color disabled white/1; Opacity 1→0 Linear |
| 99 | FORMAT20 roundtrip | points/time/value/RGB/easing/enabled exact |
| 100 | invalid payload | deterministic reject; ambiguous legacy+points도 거부 |
| 101 | point count validation | 2..8 |
| 102 | time validation | finite/0..1/strict/endpoints |
| 103 | easing validation | 기존 4 strings |
| 104 | RGB validation | 3 integers 0..255, no bool |
| 105 | render invalidation | canonical settings repr key + playback lifetime revision |
| 106 | generated invalidation | 기존 MainWindow Resource Layer command 적용·재생성 경로 유지 |
| 107 | spawn cache | scale/color/opacity curves 제외 |
| 108 | cyclic slots | RNG/resampling 0 |
| 109 | current | 같은 evaluator |
| 110 | full | 같은 current renderer sequence |
| 111 | generated | raw layer pixels exact |
| 112 | PNG | final compositor 결과 decode exact |
| 113 | parity | raw stage와 final compositor stage를 구분해 exact |
| 114 | dimensions | canvas dimensions 유지 |
| 115 | strict clip | 변경 없음; transform regression 검증 |
| 116 | overscan | 기존 tests 유지; 새 canvas 확장 없음 |
| 117 | 2-point performance | 아래 frozen renderer comparison |
| 118 | 3-point Scale performance | 아래 table |
| 119 | 4-point Opacity performance | 아래 table |
| 120 | 3-point Color performance | 아래 table |
| 121 | all curve performance | 아래 table |
| 122 | cyclic full stack performance | canonical 100/500/1000, active 200/1000/2000; table |
| 123 | allocation/sort | evaluator에서 dict/deepcopy/sort/QColor/filesystem/serialization/point collection 생성 0 |
| 124 | Hit Spark | peak+fade+white/yellow/orange+Additive/G/D |
| 125 | Explosion | small/large/smaller + white/yellow/red + bell alpha |
| 126 | Smoke | growing scale + bell alpha + neutral gray |
| 127 | Magic Wisp | white/cyan/blue + bell alpha + noise |
| 128 | Sword Slash | small/large/small + bell alpha |
| 129 | Cyclic Fire | 3 curves + prewarm + period6 exact |
| 130 | 표현력 평가 | 단일 start/end로 못 만들던 peak/bell/hold/3-stop 표현 가능; 합성 dot는 production artwork 품질 보증 아님 |
| 131 | 신규 tests | test_lifetime_multi_point.py / serialization / ui |
| 132 | focused | 127 passed / 3.40s |
| 133 | scalar tests | legacy4ease/knots/peak/hold/segments/identity |
| 134 | color tests | 3-stop/exact knot/RGB-only/alpha isolation |
| 135 | opacity tests | bell/hold/source/layer alpha/legacy endpoint rounding |
| 136 | migration tests | format19 all easing + no rewrite + format20 roundtrip |
| 137 | UI tests | add/remove/endpoints/limits/invalid times/KO-EN/selection/cancel |
| 138 | Undo tests | each accepted action1, exact Undo/Redo, no-op0 |
| 139 | cyclic tests | prewarm actual age, periodic, large seek |
| 140 | motion/blend tests | G/D/N/Linear/Orbit/Helix/Normal/Additive |
| 141 | transform tests | Parent/parent_offset/System/Surface/2.5D/revolutions/ratio/clip; full suite Keep World/overscan |
| 142 | export tests | Current/Full/Generated/Playback/PNG/reload |
| 143 | full pytest | 최종 1537 passed / 88.28s (이전 실행도 1537 passed / 93.52s) |
| 144 | compileall | exit0 |
| 145 | --version | Pixel Effect Maker v0.0.23 |
| 146 | --check | exit0; sandbox AppData log PermissionError warning |
| 147 | run_app.bat | exit0, same log warning; documented interpreter |
| 148 | diff --check | exit0; LF→CRLF 안내만 있음 |
| 149 | Multi-point Scale audit | COMPLETE (narrow automatically verified path) |
| 150 | Multi-point Opacity audit | COMPLETE |
| 151 | Multi-point Color audit | COMPLETE |
| 152 | overall Curve System | PARTIAL |
| 153 | Graph Editor gap | Bezier/tangents/free graph/per-axis/HSV/random/timeline point animation없음 |
| 154 | Trail gap | 미구현 |
| 155 | Sub-emitter gap | 미구현 |
| 156 | final HEAD | 73af974542e2b50a51a8ca57e12373149986865b |
| 157 | staged | 0 |
| 158 | v23 commit | 0 |
| 159 | tag/push/build | 각 0; PyInstaller/ZIP/Release도 0 |
| 160 | native Windows manual | 수행하지 않음 |
| 161 | 2-point render final | v22 comparison exact |
| 162 | 0→1→0 Scale | 가능 |
| 163 | 0→1→0 Opacity | 가능 |
| 164 | 3-stop RGB | 가능 |
| 165 | per-segment easing | 가능 |
| 166 | Alpha/Color split | 유지 |
| 167 | cyclic prewarm | actual age로 정확히 결합 |
| 168 | seek/export determinism | history/RNG mutation 없음; exact |
| 169 | existing project preservation | 사용자 프로젝트 읽기/쓰기/삭제 없음; 보호 PNG 해시 동일 |
| 170 | effect capability final | peak/bell/hold/3-stop 표현 증가; full Graph Editor 없음 |
| 171 | roadmap alignment | v22 Cyclic 이후 bounded Multi-point 구현; 범위 유지 |
| 172 | next recommendation | GUI 승인 후 최소 Trail/Ribbon 기반 설계·검증 |

## 최종 재검증

최종 전체 재실행: **1537 passed / 88.28s** (failures 0).
신규 3파일 focused: **127 passed / 3.40s**.
compileall/version/direct check/batch check/diff check exit0.
앱 Version0.0.23, FORMAT20. AppData sandbox log write warning 외 실행 점검 오류 없음.
최종 HEAD `73af974542e2b50a51a8ca57e12373149986865b`, main ahead41,
v23 변경은 unstaged/uncommitted, staged0. 보호 PNG hash 동일.
Tag/Push/Build/PyInstaller/ZIP/Release0. Windows native GUI manual **수행하지 않음**.
