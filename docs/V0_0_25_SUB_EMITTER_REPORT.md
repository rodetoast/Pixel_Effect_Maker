# Pixel Effect Maker v0.0.25 — Bounded Birth/Death Sub-emitter

## 결과와 승인 경계

2026-10-02 / Windows11 / Python3.12.14, application **0.0.25**, **FORMAT_VERSION22**.
History-free deterministic Birth/Death child template invocation을 구현했다.
Focused **102 passed /5.28s**; final full **1732 passed /110.58s**, failures0/errors0.
Model/Inspector/Undo/Save/Preview/Render/Generated/Playback/PNG 자동 경로 검증이다.
**Windows native GUI manual: 수행하지 않음**. 사용자 native GUI 승인 전이므로 좁은
Birth/Death 기능의 최종 COMPLETE 승인은 보류한다. 전체 Event System은 PARTIAL.

v24만 local checkpoint: **2470af26df658e72440ac4712f90973ce75008fc**,
`Add deterministic particle trails`. v25는 **unstaged / uncommitted**.
최종 HEAD도2470af2, main ahead43, staged0/v25 commit0.
Tag0/Push0/Build0/PyInstaller0/ZIP0/Release0. 보호 `테스트소스.png` 수정/삭제/rename/stage 없음.

## 실제 baseline / checkpoint

시작 HEAD9cf4a413b38111e6934e367fc758845707b6fa9c, app0.0.24/format21.
49 tracked edits +6 new approved v24 files, separate protected untracked PNG, staged0.
Full baseline **1630 passed /106.67s** (new v25-baseline temp folder).
Compileall/version/direct --check/run_app.bat --check/diff check 모두 exit0.
Baseline Trail suite에 frozen v23 OFF, direct/random/reverse/large seek, post-death tails,
Cyclic head/tail-only prewarm, periodicity, parity와 safety 경계 검증이 포함된다.

검증 후 explicit55-file whitelist만 stage/commit:1298 insertions/65 deletions.
Checkpoint 직후 staged0, main ahead43, protected PNG만 untracked. add -A 미사용.
CDev evidence, user projects/assets, caches/logs/temp/build/dist/ZIP/backup은 제외했다.
Protected SHA256 시작/끝:
`8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`.

### Explicit v24 whitelist (55)

```text
CHANGELOG.md
README.md
app/models/particle_emitter.py
app/models/project.py
app/services/effect_playback_service.py
app/services/particle_cyclic_emission_service.py
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
tests/test_lifetime_multi_point_serialization.py
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
app/services/particle_trail_render_service.py
docs/V0_0_24_PARTICLE_TRAIL_REPORT.md
tests/test_particle_trail.py
tests/test_particle_trail_serialization.py
tests/test_particle_trail_ui.py
tools/benchmark_particle_trail.py
```

위는 v24 checkpoint 목록이며 v25 stage 목록이 아니다.

## 구현 전 ownership 감사 (18 questions)

1. Stable persistent identity: `EffectResourceLayer.id`, default `uuid4().hex`, JSON id.
2. ID lookup: `Project.sync_effect_flat_order` 및 renderer `_base_key` inline maps.
   새 service는 요청별 by_id map을 준비하며 child/sample마다 전체 Layer search를 하지 않는다.
3. Source: `ParticleEmitterSettings.resource_type/clip_asset_id`와 resource_id adapter;
   `particle_render_service._resolve_particle_clip`에서 SourceAsset/Clip/Composition을 resolve.
4. Read-only reuse boundary: 기존 spawn tuple + pure motion/source/raster. 새 layer-aware
   `render_layer_particles`가 target을 resolve하고 shared group collector에 streams를 전달.
5. v24 `render_particle_frame`은 하나의 emitter/source clip을 가정한다. 새 streams는
   각 settings/clip/instances를 따로 가지고 한 depth collection에 합친다. OFF 경로 유지.
6. `effect_resource_layer_render_service`는 Project 전체 context에 접근한다.
7. Visibility/Solo: `Project.compose_frame`와 effect_effective_visible/preview_soloed 단계.
   Target template lookup은 이를 적용하지 않는다. Lock은 MainWindow edit 보호 의미.
8. Layer/Parent: current base-frame renderer에서 resolve_world_affines/local_only_transform
   후 Layer projection; Surface는 transform_rgba_frame; final compose는 기존 Parent pipeline.
9. `evaluate_particle_motion`의 ParticleMotionPosition 반환 직후, billboard/Layer projection
   직전이 event-origin XYZ 경계다. 이 origin을 child local motion에 translation으로 더한다.
10. `_spawn_position` start_x/start_y는 Particle/System-local emitter-domain 좌표다.
11. `_SPAWN_STATE_CACHE`: render-excluded settings repr + clip length; Layer ID key가 아니다.
    Sub-emitter fields를 제외하고 template one_shot adapter는 동일 canonical tuple을 재사용.
12. Trail lifetime: `ParticleTrailSettings.sample_count/delta_max`,
    `iter_particle_cycle_copies.visibility_extension_frames`, `iter_trail_samples`.
13. Unified delete는 `_effect_batch_snapshot/_push_effect_batch`의 resource/layer/pixel snapshot.
    기존 surviving transform-parent dependency는 기존 convention대로 보호한다. Sub references는
    같은 batch에서 safe disable/clear 및 surviving generated regeneration을 추가했다.
14. Rename은 기존 EditorValueCommand, stable ID 유지. Delete Undo는 whole batch snapshot 복원.
15. `duplicate_selected_effect_layers/duplicate_effect_group`는 새 uuid4().hex. Parent 복제는
    원래 target ID를 유지하고 target 복제도 기존 parents를 자동 retarget하지 않는다.
16. `Project.repair_effect_hierarchy/repair_parent_links` missing-link repair convention을
    `repair_sub_emitter_references`로 확장했다. Invalid target safe clear/disable, name retarget 없음.
17. 기존 `render_transformed_source` Normal/Additive raster를 stamp별 target blend로 재사용.
18. v24 Trail live-head/latest-projectable-tail depth와 oldest→newest→head group 규칙을
    여러 settings/clip streams로 일반화했다. OFF pixel oracle 및 existing Trail tests로 검증.

## Model / target contract / UI

Nested `ParticleSubEmitterEventSettings(enabled=False,target_layer_id=None)`,
`birth_sub_emitter`와 `death_sub_emitter` 독립, 같은 target 가능.
Enabled는 strict bool, ID는 None 또는 nonempty str. Enabled+None persistent state는 거부.
Self/non-particle/missing ID는 context validator 거부. Load/delete에서는 missing/self/nonparticle
reference를 safe clear/disable; load 원본은 rewrite하지 않는다. Over-budget valid-ID loads는 거부.

Target은 source/Count/Burst/Over Time/Delay/Spawn Shape/Direction/Speed/Lifetime/playback/
rotation/angular velocity/G/D/N/Scale/RGB/Opacity/Trail/Blend 및 emitter-domain Motion을 제공한다.
Target normal Start placement, Visibility/Solo/Lock, Group/Parent, Layer/Surface high-level
transform, cyclic repetition, own event recursion은 child invocation에서 사용하지 않는다.
Target normal timeline 자체는 기존대로 독립 렌더/편집하며 자동 hide/timing/parent/role 변경 없음.

Inspector Sub-emitter는 Trail 뒤/Over Lifetime 앞, KO/EN labels/tooltips, compact wrap-all
form이다. Particle target only, self 제외, hidden/solo/locked 포함, itemData stable IDs,
중복 name은 짧은 suffix로 구분. OFF target disabled +stored values preserved.
Default OFF/None에서 Enable은 **runtime choose-target prompt**: 저장값은 OFF/None, Undo/dirty/
revision0 유지하고 combo를 선택 가능하게 한다. 선택 완료가 한 accepted Undo action이다.
Refresh로 미완료 선택은 persistent state로 돌아간다. Pending selection 자체는 저장하지 않는다.
Stored target이 있는 enable/disable와 target 변경은 각각 accepted Undo1/Redo exact.
Invalid/no-op/refresh0. A ON→X/OFF→Y와 B OFF→Z/ON→W selection/KO/EN/scrub 보존.
Offscreen280/300px,150%font 검증은 native GUI manual이 아니다.

## Analytic timing / identities / no history

```text
Parent canonical birth B, lifetime L, cyclic period P
Birth event: E=B, origin_age=0
Death event: E=B+L, origin_age=L-1        (not invisible L)
child_relative_birth = child.birth_frame - target.start_frame
child_birth = E + child_relative_birth
child_age = T - child_birth
child_visual_lifetime = child.lifetime + target.trail.delta_max
H = max(child_relative_birth_i + child_visual_lifetime_i), empty slots =>0
Relevant invocation: 0 <= T-E < H
Cyclic E(k)=B+kP+e, e=0(Birth) /L(Death)
k_min = ceil((T-B-e-(H-1))/P)
k_max = floor((T-B-e)/P)
Invocation key=(parent_layer_id,kind,cycle,parent_particle_id,parent_copy_birth)
Child ordering key=(namespace1,event_rank,cycle,parentID,birth,parent_layer_id,childID)
Parent ordering key=(namespace0,cycle,parentID)
```

No fired flags, event lists, previous-frame position buffers, elapsed-history replay or recursion.
Canonical Parent/Target spawn slots are cached immutable tuples; no per-invocation Random or draws.
Target child Noise keeps target seed/childID/actual age. Pattern repeats intentionally across events.
Target cyclic adapter ignores cycle repetition and disables both child events. Depth is exactly1.
A child is a lightweight canonical wrapper, not a newly randomized ParticleInstance.
One Shot scans canonical parent slots; Cyclic computes relevant bounded k directly, even frame100000.

Event origin uses parent local motion age0/L-1, including existing Linear/Orbit/Helix/G/D/N.
Parent evaluated System motion uses current requested frame, not a past world transform.
Child historical motion and appearance use actual child sample_age; existing emitter-domain
Motion snapshot uses current target-frame evaluation, consistent with existing local-history
renderer. Animated emitter Motion can therefore break periodicity unless itself periodic.
All samples pass through current parent Layer/Parent affine/Surface context. Target high-level
transform/opacity is ignored. Parent particle velocity/rotation/scale/color/opacity/Noise seed/
sprite frame is not inherited; event translation only. Higher parent Layer opacity still applies.

Copy groups depth-sort live-head Z or latest projectable tail Z. Unprojectable-head fallback is
the latest projectable stamp. Inside: oldest trail→newest→head. Namespace ensures parent ties
before children; Birth rank before Death; remaining IDs/birth values provide stable tie-breaking.
Child target blend applies per stamp; final parent Layer composition follows existing blend/
opacity/Surface pipeline. No global trail-stamp interleave or alpha rounding change.

## Safety / caches / references

Before slot generation/render:
- parent visual bound=count_max, or count_max*ceil((Lmax+parent_delta_max)/P) in Cyclic.
- safe child horizon=delay_max+(emission_duration-1 for Over Time)+Lmax+child_delta_max;
  child_count_max0 gives H0. This conservative bound can overestimate gaps/actual random count.
- One Shot child bound=parent_count_max*child_count_max per event.
- Cyclic child bound=parent_count_max*ceil(H/P)*child_count_max per event.
- total visual=parent +Birth child +Death child <=4096.
- total stamps=parent stamps+sum(child_visual_bound*S_child) <=8192.
- exact boundaries accepted;4097 visual/8193 stamps explicitly rejected. No silent drops.

Canonical exact H is calculated from actual slots for enumeration; safe settings H is used for
prevalidation. Output width/height/FPS/frame count does not expand. Users must set duration
long enough for death/child tail output. Strict output clipping and existing Overscan semantics
are unchanged. Caps are not real-time/60FPS promises.

Base key adds read-only target template dependencies. Target name/high-level transform/flags
are not template dependencies; absolute template start/cyclic metadata can still cause coarse
cache invalidation though output schedule ignores them. Playback revision uses full settings
repr across layers, a deliberate coarse correctness-first invalidation. Existing global Undo
and refresh may regenerate on rename; references/pixels remain correct.
Parent/Target spawn keys exclude events (cyclic/Trail/render properties already excluded).
Target emitter edits invalidate base/preview/playback and regenerate referencing parent Generated
pixels. Motion-only target edits use the same dependent regeneration helper. Composition source
revision feeds existing resource keys. Source assets follow the existing immutable-resource
contract; changing source IDs/settings and normal resource-edit invalidation is the supported path.

Event-enabled asynchronous preview snapshot deepcopies Project **once per request**, retaining
template resources/Parent context. No deepcopy/serialization/filesystem/layer search per child
or stamp. Generated apply/current/direct/full/export use layer-aware dispatch, not recursive render.
Target delete cleans references and regenerates surviving parent pixels before the after snapshot,
so Undo restores target/references/pixels as one transaction. Parent/target duplicate keeps target
IDs unchanged; no retarget-by-name. Missing references load safely without rewriting original files.

## Verification / representative evidence

New tests:63 in `test_particle_sub_emitter.py`,19 in `_serialization.py`,20 in `_ui.py`.
Focused **102 passed /5.28s**. Final full **1732 passed /110.58s**, failures0/errors0.
Earlier integration runs1724/1731 also passed; later default-selection/identity/delete-pixel
checks are included in the final1732. Test temp `C:\Dev\pem_v25_complete_final`.

Compileall app/tests/tools exit0; --version0.0.25 exit0; direct --check exit0;
run_app.bat --check exit0; git diff --check exit0. Both check paths report sandbox
AppData log-write PermissionError/logging_unavailable. Logging/permissions were not changed;
exit0 is not claimed as proof that AppData logging works in this sandbox.

Frozen comparison reads checkpoint2470af2 renderer and its Trail helper, comparing OFF output
for One Shot/Cyclic, Normal/Additive, TrailOFF/ON and frames0/5/14/23/100000.
Shared current pure evaluator/model/dependency modules remain: this is not an isolated v24 exe.
Other tests cover L-1 origin, delayed/random/Over Time timing, ignored Target metadata/nesting,
three child motion modes with G/D/N and multi-point appearance, RNG cache object reuse,
large seek/periodicity, parent/child mixed depth ordering, safety bounds, references/Undo, preview,
current/full/generated/playback/Save/Reload/decoded PNG and unchanged dimensions/range.

Five96x96 synthetic fixtures: Projectile Impact, Explosion Secondary Smoke(random lifetimes),
Firework(rising→radial death), Birth Puff(delay/Over Time), Cyclic Death Splash Diagnostic.
All24 output frames current/full/generated/playback/Save/Reload/decoded PNG parity exact.
Projectile atframe7 still head; frame8 six children begin at its last position while parent Trail
remains. Atframe18 six child tail-only groups remain, frame23 none. Cyclic diagnostic is lifetime
Death, **not collision**. Contact sheet inspected: simple small source sprites/afterimages,
not polished production art or native GUI visual approval. No automatic collision/physics claim.

Evidence: `C:\Dev\pem_v25_sub_20261002_final\report.json`, `contact_sheet.png`,
five fixture JSON and PNG folders. Only new synthetic artifacts under CDev; no user file changes.

## Throughput — measured, not real-time guarantee

96x96 canvas /5x5 synthetic source, three warm render median; diagnostic timing includes
collection overhead and is not comparable to warm no-diagnostic baseline. Benchmarks run
before the final whole-suite run, not concurrently. ParentL8/ChildL6/P24/ChildCount4.
Light H6, full-stack TrailD8/I2 (delta6) gives H12. OFF/Birth sampledframe3; othersframe9.
Diagnostics count projectable groups/stamps, including zero-alpha/zero-scale evaluations;
counts are workload identities, not a guarantee each group contributes visible pixels.
Frozen OFF baseline shares dependencies as noted. No hardware-independent FPS claim.

| Parent | Scenario | Event H | Visual/stamp bound | Actual invocations | Heads/all visual/child visual | All/child Trail stamps | Warm ms | Frozen OFF ms | Frame100000 diagnostic ms |
| ---: | --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: |
| 100 | off | — | 100 / 0 | 0 | 100/100/0 | 0/0 | 10.686 | 10.252 | — |
| 100 | birth | 6 | 500 / 0 | 100 | 500/500/400 | 0/0 | 50.213 | — | — |
| 100 | death | 6 | 500 / 0 | 100 | 400/400/400 | 0/0 | 42.005 | — | — |
| 100 | both | 6/6 | 900 / 0 | 100 | 400/400/400 | 0/0 | 43.229 | — | — |
| 100 | cyclic | 6/6 | 900 / 0 | 100 | 400/400/400 | 0/0 | 43.135 | — | 0.551 |
| 100 | full_stack | 12/12 | 900 / 2700 | 200 | 400/900/800 | 1100/800 | 125.501 | — | 98.312 |
| 500 | off | — | 500 / 0 | 0 | 500/500/0 | 0/0 | 56.674 | 55.625 | — |
| 500 | birth | 6 | 2500 / 0 | 500 | 2500/2500/2000 | 0/0 | 275.031 | — | — |
| 500 | death | 6 | 2500 / 0 | 500 | 2000/2000/2000 | 0/0 | 222.059 | — | — |
| 500 | both | — | 초과 / — | — | —/—/— | —/— | 거부 | — | — |
| 500 | cyclic | — | 초과 / — | — | —/—/— | —/— | 거부 | — | — |
| 500 | full_stack | — | 초과 / — | — | —/—/— | —/— | 거부 | — | — |
| 1000 | off | — | 1000 / 0 | 0 | 1000/1000/0 | 0/0 | 108.706 | 105.888 | — |
| 1000 | birth | — | 초과 / — | — | —/—/— | —/— | 거부 | — | — |
| 1000 | death | — | 초과 / — | — | —/—/— | —/— | 거부 | — | — |
| 1000 | both | — | 초과 / — | — | —/—/— | —/— | 거부 | — | — |
| 1000 | cyclic | — | 초과 / — | — | —/—/— | —/— | 거부 | — | — |
| 1000 | full_stack | — | 초과 / — | — | —/—/— | —/— | 거부 | — | — |

Rejected500 both/cyclic/full configurations have conservative4500 visuals (full stamps13500);
1000 single-event configurations5000 visuals;1000 both/cyclic/full9000 (full stamps27000).
They are rejected before rendering even if a particular sampled frame would be below caps.
Full-stack100 frame100000:100 current child invocations,400 tail-only child visual copies,
800 Trail stamps, **98.312ms** diagnostic; period-modulo RGBA exact. Light Cyclic at this phase
has no contributing copies and takes0.551ms: this empty phase must not be compared as equivalent
work to the nonempty full-stack case. Tests also seek nonempty short-period cases at100000.
Valid500 Birth/Death median275.031/222.059ms shows safety acceptance is not realtime usability.

## Capability / roadmap

Automated bounded Birth/Death path verified, native GUI approval pending; final COMPLETE withheld.
Overall Sub-emitter/Event system PARTIAL. Recursive graph, Collision, threshold/frame events,
multiple targets, per-event variation, velocity/rotation/scale/color/opacity inheritance,
world-history/scripting are MISSING. Ribbon Mesh/true force/turbulence/full Graph remain MISSING.
No Timeline/Auto-Key added. Existing Trail→bounded Birth/Death roadmap followed.
Next: user native GUI/performance approval, then separately scope deterministic bounded per-event
variation. Do not speculate implementation or broaden into recursive events here.

## Requested completion items 1..256

| # | Requested item | Evidence/result |
| ---: | --- | --- |
| 1 | 실제 시작 HEAD | 9cf4a413b38111e6934e367fc758845707b6fa9c |
| 2 | 시작 Version | 0.0.24 |
| 3 | 시작 FORMAT_VERSION | 21 |
| 4 | 시작 pytest | 1630 passed /106.67s; failures0/errors0 |
| 5 | Trail commit hash | 2470af26df658e72440ac4712f90973ce75008fc, Add deterministic particle trails |
| 6 | explicit staged files | 55 explicit whitelist files below; add -A 미사용 |
| 7 | excluded files | 보호 PNG/사용자 projects/CDev evidence/build/cache/log/temp/backup/ZIP 제외 |
| 8 | checkpoint 후 Git | main ahead43; staged0; protected PNG만 untracked |
| 9 | stable Layer ID | EffectResourceLayer.id, uuid4().hex default, persistent JSON ID |
| 10 | Layer lookup | inline by_id maps: project.sync_effect_flat_order / renderer._base_key / new event service |
| 11 | Particle source reference | particle_settings.resource_type + clip_asset_id (resource_id adapter) |
| 12 | child-template reuse boundary | layer-aware render_layer_particles → request streams → shared motion/raster; lookup outside low-level raster |
| 13 | particle raster boundary | particle_clip_frame + render_transformed_source; v24 render_particle_frame assumes one clip per emitter |
| 14 | local/System coordinate boundary | evaluate_particle_motion returns ParticleMotionPosition before project_particle_billboard |
| 15 | higher transform boundary | Layer projection/current Parent affine then Surface pass then Project.compose_frame |
| 16 | visibility/solo application | Project.compose_frame: effect_effective_visible / preview Solo; target invocation ignores target flags |
| 17 | cyclic cache identity | global _SPAWN_STATE_CACHE key=settings render-excluded repr + clip length, not layer UUID |
| 18 | trail visual lifetime helper | trail.delta_max / sample_count; cyclic visibility_extension_frames |
| 19 | delete/reference cleanup architecture | MainWindow._effect_batch_snapshot + _sync repair; Project.repair_sub_emitter_references clear/disable, no retarget |
| 20 | duplicate ID semantics | duplicate_selected_effect_layers / duplicate_effect_group new UUID; event target IDs unchanged |
| 21 | Version | 0.0.25 |
| 22 | FORMAT_VERSION | 22 |
| 23 | event settings model | ParticleSubEmitterEventSettings nested static dataclass |
| 24 | Birth fields | birth_sub_emitter.enabled / target_layer_id |
| 25 | Death fields | death_sub_emitter.enabled / target_layer_id |
| 26 | target ID type | nonempty str or None; bool enabled strict |
| 27 | defaults | both False/None |
| 28 | migration | <=21 missing fields default OFF/None; original file not rewritten |
| 29 | target Particle layer requirement | existing same-Effect placement_mode particle; stable ID lookup |
| 30 | self target rejection | contribution_bounds/validate_project_sub_emitters reject self |
| 31 | target normal visibility behavior | normal visibility unchanged; invocation unaffected by hidden target |
| 32 | target solo behavior | normal preview Solo unchanged; invocation unaffected |
| 33 | target lock behavior | normal edit Lock unchanged; invocation unaffected |
| 34 | target layer transform behavior | target Layer/Surface transform ignored for invocation |
| 35 | target parent behavior | target Parent/Group ignored for invocation |
| 36 | target timeline start behavior | birth offsets subtract target.start_frame; not an added delay |
| 37 | target cyclic mode behavior | one canonical emission only; template adapter one_shot |
| 38 | target nested sub-emitter behavior | template adapter clears both events; no recursive render call |
| 39 | event frame | E=B |
| 40 | origin age | 0 |
| 41 | origin local coordinate | existing evaluate_particle_motion local XYZ |
| 42 | parent birth delay interaction | real canonical birth incl delay/spread |
| 43 | event frame | E=B+L |
| 44 | logical lifetime | parent logical lifetime, not visual lifetime |
| 45 | last-visible origin age | L-1 |
| 46 | parent Trail separation | parent Trail persists separately; no later duplicate Death |
| 47 | no invisible-age extrapolation | origin never extrapolates invisible age L |
| 48 | target canonical slots | same particle_spawn_states target immutable tuple |
| 49 | relative birth formula | relative_birth=canonical_child.birth_frame-target.start_frame |
| 50 | absolute child birth | child_birth=event_frame+relative_birth |
| 51 | child actual age | CA=T-child_birth |
| 52 | child visual lifetime | child lifetime + target.trail.delta_max |
| 53 | child Trail | shared Trail renderer/sample helper, post-death included |
| 54 | target Over Time | one canonical Over Time schedule reused |
| 55 | target Delay | canonical child random delay reused without draws |
| 56 | invocation key | (parent_layer_id,event_kind,parent_cycle_index,parent_particle_id,parent_copy_birth) |
| 57 | child copy key | flattened deterministic render_key includes invocation components+childID, namespace1 |
| 58 | parent canonical identity | parent cached canonical tuple unchanged |
| 59 | target canonical identity | target canonical tuple unchanged, including normal cyclic vs invocation adapter |
| 60 | new RNG draws | 0 per invocation; once-per-canonical cache construction remains |
| 61 | child Noise identity | target seed+canonical childID+actual child age |
| 62 | repeated template pattern semantics | same template random pattern intentionally repeats per event |
| 63 | One Shot Parent | canonical parent slot event filter 0<=T-E<H |
| 64 | Cyclic Parent | analytic integer cycle k bounds per parent/event |
| 65 | Birth event offset | e=0 |
| 66 | Death event offset | e=L |
| 67 | event horizon H | exact max(child_relative_birth+child_visual_lifetime); conservative settings horizon in bounds |
| 68 | analytic k min/max | kmin=ceil((T-B-e-(H-1))/P), kmax=floor((T-B-e)/P) |
| 69 | frame100000 | direct bounded evaluation; no elapsed-frame scan |
| 70 | mutable event history 여부 | 없음; no fired set/queue/history |
| 71 | event position inheritance | translation only, local XYZ before projection |
| 72 | velocity inheritance | 없음 |
| 73 | rotation inheritance | 없음 |
| 74 | scale inheritance | 없음 |
| 75 | color inheritance | 없음 |
| 76 | opacity inheritance | 없음; higher parent Layer opacity still applied once |
| 77 | Linear | existing child motion evaluator |
| 78 | Orbit | existing Orbit evaluator |
| 79 | Helix | existing Helix evaluator |
| 80 | Gravity | target child G at actual age |
| 81 | Drag | target child analytic Drag base clock |
| 82 | Noise | target child Noise actual age/stable identity |
| 83 | sprite playback | target source/playback/start/speed at child sample age |
| 84 | rotation | target rotation+angular_velocity*child sample age |
| 85 | Scale curve | target multi-point uniform scale |
| 86 | Color curve | target multi-point RGB only |
| 87 | Opacity curve | target multi-point alpha |
| 88 | Trail | target Trail history-free sampling/fade/group depth |
| 89 | blend mode | target Normal/Additive raster per stamp; final Layer uses parent pipeline |
| 90 | Parent local/System origin | parent age0 or L-1 origin before billboard/Layer projection |
| 91 | Parent current Layer transform | current target-frame parent Layer snapshot |
| 92 | Parent current Parent affine | current parent world affine |
| 93 | Parent System | parent motion origin at current target-frame evaluated System context |
| 94 | Parent Surface | single current parent Surface pass |
| 95 | 2.5D | existing local perspective/Layer projection/revolutions reuse |
| 96 | target high-level transform ignored | target high-level Layer/Surface/Parent ignored |
| 97 | historical world event 미지원 | UI tooltip/README/report explicitly no world history |
| 98 | child group depth | live head Z, otherwise latest projectable tail Z |
| 99 | trail group semantics | oldest→newest→head in copy group |
| 100 | invocation tie-break | namespace0 parent, namespace1 child; birth rank0 before death rank1, cycle/parentID/birth/layerID/childID |
| 101 | Birth/Death same frame | distinct event kind in stable identity |
| 102 | Normal | existing source-over raster; deterministic group depth sort |
| 103 | Additive | target additive raster; parent final composition blend unchanged |
| 104 | child count max | target particle_count_max |
| 105 | child horizon | max(relative_birth_i+L_i+delta_i), settings upper bound for prevalidation |
| 106 | One Shot child bound | parent_count_max*child_count_max per enabled event |
| 107 | Cyclic child bound | parent_count_max*ceil(H/P)*child_count_max |
| 108 | combined visual bound | parent visual bound + enabled event child bounds <=4096 |
| 109 | combined trail-stamp bound | parent stamps + child_visual_bound*target sample_count <=8192 |
| 110 | exact boundaries | 4096/8192 exact accepted |
| 111 | over-limit rejection | 4097 visual /8193 stamps rejected |
| 112 | silent drop 여부 | 없음; explicit ValueError/UI revert, never truncates |
| 113 | rename | stable ID unchanged; combo display updates |
| 114 | parent duplicate | new parent UUID, same original target ID |
| 115 | target duplicate | new target UUID, existing references stay original |
| 116 | target delete | same batch clear/disable + regenerate surviving generated pixels |
| 117 | delete Undo | batch snapshots restore target/references/pixels together |
| 118 | missing target load | safe disable/None, original file unchanged |
| 119 | arbitrary retarget 여부 | 없음; no name-based retarget |
| 120 | group placement | Trail adjacent, before Over Lifetime |
| 121 | Birth label | Birth / 생성 시 |
| 122 | Birth enable | Birth — Enable / 생성 시 — 사용 |
| 123 | Birth target | Birth Target / 생성 대상 |
| 124 | Death label | Death / 사망 시 |
| 125 | Death enable | Death — Enable / 사망 시 — 사용 |
| 126 | Death target | Death Target / 사망 대상 |
| 127 | target combo filtering | particle only, no self/missing/non-particle; hidden/solo/locked included |
| 128 | stable ID storage | combo itemData stable ID, names display; duplicates short disambiguation |
| 129 | KO | Korean labels/status/tooltips |
| 130 | EN | English labels/status/tooltips |
| 131 | tooltip | one schedule/no recursion/target flags transforms ignored/Death L-1/current parent/no world history |
| 132 | invalid target UI | invalid revert0; default None Enable is runtime choose-target prompt, model remains OFF until selection |
| 133 | safety status | combined copies/stamps/error advice; realtime 보장 없음 |
| 134 | refresh integrity | A BirthON X/DeathOFF Y ↔ B BirthOFF Z/DeathON W; selection/KO/EN/scrub exact |
| 135 | Birth Enable | accepted1 Undo / exact redo |
| 136 | Birth Target | accepted1 Undo / exact redo |
| 137 | Death Enable | accepted1 Undo / exact redo |
| 138 | Death Target | accepted1 Undo / exact redo |
| 139 | no-op | Undo0/dirty0/revision0 |
| 140 | invalid target | Undo0/dirty0/revision0; unsafe edit restored |
| 141 | refresh | Undo0/dirty0/revision0 |
| 142 | target delete transaction | one delete batch transaction includes reference cleanup/pixels |
| 143 | parent render invalidation | nested settings key invalidation |
| 144 | preview | snapshot includes whole read-only project when events ON; template context retained |
| 145 | playback revision | full settings repr for all layers in playback revision (coarse) |
| 146 | generated output | target settings edit regenerates referencing parents; delete cleanup too |
| 147 | parent spawn cache | event fields pop from spawn key |
| 148 | target spawn cache | one-shot adapter removes cyclic/events; same canonical cache tuple |
| 149 | target dependency invalidation | template_dependencies in base key + UI dependent regeneration + resource composition revision |
| 150 | target rename behavior | base dependency ignores name; existing global Undo refresh may regenerate, correctness first |
| 151 | sequential | same independent frame evaluation |
| 152 | direct | history-free target request |
| 153 | reverse | reverse/random order exact |
| 154 | frame step | direct frame evaluation |
| 155 | current | current parity |
| 156 | full | full parity |
| 157 | generated | generated parity |
| 158 | playback | exact playback parity |
| 159 | PNG | decoded PNG parity after Save/Reload |
| 160 | frame100000 | period-modulo exact; full-stack tail-only evidence |
| 161 | Birth periodicity | static/local periodic exact |
| 162 | Death periodicity | static/local periodic exact |
| 163 | Birth+Death periodicity | static/local periodic exact |
| 164 | child Trail periodicity | periodic exact |
| 165 | child lifetime curves periodicity | historical child-age modulation periodic |
| 166 | Parent Trail + Death interaction | Death logical timing unaffected while parent tail remains |
| 167 | FORMAT21 default | missing events False/None |
| 168 | Sub-emitter OFF v24 exact | same fast path, no event enumeration |
| 169 | frozen v24 comparison | read-only2470af2 renderer + frozen Trail helper; shared pure dependency limitation |
| 170 | One Shot | frozen OFF exact |
| 171 | Cyclic | frozen OFF exact |
| 172 | Normal | RGBA array_equal |
| 173 | Additive | RGBA array_equal |
| 174 | benchmark tool | tools/benchmark_particle_sub_emitter.py |
| 175 | Parent counts | 100/500/1000 |
| 176 | Child counts | 4 per invocation benchmark;6 representatives;0/1/3/large boundary tests |
| 177 | event horizon | H6 light /H12 Trail full stack; variable/delayed exact horizon tests |
| 178 | relevant invocations | actual projectable invocation count in JSON/table; not elapsed cycles |
| 179 | child visual count | actual group diagnostics count separate |
| 180 | child trail stamps | actual child Trail stamp count separate |
| 181 | total visual bound | conservative bound in JSON/table |
| 182 | total stamp bound | conservative stamp bound in JSON/table |
| 183 | OFF baseline | 100/500/1000 active atframe3 vs frozen v24 warm reference |
| 184 | Birth | 100 &500 valid |
| 185 | Death | 100 &500 valid |
| 186 | Birth+Death | 100 valid;500/1000 rejected conservative4500/9000 |
| 187 | Cyclic | 100 valid; analytic gate/period tests |
| 188 | Full Stack | 100 valid full G/D/N/Trail/multi-point/additive, full-stack900 visual/2700 stamp bound |
| 189 | frame100000 | fullstack100 at100000:100 invocations /400 child visual /800 stamps,98ms-class diagnostic |
| 190 | rejected configs | 500 both/cyclic/full and1000 all events reject before render |
| 191 | realtime claim 여부 | 없음; valid workloads often slower than realtime |
| 192 | Projectile Impact | synthetic single projectile → death burst from final visible position |
| 193 | Explosion Secondary Smoke | synthetic random-lifetime sparks → independently timed secondary puffs |
| 194 | Firework | synthetic rising particle → radial death sparks; collision unsupported |
| 195 | Birth Puff | synthetic actual Birth flash with delay/Over Time |
| 196 | Cyclic death-splash diagnostic | synthetic periodic lifetime-based falling/death splash, not collision |
| 197 | 실제 표현력 개선 | no manual Start calculations for random birth/death; simple synthetic art only |
| 198 | 신규 files | test_particle_sub_emitter.py / _serialization.py / _ui.py |
| 199 | focused count | 102 passed /5.28s |
| 200 | model/serialization | strict event payloads/format22/default21/no rewrite/repair |
| 201 | birth timing | B age0 same-frame child |
| 202 | death timing | B+L originL-1 independent Trail |
| 203 | target semantics | start/flags/transforms/cyclic/nesting ignored |
| 204 | motion | Linear/Orbit/Helix + G/D/N |
| 205 | appearance | sprite/random/rotation/Scale/RGB/Opacity/Trail |
| 206 | RNG | cached tuples+Random construction forbidden after priming |
| 207 | cyclic | P6/childL9/trails,large seeks andstatic periodic exact |
| 208 | safety | 4096/4097;8192/8193; horizon/no drop |
| 209 | references | rename/duplicate/deleteUndo/loadrepair |
| 210 | UI | KO/EN compact/280/300px/150%font, default reachable selection |
| 211 | Undo | four accepted1;invalid/no-op/refresh0;delete1 |
| 212 | cache | base key/revision/dependent Generated/snapshot tests |
| 213 | transforms | current higher transform/2.5D/revolutions/Surface/position-only isolation |
| 214 | ordering/blend | depth/group/tie ordering Normal/Additive |
| 215 | export | current/full/generated/preview/playback/save/reload/PNG/output size24 unchanged |
| 216 | full pytest | 1732 passed /110.58s; failures0/errors0 |
| 217 | compileall | compileall app tests tools exit0 |
| 218 | --version | Pixel Effect Maker v0.0.25 exit0 |
| 219 | --check | exit0; sandbox AppData logger PermissionError warning |
| 220 | run_app.bat | run_app.bat --check exit0; same logger warning |
| 221 | git diff --check | exit0, CRLF notices only |
| 222 | Birth/Death Sub-emitter status | automated narrow path verified; native GUI approval pending, final COMPLETE withheld |
| 223 | overall Event system status | PARTIAL |
| 224 | recursive child status | MISSING, depth1/no child events |
| 225 | Collision status | MISSING |
| 226 | per-event variation status | MISSING; canonical target pattern repeats |
| 227 | remaining Force status | true force/turbulence/collision MISSING |
| 228 | Ribbon Mesh status | MISSING |
| 229 | Graph status | full Graph/Bezier/tangent MISSING |
| 230 | 최종 HEAD | 2470af26df658e72440ac4712f90973ce75008fc |
| 231 | staged | 0 |
| 232 | v0.0.25 commit | 0 |
| 233 | tag/push/build | tag0/push0/build0/PyInstaller0/ZIP0/release0 |
| 234 | Windows native GUI manual 여부 | 수행하지 않음 |
| 235 | event history buffer 없는지 | 없음 |
| 236 | Direct Seek deterministic인지 | 예 |
| 237 | Birth timing 정확한지 | B actual canonical copy birth |
| 238 | Death timing 정확한지 | B+logical L |
| 239 | Death origin이 last-visible position인지 | 예, L-1 not invisible L |
| 240 | Parent Trail이 Death를 늦추지 않는지 | 예 |
| 241 | child relative schedule 정확한지 | 예, subtract target.start_frame |
| 242 | target timeline transform/visibility가 child에 영향 없는지 | 예, invocation ignores those metadata |
| 243 | Parent transform context가 child에 적용되는지 | 예, current target-frame higher transform |
| 244 | nested Sub-emitter가 실행되지 않는지 | 예, adapter clears both child events |
| 245 | target canonical pattern 재사용인지 | 예 |
| 246 | RNG draw0인지 | 0 per invocation |
| 247 | cyclic analytic enumeration인지 | 예, integer k bounds from H |
| 248 | F(t+P) 유지인지 | 예, static/local conditions |
| 249 | safety bounds 유지인지 | 예, combined conservative4096/8192 |
| 250 | target reference rename/delete 안전인지 | 예, stable IDs + one delete snapshot restoration |
| 251 | Preview/Export parity인지 | 예, automated exact pipeline comparisons |
| 252 | v0.0.24 legacy exact인지 | 예, frozen renderer/Trail helper comparison, shared dependencies noted |
| 253 | Projectile Impact practical 개선 | automatic final-position Death Impact without manual layer Start arithmetic |
| 254 | random-death secondary effects 개선 | individual random-lifetime particle deaths produce secondary emissions |
| 255 | 전체 roadmap과 일치하는지 | 예, Trail→bounded Birth/Death next foundation |
| 256 | 다음 추천 기능 | 먼저 사용자 native GUI/성능 승인; 다음 bounded deterministic per-event variation 설계 검토 |

## Final Git / manual

HEAD2470af26df658e72440ac4712f90973ce75008fc. staged0/v25 commit0.
All v25 tracked edits/new files unstaged/uncommitted. Tag/Push/Build/PyInstaller/ZIP/Release0.
ProtectedPNG SHA256 unchanged and untracked. Windows native GUI manual **수행하지 않음**.
[미실행 수동 체크리스트](MANUAL_TEST_CHECKLIST.md).

