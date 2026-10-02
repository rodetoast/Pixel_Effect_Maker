# Pixel Effect Maker v0.0.24 — Deterministic Particle Sprite Trail

## 결과 / 범위

2026-10-01, Windows 11 / Python 3.12.14. Application **0.0.24**, project **FORMAT_VERSION21**.
History-free deterministic sprite afterimages를 Model/Inspector/Undo/Save/Render/Preview/
Playback/Generated/PNG 경로에 구현했다. Ribbon mesh, world-transform historical trail,
timeline/auto-key, sub-emitter, collision, new force/Graph 시스템은 구현하지 않았다.
**Windows native GUI manual: 수행하지 않음**. Qt offscreen tests는 native manual QA가 아니다.

v23를 재검증한 후 explicit whitelist로만 local checkpoint했다:
**9cf4a413b38111e6934e367fc758845707b6fa9c**, `Add multi-point lifetime curves`.
v24 변경은 모두 **unstaged / uncommitted**, staged0, commit0, tag0/push0/build0/PyInstaller0/ZIP0.
현재 branch main은 origin/main보다 42 commits 앞선 상태다. remote update/push는 하지 않았다.

## 시작 검증 / protected file

시작 HEAD: `73af974542e2b50a51a8ca57e12373149986865b`, version0.0.23 / format20.
48 tracked modifications +6 new v23 files, staged0; 별도 untracked `테스트소스.png`.
v23 baseline: **1537 passed /96.66s**, compileall/version/direct check/batch check/diff check 통과.
Checkpoint54 files/1350 insertions/103 deletions; afterward protected PNG만 untracked.

Protected file은 읽기/해시 외에는 수정/삭제/이름 변경/stage하지 않았다. SHA256 시작/끝:
`8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`.

### v23 explicit staged files (54)

```text
CHANGELOG.md
README.md
app/models/particle_emitter.py
app/models/project.py
app/services/effect_playback_service.py
app/services/lifetime_modulation_service.py
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
tests/test_particle_cyclic_emission_serialization.py
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
app/ui/lifetime_point_editor.py
docs/V0_0_23_MULTI_POINT_LIFETIME_REPORT.md
tests/test_lifetime_multi_point.py
tests/test_lifetime_multi_point_serialization.py
tests/test_lifetime_multi_point_ui.py
tools/benchmark_lifetime_multi_point.py
```

위 목록 외 파일은 stage하지 않았다. `git add -A` 미사용. checkpoint 목록은 historical
v23 파일이며 v24 stage 목록이 아니다.

## Render audit / contract

기존 단일 sprite raster는 `effect_render_service.render_transformed_source`.
Arbitrary-age motion은 `particle_render_service.evaluate_particle_motion`, source frame은
`particle_clip_frame/particle_clip_frame_index`, scalar/color modulation은 기존 lifetime
evaluators를 재사용한다. Angular rotation은 rotation+angular_velocity*sample_age.
기존 SourceAsset의 defensive pixel copy 대신 read-only borrowed `_SpriteView`를 사용한다.
Source pixel mutation/RNG/SourceAsset construction을 금지한 test가 통과했다.

```text
D = duration_frames; I = sample_interval_frames; A = copy_age; L = particle lifetime
S = floor((D-1)/I)
delta_max = S*I
delta = I,2I,...,S*I        (strict delta < D; no delta0)
sample_age = A-delta       (0 <= sample_age < L only)
fade = 1-delta/D
sample opacity = historical lifetime opacity * Trail.opacity * fade
head visible: 0 <= A < L   (exactly one head, no Trail fade)
visual lifetime = L+delta_max
last possible visible A = L-1+delta_max
cyclic q = requested frame - gate, canonical birth b, period P:
k_min = ceil((q-b-(L+delta_max-1))/P)
k_max = floor((q-b)/P)
```

Alpha/Scale이 0이거나 strict output clipping으로 마지막 가능한 age보다 먼저 보이지 않을 수 있다.
위 공식은 수명상 가능 범위이며 visible pixel을 보장하지 않는다.

All historical motion/source/random-start/rotation/Scale/RGB/Opacity use sample_age.
Gravity/Noise actual-age clocks and Drag effective base-motion clock remain unchanged.
All samples use **current target-frame** evaluated Layer/Parent/System/Surface snapshot;
past transform keys are not replayed. Parent affine/2.5D/rotation revolutions share existing math.
This is local motion history, **not world-history**, and source playback remains existing policy.
Copy groups sort by live-head projected Z, or latest projectable tail sample Z when tail-only.
Unprojectable-head fallback is latest projectable stamp; ties keep canonical/cycle order.
Inside each group: oldest → newest → head. No global per-stamp depth interleaving.
Normal/Additive semantics and layer alpha pipeline are unchanged.

### Timing / safety / caches

Particle ResourceLayer rendering has no logical end_frame gate; output_frame_count controls
full render range. Therefore no derived end-frame adjustment was necessary. Trail does not
change frame range, project duration, export dimensions, overscan or strict clipping.
Users may need longer output duration to export the entire post-death tail.

Cyclic conservative visual-copy bound: count_max*ceil((Lmax+delta_max)/P), maximum4096.
One Shot bound: count_max. Conservative Trail stamp bound: visual_bound*S, maximum8192.
These count only Trail historical stamps (heads separate). Both exact boundaries pass; one
over is rejected explicitly, never dropped or truncated. Even rejected OFF-preserved settings
cannot be enabled until corrected. Safety limits are not performance/60FPS guarantees.

Trail settings invalidate render/preview/playback/generated output via existing draft paths
plus explicit playback revision tuple. Spawn cache removes the nested Trail key: changes do
not reseed or replace canonical slots/Noise identity. OFF dispatch never enters Trail sampling.
Current-request temporary stamps/points are not persistent histories; per-sample operations
have no QColor, dict creation, deepcopy, filesystem, serialization, RNG, point sorting, source
image copy or history scan. Batch projection and group sorting operate on this target request.

## Inspector / Undo

Compact Trail group follows Natural Motion and precedes Over Lifetime. Static settings:
Enabled False, Duration12 (strict int2..240), Interval2 (strict int1..D-1),
Opacity.75 (finite0..1; bool rejected). KO/EN labels, frame suffixes and explanatory tooltips.
OFF disables the three value fields without resetting them.
A ON17/3/.625 and B OFF41/5/.3125 preserve exact state across A→B→A selection, refresh,
language changes and scrub. Each accepted action is Undo1/Redo exact; invalid/no-op/refresh
Undo0/revision0/dirty0. No Trail Timeline keys or auto-key introduced.
Offscreen layout tests cover KO/EN,280px/300px and150%font; native manual remains unperformed.

## Automated evidence

New test files: `test_particle_trail.py` (54), `test_particle_trail_serialization.py` (27),
`test_particle_trail_ui.py` (12): **93 passed /2.63s** focused.
First integrated full run1622 passed; added pixel-borrowing/alpha/current-transform tests:
1626 passed /102.42s. Final full result: **1630 passed /98.04s, failures=0, errors=0**.

One repeated full run reused an existing pytest basetemp while its log was still locked:
1551 passed/79 setup errors (WinError32 on old test log, not assertion failures).
No project/log permissions or files were changed. The final run uses new dedicated
`C:\Dev\pem_v24_final_20261001` and records its result below.

Compileall app/tests/tools exit0; --version0.0.24 exit0; direct --check exit0;
run_app.bat --check exit0; git diff --check exit0.
Both check invocations report sandbox AppData log write PermissionError/logging_unavailable.
This is an environment diagnostic limitation, not claimed as normal logger operation.
Existing logging/permissions were not changed.

Frozen OFF oracle loads renderer from checkpoint9cf4a41 with shared current dependency
modules, so it is not a completely isolated v23 executable. Twelve mode/cycle/blend
combinations at frames0/1/5/15/23/100000 compare RGBA exactly. Dedicated OFF dispatch test
forbids invoking Trail service. Legacy format20 missing Trail migrates default-off without
rewriting original JSON, then preserves RGBA after format21 roundtrip.

Five synthetic representatives (96x96,24 frames): Projectile, Magic Wisp Comet, Hit Spark,
Sword Slash Helper, Cyclic Ember. All current/full/generated/playback and decoded PNG results
match after Save/Reload. Output size/range unchanged. Projectile includes post-death tail.
Cyclic Ember gate reports24 head copies /72 visual copies /120 historical stamps, including
tail-only copies. Contact sheet inspected: local straight/curved/radial afterimages observable,
not polished game artwork or native GUI visual approval. Sword Slash is a sprite-stamp helper,
not continuous ribbon geometry.

Evidence: `C:\Dev\pem_v24_trail_20261001_a\report.json`, `contact_sheet.png`,
representative JSON/PNG folders; generated synthetic only, outside project/user assets.

## Performance — measured, not real-time guarantee

Windows11/Python3.12.14,96x96 canvas,5x5 synthetic sprite, three warm renders median.
Diagnostic first-render timings are separate and must not be mistaken for comparable cold
startup. OFF frozen comparison shares dependencies as stated. Full-stack Cyclic includes
G/D/N/Additive/multi-point with period24/lifetime16. Dense age12 has fewer actual stamps than
its conservative maximum: duration24/interval2 gives11 potential offsets but only6 valid atA12.
Invalid dense1000/cyclic1000 are rejected before rendering. No measurements were substituted
for rejected configurations. No hardware/device-independent or60FPS claim.

| Canonical | Scenario | D/I | P/L | Visual/stamp bound | Actual head/visual/trail | Warm ms | Frozen OFF ms | Frame100000 diagnostic ms |
| ---: | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| 100 | off | 12/2 | 24/24 | 100/0 | 100/100/0 | 12.351 | 12.998 | — |
| 100 | light | 12/3 | 24/24 | 100/300 | 100/100/300 | 46.964 | — | — |
| 100 | medium | 12/2 | 24/24 | 100/500 | 100/100/500 | 70.319 | — | — |
| 100 | dense | 24/2 | 24/24 | 100/1100 | 100/100/600 | 71.957 | — | — |
| 100 | cyclic_full_stack | 12/2 | 24/16 | 200/1000 | 100/100/500 | 75.559 | — | 64.608 |
| 500 | off | 12/2 | 24/24 | 500/0 | 500/500/0 | 58.391 | 58.082 | — |
| 500 | light | 12/3 | 24/24 | 500/1500 | 500/500/1500 | 235.466 | — | — |
| 500 | medium | 12/2 | 24/24 | 500/2500 | 500/500/2500 | 347.872 | — | — |
| 500 | dense | 24/2 | 24/24 | 500/5500 | 500/500/3000 | 357.277 | — | — |
| 500 | cyclic_full_stack | 12/2 | 24/16 | 1000/5000 | 500/500/2500 | 371.853 | — | 316.835 |
| 1000 | off | 12/2 | 24/24 | 1000/0 | 1000/1000/0 | 116.971 | 119.594 | — |
| 1000 | light | 12/3 | 24/24 | 1000/3000 | 1000/1000/3000 | 439.852 | — | — |
| 1000 | medium | 12/2 | 24/24 | 1000/5000 | 1000/1000/5000 | 698.148 | — | — |
| 1000 | dense | 24/2 | 24/24 | 1000/11000 | —/—/— | 거부 | — | — |
| 1000 | cyclic_full_stack | 12/2 | 24/16 | 2000/10000 | —/—/— | 거부 | — | — |

Frame100000 Cyclic actual counts: count100 head0/visual100/trails500, count500
head0/visual500/trails2500. Modulo-period RGBA comparison exact. Work scales with bounded
visible copies/stamps, not elapsed frame history. Valid500 medium ~348ms and1000 medium
~698ms demonstrate significant cost; keep counts/afterimage density low for interactive use.
Scheduling/caches are existing mechanisms, not a new GPU renderer.

## Capability / next recommendation

Narrow Deterministic Sprite Trail: COMPLETE (automated end-to-end, native approval pending).
Ribbon Mesh: MISSING. World-space historical Trail: MISSING. Overall Trail/Ribbon: PARTIAL.
True turbulence/force stack/collision, Sub-emitter event spawning and Graph/Bezier/tangent
systems remain missing. Existing Cyclic → Multi-point → minimal Trail roadmap is respected.
First user native GUI approval, then recommend a bounded deterministic birth/death-event
Sub-emitter foundation; implement neither child emitters nor Ribbon speculatively here.

## Requested completion items 1..207

| # | Requested item | Evidence / result |
| ---: | --- | --- |
| 1 | 실제 시작 HEAD | 73af974542e2b50a51a8ca57e12373149986865b |
| 2 | 시작 Version | 0.0.23 |
| 3 | 시작 FORMAT_VERSION | 20 |
| 4 | 시작 pytest | 1537 passed / 96.66s; failures=0 |
| 5 | Multi-point Lifetime commit hash | 9cf4a413b38111e6934e367fc758845707b6fa9c — Add multi-point lifetime curves |
| 6 | explicit staged files | 54 explicit files, 아래 whitelist; git add -A 미사용 |
| 7 | excluded files | 테스트소스.png, build/release/ZIP/runtime/user assets 제외 |
| 8 | checkpoint 후 Git | main ahead 42; staged 0; protected PNG만 untracked |
| 9 | single particle raster function | effect_render_service.render_transformed_source; 기존 Normal/Additive raster 공유 |
| 10 | arbitrary-age motion evaluator | particle_render_service.evaluate_particle_motion(...particle_age=sample_age) |
| 11 | sprite-frame evaluator | particle_clip_frame / particle_clip_frame_index |
| 12 | historical Scale evaluator | evaluate_lifetime_scalar_for_render(scale_over_lifetime,t) |
| 13 | historical Color evaluator | evaluate_lifetime_color_component(color_over_lifetime,t,channel) |
| 14 | historical Opacity evaluator | evaluate_lifetime_scalar_for_render(opacity_over_lifetime,t) |
| 15 | angular rotation evaluator | instance.rotation + angular_velocity * sample_age |
| 16 | depth key | copy group: head projected Z, tail-only latest projectable sample Z; (Z, order) |
| 17 | cyclic copy lifetime gate | copy_age < lifetime + delta_max, integer analytic k bounds |
| 18 | Resource Layer end timing | Particle rendering은 logical end_frame gate를 사용하지 않음; output count/range 변경 없음 |
| 19 | current transform snapshot semantics | 요청 frame의 evaluated Layer/Motion와 Parent affine을 모든 sample에 적용 |
| 20 | Version | 0.0.24 |
| 21 | FORMAT_VERSION | 21 |
| 22 | Trail settings model | ParticleTrailSettings, ParticleEmitterSettings.trail nested dataclass |
| 23 | Enabled | strict bool, default False |
| 24 | Duration | strict integer 2..240, default 12 |
| 25 | Interval | strict integer 1..Duration-1, default 2 |
| 26 | Opacity | finite numeric 0..1, default .75, bool 금지 |
| 27 | min/max/default | 위 범위; duration/interval에서 bool/float/string 금지 |
| 28 | migration | FORMAT20 missing trail → OFF/12/2/.75; 읽을 때 원본 rewrite 없음 |
| 29 | delta formula | delta = I,2I,...,S*I |
| 30 | delta<D rule | strict delta < D; D endpoint 제외 |
| 31 | sample age | sample_age = copy_age - delta; 0 <= sample_age < L |
| 32 | no delta0 | delta0 trail 없음; live head만 1회 별도 |
| 33 | sample count formula | S = floor((D-1)/I) |
| 34 | fade formula | fade = 1-delta/D |
| 35 | final opacity multiplier | historical lifetime opacity * Trail.opacity * fade; Layer alpha 기존 경로 |
| 36 | particle lifetime | head alive ages 0..L-1; spawn lifetime 자체 변경 없음 |
| 37 | delta_max | delta_max = floor((D-1)/I)*I (OFF=0) |
| 38 | visual lifetime | L + delta_max |
| 39 | tail-only state | A >= L이어도 valid sample 있으면 tail-only |
| 40 | final visible age | 최후 가능한 copy age = L-1+delta_max; opacity/scale/clipping으로 더 일찍 안 보일 수 있음 |
| 41 | One Shot post-death trail | L5/D12/I2: head A5 사망, final sample A14, A15 없음 |
| 42 | cyclic visual lifetime extension | cyclic iterator visibility_extension_frames=delta_max |
| 43 | k-bound changes | k_min=ceil((q-b-(L+delta_max-1))/P), k_max=floor((q-b)/P) |
| 44 | previous head-alive copy | 기존 head-alive previous-cycle copies 포함 |
| 45 | previous tail-only copy | visual lifetime 안의 tail-only previous copies도 포함 |
| 46 | gate steady state | gate부터 analytic enumeration; history warm-up 없음 |
| 47 | lifetime<P | 자동 tests L5/P6 |
| 48 | lifetime=P | 자동 tests L6/P6 |
| 49 | lifetime>P | 자동 tests L9/P6 |
| 50 | duration>P | D12/P6 자동 tests |
| 51 | F(t+P) | static/local transform 조건 F(t+P)=F(t), frame100000 포함; 비주기 global animation은 별도 |
| 52 | canonical particle identity | same immutable canonical spawn slot object |
| 53 | cycle-copy identity | (cycle_index,particle_id) identity 유지 |
| 54 | Noise identity | canonical particle ID와 emitter seed 유지 |
| 55 | Trail RNG draws | 0; Random patch 및 borrowed-view tests |
| 56 | spawn cache | trail fields spawn key에서 제외 |
| 57 | reseeding 여부 | 없음; ON/OFF/값 변경 모두 same cached slots |
| 58 | Linear | 기존 evaluator sample_age 적용 |
| 59 | Orbit | 기존 Orbit base progress/radius at historical age |
| 60 | Helix | 기존 Helix progress/axial travel at historical age |
| 61 | Gravity | actual historical age의 .5*g*age² |
| 62 | Drag | historical age의 analytic effective motion clock |
| 63 | Noise | historical actual age + same stable ID/seed; no draws |
| 64 | source frame | particle_clip_frame(...sample_age,...) |
| 65 | playback random | canonical random_start_frame/playback_speed 그대로 사용 |
| 66 | angular rotation | rotation + angular_velocity*sample_age |
| 67 | Scale | normalized_lifetime_age(sample_age,L), uniform multiplier/base ratio 유지 |
| 68 | Color | historical multi-point RGB only; alpha와 독립 |
| 69 | Opacity | historical multi-point alpha; source alpha/raster pipeline 유지 |
| 70 | trail fade ordering | historical lifetime alpha에 fixed trail multiplier 적용 후 기존 raster/Layer alpha |
| 71 | Particle/System local history semantic | Particle/System-local motion history |
| 72 | current Layer transform snapshot | current frame Layer Space evaluated once |
| 73 | current Parent snapshot | caller의 current Parent affine 사용 |
| 74 | System transform | current evaluated System motion snapshot; sample age만 달라짐 |
| 75 | Surface | 기존 Surface pass를 현재 frame에 적용 |
| 76 | 2.5D | 기존 local perspective/Layer projection 재사용 |
| 77 | Rotation Revolution | 현재 rotation revolutions 의미 보존 |
| 78 | World-history 미지원 명시 | UI tooltip/README/audit/report에 world-transform history 미지원 명시 |
| 79 | oldest/newest/head | copy 내부 oldest → newest → live head |
| 80 | live-copy depth group | projectable live head가 있으면 head Z 사용 |
| 81 | tail-only depth | tail-only latest valid projectable historical sample Z |
| 82 | same-Z tie breaker | One Shot canonical enumerate order; Cyclic (cycle_index,particle_id) |
| 83 | Normal | 기존 raster와 stable copy groups; sample global interleave 없음 |
| 84 | Additive | 기존 additive raster/Layer composition 의미 유지 |
| 85 | visual-copy bound | one-shot count_max; cyclic count_max*ceil((Lmax+delta_max)/P) |
| 86 | visual-copy hard limit | 4096 visual copies; 기존 head-only bound를 extended lifetime으로 확장 |
| 87 | trail stamp estimate | conservative visual copies * floor((D-1)/I), head stamps 제외 |
| 88 | trail stamp limit | 8192 trail stamps |
| 89 | exact boundary | 4096 visual 및 8192 stamp exact boundary 통과 |
| 90 | over limit | 4097 visual / 8193 stamp 거부; dense1000 11000 / cyclic1000 10000 거부 |
| 91 | silent truncation 여부 | 없음; explicit ValueError/UI revert, 줄여서 렌더하지 않음 |
| 92 | group 위치 | Natural Motion 뒤 / Over Lifetime 앞 |
| 93 | Trail label | Trail / 잔상 궤적 |
| 94 | Enabled | Enable Trail / 잔상 사용 |
| 95 | Duration | Duration / 지속 시간, frame suffix |
| 96 | Interval | Sample Every / 샘플 간격, frame suffix |
| 97 | Opacity | Opacity / 불투명도, decimals6 |
| 98 | KO | Korean field labels/status/tooltips |
| 99 | EN | English field labels/status/tooltips |
| 100 | tooltip | arbitrary-age/no history/current transform/not Ribbon/world history + 필드별 설명 |
| 101 | disabled state | OFF 3 controls disabled; 값 보존 |
| 102 | validation | invalid duration/interval/budget 원래 값 복원, Undo/dirty 없음 |
| 103 | safety/status | conservative visual/stamp estimate, rejection advice, realtime 보장 아님 |
| 104 | refresh integrity | A17/3/.625 ON ↔ B41/5/.3125 OFF; selection/refresh/scrub/KO/EN 보존 |
| 105 | Enable | accepted action Undo1, exact redo |
| 106 | Duration | accepted action Undo1, exact redo |
| 107 | Interval | accepted action Undo1, exact redo |
| 108 | Opacity | accepted action Undo1, exact redo |
| 109 | no-op | command0, revision/dirty unchanged |
| 110 | invalid edit | command0, revert, revision/dirty unchanged |
| 111 | refresh | command0; no Auto-Key/Timeline track added |
| 112 | render cache | nested trail serialized settings가 render-relevant key에 포함 |
| 113 | preview | accepted draft change 기존 preview invalidation |
| 114 | playback revision | explicit trail tuple in playback_relevant_revision |
| 115 | generated | 기존 regenerate/invalidation 경로, direct/full/generated parity test |
| 116 | spawn cache | trail pop from _spawn_cache_key |
| 117 | mode changes/reseed 여부 | mode unchanged; trail edit alone no reseed |
| 118 | sequential | full sequence/direct equality |
| 119 | direct | history 없이 analytic target evaluation |
| 120 | reverse | reverse order equality |
| 121 | frame step | requested independent frame evaluation |
| 122 | current | current single-frame parity |
| 123 | full | full sequence parity |
| 124 | generated | baked Generated pixels parity |
| 125 | PNG | decoded PNG exact; representative Save/Reload/PNG parity |
| 126 | frame100000 | 100000 직접 계산; static cyclic modulo-period equality |
| 127 | FORMAT20 default | missing nested settings default OFF/12/2/.75 |
| 128 | Trail OFF exact | 기존 renderer fast path에 trail enumeration 없음 |
| 129 | frozen v23 comparison | 9cf4a41 renderer git-show frozen oracle; shared current dependencies 제한 명시 |
| 130 | One Shot | 3 motion modes × Normal/Additive, One Shot frozen exact |
| 131 | Cyclic | 3 motion modes × Normal/Additive, Cyclic frozen exact |
| 132 | Normal | RGBA np.array_equal |
| 133 | Additive | RGBA np.array_equal |
| 134 | benchmark tool | tools/benchmark_particle_trail.py; machine-readable report.json/contact_sheet.png |
| 135 | 100 | 100 all scenarios valid, benchmark table |
| 136 | 500 | 500 all scenarios valid, benchmark table |
| 137 | 1000 | 1000 OFF/light/medium valid; dense/cyclic explicit rejection |
| 138 | duration/interval | OFF12/2; light12/3; medium12/2; dense24/2; cyclic12/2 |
| 139 | head copies | actual diagnostics count separately; table/report.json |
| 140 | visual copies | actual diagnostics distinct copy keys; table/report.json |
| 141 | trail stamps | actual historical stamp count separate from head count |
| 142 | OFF baseline | frozen-v23 OFF same pixels and comparable measured warm baseline |
| 143 | light trail | light S3, actual count*3 at age12 |
| 144 | medium trail | medium S5, actual count*5 at age12 |
| 145 | cyclic full stack | Cyclic + G/D/N/Additive/multi-point; period24/lifetime16, large frame tail-only |
| 146 | frame100000 | frame100000 measured without history scan; modulo-period exact |
| 147 | sample-budget rejection | 1000 dense11000/cyclic10000; no render/truncation on rejection |
| 148 | realtime claim 여부 | 하지 않음; even valid500/1000 scenarios exceed realtime frame budgets |
| 149 | Projectile | Projectile synthetic fixture: moving sprite stamps; post-death retained |
| 150 | Magic Wisp/Comet | Magic Wisp Comet synthetic fixture: curved colored stamps |
| 151 | Hit Spark | Hit Spark synthetic fixture: radiating decaying stamps |
| 152 | Sword Slash helper | Sword Slash Helper: curved afterimages, not continuous Ribbon |
| 153 | Cyclic Ember | Cyclic Ember: gate 24 live /72 visual /120 trails; previous tail-only |
| 154 | 실제 표현력 개선 | Contact sheet inspected, alpha coverage and five pipeline parity checks; production art/native QA 아님 |
| 155 | 신규 files | tests/test_particle_trail.py, tests/test_particle_trail_serialization.py, tests/test_particle_trail_ui.py |
| 156 | focused count | 93 passed / 2.63s after final focused additions |
| 157 | sampling | positive offsets/fade/no delta0 |
| 158 | post-death | death persistence/final age/disappearance |
| 159 | cyclic | L<P/=P/>P, D>P, gate, periodic |
| 160 | historical appearance | sprite/random/rotation/multi-point historical age |
| 161 | identity | spawn object/no Random draws/canonical copies |
| 162 | ordering | oldest/head/depth tie Normal/Additive |
| 163 | safety | 4096/4097 and8192/8193, no dropping |
| 164 | UI | offscreen KO/EN +280/300px +150%font; native manual이 아님 |
| 165 | Undo | accepted4 actions Undo1, invalid/no-op/refresh0 |
| 166 | serialization | format20 missing + format21 roundtrip/strict malformed fields |
| 167 | transform | parent/System/Surface/2.5D/revolutions and current-transform history independence |
| 168 | export | PNG decoded exact, output range/dimensions unchanged |
| 169 | full pytest | 1630 passed /98.04s; failures=0, errors=0; dedicated basetemp |
| 170 | compileall | compileall app tests tools exit0 |
| 171 | --version | Pixel Effect Maker v0.0.24, exit0 |
| 172 | --check | direct --check exit0; AppData logger permission warning (sandbox) |
| 173 | run_app.bat | run_app.bat --check exit0, same logger warning |
| 174 | git diff --check | exit0; CRLF notices only, no whitespace errors |
| 175 | Deterministic Sprite Trail status | COMPLETE for narrowly specified deterministic sprite trail end-to-end; GUI approval pending |
| 176 | Ribbon Mesh status | MISSING |
| 177 | World-space Trail status | MISSING |
| 178 | overall Trail/Ribbon family status | PARTIAL |
| 179 | 남은 Sub-emitter gap | event-based birth/death sub-emitter/child effect ownership 미구현 |
| 180 | 남은 Force gap | true force stack/turbulence/collision 미구현; analytic G/D/Nのみ |
| 181 | 남은 Graph gap | Graph Editor/Bezier/tangents/per-axis/HSV/random curves 미구현 |
| 182 | 최종 HEAD | 9cf4a413b38111e6934e367fc758845707b6fa9c |
| 183 | staged | 0; all v24 tracked edits/new files unstaged |
| 184 | v0.0.24 commit | 0 |
| 185 | tag/push/build | tag0/push0/build0/PyInstaller0/ZIP0 |
| 186 | Windows native GUI manual 여부 | 수행하지 않음 |
| 187 | history buffer 없는지 | 없음; current-request stamps/points arrays는 playback history가 아님 |
| 188 | Direct Seek deterministic인지 | 예, pure arbitrary-age evaluation |
| 189 | birth에서 Trail zero인지 | 예, age0 historical samples0 |
| 190 | head double render 없는지 | 예, delta0 제외 + live head1 |
| 191 | post-death trail persistence인지 | 예, visual lifetime tail-only |
| 192 | sample historical motion exact인지 | 기존 evaluators 재사용; sampled diagnostics exact |
| 193 | sample historical appearance exact인지 | sprite/rotation/Scale/RGB/Opacity historical exact tests |
| 194 | multi-point curves와 결합되는지 | 예, 모든3 bounded multi-point channels |
| 195 | cyclic prewarm trail steady인지 | 예, head-alive/tail-only previous copies |
| 196 | F(t+P) 유지인지 | 예, static/local periodic assumption에서 exact |
| 197 | RNG identity 보존인지 | 예, draw0/same canonical/Noise identity |
| 198 | visual-copy/stamp safety인지 | 예, conservative reject-without-truncation |
| 199 | current-transform local trail 의미 유지인지 | 예, 과거 transform 키가 달라도 현재 snapshot 같으면 RGBA 같음 |
| 200 | Preview/Export parity인지 | 예, current/full/generated/playback/save-reload/PNG exact |
| 201 | legacy v23 exact인지 | 예, frozen v23 ON 아닌 OFF comparisons; shared-dependency oracle 제한 명시 |
| 202 | Projectile 표현력 개선 | 경로/사후 fade 추가; synthetic coverage 증거 |
| 203 | Magic/Comet 표현력 개선 | 곡선 local afterimage/colored decay 추가 |
| 204 | Spark 표현력 개선 | radiating decaying afterimages 추가 |
| 205 | Ribbon Mesh를 과장하지 않았는지 | 예, Ribbon/world-history 명시 MISSING |
| 206 | 기존 roadmap과 일치하는지 | 예, Cyclic → Multi-point → 최소 deterministic Trail |
| 207 | 다음 추천 기능 | 먼저 사용자 Windows GUI 승인; 다음 deterministic bounded birth/death Sub-emitter foundation |

## Final Git / manual boundary

HEAD remains9cf4a413b38111e6934e367fc758845707b6fa9c. v24 staged0/commit0.
Tag0,Push0,Build0,PyInstaller0,ZIP0. ProtectedPNG untouched and untracked.
All current v24 code/docs/tests/tool edits remain unstaged/uncommitted.
Windows native GUI manual: **수행하지 않음**; see [manual checklist](MANUAL_TEST_CHECKLIST.md).
