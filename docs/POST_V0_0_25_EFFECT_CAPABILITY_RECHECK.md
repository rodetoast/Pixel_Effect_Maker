# Pixel Effect Maker — Post-v0.0.25 Effect Capability Recheck

2026-10-02. Code audit / automated synthetic diagnostics only.
Windows native GUI manual: **수행하지 않음**.

## Outcome and boundary

**v0.0.26 1순위: Deterministic Local Flat-ground Contact Foundation**.
2순위 Continuous Ribbon; 3순위 spatial Force/Turbulence.
Per-event Variation은 유의미한 품질 개선이지만 이번 12종의 기본형을 막는 구조적
blocker로 입증되지 않았다. 이전 v25 추천을 유지하지 않는다.

이는 제품 사용 통계나 모든 게임 effect에 대한 일반 순위가 아니다. 아래 명시한
12 archetype와 10 advanced goals 안에서 구조적 결손/우회 비용/구현 위험을 비교한
설계 판단이다. Contact4 > Ribbon3 = Force3; Graph 편집 편의12는 표현 unlock12가 아니다.
작은 dot/strip source로 확인한 기능 경로를 polished artwork/자연스러움으로 과장하지 않는다.
임의 terrain 접촉은 offline fixed PNG가 게임의 동적 world에 대응한다는 뜻이 아니다.

작업 루트: `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`.
시작 HEAD `2470af26df658e72440ac4712f90973ce75008fc`, v0.0.25 / FORMAT22.
Baseline **1732 passed /116.78s**, focused Sub-emitter **102 passed /5.12s**.
Compile/version/format/direct check/batch check/diff check 통과, staged0, PNG 해시 동일.
Timing/L-1/Trail separation/ID references/Undo/template isolation/RNG0/periodicity/parity/
4096+8192 safety tests를 포함한 정상 baseline 뒤에만 승인 범위58개를 explicit stage했다.

Checkpoint: **`01797ec946ec39c90de34c60253b7802c386c054`**,
`Add deterministic birth and death sub-emitters`.
58 files,1641 insertions/99 deletions. 직후 main ahead44, staged0, 보호 PNG만 untracked.
네트워크 fetch/push 없음. 이 audit의 변경은 그 이후 **unstaged/uncommitted**로 남긴다.
Production app/tests/version/schema 수정0; v26 구현0; tag/push/build/PyInstaller/ZIP/release0.
사용자 project를 읽거나 변경하지 않았다. 보호 PNG는 읽기/해시만 사용, 이름/내용/stage 유지:
`8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`.

### Explicit checkpoint whitelist (58)

```text
CHANGELOG.md
README.md
app/models/particle_emitter.py
app/models/project.py
app/services/effect_playback_service.py
app/services/effect_resource_layer_render_service.py
app/services/particle_preview_service.py
app/services/particle_render_service.py
app/services/particle_sub_emitter_service.py
app/services/particle_trail_render_service.py
app/ui/main_window.py
app/ui/particle_properties_panel.py
app/version.py
docs/EFFECT_AUTHORING_CAPABILITY_AUDIT.md
docs/MANUAL_TEST_CHECKLIST.md
docs/V0_0_25_SUB_EMITTER_REPORT.md
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
tests/test_lifetime_multi_point_serialization.py
tests/test_particle_additive_blend.py
tests/test_particle_color_lifetime_serialization.py
tests/test_particle_cyclic_emission_serialization.py
tests/test_particle_drag_serialization.py
tests/test_particle_gravity_serialization.py
tests/test_particle_noise_serialization.py
tests/test_particle_pipeline.py
tests/test_particle_scale_over_lifetime.py
tests/test_particle_sub_emitter.py
tests/test_particle_sub_emitter_serialization.py
tests/test_particle_sub_emitter_ui.py
tests/test_particle_trail_serialization.py
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
tools/benchmark_particle_sub_emitter.py
```

기존 tests의 mechanical 현재-version/format assertions도 v25 승인 범위다.
제외: `테스트소스.png`, 사용자 project, CDev evidence, build/dist/exe/ZIP/cache/log/temp/backup.
`git add -A` 사용하지 않음. 위 목록은 이번 audit stage 목록이 아니다.

## Sources, definitions and current delta

기존 `EFFECT_AUTHORING_CAPABILITY_AUDIT.md`와 v22/v23/v24/v25 보고서의 실제 파일을
읽고 현재 코드와 대조했다. 과거 overlay/보고서는 그대로 보존한다.
v22 보고서 앞부분에 v23 요청 본문이 섞여 있는 역사적 문서 이상을 발견했다.
뒷부분의 실제 Cyclic 보고와 코드/tests를 근거로 사용했으며 이번 audit에서 정리하지 않았다.

기존 정의: COMPLETE=명시한 좁은 end-to-end 경로 자동 검증, PARTIAL=범위/접근/검증 제한,
MISSING=모델/UI/실행 경로 없음. BUGGY는 재현 결함, UI_ONLY/MODEL_ONLY/RENDER_ONLY는
경로 비대칭, EXPORT_GAP은 실제 final 전달 결손이다. 미구현을 BUGGY라 부르지 않는다.

| Current feature | Status | Actual scope / residual gap |
|---|---|---|
| Scale over Lifetime | COMPLETE narrow | uniform 2..8 points, base XY ratio 유지; independent XY 없음 |
| Opacity over Lifetime | COMPLETE narrow | alpha 2..8 points, RGB와 분리, four segment easings |
| Color over Lifetime | COMPLETE narrow | RGB tint 2..8 points, encoded component lerp; HSV/random palette 없음 |
| Multi-point Lifetime family | PARTIAL overall | 세 narrow channels COMPLETE; free Graph/Bezier/tangents 없음 |
| Additive | COMPLETE narrow | particle/resource/effect/generated/final RGBA contract; Multiply/Screen 없음 |
| Gravity | COMPLETE narrow | actual age² constant signed local-Y displacement |
| Drag | COMPLETE narrow | analytic base-motion clock; Gravity 감쇠하는 physical air drag 아님 |
| Noise | COMPLETE narrow | deterministic smooth XY positional displacement; force/curl 아님 |
| Cyclic Emission | COMPLETE narrow | analytic prewarm/copy enumeration, repeated canonical schedule; rate/sec 아님 |
| Sprite Trail | COMPLETE narrow | history-free age resampling, post-death stamps; Ribbon/world-history 없음 |
| Birth Sub-emitter | PARTIAL approval | narrow automated end-to-end verified; native final COMPLETE 승인 유보 유지 |
| Death Sub-emitter | PARTIAL approval | B+L originL-1; Trail 늦춤 없음, translation only; 동일 승인 유보 |

이번 새 BUGGY/UI_ONLY/RENDER_ONLY/EXPORT_GAP 판정 없음. 넓은 Event family는 PARTIAL:
recursive graph, multiple targets, threshold/contact events, inheritance, per-event variation MISSING.
기존 source once/hold selector의 MODEL_ONLY 접근 제한, sheet/engine metadata 부재는
별도 authoring/delivery gap이며 이번 Particle 후보 unlock 수에는 더하지 않는다.

### Code evidence and negative audit

`particle_emitter.py`: dataclasses, serializer/validation, four shapes, 2..8 points, two events.
`particle_render_service.py`: `build_particle_instances`, `_spawn_position`, `_spawn_cache_key`,
`evaluate_particle_motion`, `particle_clip_frame_index`, raster dispatch.
`particle_sub_emitter_service.py`: `template_settings`, `iter_invocations`, `contribution_bounds`,
`render_layer_particles`, `template_dependencies`.
`particle_trail_render_service.py`: `iter_trail_samples`, group collection/current transforms.
`lifetime_modulation_service.py`: point evaluator/legacy exact rounding adapters.
`particle_properties_panel.py` + `lifetime_point_editor.py`: active controls/ID combo/point list.
`effect_resource_layer_render_service.py` + playback/preview/project_io/export: same pipeline.
`main_window.py`: settings commands/dependent regeneration/delete batch/Undo/reference repair.

Whole `app` case-insensitive searches and model→UI→render dispatch review covered:
particle collision, ground plane, scene-bounds contact, mask/sprite collision, surface hit,
bounce, kill-on-hit, collision event, contact normal/impact point; connected strip/path mesh,
joins/caps, UV/texture/continuous width/tangent; force stack/wind/acceleration noise/curl/vortex/
attractor/repulsor/flow; Graph/Bezier/tangents. **No corresponding particle execution system**.
Collision search positives concern Timeline key destination conflicts; debounce is not bounce.
Gizmo hit-testing and 2.5D projection/bounds clipping are UI/culling, not collision response.
Ribbon positives are explicit unsupported tooltips/docstrings, not mesh generation.
No collision/ribbon/force schema or active Inspector control. A negative text search alone is
not the proof: dataclass fields, pure motion and shared sprite raster were also inspected.

Canonical spawn fields include direction-derived XY velocity, speed, life, scale, rotation,
angular velocity, clip start/speed/delay and stable slot ID/Noise identity. Events reuse those
objects; only event frame/origin/ordering key changes. No per-invocation RNG.
Target nested events/cyclic repetitions/high-level transform/flags ignored; local child settings
still apply. No parent velocity/rotation/scale/color inheritance. Circle = circumference/arc,
not disk. Filled disk/annulus/mask/path and face-velocity orientation remain absent.

## 12 archetypes × 11 axes

S=Spawn/Emission; D=Direction/Distribution; M=Motion; L=Lifetime;
A=Appearance/Blend; T=Trail/path persistence; E=Event chaining; C=Collision/contact;
X=Transform/Parenting/2.5D; P=PNG/Determinism; U=Authoring UX.
가능=direct current API/control; 부분=variant/coverage limitation; 우회=manual timing/source;
고비용=many manual layers/bakes; 불가=no procedural execution path.
Contact column is capability availability even where basic effect does not need contact.
It is **not** counted as 12 practical blockers. E 부분 means Birth/Death only, not arbitrary graph.

| Effect | S | D | M | L | A | T | E | C | X | P | U |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Hit Spark | 가능 | 가능 | 가능 | 가능 | 가능 | 가능 | 부분 | 불가 | 가능 | 가능 | 부분 |
| Explosion | 가능 | 가능 | 가능 | 가능 | 가능 | 가능 | 부분 | 불가 | 가능 | 가능 | 부분 |
| Smoke | 가능 | 가능 | 부분 | 가능 | 가능 | 가능 | 부분 | 불가 | 가능 | 가능 | 부분 |
| Fire/Ember | 가능 | 가능 | 부분 | 가능 | 가능 | 가능 | 부분 | 불가 | 가능 | 가능 | 부분 |
| Magic Wisp/Comet | 가능 | 가능 | 부분 | 가능 | 가능 | 부분 | 부분 | 불가 | 가능 | 가능 | 부분 |
| Projectile | 가능 | 가능 | 가능 | 가능 | 가능 | 부분 | 부분 | 우회 | 가능 | 가능 | 부분 |
| Sword Slash | 가능 | 가능 | 가능 | 가능 | 가능 | 부분 | 부분 | 불가 | 가능 | 가능 | 부분 |
| Area Dust | 가능 | 가능 | 부분 | 가능 | 가능 | 가능 | 부분 | 불가 | 가능 | 가능 | 부분 |
| Ring Burst | 가능 | 가능 | 가능 | 가능 | 가능 | 가능 | 부분 | 불가 | 가능 | 가능 | 부분 |
| Rain/Snow | 가능 | 가능 | 부분 | 가능 | 가능 | 가능 | 부분 | 우회 | 가능 | 가능 | 부분 |
| Firework | 가능 | 가능 | 가능 | 가능 | 가능 | 가능 | 부분 | 불가 | 가능 | 가능 | 부분 |
| Debris→Smoke | 가능 | 가능 | 가능 | 가능 | 가능 | 가능 | 부분 | 우회 | 가능 | 가능 | 부분 |

M 부분 above concerns specified flow-field variants, not failure to render basic G/D/N.
C 우회=only known fixed lifetime choreography, never contact support. U 부분 reflects compact
list/missing reusable preset workflow/approval boundary, not a newly reproduced UI bug.
X/P use broad existing regression tests; new dot fixtures do not newly cover every transform.

## Practical state / workarounds

Practical = reusable small-number-of-layer basic effect with suitable artwork, not a finished
asset preset. Partial = basic is practical, but requested important procedural/contact variant
blocked. Impractical = only expensive baked/manual recreation; Blocked = required native behavior
absent. Ratings are task-scoped authoring judgments, not automated aesthetic classifications.

| Effect | Practical state | Primary blocker | Secondary blocker | Current workaround |
|---|---|---|---|---|
| Hit Spark | Practical basic | none basic; ground-contact spark blocked | no face velocity | radial burst + peak/bell/RGB/Additive/G/D/Trail; angular sprite authoring |
| Explosion | Practical | repeated smoke is quality gap, not structural blocker | no moving fragment inheritance | random parent life + Death smoke target; two layers, no Start arithmetic |
| Smoke | Practical basic | spatial curl-driven circulation blocked | point-list UX | Box/Cyclic/upward G/D/N + growth/bell; no force-field substitute |
| Fire/Ember | Practical basic | spatial vortex plume blocked | exact cycle repetition | Cyclic/G/D/N/color/alpha, optional stamp Trail; longer authored period reduces obvious looping |
| Magic Wisp/Comet | Partial | continuous-width curved Ribbon absent | true attracted flow absent | Orbit/Helix/noise + additive colored stamps practical; long baked source expensive for arbitrary path |
| Projectile | Partial | changed trajectory/ground Contact absent | continuous long tail / inheritance | fixed-route Death at L-1 practical; each route needs lifetime recalculation |
| Sword Slash | Partial | procedural continuous arc strip absent | tangent alignment absent | imported/animated slash silhouette + stamp afterimages practical; arbitrary path mesh requires bake |
| Area Dust | Practical basic | spatial attractor/repulsor behavior blocked | point-list UX | filled Box/Cyclic/G/D/N/bell; local drift is not response to field |
| Ring Burst | Practical | none for circumference ring | filled disk/annulus thickness absent | Circle circumference/arc + radial/scale/alpha/Additive; asset thickness if desired |
| Rain/Snow | Partial | reusable landing splash Contact absent | spatial wind/flow absent | cyclic Line/Box/G/N falling practical; known equal heights/speeds can use Death, otherwise retune |
| Firework | Practical | no structural blocker for rising→burst | repeated canonical fan; inherited velocity absent | rising parent + Death radial target; source-art tailoring, few layers |
| Debris→Smoke | Practical timed | landing-triggered dust variant blocked | repeated smoke; velocity inheritance | random L parents→Death smoke practical; not ground contact |

Summary: 8 Practical +4 Partial; **12 basic forms feasible**, not 12 complete production art
approvals. Advanced required variants below are currently Blocked/Impractical; no full basic
archetype is declared wholly Blocked. Repeated quality patterns do not become practical
blockers merely because variation would look better.

## Named advanced goals and candidate impact

These exact goals are encoded in `GOALS` in the diagnostic, linked to the matrix rows.
They are capability requirements, not simulated future implementations. Unlock counts mean
potential after a suitably scoped implementation; **nothing is unlocked in this audit**.

| Goal ID | Matrix archetype | Requirement presently blocked | Candidate |
|---|---|---|---|
| contact_projectile | Projectile | variable-height flat-ground impact | Collision |
| contact_rain | Rain/Snow | variable-height ground splash | Collision |
| contact_debris | Debris→Smoke | landing-triggered dust | Collision |
| contact_spark | Hit Spark | spark dies on ground contact | Collision |
| strip_comet | Magic Wisp/Comet | continuous curved tail with defined width | Ribbon |
| strip_projectile | Projectile | continuous long tail | Ribbon |
| strip_slash | Sword Slash | procedural continuous arc sweep | Ribbon |
| flow_smoke | Smoke | spatial curl-driven circulation | Force |
| flow_fire | Fire/Ember | spatial vortex-driven plume | Force |
| flow_dust | Area Dust | spatial attractor/repulsor field | Force |

Force is a family; a minimal wind vector alone would not unlock those3 spatial goals.
Collision4 deliberately require flat local ground, NOT arbitrary/moving terrain or bounce.
Those broader goals remain blocked even under the proposed minimal v26.

| Candidate | Newly practical basic archetypes | Named advanced goals | Major improvement rows | Current workaround / classes |
|---|---:|---:|---:|---|
| Per-event Variation | 0 | 0 | 3 quality | Explosion/Firework/Debris; several separate targets/seeds or longer pattern, loses automatic per-event variation |
| Collision / Contact | 0 | 4 | 0 separately | Projectile/Rain/Debris/Spark; fixed L for known ground, retune each spawn/velocity |
| Ribbon | 0 | 3 | 0 separately | Magic/Projectile/Slash; dense stamps or custom source bake; neither defines continuous strip geometry |
| Force/Turbulence | 0 | 3 | 5 polish | Smoke/Fire/Dust/Wisp/Snow basic motion already possible with G/D/N; true field requires bake/manual layers |
| Graph Editor | 0 | 0 | 12 UX opportunities | existing 2..8 point lists already represent common shapes; no speed/quality improvement measurement |
| Velocity/Rotation/Scale inheritance | 0 | 0 in declared set | 4 quality/workflow | Projectile/Explosion/Firework/Debris directions hand authored; cannot respond per parent sample |
| Filled disk / annulus / mask / path | 0 | 0 in declared set | 0 | circumference enough Ring; Box enough Dust; shape-specific advanced brief would change this count |

Counts generated directly from `GOALS` and `IMPROVEMENTS`, deduplicated archetypes per candidate.
Do not sum across candidates: Projectile appears in both contact and strip goals. Birth Puff/
Cyclic Death/optional Lightning are diagnostic-only, not extra scored archetypes. Quality-only
variation3/12 is reasoned from the three repeated event archetypes; no perceived-unacceptable
count is proven (0 confirmed). Graph12 means potential list-edit convenience, not observed
12 severe UX blockers or12 new effect classes. No subjective1..10 score used.

## Executed diagnostics

Tool: `tools/recheck_post_v25_capabilities.py --output <fresh-directory>`.
Authoritative final evidence: **`C:\Dev\pem_post_v25_recheck_20261002_complete`**.
Final tool exit0,10.464s. Earlier `_a`/`_b` were incomplete diagnostic development runs;
`_verified`/`_final` were earlier successful revisions. They are not substituted for final evidence.
Only synthetic files created under CDev; no user source/artwork/build output modified.

All five repetition cases have12 distinct origins and1 normalized child-only RGBA pattern.

12 representative projects×24 decoded PNG frames;9 Trail comparisons×24=**504 sequence PNGs**,
21 JSON projects. Three contact sheets +5 normalized-child images=8 additional PNG images.
All21 raw Current/Full/Generated, reverse seek, final Playback, Save/Reload **logical
rematerialization** and decoded PNG comparisons exact. Basic cyclic representative frames
0/3/11/100000 compared against t+P exact. Same-stage raw/final boundaries not conflated.
5 repetition comparisons render child-only normalized images plus parent composite sequences;
these are not five extra complete authoring archetypes. No future renderer mocked for comparison.

### Per-event repetition

Explosion secondary smoke, Debris smoke(random parent L), Firework radial bursts,
Birth Puff and Cyclic Death each use12 parent slots,6 child canonical slots, separated
Circle32 origins. Each12 has **1 unique origin-normalized, age2 child RGBA hash**; canonical
object identity and sampled dictionaries match. Direction/speed/life/rotation/scale/random clip
start/playback speed/Noise identity and age-based modulation repeat. Event absolute frame and
origin differ; translation/overlap and random parent death times can partially mask repetition.
Final animation has3 synthetic frames so random start is not a trivial single-frame range.

Contact sheets inspected: sparse repeated fans/puffs are visible; normalized cells match.
Firework fan is deliberately radial; smoke has gray growing target/Normal blend. Tiny art and
alpha overlap may hide details; exact canonical and RGBA evidence, not visual intuition alone,
establish repetition. Still structurally usable for timed Explosion/Firework/Debris and Birth
Puff. Classify Explosion/Firework/Debris **obviously repetitive but usable**, not automatically
natural or unacceptable. Birth Puff/Cyclic Death remain structurally usable diagnostics.
Strict non-repeating art brief would change priority but is not evidenced by these fixtures.

### Contact workaround

Read-only measurement uses existing `evaluate_particle_motion` integer positions, not contact
logic added to renderer. Projectiles y=20,v=2,ground40 have crossing age10; fixed L11 Death
at frame11 originates y40 (ageL-1). Changing only start to10 gives y30 (−10 error); only speed3
gives y50 (+10); only ground30 gives +10. Thus even fixed linear tuning is not reusable.
Rain g.1 tuned first sample age9 gives y42.05 (+2.05 overshoot); changed start/speed/ground
errors −7.95/+11.05/+12.05. Debris g.25 tuned age7 gives y40.125 (+.125); changes give
−9.875/+7.125/+10.125. Crossing frame and Death frame are also not the same event contract.

Known height/fixed trajectory can author a practical baked impact through chosen L. Random
height/velocity requires particle-specific timing not exposed as contact rule. Arbitrary terrain,
moving target, mask/normal/bounce/kill-on-hit are MISSING, not rescued by manual layer Start
calculations. Offline contact in local Effect space still cannot query arbitrary runtime terrain.

### Sprite Trail vs Ribbon

Same5×5 source, age12, D16, I1/2/4; neutral Scale and opacity, existing raster unchanged.
193 continuous-age centerline probes sample the actual output alpha; the probe is a diagnostic
of coverage, not new Ribbon rendering or general aesthetic metric.

| Path | I1 uncovered /193 | I2 | I4 | Stamps I1/I2/I4 |
|---|---:|---:|---:|---|
| Curved Projectile (Gravity) | 0 | 0 | 96 | 13/7/4 |
| Orbit | 27 | 108 | 151 | 13/7/4 |
| Slash (25°/frame angular sprite) | 28 | 105 | 149 | 13/7/4 |

Max neighbor-center distance Curved4.16/8.14/15.62px, Orbit/Slash6.53/12.94/25px.
Source-diagonal threshold in JSON is just a center-spacing measurement; raster footprints,
rounding and width differ, so it is not itself a proof of disconnected visible components.
Sheets inspected: I1 can overlap into a plausible short streak; I2/I4 show stamped/gapped
curves, changing angular quads on Slash. No tangent continuity, join/cap, width/UV continuity.
Pixel-art discrete afterimages can be desirable: not every gap is a bug, and Ribbon is not
universally better. Dense stamps help Curved Projectile here but cannot promise continuous
width along arbitrary speed/curvature. Long source bake works only for preauthored silhouettes.
Sword representative uses a synthetic13×3 strip + afterimages, not an animated true arc mesh.

### Force and Graph

Five G/D/N basic representatives are nonempty; age10 positions differ from same canonical
instance with G/D/N disabled. Sheets show bounded rising/sway/falling/area and curved dot
motion; classify basic motion achievable, not artist-approved natural smoke/fire/snow.
Current gravity is constant contribution, Drag modifies base clock only, Noise is positional.
Curl/vortex/attractor/wind vector acceleration/repulsor/flow-field/order of force integration
do not exist. Those are quality-only for basic Smoke/Fire/Dust/Wisp/Snow but structural for
the3 named spatial behavior goals. Orbit geometry is not an attracting force.

Existing evaluators validated exact knots and21 samples for bell0→1→0, fade-in/hold/fade-out,
5-point two-pulse and White→Yellow→Red RGB. These shapes need no free Graph. Hold comes
from two equal neighboring values, not a new Step easing. Free Bezier/tangents, separate XY
Scale, HSV, randomized curves/timeline point tracks remain genuine expression gaps outside
this selected goal set; Graph UI alone cannot add those model capabilities.

## Candidate implementation/risk comparison (assessment, not implementation)

Each table cell covers the stated scope, not a promised implemented feature.

| Concern | Variation | Contact | Ribbon | Force/Turbulence | Graph |
|---|---|---|---|---|---|
| Model | bounded event variation mode/seed policy | local ground+response+event target | ribbon width/history/sample mode | field params/order/integrator | none for existing-point view; tangents would change model |
| UI | mode/seed/repeat warning | plane/edit restrictions/target/status | width/samples/joins/texture | field controls/order/guides | draggable bounded graph synced to list |
| Renderer | event-key samples, Noise separation | first contact/effective death/invocation | sample path→connected mesh/raster | force composition/integration | existing evaluator if UI-only |
| Serialization | new event variation settings | new collision settings/contact reference | ribbon schema | force list/schema | none UI-only; Bezier schema new |
| Migration | OFF identity | OFF identity | OFF identity | OFF identity | retain points; never duplicate writable truth |
| Undo | settings command+dependent regeneration | one edit+target cleanup batch | settings snapshot | field reorder/add/edit transaction | one drag one command; list exact |
| Save/Reload | stable seed/key exact | exact contact rule/references | exact settings/asset refs | force order/step exact | existing points exact |
| Preview/Export | shared invocation samples | shared contact plan/raster | shared exact mesh raster | same integration contract | same point evaluator |
| Direct Seek | no persistent RNG/history | root/first-hit scan bounded independent of T | resample finite past ages | bounded solver from birth, not playback state | UI-only low; spline evaluator changes high |
| Determinism | stable fixed mixer, no Python hash() | tie/root/tolerance/event frame defined | ordering/joins/rounding defined | step size/order/floating behavior fixed | knot/easing/legacy rounding preserved |
| Performance | avoid rebuild per event×stamp | one contact plan per canonical slot | segment/pixel footprint cost | particle×child×trail×force steps dangerous | UI sampling bounded, no per-particle new graph |
| Cache dependency | template settings+event variation policy | plane+parent path+contact target/source | width/source/path/transform | fields/order/source/global tracks | points only; view state not render key |
| Reference integrity | stable layer/event key across rename/delete | stable target ID, never by name | optional texture source ref repair | optional field-object dependencies | selected point index/identity across refresh |
| Test surface | RNG isolation/period/Noise/slots/parity | crossing/nohit/tangency/gates/Trail/events/parity | joins/caps/UV/depth/Seek/blend/caps | integration/GDN/order/period/Seek/caps | crossing/no-op/Undo/list sync/legacy exact |

Inheritance option would add coefficients/modes, future parent derivatives/orientation sampling,
serializer migration/Undo/cache fields and parity tests. Position-only fixed templates are
not equivalent; transformed Parent Layer applies higher context, not per-particle inheritance.
Optional filled shapes change spawn RNG order/distribution, validation/UI/schema/cache/goldens;
not a required unlock for current ring/Box targets.

Variation special risk: full event key includes cycle; hashing cycle into random pattern would
break F(t+P)=F(t). Repeat-per-period policy must use stable layer+kind+canonical parent slot,
ignore cycle salt for periodic mode, or explicitly opt out. Same event must be identical after
seek/save. Isolate child Noise identity and spawn random draw order. Do not use Python hash,
wall clock, history RNG, or silently changing seeds. Existing slot reuse needs bounded cache.

Contact special risk: analytic monotonic Linear+G roots can be O(1); nonlinear Drag may need
bracketed solve. Orbit/Helix/noise/nonperiodic tracks break monotonic assumptions; arbitrary
sprite/mask terrain needs continuous/cell/step tests and normals. Bounce means changed future
motion and many contacts, not same minimum kill event. The minimal proposal below restricts
those combinations explicitly. Direct seek cannot scan from frame0 to requestedT.

Ribbon special risk: history-free local path sample count bounded; meshes need joins/caps,
width and texture sampling, degenerate tangent rules and2.5D depth/blend group contract.
One mesh per head and repeated current world snapshot vs historical world trail must be explicit.
Segment multiplication/canvas footprint may cost more than denser sprite stamps.

Force special risk: constant wind can be closed-form but does not implement curl/flow.
General fields need bounded integrator, fixed step/time/order and deterministic checkpoint
or birth reconstruction; trail samples must reuse solution rather than reintegrate per stamp.
Existing Gravity/Drag/Noise meanings cannot silently become physical force laws.
Local autonomous periodic copies can repeat; absolute-time/world fields may break F(t+P).

Graph special risk: editor-only view of existing points needs no format bump/evaluator rewrite.
Bezier handles would require new schema/evaluation/legacy rounding contract; point list and
graph must never be independent truths. Graph convenience and new per-axis/HSV capabilities
are distinct candidates; no common expression is newly unlocked by UI-only graph here.

## Throughput reality / priority

Reuse measured v25 final report `C:\Dev\pem_v25_sub_20261002_final\report.json`:
96×96 /5×5 sprite, three warm-render median, measured on same local environment on2026-10-02.
Not freshly measured in this audit and not native GUI frame-rate evidence.
Valid500-parent Birth275.031ms /Death222.059ms; FullStack100125.501ms.
500 both/cyclic/full conservative4500 visual rejected,1000 single-event5000 rejected;
4096 visual/8192 historical stamps are safety caps, not real-time guarantees.
100 full-stack T10000098.312ms includes actual tail-only work; light cyclic.551ms phase was
empty and is not a comparable workload. Diagnostic runtime10.464s is not warm rendering latency.

Contact ranks1 because four reusable contact goals have no cheap authored rule now; even simple
ground/velocity edits break fixed Death. Shared stable-target invocation, analytic copies and
canonical path foundation allow a small flat-ground subset without integrator-per-stamp cost.
Ribbon ranks2: three genuinely structural strip goals, but mesh/blend/depth/width/UV surface
larger and discrete afterimages already suit many pixel effects. Force ranks3: three spatial
behavior goals, but curl/field integrator risk/cost greater than existing basic G/D/N polish.
Variation0 unlock/3 quality improvements remains valuable but not1st solely because simpler.
Graph0 unlock/12 potential UX improvements follows expression foundations.
If primary product brief becomes continuous slash trails, non-repeating crowds or spatial
fluid motion, redo this goal matrix; rankings are not timeless. No user-frequency study claimed.

## v0.0.26 minimal proposal — design only

Name proposal: **v0.0.26 Deterministic Local Flat-ground Contact**; expected FORMAT23 if
persistent fields approved. Current code remains v25/FORMAT22.

Persistent Particle contact block: enabledFalse, local_ground_y finite, response `kill`,
contact_sub_emitter.enabledFalse/target_layer_idNone. One local horizontal plane, downward
crossing, maximum one contact per parent copy. Reuse targetID validator/delete Undo/no recursion.
No renderer implementation, new dataclass or UI control was added in this audit.

Supported first scope: static Linear trajectories + constant Gravity, DragOFF/NoiseOFF,
nonanimated emitter Motion. Nonlinear/animated settings must be explicitly rejected or contact
disabled with clear validation; never silently ignored or alter their existing motion.
Plane is **Particle/System local space before current Layer/Parent/System projection/Surface**,
not canvas/world terrain. Parent transforms move path and plane together. v26 has no per-frame
plane track, sprite extent, arbitrary mask, moving terrain, bounce, repeated contacts, force,
recursive events, inheritance, per-event variation or Ribbon.

Proposed math contract: evaluate continuous center path y(a)=y0+vy*a+.5*g*a² over visible
ages0..L-1. Smallest downward crossing with y(0)<ground and derivative>=0; birth already
below/on plane treated as contact at age0 with specified normal; nohit/tangent/upward-only
cases must be specified in tests. Root precision/robust quadratic solution/epsilon policy fixed.
Contact event age c=ceil(root) clamped only by explicit domain validation, not frame history.
Proposed contact origin is analytic interpolated root position projected onto plane, normal
local(0,-1,0), event at B+c. This is **not** v25 Death originL-1. The discrete head disappears
at c, earlier ages keep original path; no post-hit motion or bounce.

Two ownership rules must be approved before implementation:
contact replaces lifetime Death when hit occurs by suppressing that copy's scheduled Death;
only Contact target fires on hit (Birth remains unaffected). No hit preserves v25 Death B+L
originL-1 exactly. Kill's effective head lifetime=c, or special age0 zero-head case. Existing
normalized modulation still uses original L at every precontact age; no curve acceleration.
Trail resamples only pre-hit ages, never extrapolates beyond hit; continues old samples after
kill with same delta/fade. L'=0 needs explicit Trail/no-head handling, not invalid ParticleInstance.
No recursive contact on invoked children in first scope; enabled contact on a target is excluded
from invocation template like nested events, with truthful tooltip. Target's own normal timeline
may contact. This conservative limitation leaves chained child collisions for later.

Canonical event identity: parent stableID +kind `contact` +canonical parentID +copy birth/cycle;
contact age/origin cached from static canonical path/plane, no RNG/history/fired set.
Cyclic copies reuse exact same relative root/age so F(t+P) remains; enumerate only relevant
contact invocations using child horizon and shifted contact offset, including prewarm negative
cycles. Direct largeT uses plan/copy bounds, not 0..T simulation. Parent head bounds reduce
or remain conservative; do not expand existing limits to claim faster output.

UI: localized compact Contact group, Enabled/Local Ground Y/Kill response/Contact Target,
unsupported-motion validation, copy/stamp costs; optional local plane guide editor-only.
One accepted setting action Undo1; invalid/no-op/refresh0, A→B→A/KO-EN/scrub integrity.
Same target choice prompt, self/nonparticle/missing filtering, stableID storage/duplicate rules.
Delete cleanup/Generated regeneration must share existing batch so Undo restores target+pixels.
Save/Reload FORMAT23 exact;<=22 missing block defaultOFF/no rewrite, disabled golden v25 exact.

Cache: include ground/rule/support mode/parent path settings/contact target/source revisions;
canonical plan cached outside per-event/per-child/per-trail raster, settings edit invalidates
base/preview/generated/playback/dependents. Spawn RNG cache unchanged. Preview snapshot remains
read-only project context. Raw/current/full/generated and final playback/PNG share contact plan.
No new surface-dependent world collision key. Rename must not alter ID plan; delete/load repair
must invalidate cached invocations and regenerate surviving parent output.

Safety: <=one contact per parent copy, combined visual4096/trail8192 and child horizon bounds,
no silent drops. Bound natural Death vs Contact as alternative events, not both firing on hit;
Birth may overlap. Reject malformed/nonfinite plane/settings and unsupported combinations.
No unbounded event graph, lifetime scan or force-step multiplier.

Benchmarks proposal:100/500/1000 canonical counts OFF/nohit/allhit/mixed/Cyclic/subtarget/Trail,
same dimensions/source/samples. Cold plan creation vs warm plan lookup/render, actual copies/
events/stamps and conservative bounds separately; frame100000 direct; reject invalid budgets.
Compare OFF v25 frozen path RGBA and latency; nohit setup should not multiply child/stamp cost.
No promise that safety-accepted500-parent effect becomes real-time. Geometry+export memory also
needs p95 native follow-up. Avoid render-many historical solutions per Trail stamp.

Test plan: continuous root/exact integer crossing/ceil/tangency/birth below/zero velocity/G0/
negativeG/nohit/random birth/parent life truncation; Death unaffected nohit and suppressed hit;
Birth+Contact mixed, positive/negative cyclic copies, period gates and tie sort; zero-head case;
tail before/after hit; child templates ignoring contact; curves/source ages/Normal/Additive;
direct/reverse/random/largeSeek/period; references/rename/duplicate/deleteUndo/load repair;
schema oldOFF/new/invalid/no rewrite; unsupported Drag/Noise/Orbit/Helix/animated rejection;
Parent/KeepWorld/System/Surface/2.5D/revolutions/overscan/clip; all preview/export/reload parity.

Manual QA proposal: actual Windows controls/layout/plane space explanation/A-B/Undo/Save;
visually compare Hit/Rain/Projectile/Debris variable start/speed and fixed local plane; verify
contact point/particle death/old trails/cyclic prewarm, target deletion, responsive KO/EN and
slow-workload status. **Not performed now.** Future implementation requires user direction.

## GUI Validation Recommended (not executed)

Open the synthetic JSON only in a user-controlled test session; check12 basic flows with real
artwork, point list workflow, target choice/rename/delete/Undo, output duration for child tails,
current Parent/System/Surface meaning, narrow inspector clipping, cyclic loop perception.
Judge repeated Firework/smoke acceptability and TrailI1/2/4 pixel aesthetic manually.
Measure playback/gizmo latency on intended particle/canvas sizes; exact PNG parity is not UX
approval. No mouse/keyboard/native GUI task was performed in this audit.

## Verification and final Git

Final full pytest: **1732 passed /100.96s**, failures0/errors0;
`--basetemp=C:\Dev\pem_post_v25_final --tb=short`.
Final compileall app/tests/tools exit0; --version0.0.25, FORMAT22;
direct --check/batch --check exit0; diff check0; protected hash unchanged.
AppData log write PermissionError/logging_unavailable observed in baseline direct/batch checks,
both exit0. Logger/permissions were not changed; normal installed logging not confirmed.
No changes under app/tests after checkpoint. Final audit artifacts expected: this report,
capability overlay and diagnostic script only. Final HEAD remains01797ec…; stage0.

## Requested completion report 1..130

| # | Requested item | Result / evidence |
|---:|---|---|
| 1 | 실제 시작 HEAD | 2470af26df658e72440ac4712f90973ce75008fc |
| 2 | 시작 Version | Pixel Effect Maker v0.0.25 |
| 3 | 시작 FORMAT_VERSION | 22 |
| 4 | 시작 pytest | 1732 passed /116.78s; focused102 /5.12s |
| 5 | Sub-emitter commit hash | 01797ec946ec39c90de34c60253b7802c386c054 |
| 6 | explicit staged files | 58 files, exact whitelist above; git add -A 미사용 |
| 7 | excluded files | 보호 PNG/user projects/CDev evidence/build/dist/ZIP/cache/log/temp/backup |
| 8 | checkpoint 후 Git | main ahead44, staged0, 보호 PNG만 untracked |
| 9 | Multi-point Lifetime | narrow Scale/Opacity/RGB COMPLETE; overall Curve PARTIAL |
| 10 | Cyclic Emission | narrow COMPLETE; canonical repeated prewarm, rate API 없음 |
| 11 | Sprite Trail | narrow COMPLETE; sample age local stamps, no Ribbon/world history |
| 12 | Birth Sub-emitter | automated narrow path verified; PARTIAL final native approval |
| 13 | Death Sub-emitter | B+L, originL-1; automated verified, native approval 유보 |
| 14 | remaining Event gaps | contact/threshold/multitarget/recursion/variation/inheritance 없음 |
| 15 | Hit Spark | Practical; basic blocker없음; ground spark/orientation secondary; radial+peak/bell/Trail |
| 16 | Explosion | Practical; repetition quality gap; inheritance secondary; Death smoke target |
| 17 | Smoke | Practical basic; spatial flow blocked; list UX secondary; Box/Cyclic/GDN growth/bell |
| 18 | Fire/Ember | Practical basic; vortex goal blocked; repeated period secondary; GDN/color/Cyclic |
| 19 | Magic Wisp/Comet | Partial; continuous strip blocked; force flow secondary; colored local stamps |
| 20 | Projectile | Partial; variable-ground impact blocked; continuous tail/inheritance secondary; tuned fixed L |
| 21 | Sword Slash | Partial; procedural strip blocked; tangent secondary; imported silhouette/afterimages |
| 22 | Area Dust | Practical basic; spatial field blocked; list UX secondary; Box/Cyclic/GDN |
| 23 | Ring Burst | Practical circumference; no primary basic blocker; filled thickness secondary; radial ring |
| 24 | Rain/Snow | Partial; reusable splash blocked; spatial wind secondary; Cyclic fall + tuned Death only |
| 25 | Firework | Practical; repetition quality primary residual; inheritance secondary; rise→Death radial |
| 26 | Debris→Smoke | Practical timed; landing variant blocked; repetition/inheritance secondary; randomL→Death |
| 27 | current repeated canonical pattern | same direction/velocity/life/scale/rotation/clip start/speed/Noise ID |
| 28 | affected archetypes | Explosion/Firework/Debris; Birth Puff/Cyclic Death supplementary only |
| 29 | practical blocker count | 0 confirmed in selected basic/advanced goals; no unacceptable aesthetic proof |
| 30 | quality-only count | 3 of12 rows, reasoned quality opportunity not automatic beauty score |
| 31 | workaround | separate targets/seeds/longer period/manual duplication; not actual per-event randomness |
| 32 | current collision support | MISSING; no particle model/control/dispatch, culling/gizmo/key conflict excluded |
| 33 | fixed-lifetime workaround | practical known fixed ground/trajectory; y20 v2 ground40 L11 example |
| 34 | arbitrary terrain limitation | no mask/moving scene/runtime terrain/normal/bounce; fixed PNG not runtime response |
| 35 | affected archetypes | Projectile/Rain/Debris/Hit Spark contact variants |
| 36 | practical blocker count | 4 named flat-contact variants; not four wholly impossible basic effects |
| 37 | current Sprite Trail scope | positive delta age samples, post-death, local history/current world snapshot |
| 38 | missing Ribbon scope | connected mesh/joins/caps/width/UV/tangent/depth contract |
| 39 | affected archetypes | Magic Comet/Projectile/Sword Slash continuous strip variants |
| 40 | practical blocker count | 3 named strip goals; basic afterimages still practical |
| 41 | Sprite Trail workaround quality | I1 dense can streak; curved Orbit gaps even I1; stamps not width-continuous geometry |
| 42 | current G/D/N | analytic age² G/base clock D/stable positional XY N; not force stack |
| 43 | missing force types | wind acceleration/curl/vortex/attractor/repulsor/flow/ordered force integration |
| 44 | affected archetypes | Smoke/Fire/Dust structural field variants; Wisp/Snow additional polish |
| 45 | practical blocker count | 3 named spatial behavior goals; basic GDN not blocked |
| 46 | quality-only count | 5 basic-motion improvement rows, not naturally looking automatic verdict |
| 47 | current Multi-point capability | 2..8 points, uniform Scale/RGB/alpha, per-segment four easings |
| 48 | missing graph capability | free graph/Bezier/tangents/peraxis/HSV/random/timeline curve points |
| 49 | capability blocker count | 0 for declared bell/hold/RGB/pulse/basic goals; excluded expressions still absent |
| 50 | UX-only blocker count | 12 potential list-edit convenience rows; 0 measured severe UX blockers |
| 51 | velocity inheritance | MISSING; position translation only; directional fragments need authored target |
| 52 | rotation inheritance | MISSING; scale also absent; higher Layer projection not per-parent particle inheritance |
| 53 | spawn shape residual gaps | filled disk/annulus/mask/path/random Z absent; Circle circumference/arc |
| 54 | any newly discovered blocker | no new reproduced production bug; historical v22 report request-text contamination noted/preserved |
| 55 | Per-event Variation impact | basic unlock0/advanced0/quality3 |
| 56 | Collision impact | basic unlock0/advanced4, known local flat-contact only |
| 57 | Ribbon impact | basic unlock0/advanced3 continuous-strip goals |
| 58 | Force impact | basic unlock0/advanced3 spatial goals/polish5; minimal wind alone not3 |
| 59 | Graph impact | basic unlock0/advanced0, potential UX12 |
| 60 | optional candidate impact | inheritance improvement4; spawn current unlock0; no extra counted goals |
| 61 | newly practical goals per candidate | Variation0/Contact4/Ribbon3/Force3/Graph0, exact named-goal matrix |
| 62 | major improvement count | quality/UX sets:3/0/0/5/12; inheritance4; no subjective score |
| 63 | workaround cost summary | fixed L retuning; strip source bake; field manual layers; seeds separate targets; graph list workable |
| 64 | per-event variation scope | stable event mixer/period policy/Noise partition; avoid per-event spawn rebuilding |
| 65 | collision scope | analytic flat local plane kill/contact vs broad terrain/bounce separate |
| 66 | ribbon scope | bounded past-age path samples→mesh, joins/caps/width/UV/2.5D |
| 67 | force scope | constant closed form distinct from bounded ordered curl/flow integrator |
| 68 | graph scope | current points UI-only possible; Bezier schema/evaluator distinct |
| 69 | seek determinism risk | no elapsed history/RNG; contact roots, ribbon sample/tangent, force fixed integration |
| 70 | cyclic periodicity risk | cycle-salted variation/world fields break loop; repeated static local contact preserves |
| 71 | performance risk | existing500 event275/222ms; avoid particle×child×trail×steps; caps not realtime |
| 72 | schema risk | current22 unchanged; variation/contact/ribbon/force persistent fields need migration; graph UI-only none |
| 73 | UI complexity | target prompt/unsupported motion/plane; Ribbon width/sample; Force order; graph/list single truth |
| 74 | renderer complexity | contact first event/kill; ribbon mesh raster; forces full solver; variation identities |
| 75 | cache/reference complexity | target/source/plane/path dependencies; delete Undo+Generated; immutable canonical RNG untouched |
| 76 | 1순위 | Deterministic Local Flat-ground Contact Foundation |
| 77 | 1순위 근거 | 4 structural reusable goals, repeated fixedL failure, v25 invocations/cyclic foundation reuse |
| 78 | 실제 새로 practical해지는 Effect | future scoped flat-ground Projectile impact/Rain splash/Debris landing/Spark kill; audit unlock0 |
| 79 | current workaround가 부족한 이유 | position errors when height/speed/ground change, crossing not lifetime Death |
| 80 | 2순위 | Continuous Ribbon foundation;3 named goals, bigger raster/depth/UV surface |
| 81 | 3순위 | Spatial Force/Turbulence;3 goals, bounded integration costly |
| 82 | 다음 버전 이름 | proposed v0.0.26 Deterministic Local Flat-ground Contact, current v25 unchanged |
| 83 | 최소 기능 범위 | one static local horizontal plane, supported Linear+G, first downward contact, kill+one target |
| 84 | 제외 범위 | Drag/Noise/Orbit/Helix/animated path active contact, masks/moving terrain/bounce/recursion/variation/ribbon |
| 85 | persistent model | proposal enabled/ground_y/kill/contact target; expected FORMAT23, no fields implemented |
| 86 | deterministic identity | stable parentID/contact/canonical slot/copy birth/cycle; no Random/history/hash() |
| 87 | Direct Seek contract | per-canonical analytic contact plan + bounded relevant cycles, not frames0..T |
| 88 | Cyclic interaction | same relative contact age/origin repeat; negative prewarm; F(t+P) static-local |
| 89 | Sub-emitter interaction | Contact target on hit, suppress scheduled Death there; nohit legacyDeath; Birth unchanged; approval needed |
| 90 | Trail interaction | only pre-hit sample ages; post-kill tail persists; age0 zero-head explicit; originalL modulation |
| 91 | UI | compact KO/EN Contact group, unsupported-motion validation, stable target prompt, optional local guide |
| 92 | migration | proposed FORMAT23; <=22 missing block OFF identity/no rewrite, oldOFF exact goldens |
| 93 | Undo | accepted1/noop0; settings/target-delete snapshot+dependent regenerated pixels exact |
| 94 | cache | path+plane+target/source revision plan once, render/playback/preview/Generated invalidate |
| 95 | safety | <=one contact percopy, shared4096/8192 caps, no silent drop/unbounded event graph |
| 96 | performance | benchmark100/500/1000 OFF/nohit/mixed/allhit/Cyclic/Trail; cold plan vs warm; largeSeek; no FPS guarantee |
| 97 | test plan | root/tie/gate/nohit/age0/randomL/Trail/events/refs/schema/UI/Undo/Seek/period/parity/transforms |
| 98 | manual QA | proposed controls/space/ground changes/targets/Undo/native latency checks; not executed |
| 99 | diagnostic tool | tools/recheck_post_v25_capabilities.py, production render API only |
| 100 | representative fixture count | 12 archetypes;9 extra Trail comparison projects,5 repetition scenarios |
| 101 | PNG/contact sheet 여부 | 504 sequence PNGs,21 JSON,3 contact sheets+5 normalized PNGs under CDev final |
| 102 | per-event repetition evidence | 5 cases×12 slots;1 unique normalized-age2 child RGBA each +canonical identity/fields |
| 103 | collision workaround evidence | 12 integer-position cases; linear tuned0error, changed ±10; gravity overshoot/retune errors |
| 104 | ribbon evidence | 9 I1/2/4 cases;193 centerline probes each; Orbit uncovered27/108/151; stamps only |
| 105 | force evidence | 5 nonempty GDN fixtures +age10 ON/OFF positional differences; no new force renderer |
| 106 | graph capability evidence | exact bell/hold/pulse knots+21 samples and White/Yellow/Red RGB; no Graph UI |
| 107 | full pytest | final1732 passed /100.96s, failures0/errors0 |
| 108 | compileall | app/tests/tools exit0 |
| 109 | --version | Pixel Effect Maker v0.0.25 |
| 110 | FORMAT_VERSION | 22 unchanged |
| 111 | --check | exit0; sandbox AppData log PermissionError/logging_unavailable |
| 112 | run_app.bat | --check exit0, same warning; documented test interpreter env |
| 113 | git diff --check | exit0; LF→CRLF notice only, no whitespace errors |
| 114 | 최종 HEAD | 01797ec946ec39c90de34c60253b7802c386c054 |
| 115 | staged | 0; audit3 files unstaged/uncommitted, PNG untracked unchanged |
| 116 | audit commit | 0; only v25 checkpoint committed |
| 117 | v0.0.26 implementation | 0; production app/tests/version/format diff0 from checkpoint |
| 118 | tag/push/build | all0; PyInstaller/ZIP/release0 |
| 119 | Windows native GUI manual 여부 | 수행하지 않음 |
| 120 | 현재 practical한 Effect 유형 | 8 overall basic rows; all12 narrow basic forms feasible with appropriate source art |
| 121 | 현재 partial한 Effect 유형 | Magic Comet/Projectile/Sword Slash/RainSnow, variant limits not failed basic render |
| 122 | 현재 실제로 blocked한 Effect 유형 |10 named advanced goals; arbitrary/moving terrain/bounce also absent outside counted set |
| 123 | Sub-emitter 전후 가장 큰 변화 | random/delayed perparticle Birth/Death automatically drives child at actual event, no Start arithmetic |
| 124 | 가장 반복적으로 남은 blocker | reusable contact timing across4 named variants; strip3 and field3 next |
| 125 | 기존 per-event variation 추천이 유지되는지 | 아니오; structural unlock0/quality3, demoted after recheck |
| 126 | Collision이 더 중요한지 | selected reusable flat-contact set yes; not broad runtime collision engine |
| 127 | Ribbon이 더 중요한지 | variation보다 structural priority 높음, Contact 다음2nd |
| 128 | Force가 더 중요한지 | structural field goals yes, scope/Seek/perf risk로3rd; basic GDN already available |
| 129 | Graph가 더 중요한지 | current shapes require no Graph; UX work valuable but not top expression unlock |
| 130 | 최종 v0.0.26 추천 | design-only bounded local flat-ground Contact/Kill + stable-target Contact event |
