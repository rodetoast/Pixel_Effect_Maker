# Post-v0.0.21 Effect Capability Recheck

2026-10-01 · Pixel Effect Maker · 코드/자동 검증 기반, production 구현 없음.

## 결론과 범위

다음 하나의 우선순위는 **A: Spawn/Emission 중 Deterministic Cyclic Emission**이다.
새 도형을 먼저 추가하는 작업이 아니다. Point/Line/Box/Circle circumference는 이미
Model→UI→Render→Save→Tests까지 존재한다. 특히 Ring Burst와 넓은 Box Dust를
Point-only 한계로 분류하면 잘못된 결론이다.

기본 유한 애니메이션은 10종 모두 렌더 가능하다. 적은 논리 레이어와 일반적인
source artwork로 제작 가능한 기본형은 10/10이다. 이 중 Fire/Ember, Area Dust,
Rain/Snow를 **지속 밀도와 반복 경계까지 재사용 가능한 지속형**으로 요구하면
현재 3/10은 PARTIAL이다. 반복 Emission은 이 3개의 목표를 practical로 바꾸는
가장 직접적인 후보다. 완전히 새로운 시각적 archetype 3종을 발명한다는 의미는 아니다.
이 구분 없이 “3종을 이제 처음 만들 수 있다”고 말하면 과장이다.

Trail은 Projectile 헤드나 sprite-based Sword Slash 자체를 막지 않는다.
경로를 바꾸어도 따라오는 ribbon/comet/afterimage 변형은 막는다. Sub-emitter도
고정 시점 impact를 막지는 않지만 임의 death/collision에 반응하는 자식 방출을 막는다.
Lifetime multi-point는 가장 넓은 품질/작업량 개선 후보이나, 이번 10종의 기본형을
새로 여는 기능은 아니다. Gravity/Drag/Noise 이후 true force 부재를 최우선 blocker로
유지할 근거는 약해졌다. 이것은 사용자가 직접 만든 final art에 대한 평가가 아니라
명시된 목표, 현재 코드와 합성 fixtures에서 도출한 설계 판단이다.

## 실제 기준선과 checkpoint

| 항목 | 실제 결과 |
| --- | --- |
| 시작 HEAD | `d0173ef799b6776ff7d9ebd98ceefd8ca3397bed` |
| 시작 Git | main, origin/main보다 38 commits 앞섬; tracked 수정 46, Noise 관련 신규 5, 보호 PNG 1; staged 0 |
| 시작 full pytest | **1335 passed in 80.16s**, 실패 0 |
| 시작 진단 | compileall app/tests/tools, --version, --check, run_app.bat --check, diff --check 모두 exit 0 |
| checkpoint | `af9be4c948f3d3a09700478dc00dd2102196c2ab` — `Add deterministic particle noise` |
| staging | 검사한 51개 Noise 관련 경로만 explicit git add; `git add -A` 사용하지 않음 |
| 제외 | `테스트소스.png` 및 이 감사에서 이후 작성한 문서/diagnostic |
| 현재 버전/형식 | **v0.0.21 / FORMAT_VERSION 18**, 변경하지 않음 |

`테스트소스.png`의 SHA256은 시작/최종 모두
`8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`.
내용/이름/위치 보존, stage하지 않음. checkpoint 후 감사 변경만 unstaged/uncommitted다.

## 역사 대비 delta

기존 `EFFECT_AUTHORING_CAPABILITY_AUDIT.md`의 v0.0.15 최초 감사 및 번호별 결론은
역사 기록이다. 이후 일부 matrix가 갱신되어 오래된 “Color/Additive 없음” 문장과
혼재한다. 이 문서를 현재 판정의 overlay로 사용하고 이전 기록은 삭제하지 않는다.

| 이전 병목 | 현재 end-to-end 범위 | 실제 남은 gap |
| --- | --- | --- |
| uniform lifetime Scale | enabled, Start/End, 4 easings; birth scale × lifetime multiplier | 3+ points, 독립 XY curve |
| lifetime Color | RGB multiplier Start→End, white source 사용 가능 | multi-stop, HSV, random palette; source의 검은 픽셀을 tint로 밝힐 수 없음 |
| Additive | Particle 및 Particle Resource Layer 경로, 겹친 particle/layer 합성 | 모든 Resource 내부 layer에 대한 범용 blend stack 아님 |
| Gravity | signed local Y, 실제 age에 .5*g*age² | 물리 force integration/충돌 아님 |
| Drag | analytic effective age, Linear 및 Orbit/Helix 진행 감쇠 | Gravity/Noise 변위까지 감쇠하는 통합 물리 솔버 아님 |
| Noise | seed/particle ID 기반 smooth XY positional displacement, birth offset 0 | 가속도 noise, curl, force, Z/world-space noise 아님 |

위 6개는 좁은 구현 경로에서 기능 존재를 인정한다. multi-point 등의 부재 때문에
그 자체를 MISSING으로 되돌리지 않는다. 캐시 prebuffer는 simulation prewarm이 아니다.

## 코드 증거: Model → UI → Render → Save → Tests

| 범위 | 실제 경로 / 검증 |
| --- | --- |
| spawn/emission | `app/models/particle_emitter.py:ParticleEmitterSettings`, validate/to_dict/from_dict → `app/ui/particle_properties_panel.py` emission/spawn groups, set_emitter/settings → `app/services/particle_render_service.py:build_particle_instances/_spawn_position` → compact `project_io.py` / Project serializer → `tests/test_particle_pipeline.py` all_spawn_shapes, fixed seed, timing; 새 diagnostic shape bounds/Inspector/save parity |
| mutation/Undo | `main_window.py:update_particle_draft`, resource_layer_settings EditorValueCommand, adapter sync; `tests/test_particle_noise_serialization.py` toggle/strength/frequency undo/noop/redo, 기존 numeric commit 및 layer tests |
| lifetime | LifetimeScalarModulation/LifetimeColorModulation + opacity fields → Inspector groups → `lifetime_modulation_service.py`와 render_particle_frame → nested serializer → scale/color/alpha easing tests 및 새 fixtures |
| natural motion | particle_natural_motion_service.py, particle_noise_service.py → Inspector controls → evaluate_particle_motion → settings serialization → gravity/drag/noise 및 noise_serialization tests |
| layer/hierarchy | EffectResourceLayer, layer_space_transform / layer_parenting → Resource Inspector / MainWindow → effect_resource_layer_render_service, layer_space_transform_service → Project → 2.5D/group/parent/multiselect/undo tests |
| export | MainWindow materializes logical Resource Layers → export_service.export_png_frames → Project.compose_frame → PIL RGBA; 새 fixture 240개 decoded PNG exact 비교 |
| absent families | Particle settings/instance, serializer keys, Inspector controls, evaluator dispatch 대조; trail/history/ribbon/event/child/attractor/repulsor/force 실행 경로 없음. 일반 Qt signals·Group·Parent는 particle event가 아님 |

단순 이름 검색만으로 기능 부재를 판정하지 않았다. 기존 모델 필드와 렌더 함수의
전 경로 및 실제 UI reconstruction을 함께 확인했다. UI introspection은 offscreen
자동 검사이며 Windows native GUI manual QA와 다르다.

## Spawn / Emission 상세

| 항목 | 판정 / 정확한 의미 |
| --- | --- |
| count | COMPLETE: emitter당 total count를 min/max에서 한번 샘플, 0..4096 |
| burst | COMPLETE: 단일 birth frame + per-instance random delay |
| over_time | COMPLETE(유한): round(i*(duration-1)/(count-1)) 분포; count≤1은 0 |
| rate/interval | MISSING: particles/sec, 독립 interval 필드 없음. count/duration으로 비슷한 평균 밀도 조절은 가능하지만 일정 rate API와 같지 않음 |
| multi-burst schedule | MISSING: 여러 emitter layer의 Start Frame으로 우회; 소수 고정 explosion stages는 실용적, 긴 자동 schedule은 duplication 비용 큼 |
| point | COMPLETE: origin 고정; radial_outward에서는 중심일 때 무작위 0..360 direction |
| line | COMPLETE: 두 점 사이 uniform t. Rain 상단의 넓은 분포에 충분 |
| box | COMPLETE: 중심 기준 XY 독립 uniform filled rectangle. 이미 넓은 area distribution 지원 |
| circle | COMPLETE(둘레/호): 지정 angle range에 uniform angle, 고정 radius |
| filled disk | MISSING: radius를 면적 균등하게 샘플하지 않음. 별도 disk 또는 fill option 없음 |
| ring | COMPLETE(둘레): circle + radial_outward. 두께/annulus fill은 MISSING |
| direction | fixed/radial_outward + ±spread; speed range. cone-like velocity fan 가능, 3D cone volume 아님 |
| missing shapes | alpha mask, custom path, fill/edge switch, independent random Z 없음 |
| seed | random.Random(seed) spawn state 한번 구축; ID=순번. natural motion은 RNG draws를 추가하지 않음 |
| continuous loop | PARTIAL: editor replay/clip loop는 유한 spawn을 다시 재생할 뿐. emitter 자체 반복 birth, 이전 cycle particle, steady start density 없음 |

256 instances/shape 측정: Point radius 0; Line radius 0.067..23.964;
Box radius .542..17.637 (bounds ±15/±10); Circle radius
15.999999999999995..16.000000000000004. Circle filled disk라는 해석은 실측으로도 부정된다.

## Lifetime / Trail / Events / Force

Scale, RGB, Alpha 모두 두 endpoint 사이의 monotonic easing이다.
`0→1→0 scale`, `transparent→opaque→transparent`, `white→yellow→red`,
`small→large→small`, 반복 pulse/flash를 **한 normalized particle lifetime 채널로 직접** 만들 수 없다.
source clip에 baked frame animation을 넣거나 Resource/Effect absolute keyframes로 우회 가능하다.
고정 동기 flash 몇 개는 practical하지만 random birth/lifetime particle마다 동일한 중간 peak를
재사용하려면 source 재제작/복제가 필요하다. absolute tracks는 per-particle normalized curve가 아니다.

Trail/ribbon/path mesh/history/echo 없음. 긴 sprite·arc sprite·애니메이션 클립은 artwork다.
직선 streak/slash 자체는 practical하지만 curved projectile/comet의 실제 이동 경로 뒤를 잇는
tail이나 회전 궤적 afterimage를 source-independent하게 재편집하는 작업은 비실용적이다.
velocity alignment도 자동으로 제공되지 않는다. render cache는 motion history가 아니다.

Birth/Death/Collision/Frame/Lifetime-threshold child emission 없음. Start Frame이 고정된
impact·secondary smoke는 2~3 logical layers로 practical하다. 임의 lifetime/Noise 경로의
끝점에 child emitter를 자동 생성하는 기능은 없으며, 수십개 고정 emitter를 수동 배치하는
것을 practical로 세지 않는다. 엔진에서 collision-triggered sprite를 배치하는 방법은
이 제작툴 내부의 Sub-emitter 지원 증거가 아니다.

Gravity는 탄도/상승, Drag는 이동 감쇠, Noise는 smooth wandering을 실제로 해결했다.
wind constant vector는 direction/speed·system tracks로 단순 우회 가능하다.
attractor/repulsor/curl/vortex/force stack/물리 collision은 없지만 10종의 기본 제작 목표를
막는 공통 필수조건은 아니다. Orbit는 정해진 원궤도이지 attractor physics가 아니다.

## 10종 × 10축 capability matrix

기호: **가능** 직접 지원; **부분** 목표의 일부만 지원; **우회** 소수 레이어/일반 artwork로
실용적; **고비용** source/particle별 반복 수작업; **불가** 해당 실행 경로 없음.
appearance는 diagnostic white dot/arc를 사용했다. 좋은 완성품 art라는 뜻은 아니다.
각 셀은 지정 목표에 대한 판정이며 모든 선택적 고급 변형을 보증하지 않는다.

| 목표 | Spawn/Emission | Direction/Distribution | Motion | Lifetime | Appearance/Blend | Layer/Transform | Timing/Events | Trail/Persistence | Export | Authoring UX |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hit Spark | 가능 burst | 가능 radial fan | 가능 G+D | 부분 shrink/fade, flash peak 없음 | 가능 tint/additive | 가능 1 layer/2.5D | 가능 fixed hit timing; child 불가 | 부분 fixed streak artwork 우회 | 가능 PNG | 가능 기본형, flash curve 우회 |
| Explosion | 가능 point + box | 가능 radial + area | 가능 D+N | 부분 grow/fade, 3-stage 색 없음 | 가능 flash additive/smoke normal | 가능 2 layers | 우회 scheduled smoke; event 불가 | 가능 puff형; lingering echo 불가 | 가능 PNG | 우회 소수 stage는 practical |
| Smoke Puff | 가능 box burst | 가능 rising spread | 가능 G+D+N | 부분 grow/fade, bell alpha 없음 | 가능 tint/normal | 가능 1 layer | 가능 finite puff | 가능 lifetime persistence, history 불가 | 가능 PNG | 가능 basic; bell baked clip 우회 |
| Fire/Ember 지속형 | 부분 finite over_time | 가능 narrow box/upward | 가능 G+D+N | 부분 shrink/fade, pulse 없음 | 가능 additive warm tint | 가능 1 layer | 부분 finite births, cyclic steady 불가 | 가능 emitter age; flame history 불가 | 가능 finite PNG, loop 검증 별도 | 부분 duration 변화마다 밀도/시작 수작업 |
| Magic Orbit/Wisp | 가능 point burst | 가능 phase spread | 가능 Orbit+N, Helix 가능 | 부분 fade/color, pulse 없음 | 가능 additive | 가능 1 layer + 2.5D | 가능 fixed timing; event 불가 | 부분 comet-tail 고비용 | 가능 PNG | 가능 orbiter, path-tail 고비용 |
| Projectile | 가능 single particle | 가능 fixed velocity | 가능 analytic linear/ballistic | 가능 persistent head lifetime | 가능 additive head | 가능 head+impact 2 layers | 우회 fixed impact; dynamic death 불가 | 부분 straight long sprite 우회, curved tail 고비용 | 가능 PNG | 가능 fixed clip, reactive variant 불가 |
| Sword Slash/Arc | 가능 single burst | 우회 static arc artwork | 가능 rotation/scale | 부분 shrink/fade, grow-shrink 없음 | 우회 arc source + tint | 가능 1 layer | 가능 fixed short slash | 우회 static/animated arc; path-ribbon 고비용 | 가능 PNG | 가능 authored arc, path reauthoring 고비용 |
| Area Dust/Ambient 지속형 | 부분 filled box+finite births | 가능 broad area | 가능 slow N/D | 부분 fade, fade-in/out 없음 | 가능 normal/tint | 가능 1 layer | 부분 no cyclic/prewarm | 가능 particle life, repeating density 부분 | 가능 finite PNG | 부분 반복 source boundary 직접 조정 |
| Ring Burst/Shockwave | 가능 circle circumference | 가능 radial outward | 가능 speed/drag | 가능 scale/fade; multipeak 없음 | 가능 additive | 가능 1 layer | 가능 synchronized burst | 우회 solid ring artwork; trail 불필수 | 가능 PNG | 가능 dots ring; continuous ring art 필요 |
| Rain/Snow/Falling debris 지속형 | 부분 line/box+finite births | 가능 downward distribution | 가능 G+N/D | 가능 fixed/random lifetime | 우회 droplet/snow source | 가능 1 layer | 부분 cyclic steady 없음; collision 불가 | 우회 static rain streak; path-tail 선택 | 가능 finite PNG | 부분 지속 시작밀도/loop는 수작업 |

### Practical state / primary / secondary / workaround

| 유형 | practical state | primary gap (기본형 불가능과 구분) | secondary | 실제 workaround 비용 |
| --- | --- | --- | --- | --- |
| Hit Spark | practical finite | 고급 flash peak lifetime | moving streak alignment | sprite strip 1개; peak 재편집은 source 작업 |
| Explosion | practical finite | 고급 3-stage lifetime/color | secondary death event | 2~3 scheduled layers는 낮은 비용; 랜덤 death마다 배치하면 높음 |
| Smoke | practical puff | 고급 fade-in/out | filled disk/force quality | box 및 two-point grow 충분; bell clip 재제작은 중간 |
| Fire/Ember | finite practical / sustained partial | cyclic steady emission | lifetime pulse / true turbulence | finite count-duration 조정 가능; seamless density 반복 수작업 높음 |
| Magic Wisp | orbit practical / comet partial | path-derived trail (comet target) | pulse/attractor variant | orbit 직접, comet clip bake는 궤도 변경 때 재작업 높음 |
| Projectile | head+fixed impact practical / reactive partial | path tail/death event (고급 목표) | orientation | 긴 직선 sprite는 낮음; curved tail/event 복제는 높음 |
| Sword Slash | sprite arc practical / generated ribbon partial | path ribbon (고급 목표) | grow-shrink lifetime | static/animated arc는 정상 asset workflow; arbitrary path 새로 bake는 높음 |
| Area Dust | finite practical / sustained partial | cyclic steady emission | bell alpha/disk shape | broad box 직접; steady start/loop를 손으로 맞추기는 높음 |
| Ring Burst | practical finite | solid shockwave art/annulus 품질 (기본형 아님) | lifetime pulse | circle 직접, 수동 30-layer ring 배치 불필요; solid ring source 1개는 낮음 |
| Rain/Snow | finite practical / sustained partial | cyclic steady emission | collision response 선택 | line/box 직접; over_time total count workaround는 finite만 해결 |

Optional Poison/Electric 별도 fixture는 만들지 않았다. Smoke tint 및 Hit additive 응용은
가능하지만 새로운 검증 archetype 수에 더하지 않았다.

## 후보 영향: 수치의 기준과 과장 방지

count 기준은 위에서 명시한 10개 기본 제작 목표다. 7 finite 기본형은 practical,
3 sustained 목표는 partial. 새 visual family/모든 고급 변형이 아니라 **목표 달성 수**다.
각 후보는 다른 후보 없이 제공되는 경우로 비교한다. 현재 tool도 10종의 finite render를
만들므로 “완전한 불가능→어떤 렌더라도 가능” 기준에서는 전 후보 unlock=0이다.

| 후보 | 새 practical 목표 | 기존 practical 기본형 큰 개선 | 구체적인 집합 / 근거 |
| --- | --- | --- | --- |
| A Spawn/Emission: cyclic steady | **3** | **0** | Fire, Area Dust, Rain: 지속 시작밀도·bounded repeating births. Shapes만 추가하거나 rate만 추가하면 unlock=0 |
| B Multi-point Lifetime | 0 | **5** (+partial 2) | Hit, Explosion, Smoke, Magic, Slash 기본형의 peak/pulse/multicolor 재사용; Fire/Area도 개선하나 emission gap 남음. 총 affected 7 |
| C Trail/Ribbon | 0 | **4** | Hit streak, Magic comet, Projectile curved tail, Slash path ribbon. 경로 기반 variant만 별도 목표로 세면 2(Projectile/Slash); 기본형 unlock으로 더하지 않음 |
| D Sub-emitter/Event | 0 | **2** | Explosion secondary, Projectile death impact. fixed choreography는 이미 practical; reactive variants는 2지만 collision까지 구현하지 않으면 collision impact는 여전히 별도 |
| E Force/Turbulence | 0 | **2** (+partial 3) | Smoke, Magic은 복잡 흐름 품질 향상; Fire, Area, Rain의 흐름도 개선하지만 cyclic gap 남음. 총 affected 5 |

A의 별도 fill-disk/annulus 확장은 Explosion/Smoke/Ring 3개를 품질 개선할 수 있으나
이는 위 **최소 cyclic 제안에서 제외**한다. Hit radial도, 넓은 Box Dust도 이미 가능하다.
다양한 후보 기능을 한 묶음으로 A의 3+3=6 unlock처럼 합산하지 않는다.
양적 결과는 코드상의 gap과 목표 정의에서 계산한 추론이며 아직 구현되지 않은 후보의
성능이나 실제 사용자 완성도에 대한 실험 결과가 아니다.

### 비용 / 위험 / 재사용

| 후보 | Model/UI/Renderer/Save/Test 범위 | seek / performance 위험 | 기존 기능 재사용 / 기반 |
| --- | --- | --- | --- |
| A | loop policy+period, Inspector, bounded birth enumerator, defaults migration, cycle tests | previous cycle alive copies 누락/중복; active copies가 period 대비 lifetime 비율로 증가 | spawn shapes/RNG/analytic age/finite export 재사용; 추후 rate/schedule 기반 |
| B | normalized sorted scalar/color knots, curve UI, evaluator, old endpoints migration | history 필요 없음; knot 탐색/validation. schema 의미/duplicate knots 중요 | 기존 modulation 재사용, 가장 넓은 quality improvement |
| C | sampling interval/duration/width/fade, history-free time resampling, mesh/stamps, UI/save | particles×samples, 2.5D depth/blend order; 이전 프레임 의존하면 seek 깨짐 | analytic motion 재사용; comet/slash 도구 기반 |
| D | graph references/events/child settings, event schedule/depth limits, UI graph/save | stable child IDs/recursive explosion/cycle detection/collision 재현 | emitter 재사용, chain effects 기반; 그룹/Parent와 별개 |
| E | force types/space/parameters, stack UI, analytic 또는 bounded integrator, state schema | step order/seek/cache/복잡 integration; per-particle×force 비용 | G/D/N 참고 가능하나 physics로 자동 승격 불가 |

모든 후보는 persistent model을 추가하면 향후 schema/migration 검토가 필요하다.
UI 복잡도는 A 2개 핵심 controls가 가장 좁고, B knot editor, C sampling+geometry,
D graph, E stack 순으로 저마다 새 interaction 요구가 생긴다. 주관적인 1~10 점수 없음.

우선순위는 **1 A(cyclic), 2 B(multi-point), 3 C(trail)**, D/E는 그 뒤다.
이전의 force/turbulence-first 잔여병목 서술과 달라졌다. B는 quality breadth에서는
1위지만 이번 기준인 partial 기본 제작 목표 completion 수에서는 A가 우세하다.
게임이 one-shot effects만 필요하다면 A의 이점은 0이므로 B를 먼저 고르는 것이 합리적이다.

## v0.0.22 설계 제안만: Deterministic Cyclic Emission

**최소 하나의 기능:** finite output에 대해 반복 period를 가진 steady cyclic births.
UI replay loop와 달리 frame 0부터 이전 cycle의 살아있는 particles도 존재한다.

- Model: `emission_cycle_mode = one_shot | cyclic_steady`, `emission_period_frames`
  positive integer (제안 1..512). 기존 burst/over_time/count/duration/start/delay를 유지.
  defaults는 one_shot. normalized birth span이 period 밖에 걸치면 명시적으로 거절한다.
- UI: Emission group에 mode, period; 예상 active-copy count와 validation 메시지.
  cyclic_steady는 prewarm 포함 의미를 tooltip에 명시. 기존 controls가 rate라고 오인되지 않도록
  “Total particles per cycle” 설명. cyclic 대상은 static/local analytic settings가 최소 범위다.
- Renderer: 동일 seed로 기존 spawn slots를 한번 구축하고, 요청 frame에 살아있는
  cycle copies만 birth=slot_birth+k*period로 열거한다. 과거 state를 재생하지 않는다.
  per-copy actual age를 기존 G/D/N/lifetime/source-frame evaluator에 전달한다.
  start_frame은 cycle 시작 gate이며 steady mode에서는 gate에서 이미 살아있는 copies를 포함.
- Seed/identity: cyclic pattern의 같은 slot은 매 cycle 동일 샘플/Noise salt를 사용한다.
  generation/depth sort는 `(cycle index, slot index)`로 stable; canonical slot seed와 cycle-copy
  identity는 구분한다. 매 cycle 새 난수를 뽑으면 exact tile 계약이 깨지므로 최소 범위에서 제외.
  one_shot disabled 경로는 기존 birth/ID/RNG 순서와 픽셀이 bit-exact여야 한다.
- Periodicity: slot age와 birth copies가 wrap되어 static system에서 F(t+P)=F(t).
  last PNG와 first PNG가 같아야 한다는 뜻은 아니다 (서로 인접한 다른 시간이다).
  자동 반복 보증은 output length가 P의 배수일 때만. global transform/motion tracks가
  period와 맞지 않으면 경고/보증 제외; 임의 global keyframes까지 seamless로 바꾸지 않는다.
- Bounds: count×(ceil(max lifetime/period)+2) 등의 보수적 upper bound를 검증하고
  active copy limit 제안 4096을 넘는 조합은 validation error; 조용히 birth를 drop하지 않는다.
  lifetime/period 극단 조합과 count=0, lifetime=1을 test한다. 캐시 키에 mode/period 추가.
- Migration: 향후 채택 시 format 19 검토, legacy missing fields→one_shot,
  load 시 파일 재저장/덮어쓰기 없음. **이번 파일/버전은 여전히 format 18/v0.0.21**.
- Undo: resource_layer_settings payload의 두 fields로 기존 transaction 사용;
  한 조작 한 command, no-op/Inspector refresh는 command 없음. mode/period undo/redo 후
  spawn/base/playback cache invalidate와 adapters sync; generated layer만 dirty하는 오류 방지.
- Save/reload: compact persistent settings 보존; generated pixels를 유일한 진실로 삼지 않음.
  save→load→regenerate bit-exact. source art, layers, hierarchy는 기존 계약 유지.
- Preview/export: current-frame/full sequence/materialize/export 동일 evaluator.
  pixel clipping/PNG canvas/fps는 그대로. Sprite Sheet/metadata는 이번 범위 밖.
- Performance: period가 짧아질 때 copies 증가를 먼저 계측; 100/500/1000 instances,
  P=1/12/24, lifetimes 1/24/96; cold seek 및 warm median 비교, counts와 machine조건 명시.
  prebuffer로 correctness/per-frame throughput 문제를 숨기지 않는다.
- Tests: legacy disabled bit-exact, F(t+P)=F(t), random/reverse/direct seek, prewarm active count,
  scheduled burst/over_time+delay, seed cross-process, G/D/N all combinations,
  scale/color/opacity/Additive, 2.5D/parent/depth, nonperiodic tracks warning,
  roundtrip old defaults, Undo/noop/cache invalidation, materialize/decoded PNG parity,
  bounds/zero/extremes/finite rejection, full regression. Native GUI manual 별도 사용자 확인 필요.

제외: 신규 shapes/rate UI/multiple-burst editor, free infinite streaming simulation,
new noise forces, force stack, collision, sub-emitter, trail/ribbon, multi-point curves,
palette, sprite sheet, renderer rewrite. 이 최소 범위도 구현 전 별도 승인/요청이 필요하다.

## 실제 diagnostic evidence

재현 가능한 `tools/recheck_effect_capabilities.py`를 repo에 남긴 이유는 10종의
구성/계약/산출물을 재실행해서 우선순위 판단을 검토할 수 있게 하기 위해서다.
production preset/menu/test-count 증가가 아니다. 새 output 경로를 요구해 기존
산출물 덮어쓰기를 막는다. 사용자 프로젝트/보호 PNG에 접근하지 않는다.

명령: `C:\Dev\pixel_effect_test_venv\Scripts\python.exe tools/recheck_effect_capabilities.py --output C:\Dev\pem_post_v21_recheck_20261001_b`

Evidence: 위 폴더의 `results.json`, `contact_sheet.png`, 10 fixture project JSON,
240 exported RGBA PNG. Contact sheet는 행이 matrix 순서, 열이 frame 0/4/8/12/16/20.
이미지를 직접 확인했다. 작은 점/단순 arc의 합성 diagnostic이고 완성품 preset은 아니다.

| fixture | logical layers | first / last alpha pixels | peak | cold materialize ms (1회, reference 실행) |
| --- | --- | --- | --- | --- |
| Hit Spark | 1 | 9 / 0 | 59 | 43.946 |
| Explosion | 2 | 9 / 0 | 277 | 99.660 |
| Smoke Puff | 1 | 39 / 0 | 312 | 49.970 |
| Fire Ember | 1 | 4 / 6 | 31 | 40.010 |
| Magic Wisp | 1 | 60 / 0 | 60 | 19.850 |
| Projectile | 2 | 9 / 0 | 32 | 25.590 |
| Sword Slash | 1 | 973 / 0 | 973 | 10.490 |
| Area Dust | 1 | 12 / 59 | 60 | 43.310 |
| Ring Burst | 1 | 163 / 0 | 163 | 55.600 |
| Rain Snow | 1 | 9 / 51 | 55 | 39.740 |

수치는 특정 synthetic workload의 1회 측정이며 speedup/GUI latency를 주장하지 않는다.
10/10 rerender, random-order current frame, offscreen Inspector reconstruction,
settings preservation, save/reload/regenerate, full decoded PNG equality passed.
7 combinations: G+D, D+N, G+N, G+D+N, Scale+Color+Opacity, Additive+Color,
full stack: nonempty/seek exact/spawn RNG unchanged passed.
Boundary unequal 측정만으로 loop 불가능을 증명할 수는 없다. finite births와
previous-cycle evaluation 부재가 코드 근거이며 boundary density ramp는 보조 관측이다.

진단 작성 중 version symbol 오참조, 다른 fixture의 clip ID 혼동 2건을 수정했다.
production bug가 아닌 diagnostic 초안 문제다. 최초 미완료 출력 `_a`는 근거에서 제외하고
성공 출력 `_b`와 최종 재실행만 증거로 사용한다. 기존 파일을 삭제하지 않았다.

## 최종 재검증

| 최종 항목 | 결과 |
| --- | --- |
| full pytest | **1335 passed in 78.06s**, failures 0 |
| compileall app/tests/tools | exit 0 |
| `python -m app.main --version` | Pixel Effect Maker v0.0.21, exit 0 |
| imported FORMAT_VERSION | 18 |
| `python -m app.main --check` | exit 0 |
| `run_app.bat --check` + PIXEL_EFFECT_PYTHON override | exit 0 |
| diagnostic 최종 재실행 | exit 0; `C:\Dev\pem_post_v21_recheck_20261001_final` |
| 서로 다른 process의 fixture 픽셀 SHA256 | reference `_b`와 `_final` 10/10 일치 |
| final artifact | 10 fixture JSON, 240 sequence PNG + 1 contact sheet, results.json |
| Git | HEAD af9be4c948f3d3a09700478dc00dd2102196c2ab; staged 0; production diff 0 |
| audit working tree | 기존 audit 문서 수정 1 + 신규 보고서/diagnostic 2; 전부 unstaged/uncommitted |
| 보호 PNG | unchanged/untracked/unstaged, 시작과 동일 SHA256 |

처음 최종 CLI 재검증에서 `-m app`으로 잘못 호출하여 missing `app.__main__` 메시지가
발생했다. batch의 실제 진입점인 `-m app.main`으로 수정해 version/check를 독립 실행했고
모두 exit 0을 확인했다. 실패 호출을 성공 검증으로 계산하지 않았다.
direct/batch check는 sandbox의 AppData log 쓰기 권한 때문에 logging_unavailable
PermissionError warning을 출력했다. 진단 exit 0과 로그 파일 쓰기 제한은 별개이며,
logging/native GUI 동작을 검증했다고 주장하지 않는다. 권한/production 코드를 변경하지 않았다.
Tracked diff 및 신규 문서/스크립트 whitespace 검사도 통과했다.
Windows native GUI manual: **수행하지 않음**.

## 요청 120항목 completion index

다음 번호는 요청의 completion report 번호와 대응한다. 상세 의미와 근거는 위 각 절에 있다.

1. 시작 HEAD d0173ef799b6776ff7d9ebd98ceefd8ca3397bed.
2. 시작 staged0, modified46, Noise new5, 보호PNG1.
3. v0.0.21 유지.
4. FORMAT_VERSION18 유지.
5. baseline1335passed/80.16s.
6. checkpoint af9be4c948f3d3a09700478dc00dd2102196c2ab.
7. PNG와 이번 audit 변경은 stage 제외.
8. checkpoint 후 main ahead39; audit만 미커밋.
9. 이전 bottleneck은 Scale/Color/Additive/Natural Motion과 고급 표현.
10. Scale2point 완료, multi-point 남음.
11. RGB2point 완료, multi-stop 남음.
12. Particle Additive 완료, 모든 내부 layer의 범용 기능은 아님.
13. analytic Gravity 완료.
14. analytic Drag 완료.
15. deterministic positional Noise 완료.
16. point/line/box/circle.
17. total count min/max, 0..4096.
18. rate API 없음.
19. single burst 있음, schedule 없음.
20. fixed/radial_outward.
21. ±spread 있음.
22. point 지원.
23. line uniform 지원.
24. box filled XY 지원.
25. circle은 고정 반지름 원둘레/arc.
26. ring circumference 기존 지원, thickness 없음.
27. box area 지원, filled disk/mask/path 없음.
28. seed와 slot ID 재현, Noise RNG 소비 없음.
29. Scale start/end multiplier.
30. RGB start/end multiplier.
31. Alpha start/end.
32. Linear/Ease In/Ease Out/Ease In-Out.
33. 3+point 미구현.
34. midlife peak 직접 불가, clip/keyframe 우회.
35. multi-stop 미구현.
36. true trail 없음.
37. ribbon 없음.
38. particle history/afterimage 없음.
39. long/animated source sprite 우회.
40. Projectile/Slash/Magic/Hit path variants 영향.
41. birth child event 없음.
42. death child event 없음.
43. child emitter graph 없음.
44. fixed Start Frame layer 우회.
45. Explosion/Projectile reactive variants 영향.
46. Gravity는 local-Y acceleration 변위.
47. Drag는 base motion age 감쇠.
48. Noise는 smooth XY position.
49. force/turbulence integration 없음.
50. wind stack 없음, simple velocity 우회.
51. attractor/repulsor 없음.
52. Smoke/Magic/Fire/Area/Rain 고급 흐름 품질, basic blocker0.
53. Hit practical; peak/trail은 advanced gap.
54. Explosion practical; multi-stop/event는 advanced gap.
55. Smoke practical; bell-alpha/disk는 advanced gap.
56. Fire finite practical/sustained partial; cyclic primary, pulse secondary.
57. Magic Orbit practical/comet partial; trail primary, pulse/force secondary.
58. Projectile head+fixed impact practical/reactive partial; path/event gap.
59. Slash authored arc practical/generated ribbon partial; trail/curve gap.
60. Area finite practical/sustained partial; cyclic primary, alpha secondary.
61. Ring practical viaCircle; solid-ring art/annulus quality gap.
62. Rain finite practical/sustained partial; cyclic primary, collision optional.
63. optional 별도 fixture 없음.
64. A cyclic3target completion, shape만 추가하면0.
65. B basic unlock0, 5basic+2partial 개선.
66. C basic unlock0, 4개선, path variant2는 별도 집계.
67. D basic unlock0, 2개선.
68. E basic unlock0, 2basic+3partial 개선.
69. completion count A3/B0/C0/D0/E0, finite-render unlock은 전부0.
70. established-basic 개선 A0/B5/C4/D2/E2, partial 개선은 분리.
71. A bounded cyclic births/period/defaults/Inspector.
72. B normalized knot channels/editor/migration.
73. C sampling/stamps/geometry/depth.
74. D stable event graph/depth/cycle guards.
75. E force stack/space/integrator.
76. A cycle enumeration, C history 의존, D IDs, E integration 순서.
77. active cycle copies / trail samples / child fanout / force cost.
78. persistent additions은 향후 migration 필요, 지금18.
79. A controls2 중심, B knot/C geometry/D graph/E stack.
80. 기존 analytic evaluator 재사용, historyful rewrite 피함.
81. 1순위 A Deterministic Cyclic Emission.
82. Fire/Area/Rain sustained3 목표 completion.
83. count-duration finite만으로 prewarm/periodic birth 불가.
84. 같은3종의 sustained reusable variant, 새 visual family 아님.
85. 2순위 B multi-point lifetime.
86. 3순위 C trails/ribbon.
87. v0.0.22 Deterministic Cyclic Emission (제안만).
88. cyclic mode+period+steady previous-cycle alive copies.
89. rate/shapes/events/forces/trails/curves/rewrite 제외.
90. mode one_shot/cyclic_steady, period frames.
91. same slot samples per cycle, stable copy IDs, disabled exact.
92. Emission mode/period/active-count/validation tooltip.
93. time-pure bounded birth enumeration과 기존 age 평가.
94. 향후19 검토, legacy→one_shot, load 시 rewrite 없음.
95. resource_layer_settings 기존 transaction/noop/refresh 계약.
96. compact settings roundtrip→regenerate exact.
97. current/full/materialized/PNG 일치, periodic 계약은 별도.
98. active-copy cap/period-lifetime 극단값 benchmark.
99. legacy/seek/seed/period/lifetime/blend/2.5D/Undo/save/export 검증.
100. tools/recheck_effect_capabilities.py, C:/Dev evidence.
101. 10projects/240PNG/contact sheet 렌더 및 확인.
102. full pytest baseline 통과, 최종 결과는 재검증 절.
103. compileall exit0, 최종 결과는 재검증 절.
104. --version v0.0.21.
105. --check exit0, log 권한 warning 별도 기록.
106. run_app.bat --check exit0.
107. git diff --check exit0.
108. 최종HEAD af9be4c948f3d3a09700478dc00dd2102196c2ab.
109. 최종staged0.
110. audit commit 없음.
111. v0.0.22 production 구현 없음.
112. tag/push/build/PyInstaller/ZIP 없음.
113. Windows native GUI manual **수행하지 않음**.
114. 10 finite basic, 7개 지정 complete/3개 sustained partial.
115. sustained steady loops, path trails, reactive child, multi-peak 직접 편집.
116. 지정 basic completion은 cyclic emission3, 품질은 multi-point7.
117. G/D/N으로 ballistic/deceleration/wandering 제작 비용 감소.
118. 이번 목표 completion은 A3 최다, 품질 breadth는 B.
119. 이전 force-first 예상에서 emission-first로 변경.
120. v0.0.22는 Deterministic Cyclic Emission 하나만 권장.
