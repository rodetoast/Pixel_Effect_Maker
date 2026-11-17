# Aseprite-style Timing & Timeline Architecture Audit

2026-10-28. **설계 감사만 수행. 시간 계산/재생/저장 모델 구현0.**
현재 v0.0.25 / FORMAT22. UX-2의 UI-only 변경과 별개다.
코드가 확인된 사실과 아래 추천 설계를 구분한다. Native Windows GUI manual 수행하지 않음.

## 현재 소유권과 활성 경로

| 대상 | 실제 소유자 / 활성 코드 | 현재 의미 |
|---|---|---|
| Effect FPS | models/project.py:Project.fps, to_dict의 animation.fps | 1..120 정수, 프로젝트 저장 데이터 |
| Effect output 길이 | Project.frames; MainWindow._display_frame_count; ParticleEmitterSettings.output_frame_count | 문서 frame 수, 임시 preview 표시 길이, 각 emitter의 유한 출력 길이는 서로 다름 |
| Effect Frame | models/frame.py:Frame | id/name/layer_pixels, duration 필드 없음 |
| Resource FPS / 길이 | models/resource_composition.py:ResourceComposition.fps/frame_count/loop | Effect와 독립된 정수 FPS와 프레임 수, duration 배열 없음 |
| SourceAsset | models/source_asset.py | 정적 RGBA, FPS/프레임 지속 시간 소유자 아님 |
| AnimationClipAsset | models/animation_clip.py | fps, frame_durations_ms, loop/playback_mode, tags; per-source duration은 이미 존재 |
| Source import | services/resource_import_service.py | GIF의 frame duration을 ms 배열에 보존, 평균에서 fps 추정. 원본 exact FPS 계약은 아님 |
| Aseprite bridge | services/aseprite_import_service.py:import_aseprite | CLI로 임시 GIF를 만든 뒤 위 importer 사용. 원본 path/format/name을 설정 |
| Asset preview | ui/resource_editor_v2/asset_inspector_widget.py:asset_durations | clip ms 배열 사용, ResourceEditorWidget._advance에서 프레임별 timer interval |
| Resource preview | ResourceEditorWidget.toggle_play/_advance | composition은 round(1000/fps) timer로 매 tick 한 frame; source GIF preview와 다른 경로 |
| Resource source sampling | services/resource_composition_render_service.py:_pixels_at/_clip_index | local frame→local*1000/composition.fps→source duration 누적 경계; source once/hold/loop |
| Resource materialization | composition_as_clip | 각 Resource frame을 생성, clip에 반올림된 uniform ms 배열. source_format=composition |
| Particle sprite sampling | services/particle_render_service.py:particle_clip_frame_index | composition은 floor(age/effect_fps*clip.fps*speed)+start; 일반 clip은 age/FPS 기반 ms와 duration 배열 |
| Effect exact rendering | services/effect_playback_service.py:render_exact_playback_frame | 요청 integer frame의 정확한 RGBA를 만드는 서비스. variable-duration scheduler가 아님 |
| Effect scheduler | MainWindow.set_playing/_advance_playback | 준비 완료 뒤 timer/clock 시작. full-prebuffer는 tick마다 1frame, 다른 경로는 elapsed*FPS와 drop 집계 |
| Generated materialization | effect_resource_layer_render_service.py:apply_effect_resource_layer_current_frame | 필요하면 Project.add_frame으로 확장하고 generated pixels 기록. timing 소유자로 삼으면 안 됨 |
| PNG export | services/export_service.py:export_png_frames, preview_export_service.py | 순번 PNG만 저장, frame duration/FPS sidecar 없음 |
| Save/Load | Project.to_dict/from_dict, project_io.py; AnimationClipAsset.to_dict/from_dict | project FPS, composition FPS, clip ms를 구별해 직렬화. FORMAT22에는 output duration 모델 없음 |

### A–J에 대한 답

**A/B.** Project/ResourceComposition/AnimationClipAsset에 각자의 FPS가 있다. Resource와 Effect는
독립 timebase이며, source를 샘플링할 때 명시적으로 변환한다. 모든 FPS를 하나로 합치면 안 된다.

**C.** 원본 Aseprite JSON/ase frame metadata를 직접 읽지 않는다. 임시 GIF에서 얻은 duration까지만
전달된다. 따라서 GIF 변환의 시간 양자화 가능성이 있으며 원본 ms, tags/방향/셀 구조의 exact 보존을
현재 지원한다고 주장할 수 없다. tags 모델 필드는 존재하지만 이 bridge는 원본 tag를 채우지 않는다.
Frame duration 정보를 전혀 지원하지 않는다는 과거 일반화도 부정확하다: **imported clip은 이미 지원**한다.

**D.** Effect table은 SingleSelection/SelectItems. current frame/cell과 logical layer selection은
별도이고, TimelineKeySelection은 (layer/property/frame) identity의 custom set/anchor/primary다.
Ctrl/Shift/marquee/Alt-duplicate는 key 또는 layer 문맥에서 동작한다. 이는 frame-header 다중 선택이 아니다.
Resource CompositionTimeline도 custom key selection과 logical layer selection을 구별한다.

**E.** 새 출력 duration은 Project/ResourceComposition이 소유한 **논리적 TimelineTiming**을 추천한다.
출력 schedule을 Generated pixels, ParticleInstance, SourceAsset 또는 view preference에 넣지 않는다.
Project의 Frame ID는 편집 identity로 활용할 수 있지만 generated 재생성이 시간 데이터를 소유하면 안 된다.
Resource에는 frame 객체 배열이 없으므로 별도 duration schedule이 특히 필요하다.

**F.** Parent/System/Surface tracks와 easing은 Effect integer frame, Resource tracks는 resource frame,
Particle birth/death/cyclic/Trail은 birth와 age/lifetime frame, Motion track은 absolute effect frame을 사용한다.
정규화 Lifetime point는 particle age 축이다. Sub-emitter는 Birth B / Death B+L, origin age L-1 계약이다.
source clip 선택에만 FPS/ms 변환이 있으며 이것을 simulation time으로 확대 해석하지 않는다.

**G.** 가능하다. Mode A는 scheduler가 Frame N을 보여주는 시간만 바꾸고 모든 렌더 entrypoint에
같은 N/기존 sampling FPS를 넘긴다. prefix-duration lookup 결과를 simulation age에 넣지 않는다.
Mode B(실제 ms 기반 물리/이벤트)는 별도의 schema/RNG/seek/periodicity 계약이 필요한 큰 기능이다.

**H.** Current/Full/raw Generated RGBA 계산은 Mode A에서 바뀌지 않는다. Playback의 준비 구간,
두 advance 경로, loop/once 종료, 시작 frame offset, elapsed/drop 집계와 status에는 schedule이 필요하다.
Generated frame append는 duration fallback을 명시하고 기존 override를 보존해야 한다.
PNG pixels는 같지만 정확한 전달에는 timing sidecar가 필요하다. Resource preview와 source clip preview를
각각 다뤄야 하며 full-prebuffer 분기를 놓치면 uniform timer 경로만 남는 결함이 생긴다.

**I.** 원칙적으로 가능하다. 구버전 FPS를 그대로 보관하고 duration override가 없는 exact uniform
schedule로 읽는다. v22 재저장은 이번 작업에서 그대로다. Timing-2의 새 필드 저장에는 새 FORMAT이 필요하며,
구버전 앱이 이를 읽고 duration을 유실하는 down-save를 허용하지 않는다. v22 export는 명시적 손실 확인이 필요하다.
과거 clip constructor가 이미 round(1000/fps)로 만든 duration은 provenance가 없어 원래 정확한 속도를
역추론할 수 없다. 그 legacy 배열은 임의로 고치지 않고 그대로 보존해야 한다.

**J.** frame-header selection을 새로운 별도 state로 만들면 가능하다. key set을 frame selection으로
재사용하지 않는다. 기존 copy/paste/move/Alt-duplicate/nudge/easing/snap과 clipboard context를 보존한다.

## 추천 시간 표현 (미구현)

비교:

| 안 | 장점 | 단점 / 판정 |
|---|---|---|
| 모든 frame을 integer ms로 변환 | 단순, Aseprite식 입력 | 24/30/60 FPS exact 보존 실패. legacy 자동 변환으로 부적합 |
| float seconds 누적 | 표현 간단 | 누적 오차/경계/직렬화 비교 불명확. authoritative clock으로 비추천 |
| exact uniform FPS + rational-ms overrides | legacy FPS exact, 새 ms 입력 exact, % scale도 exact | rational validation/prefix lookup 필요. **추천** |

예상 TimelineTiming: `uniform_rate={numerator:fps, denominator:1}` + sparse frame overrides의
`duration_ms={numerator:n, denominator:d}`(양수, gcd 정규화). override 없음은 정확히 1000/fps ms다.
24=125/3ms, 30=100/3ms, 60=50/3ms. UI의 41.667/33.333/16.667은 표시값이지 저장값이 아니다.
Uniform FPS를 integer ms로 바꾼 후 legacy FPS 필드에 역산해 저장하지 않는다.
표시 preference `ms/frame` 기본 / `FPS` 선택은 QSettings: Project Dirty0/Undo0/renderer invalidation0.
Per-frame 상태에서 FPS는 frame별 1000/d 또는 평균임을 명시하고, 하나의 전역 FPS인 척 편집하지 않는다.

Prefix S0=0, S(n+1)=S(n)+d(n), 반개구간 [S(n),S(n+1)). monotonic clock 경과와 시작 offset을
더해 binary search하고 loop일 때만 total duration modulo. 마지막 frame hold가 끝난 뒤 once 정지.
QTimer는 wake-up 알림일 뿐 authoritative time이 아니다. 절대 deadline으로 다음 tick을 예약해
round(ms) 누적 drift를 막는다. pixel key와 timing revision/plan key를 분리해야 한다.
현재 전역 _project_edit_revision을 그대로 쓰면 duration edit이 pixels까지 invalidate할 수 있으므로
Timing-2에서 timing-only command/invalidation 경로를 명시적으로 분리한다.

## Per-frame / bulk 조작 계약 제안

- Frame Properties: 정수 ms 입력 1..65535. 이 범위는 **제안하는 PEM 제한**이며 기존/Aseprite validation
  범위를 같다고 단정한 것이 아니다. nonfinite/0/음수/범위 밖은 거부, clamp로 숨기지 않는다.
- Set Duration for Selected Frames: frame-header selection snapshot 전체를 atomic 적용, Undo1.
- Scale Duration(%): 1..10000%, rational로 정확히 곱한 결과를 저장. 모든 결과가 위 범위 내인지 먼저 검사,
  하나라도 실패하면 Undo0. UI 소수 표시의 반올림을 저장으로 돌려 쓰지 않는다.
- Set Uniform Duration: 전체 논리 frame schedule에 exact integer-ms 적용; Undo1. Uniform FPS 편집은
  정확한 rate 변경이며 override를 지울지 유지할지 별도 명시 확인 후 한 transaction.
- Insert: 직전 frame duration 상속, 처음 삽입은 다음 frame, 빈 문서는 exact uniform fallback.
- Duplicate: duration 포함 복사. Delete: 해당 duration 제거, 최소1frame 보호.
- Reorder: duration과 frame content identity를 함께 이동. raw cel만 움직이는 경우 duration은 column에 남김.
- Generated append/preview extension: 새 논리 frame만 uniform fallback. 기존 schedule/ID를 덮어쓰지 않는다.
  임시 preview 범위 확장은 view-only이며 문서 schedule을 자동 확장하지 않는다.
- Save/Reload: rational normalized equality, override 길이/참조 검증, legacy uniform fallback.
- Resource/Effect 각각 schedule, loop duration=sum(durations). 같은 frame 수라도 총 시간이 다를 수 있다.
- Export sidecar: exact numerator/denominator, frame order/name, loop/size/pivot 포함. PNG 단독은 무시간 이미지다.

Resource output hold와 **Effect에서 Resource를 source로 샘플링하는 방식**은 별개의 계약이다.
최소 Mode A에서는 기존 composition source의 floor(FPS ratio) 샘플링을 유지해야 Effect Frame N RGBA가 같다.
따라서 Resource hold 변경을 Effect source에 자동 전파하면 안 된다. Timing-2 UI에서 이 차이를 명시하고,
향후 `honor_source_schedule` 같은 명시적 source sampling opt-in은 별도 승인/픽셀 변화 테스트로 분리한다.
현재 composition_as_clip에 duration을 넣기만 해서는 particle의 composition fast path가 이를 소비하지 않는다.
Imported Aseprite clip exact-ms 전달 개선도 output hold와 분리한 Source Timing 후속 과제다.

## 공식 Aseprite 비교 근거

공식 [Frame Duration](https://www.aseprite.org/docs/frame-duration/)은 현재 frame 및 선택 frame 범위의
Properties 편집을 설명한다. [Timeline](https://www.aseprite.org/docs/timeline/)은 layer/frame/cel을 구별하고
태그·loop 구간·문서 간 복사를 다룬다. [Copy Frames](https://www.aseprite.org/docs/copy-frames/)는 선택 경계의
Ctrl/Alt drag 복사와 문서 끝 확장을 설명한다. [Animation](https://www.aseprite.org/docs/animation/)은 frame 탐색,
재생과 태그/역순 등의 작업 입구를 제공한다. 공식 문서 확인일 2026-10-28. PEM과 단축키가 같다고 주장하지 않는다.
Onion Skin은 [공식 문서](https://www.aseprite.org/docs/onion-skinning/)의 별도 기능이며 timeline ghost key와 다르다.

| 경험 | 현재 PEM 상태 | 차이 / 후속 interaction |
|---|---|---|
| Frame selection/range | Partially supported | current frame/scrub 있음, header multi-frame range state 없음 |
| Shift/Ctrl selection | Different semantics by design | layer/key selection에 사용. header에만 새 frame selection 도입 |
| Frame Properties | Missing | ms dialog 없음; frame header context로 도입 |
| Per-frame ms | Partially supported | imported AnimationClipAsset만 보유; Project/Composition 출력 duration 없음 |
| Bulk duration | Missing | selected/all/scale atomic command 필요 |
| Insert/delete/duplicate | Partially supported | Effect Project 현재 frame 명령 있음; Resource는 frame_count 중심. multi-frame ripple 미구현 |
| Copy/paste | Different semantics by design | multi-key clipboard와 layer duplicate 있음; Aseprite frame/cel block 복사와 다름 |
| Drag/reorder | Partially supported | key/Layer reorder 있음, frame block reorder 없음 |
| Loop/playback direction | Partially supported | full loop/once/step 있음. tag loop/reverse/ping-pong 없음 |
| Zoom/scroll | Already supported | Timeline frame cell width/zoom/pan/fit/reveal; 가변 ms여도 index grid 기본 유지 |
| Playback/navigation shortcuts | Already supported | 기존 context-aware shortcut 유지; Aseprite 배치를 무조건 복사하지 않음 |
| Tags/named ranges | Missing | clip tags 필드가 Effect/Resource timeline 편집 UI 지원을 뜻하지 않음 |
| Onion Skin | Missing | preview guide/overscan과 다름; 별도 editor-only overlay |
| Cell/keyframe distinction | Different semantics by design | raster frame/cell과 procedural property key를 별도 layer/track 행으로 유지 |

추천 interaction: header click=current frame, header Shift=frame range, header Ctrl=toggle(후속 spec),
property row key click=기존 multi-key. 활성 selection domain을 명시하고 Delete/Copy/Paste는 그 domain만 처리한다.
frame-header context에는 Frame Properties/Set Duration/Scale/Insert/Duplicate/Delete를 두고,
key context에는 기존 Key Copy/Paste/Delete/Easing을 유지한다. 같은 drag가 key와 frame을 동시에 이동시키면 안 된다.
Frame reorder의 key/Particle start/end shift는 현재 frame 명령과 별개이므로 ripple 규칙을 먼저 승인한다.
Mode A duration만 바꾸는 작업은 key index/particle birth를 옮기지 않는다.

## 분리된 구현 Roadmap (이번에 구현하지 않음)

| 단계 | 실제 변경 예상 파일 / 소유권 | Schema | 테스트 / native 위험 |
|---|---|---|---|
| Timing-1 ms 기본 표시/FPS 선호 | settings_service/localization_service, interface_settings_dialog, new_project_dialog, project_settings_dialog, resource_editor_v2/new_resource_dialog/composition_inspector, Timeline status | preference만, FORMAT 유지 | 24/30/60 exact roundtrip, preference Undo/dirty/cache0, IME/locale/단위 오해 |
| Timing-2 duration+bulk | 새 models/timeline_timing.py, project/frame/resource_composition, project_io, undo_commands, MainWindow 두 playback branch, resource_editor_widget, effect_playback_service, composition_as_clip, exporter metadata | Project/Resource output schedule 새 FORMAT 필요. 현22는 변경 없음 | migration/rational/bounds/atomic Undo1/Save/Reload/loop/large seek/full-prebuffer/current/full/generated/PNG RGBA exact; timer jitter/길게 hold/재생 중 편집 |
| Timeline-UX | 새 frame-selection state와 commands, timeline_widget/composition_timeline, timeline_scrub_controller, frame_shortcut_controller/shortcuts/localization | frame view selection은 비영속. tags/named ranges는 별도 persistence 승인 | header vs key priority, clipboard domain, reorder conflicts/ripple, key easing/Alt duplicate/lock/group/parent; drag/trackpad/IME/단축키 충돌 |

Timeline-UX 우선순위: (1) header selection+Frame Properties, (2) bulk duration+frame actions,
(3) frame drag/ripple spec와 명시적 transaction, (4) tag/loop ranges, (5) onion skin 및 playback direction.
Source Timing은 Aseprite JSON/직접 metadata import와 composition sampling opt-in을 별도 계획으로 둔다.
기존 Multi-Key suite와 deterministic render/pixel goldens를 통과하지 못하면 그 단계는 완료가 아니다.
이번 변경에는 새 timing model, FPS/ms preference UI, timer/재생/serialization/export 수정이 없다.
