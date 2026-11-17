# UX-2 — Particle Inspector Information Architecture

> 후속 Native GUI Corrections / Visual Quality 보정은
> [별도 보고](UX2_NATIVE_GUI_CORRECTIONS_REPORT.md)를 참조한다.
> 아래 수치와 미실행 native 경계는 최초 UX-2 시점의 이력이다.

## 1. Baseline / UX-1 Checkpoint

2026-10-28, 실제 작업 루트 `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`.
UI_UX_ARCHITECTURE_AUDIT / UI_UX_PRINCIPLES / UX1_INSPECTOR_FOUNDATION /
POST_V0_0_25_EFFECT_CAPABILITY_RECHECK / EFFECT_AUTHORING_CAPABILITY_AUDIT의 실제 파일과
활성 Particle panel, TransformPanel, PointEditor, MainWindow와 관련 테스트를 대조했다.
과거 문서의 disclosure0/기존 순서는 UX-1 이전 이력이다. 이번 baseline은 Trail/Sub pilot이 적용된 상태다.

시작 HEAD `d5aaad2c7787c86b6f7d969fec6bc3547ca3fb1d`, main ahead45,
v0.0.25 / FORMAT22 / staged0, UX-1 6개 파일만 미커밋 상태였다.
최초 요청 명령 baseline은 1725 passed / 8 failed / 28 errors:
과거 렌더러를 읽는 git show subprocess가 현재 사용자와 저장소 소유자 차이로 거부된 결과다.
사용자/시스템 Git config나 소유권을 바꾸지 않고, 테스트 프로세스에만
GIT_CONFIG_COUNT=1, KEY_0=safe.directory, VALUE_0=이 프로젝트 정확한 경로를 넘겼다.
이 조건의 baseline은 **1761 passed, 1 warning in 118.76s**,
`C:\Dev\pem_ux2_baseline_verified`. warning은 기존 .pytest_cache ACL 쓰기 제한이다.

실제 diff/신규 구현과 테스트를 확인하고 승인된 6개만 explicit stage하여
`Add reusable inspector UI foundation` local checkpoint를 만들었다.
**`ca9ed1c287022a653b96c2d75f81ea737b94d5f1`**.
직후 staged0, main ahead46, 보호 PNG만 untracked. UX-2 변경은 이 commit에 포함되지 않는다.

## 2. UX-2 구현 및 실제 Inspector 구조

`particle_inspector_workflow.py`는 UI layout/navigation만 소유한다. 기존 editor를
reparent/takeRow하여 이동하며 각 value/signal/command는 ParticlePropertiesPanel에 남긴다.
Random Range를 의미별로 분리하고 기존 translation/tooltip registry도 같은 label/editor를 가리킨다.

| Category | 실제 기존 editor 위치 |
|---|---|
| Source | Clip/Resource, Clip Speed Min/Max, Random Start, Refresh/Bake/Export Preview/Revert |
| Emit | Count/Mode/Duration/Cyclic/Period, Output/Start Frames, Spawn Shape/Origin/상세, Direction/Speed, Delay/Lifetime 범위, Seed/Randomize |
| Motion | Linear/Orbit/Helix 및 기존 조건부 groups/key controls, Angular Velocity, Gravity/Drag/Noise |
| Lifetime / Look | 초기 Scale/Rotation 범위와 기존 Scale/Opacity/RGB LifetimePointEditor |
| Trail | UX-1 Section과 기존 enable/detail/safety/editor 신호 그대로 |
| Events | UX-1 Sub-emitter Section과 Birth/Death/Target. 실제 header 이름은 기존 Sub-emitter/하위 방출기 유지, nav는 Events/이벤트 |
| Rendering | 기존 Normal/Additive selector |
| Transform / Advanced | 기존 Name/Parent/Placement, ResourceLayerTransformPanel 전체와 별도 접기 Surface Compatibility |

기존 hidden endpoint adapters는 계속 숨겨진 같은 widget으로 보존했다. 입력을 복제하지 않았다.
Advanced check는 여전히 bypass feature이며 새 outer disclosure/surface disclosure와 독립적이다.
System/Surface/animated 상태는 Transform summary에 파생 표시한다. PointEditor의 age 축과
Motion/Layer Timeline key 축을 통합하지 않았다. Global Export 및 다른 workspace layout은 유지한다.

## 3. Navigation / Disclosure / View State

QScrollArea 상단 viewport margin 안의 고정 navigation은 Layer 이름/Particle 타입/Parent와
Category combo, Property search/results, 중요한 warning의 개수·위치 combo를 제공한다.
search는 EN alias + KO 번역/현재 label/기존 tooltip을 검색해 **같은 editor 객체**를 reveal한다.
새 shortcut은 없다. Jump는 범주를 열고 해당 control로 scroll/focus한다.

Source/Emit만 기본 펼침. 나머지는 접힘, 서로 배타적이지 않다.
UX-1 ViewState를 `(particle, stable selection ID, section ID)`로 재사용하고 세션 scroll 위치도 기억한다.
선택 A→B→A로 category를 복원하며 Project JSON/Undo/QSettings에는 쓰지 않는다.

Point/Line/Box/Circle 무관 상세, OFF Gravity/Drag/Noise, OFF Scale/RGB editor,
OFF Cycle Period는 label+editor row 전체를 숨긴다. Trail/Events의 OFF 값 보존도 유지한다.
명시적 검색은 OFF 상세의 기존 disabled editor를 일시적으로 보여줄 수 있다. enable은 자동 변경하지 않고
사용하려면 켜라는 local 안내를 보인다. 이 reveal 예외는 다음 selection까지의 UI state다.
Linear의 Orbit/Helix 상세는 기존 mode 조건부 표시를 유지하며 명시적 검색 reveal도 지원한다.

정상 bounded-cost status는 info이며 중요한 오류 개수로 부풀리지 않는다.
Cycle/Trail/Sub/PointEditor 거부는 local 설명과 closed category badge/상단 warning 입구를 유지한다.
View API가 미확정 숫자를 숨기거나 다른 control로 이동시키려 하면 보류하고 안내한다.
Qt의 기존 mouse/Tab focus-out이 먼저 확정한 accepted numeric edit의 Undo1은 그대로다.
Disclosure 자체가 새 command를 만들거나 numeric commit을 가로채지는 않는다.

## 4. Aseprite Timing & Timeline Architecture Findings

별도 `ASEPRITE_TIMING_TIMELINE_ARCHITECTURE_AUDIT.md`에 A–J, time owner/consumer,
per-frame/bulk/reorder/legacy migration/Mode A·B, 14행 Gap Matrix와 세 단계 roadmap을 작성했다.

- Project FPS, Resource FPS, imported AnimationClipAsset의 ms 배열은 이미 서로 다른 owner다.
- Aseprite import는 현재 CLI→GIF→clip이다. 원본 frame ms/tags/cel metadata의 exact 전달이 아니다.
- 추천은 exact uniform FPS + rational-ms override. 24/30/60 FPS를 integer ms로 반올림 저장하지 않는다.
- 우선 Frame Hold Mode A: Frame N의 Particle/Key/Trail/Sub RGBA를 그대로 두고 표시 시간만 변경.
- Imported source timing/Resource-as-source sampling opt-in은 output hold와 별도로 정의해야 한다.
- Timing-1 표시 preference, Timing-2 persistent duration/bulk/playback/export,
  Timeline-UX frame-header selection/Properties/reorder를 별도 구현 단계로 제안했다.

이번에는 ms/FPS 전환 UI, timing dataclass/schema, timer/재생/저장/PNG exporter를 구현하지 않았다.
공식 Aseprite 기능 근거와 코드 근거는 별도 audit에 링크했다.

## 5. Tests / Layout / Performance

새 `test_particle_inspector_workflow.py` 24개:
8 category 순서, 기존 registry editor 단일 identity와 접근 가능성,
collapse/jump/search model·Undo·dirty·revision0, A→B→A,
OFF 보존/disabled reveal, pending numeric 보류, closed warning/Surface 상태,
EN/KO × 280/320/360 × font100/125/150%, pinned navigation과 실제 body 최소 높이를 검증한다.
기존 구조 테스트는 삭제하지 않고 새 범주 순서·명시적 펼치기·OFF row 계약으로 갱신했다.

기존 `audit_editor_ux.py`를 재사용했다. navigation은 scrolling body의 형제가 되었으므로
가로 bounds 좌표 owner만 구별하도록 보완했다. Before
`C:\Dev\pem_ux2_before_20261028\inventory.json`, final
`C:\Dev\pem_ux2_inventory_complete\inventory.json`: 36조건/14panels, 가로 bounds flag0.
추가 `audit_particle_workflow.py`의 final evidence는
`C:\Dev\pem_ux2_workflow_complete\workflow.json`이다.
이는 36조건별 initial metrics, category 펼침 높이, 3회 jump/selection roundtrip median,
1024/1280/1600×Group/Single/Particle의 9개 shell 결과를 기록한다.
모든 output은 repo 밖 합성 데이터이며 사용자 project/artwork를 읽지 않았다.

320px / Malgun Gothic 9pt / 100% 기본 펼침 상태 비교:

| 조건 | 전체 content height before→after | layout-visible controls | viewport-intersecting controls |
|---|---|---|---|
| EN Linear OFF | 6235→2439 | 133→39 | 10→12 |
| EN Helix ON | 7841→2455 | 160→39 | 10→12 |
| KO Linear OFF | 6245→2375 | 133→39 | 10→13 |
| KO Helix ON | 7851→2391 | 160→39 | 10→13 |

nav 높이는 이 조건에서92px이며 nav control은 viewport-intersecting 값에 포함하지 않는다.
39개는 스크롤 밖을 포함한 logical controls이며 39개가 첫 화면에 모두 보인다는 뜻이 아니다.
기본 접힘 조건이 달라졌으므로 단순 height 감소를 성능/UX 점수로 쓰지 않는다.

KO Helix ON/320/100%의 category별 펼침 높이(px): Source426, Emit1404, Motion1980,
Look1300, Trail306, Events310, Rendering188, Transform1268(Surface는 별도 접힘).
Motion/Emit을 펼치면 여전히 길다. 복수 범주를 전부 열면 property wall이 다시 길어질 수 있으며
검색/Jump와 명시적 view state가 탐색을 보완한다. 네이티브 사용자 승인으로 해석하지 않는다.

36조건의 jump median 범위 **2.058–4.301ms**, 선택 A→B→A roundtrip median
**13.718–27.285ms**. 3회씩 합성/로컬/offscreen, 전체 회귀와 병행한 수치이며
native latency/p95/renderer throughput이나 이전 버전 대비 speedup이 아니다.
main window9조건은 요청 width를 유지하며 Group/Single/Particle에 맞는 기존 stack이 선택됐다.
스크린샷의 320px KO/font150%를 직접 확인했다. 최초 점검에서 한글 narrow label 세로 쪼개짐을
발견해 이동된 label의 최소 폭을 보완했다. 이후 펼친 body 압축도 최소 높이 계약/테스트로 수정했다.

최소10개 탐색 경로(실마우스 click count 아님):

| 작업 | UX-1 위치 | UX-2 탐색 경로 |
|---|---|---|
| Count | Emission, 상부 scroll | Jump Emit / Search Count→동일 Min/Max |
| Cyclic | Emission/period | Jump Emit / Search Cycle Period→원래 row |
| Gravity | 깊은 Natural Motion | Jump Motion / Search Gravity Strength |
| Noise | 깊은 Natural Motion | Jump Motion / Search Noise |
| Trail | 깊은 Trail | Jump Trail→enable/detail, closed summary 유지 |
| Color Lifetime | 깊은 Over Lifetime | Jump Look / Search Color→기존 PointEditor |
| Sub-emitter | 깊은 Sub-emitter | Jump Events / Search Birth/Death→stable-ID Target |
| Parent | 상부 Resource Layer | Jump Transform / Search Parent→원래 combo |
| Blend | 깊은 Rendering | Jump Rendering / Search Blend Mode |
| Export | Global Export 또는 최하단 footer | 기존 Global Export 유지 / Search Export→Source의 원래 Preview Export |

OFF 검색 reveal은 feature를 자동으로 켜지 않으므로 실제 편집에는 enable 조작이 따로 필요하다.

## 6. Regression / Compatibility

최종 full suite: **1785 passed, 1 warning in 158.11s (0:02:38)**,
`--basetemp=C:\Dev\pem_ux2_final_complete --tb=short`.
최종 run은 summary/실제 body 높이 보완을 포함한 뒤 다시 실행했다.
기존 frozen pixel tests 및 numeric Enter/Tab/focus-out/Ctrl-wheel/Revolution,
Lifetime point/color cancel, Trail/Sub reference/Undo, parenting/Keep World/lock/solo/group/multi,
Auto-Key/save/reload 회귀가 전체 suite에 포함된다. 새로운 renderer를 mock하지 않았다.
Model/RNG/Direct Seek/Cyclic/GDN/curves/Trail/Sub/Parent/System/Surface/2.5D/PNG dimensions와
serialization production 파일 변경0. v0.0.25 / FORMAT22 유지.
compileall app/tests/tools, direct --check, 지정 interpreter의 run_app.bat --check, diff --check 통과.
현재 direct/batch --check는 각각 exit0/경고 출력 없음. 실제 설치 GUI 수동 검증을 뜻하지 않는다.
pytest warning은 기존 .pytest_cache ACL이며 권한/소유권을 수정하지 않았다.

## 7. Git / Native Windows Manual Boundary

UX-1 checkpoint 이후 변경 파일:

- app/ui/inspector_components.py, app/ui/particle_properties_panel.py,
  새 app/ui/particle_inspector_workflow.py
- tests/test_2_5d_inspector_architecture.py, test_effect_inspector_responsive_layout.py,
  test_inspector_components.py, test_particle_motion_gizmo.py,
  test_particle_sub_emitter_ui.py, test_particle_trail_ui.py,
  새 test_particle_inspector_workflow.py
- tools/audit_editor_ux.py, 새 tools/audit_particle_workflow.py
- docs/UI_UX_PRINCIPLES.md, 본 문서, 새 ASEPRITE_TIMING_TIMELINE_ARCHITECTURE_AUDIT.md

모두 **unstaged/uncommitted**, staged0, main ahead46. HEAD는 위 UX-1 checkpoint.
기존 capability/UX audit 이력은 보존했고 UX-2 commit/tag/push/build/PyInstaller/ZIP/release는 하지 않았다.
보호 테스트소스.png는 untracked 그대로, SHA256
8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564 일치.

**Windows native GUI manual: 수행하지 않음.** offscreen font scaling은 실모니터 DPI QA가 아니다.
native IME/mouse/keyboard feel/dropdown/high contrast/실제 사용자 탐색 속도는 후속 승인 대상이다.
