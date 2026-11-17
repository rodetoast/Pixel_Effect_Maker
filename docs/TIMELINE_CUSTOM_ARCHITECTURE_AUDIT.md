# TIMELINE-ARCH — Custom Timeline Architecture & Interaction Design

2026-10-30. **읽기 전용 아키텍처 감사 완료. 아래 새 클래스·조작·테스트는 제안이며 구현되지 않았다.**

## 0. 기준, 승인, 감사 범위

- 실제 HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`, v0.0.25 / FORMAT22, staged 0. 기존 UX-2/FPS/DevEx 및 회귀 수정은 미커밋 상태로 보존한다.
- `AGENTS.md`, `docs/tasks/WORK_QUEUE.md`, `ASEPRITE_TIMING_TIMELINE_ARCHITECTURE_AUDIT.md`, `UX2_CHECKPOINT_FILE_MANIFEST.md`, `UI_UX_PRINCIPLES.md`, `ROADMAP.md`를 기준으로 활성 코드를 추적했다. 과거 ROADMAP 버전보다 실제 코드/현재 queue를 우선한다.
- 사용자 Native QA: **Lifetime / Group / Gizmo / 한글 UI 정상 확인**. 이것이 모든 DPI/IME/테마/입력 장치 조합의 승인은 아니다.
- **Resource→Effect 회전 재생은 사용자 문제 확인, 미해결**. 자동 `TIMING-FPS-PLAYBACK` 완료와 구별한다. `TIMING-ROTATION-USER`, `TIMING-FPS-CHECKPOINT`는 BLOCKED. CP2와 이를 선행으로 요구하는 checkpoint는 승인하지 않는다.
- 보호 `테스트소스.png` SHA-256: `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`.
- 이번 변경은 이 문서와 WORK_QUEUE뿐이다. Production/테스트/도구 구현, 모델/FORMAT/버전/수학/Undo 수정, UI 제거, Git 설정·권한 변경 없음. Window Use 0.

표기: **현재**는 코드에서 확인한 사실, **제안**은 후속 승인 대상, **미확인**은 측정 또는 사용자 재현이 필요한 사실이다. 구조상 비용과 관찰된 사용자 결함을 같은 것으로 취급하지 않는다.

## 1. 기존 Timeline의 실제 구조와 소유권

### 1.1 활성 View와 데이터 흐름

| 영역 | 실제 소유 코드 | 현재 계약/연결 |
| --- | --- | --- |
| Effect Timeline | `app/ui/timeline_widget.py:TimelineWidget`, `timeline_command_bar.py:InactiveTimelineTable` | QTableWidget 기반. visibility/name 두 열 뒤 frame 열. SingleSelection/SelectItems, 셀 편집 금지. playback/FPS/zoom/reveal/snap 및 frame/layer 명령 바 |
| Resource Composition Timeline | `app/ui/resource_editor_v2/composition_timeline.py:CompositionTimeline`, `LayerOrderTable` | QTableWidget 기반. frame 열은 0부터, vertical header에 hierarchy. leaf 바로 뒤 property rows. layer hierarchy drop도 이 table에서 처리 |
| Resource Asset Strip | `asset_inspector_widget.py:AssetFrameStrip` | LeftToRight QListWidget, currentRowChanged→frame_selected. source frame preview이며 문서 frame/cel range 편집기가 아님 |
| 숨은 구형 경로 | `resource_editor_widget.py`의 `timeline=QTableWidget(...); hide()`, `_legacy_timeline` | 활성 CompositionTimeline과 다르다. 숨은 table을 바꾸고 활성 편집기를 이식했다고 판단하면 안 됨 |
| 공통 좌표/탐색 | `app/ui/timeline_time_view.py:TimelineTimeView`, `navigation_frame` | cell width 8..160, anchor zoom/fit/header stride, visible key 이전/다음 탐색. 시간 모델을 수정하지 않음 |
| 공통 scrub | `app/ui/timeline_scrub_controller.py:TimelineScrubController` | viewport press/move→column 선택, 같은 column 중복 억제, release→finish. Effect first_column=2 / Resource=0 |
| Key 선택/변경 | `app/ui/timeline_multi_key.py` | TimelineKey, TimelineKeySelection, atomic move/duplicate/delete/easing/clipboard 순수 helper |
| Key snapping | `app/ui/timeline_snapping.py` | visible nonselected keys, frozen playhead/start/end snapshot; 화면 거리 8px 기준, 충돌/경계 검증 후 shared delta |
| Layer 선택 | `app/ui/layer_selection_state.py:LayerSelectionState` | stable ID set + primary/anchor, Shift 표시 순서 범위/Ctrl toggle. table의 current index와 별도 |
| Output/Undo 소유 | `app/ui/main_window.py` | Project/현재 frame/layer, QUndoStack, Effect 명령, Canvas/Inspector/derived render/playback/prewarm 연결 |
| Resource 소유 | `resource_editor_widget.py`, `resource_editor_controller.py` | composition/session/frame/layer state, shared Undo, canvas/Inspector/timeline 동기화 |

Effect `TimelineWidget.refresh`는 main layer rows 다음에 property rows를 모아서 붙인다. Resource `CompositionTimeline.refresh`는 hierarchy의 각 leaf 다음에 해당 property rows를 붙인다. 공통 UI인 듯 보여도 row topology와 header 의미가 다르다.

주요 코드 위치(현재 working tree 기준): Effect `timeline_widget.py:314` current cell, `:412` key visuals, `:461` refresh, `:523` current-frame update, `:569` layer selection, `:590` frame highlight. Resource `composition_timeline.py:232` key visuals, `:270` refresh, `:369` vertical-header action. 이후 구현 변경 시 line은 이동할 수 있으므로 method 이름을 함께 기준으로 삼는다.

```text
Pointer/Keyboard
  → TimelineWidget / CompositionTimeline + ScrubController
  → navigation signal OR key/layer edit request
  → MainWindow / ResourceEditorWidget (authoritative document + Undo)
  → existing controller/service invalidation + Canvas/Inspector
  → Timeline refresh/current-frame update
```

### 1.2 선택·playhead는 현재 어디서 섞이는가

| 구분 | 현재 구현 | 구별해야 할 경계 |
| --- | --- | --- |
| Frame selection | table.currentCell + owner current frame, scrub 있음 | 독립 header frame-set/range 모델은 없음. current frame을 여러 frame 선택으로 볼 수 없음 |
| Cel/Resource frame selection | Effect raster pixels 존재 여부 marker, Resource active span, source AssetFrameStrip | raster cel identity, procedural active span, source asset index가 서로 다름. 통합 cel block clipboard 없음 |
| Keyframe selection | TimelineKey(layer_id, scope, property_id, frame), selected/primary/anchor | Shift는 같은 track의 **존재하는 key** 범위. frame columns 전체 범위가 아님 |
| Layer selection | LayerSelectionState + MainWindow/Resource controller, logical/generated layer mapping | layer multi-selection은 table SingleSelection과 별도. Effect cell 선택은 layer와 playhead를 함께 바꿀 수 있음 |
| Playhead | MainWindow frame_index / Resource controller.current_frame + view `_current_frame` | owner가 authoritative. key click/drag의 local preview와 실제 seek를 구분해야 함 |
| Time-range selection | 독립 모델 없음 | key rubber band와 loop/active range를 time selection으로 부르면 안 됨 |

Effect `_on_current_cell_changed`는 두 cell 신호를 내지만 MainWindow는 `cell_selected_with_modifiers`만 연결한다. `select_cell`은 layer+frame, `select_frame`은 frame만 바꾼다. Key hit branch는 local current cell/playhead와 custom key selection을 직접 갱신한다. 같은 모양의 선택이라도 모든 경로가 같은 owner seek 호출을 뜻하지 않는다. 이는 정리할 소유권 경계이지, 이 감사에서 새 재생 결함을 재현했다는 뜻이 아니다.

Resource key click은 frame_selected→set_frame을 호출한다. `set_frame`은 재생을 멈추고 controller.frame_changed→`_apply_state`를 통해 timeline을 다시 refresh한다. Resource single-key release는 compatibility `move_keyframe_requested`와 multi-key 신호를 모두 낼 수 있지만 활성 ResourceEditorWidget는 multi-key 경로만 연결한다. **두 Undo가 발생한다고 단정할 근거는 없다.**

### 1.3 입력·명령·Undo·refresh

- 두 View는 자체 eventFilter로 key hit/marquee/drag, Ctrl-wheel zoom, Shift-wheel horizontal scroll, MMB pan을 처리하며 공유 ScrubController도 viewport filter를 갖는다. 설치/소비 순서와 branch 조건이 입력 우선순위를 결정한다. key/property-row press를 소비하고 나머지가 scrub으로 이어진다.
- Key drag는 Qt startDragDistance 이후 시작, 선택 snapshot/shared delta/clamp/snap/충돌 검증, ghost preview 후 release 한 번 commit이다. Alt duplicate는 threshold를 넘는 시점에 고정한다. Escape 취소. mouse move마다 document/Undo를 쓰는 구조가 아니다.
- key clipboard MIME는 `application/x-pixel-effect-maker-timeline-keys`, version1. scope/resource/effect 및 runtime document context와 track 존재/경계/충돌을 검증한다. 타 문서 frame/cel 붙여넣기와 다르다. 붙여넣기 anchor는 playhead다.
- MainWindow의 Effect multi-key handlers와 ResourceEditorWidget multi_tracks는 기존 EditorValueCommand/QUndoStack으로 snapshot 원자 적용한다. View는 render service 직접 호출자가 아니다.
- Effect +Frame/Duplicate/Delete는 현재 frame 중심 기존 EditorOperationCommand다. `MainWindow.apply_undo_operation`의 insert/duplicate/delete branches와 `Project.insert_empty_frame/duplicate_frame/delete_frame`은 frame/pixels 배열을 조작한다. 여기서 property keys/emitter start/end의 일반 ripple retime는 확인되지 않는다.
- ResourceComposition은 `frame_count`와 tracks 중심이며 별도 frame 객체 배열이 없다. Effect의 기존 raster frame 명령을 그대로 Resource column move에 연결할 수 없다.
- MainWindow.select_frame/select_cell은 Canvas/Inspector/상태/현재 열 및 prewarm을 조정한다. Resource `_apply_state`는 Inspector/Canvas/source list와 full timeline refresh를 함께 수행한다. 모델 revision/렌더 cache invalidation은 기존 owner/service가 관리한다.
- Effect playback은 full-prebuffer timer에서 frame 단위 advance, 다른 분기에서 elapsed×FPS 기반 seek/drop 집계다. Resource composition playback은 FPS 기반 timer, asset preview는 imported frame durations를 사용한다. 새 View가 scheduler를 새로 만들면 안 된다.

### 1.4 단축키 충돌 감사

| 현재 입력 | 현재 owner/의미 | 새 Timeline의 계약 |
| --- | --- | --- |
| Enter/Return | PlaybackShortcutController, configured play/stop | 유지. 임의 Space/P 재생 단축키 추가 금지 |
| Left/Right, </> | FrameShortcutController, 현재 editor previous/next frame | 유지. 선택 확장을 위해 plain Left/Right를 훔치지 않음 |
| Ctrl+Alt+Left/Right | 두 timeline local filter, prev/next key | Key domain에서 유지 |
| Alt+Left/Right | 선택 key nudge | Key domain에서 유지; frame move로 중복 사용 금지 |
| Ctrl+C/V, Delete | 선택 key일 때 key copy/paste/delete, 그 외 layer delete 등의 context | active edit domain 단일 dispatch. invalid paste가 다른 domain으로 fall-through하지 않음 |
| Ctrl+A | 현재 layer select all 경로 | Layer/Key/Frame domain을 명시한 뒤 단계별 전환; 기존 앱 전체 의미를 몰래 바꾸지 않음 |
| Ctrl+D | Resource LayerOrderTable layer duplicate | frame duplicate와 충돌. Frame context menu를 우선 제공하고 새 키는 별도 승인 |
| Alt+N / Alt+B | configured new_frame / new_empty_frame | MainWindow에서 각각 duplicate_frame / add_frame 연결. 이름만 보고 빈 frame 생성으로 바꾸면 안 됨 |
| Ctrl+Z / Ctrl+Shift+Z, Ctrl+Y | 기존 Undo/Redo | native text editor의 편집 Undo와 document Undo 우선순위 유지 |
| Ctrl-wheel / Shift-wheel / MMB | zoom / horizontal scroll / pan | 유지, native scrollbar와 일관되게 좌표 변환 |

ResourceEditorWidget.keyPressEvent에도 Enter/좌우 legacy 처리가 있다. Playback/FrameShortcutController는 modal/popup/text/SpinBox/editable Combo/편집 중 item view를 보호하며 allowed timeline을 구별한다. 새 view는 이 focus whitelist/guard와 함께 검증해야 한다. hardcoded local shortcuts가 중앙 shortcuts registry와 분산되어 있는 것은 확인된 유지보수 문제이나 실제 IME 충돌은 이번에 재현하지 않았다.

## 2. 확인된 구조 문제와 미확인 위험

| 분류 | 코드 근거와 영향 | 확인 수준 |
| --- | --- | --- |
| 선택 상태 중복 | table current index, local `_current_frame`, custom key state, layer state, owner playhead. frame-set/time-range 부재 | 현재 구조 확인. 모든 선택이 잘못된다는 주장은 아님 |
| 이벤트 분산 | View eventFilter + shared scrub + table keyPress + window shortcut + Resource legacy keyPress | 우선순위 규약이 한곳에 없음. 미래 기능 추가 시 충돌 위험; 현재 모든 drag가 실패한다는 근거 없음 |
| full allocation | 두 refresh는 clear/rebuild 후 **모든 row×frame에 QTableWidgetItem** 생성 | O(R×F) item 비용 확인. **칸마다 QWidget을 만들지는 않는다**; toolbar widgets는 고정 개수 |
| full visual scan | `_apply_key_visuals`, Effect `_highlight_frame_column`/set_effect_selection, marquee hit 수집이 grid 전체 순회 | playhead/key selection만 바뀌어도 전체 순회 비용. 실제 대형 UI stall 시간은 미측정 |
| refresh 범위 | Resource frame_changed→`_apply_state`→timeline.refresh, Effect refresh 중 stored pixels alpha.any marker 조회 | view-only 변화와 full snapshot rebuild 결합. alpha.any는 stored pixels 검사이지 renderer 호출이 아님 |
| row/header 계산 | Effect metadata 2열 vs Resource 0열, 서로 다른 row order/hierarchy, ResizeToContents/column width 재설정 | 공통 좌표 adapter 필요. 별도 header를 추가하면 scrollbar origin 불일치 위험 |
| 중복 구현 | 두 View에 key gesture/clipboard/navigation/zoom/snap/visual logic 반복 | 공통 순수 controller + 서로 다른 adapters로 정리할 근거 |
| frame 편집 의미 공백 | multi-key atomic command는 있으나 frame range/cel transfer/다중 frame ripple command 없음 | custom paint만으로 해결되지 않음. 모델/Undo 설계가 별도 선행 |
| 확장 한계 | ResourceComposition validation frame_count 1..512, FPS 1..120 | 수천 frame POC는 synthetic 데이터로만. production 제한 해제는 이번 범위 아님 |
| DPI/접근성/IME | custom glyph/font/header sizing 및 새로운 painted hit target | 위험 평가만. 100/125/150% native·screen reader·KO IME는 후속 확인 필요 |

기존 performance tests는 1000/5000 key의 순수 navigation/set/clipboard 연산 등을 제한 시간으로 검사한다. QTableWidget 대규모 paint/메모리/스크롤/입력 지연 benchmark가 아니므로 이를 근거로 수만 frame UI의 60FPS를 보증하지 않는다. 또한 기존 렌더 캐시/Undo/dirty 문제를 이 문서에서 새로 해결했다고 보고하지 않는다.

## 3. Qt 구현 방식 비교와 결정

아래는 코드 구조와 공식 API를 바탕으로 한 설계 판단이며 네 방식의 동일 workload 실측 결과가 아니다.

| 기준 | A. QTableView + model/delegate | B. QAbstractScrollArea + QPainter | C. QGraphicsView/Scene | D. 기존 table 제한 개선 |
| --- | --- | --- | --- | --- |
| Frame/cel block 편집 | index/selection 재사용 좋음, header/range overlay 별도 | frame/cel/key hit 영역 직접 표현에 가장 유연 | item/scene selection 편리, rectangular timeline에는 추가 정책 필요 | 새 selection state·header를 기존 branch에 추가해야 함 |
| 키 편집 | delegate glyph/overlay + custom gesture | sparse key query + overlay, 기존 pure helper 재사용 | key items/event routing 가능 | 기존 코드 보존 쉬움, 중복 유지 |
| Pixel 표시 | delegate에서 nearest-neighbor/정렬 제어 | grid/glyph/thumbnail 경계 직접 통제 | scene transform의 fractional scale/AA 주의 | 현재 marker 위주, 확장 제약 |
| 대형 데이터 | model data lazy, viewport delegate paint. header/row topology 관리 필요 | visible row/frame/key만 그리기, 전체 grid allocation 불필요 | sparse items는 적합; item-per-cell이면 다시 객체 수 비용. 항상 느리다고 단정하지 않음 | R×F item 생성/전체 visual scan 남음 |
| 선택/drag 비용 | Qt 기본 선택과 6 domain 동기화 조정 | 단일 state machine 명확, 직접 구현량 큼 | built-in scene 선택과 domain 정책 조율 | 초기 변경 작음, 이후 분기 비용 큼 |
| 이벤트 안정성 | item view/focus/editor 기반 활용 | native scrollbars/viewport 활용, capture/cancel/IME guard 직접 검증 | scene/view/focusitem 이벤트 경로 검증 | 기존 테스트 풍부, 분산 filter 유지 |
| 접근성/키보드/DPI | 기본 item-view 인프라 유리, custom delegate도 검증 필요 | 가상 cells의 QAccessible/keyboard/semantic focus 직접 제공 필요 | custom graphics item의 접근성/키보드 별도 설계 | 기본 table 인프라 있음, 현 domain은 별도 |
| 테스트 | model/persistent index/delegate geometry 분리 | pure geometry/hit/selection + offscreen paint 분리 용이 | scene transform/hit tests 가능 | parity tests 재사용, 구조 격리 어려움 |
| 유지보수 | 중간, Qt model signals/index 생명주기 관리 | 초기 높음, 명시적 경계/성능 예산 필수 | scene item lifecycle 및 index 관리 비용 | 단기 낮음/장기 높음 |
| 코드 재사용 | 명령/helper/owner/service 재사용 | 동일. QTableWidget 메서드 의존 View 테스트만 adapter화 필요 | 동일, Qt item 기반 UI는 이식 | 가장 높음, 문제 구조도 보존 |

**권장 하나: B — QAbstractScrollArea + QPainter 기반 viewport 가상화.** Frame header/cel/key/range/playhead를 서로 다른 domain과 hit 영역으로 표현하고, sparse 데이터와 dirty rect 중심으로 그린다. native scrollbar/Qt Widgets/focus/대화상자는 유지한다. per-cell QWidget도 per-cell scene item도 필요 없다.

**보조 대안 하나: A — QTableView + QAbstractTableModel/QStyledItemDelegate.** POC에서 B의 접근성·키보드·IME·스크롤 예산을 만족하지 못하거나 유지보수 비용이 수용되지 않으면 A로 전환한다. pure geometry/controller/adapter/command interfaces를 공유하므로 renderer만 교체할 수 있게 한다. C/D는 비교 대상이지 추가 권장안이 아니다. QML/프레임워크 교체는 제안하지 않는다.

Qt 공식 문서 근거: [QAbstractScrollArea](https://doc.qt.io/qt-6.10/qabstractscrollarea.html)는 viewport/margins/scrollbar 및 viewport event 확장 지점을 제공한다. [Model/View Programming](https://doc.qt.io/qt-6.10/model-view-programming.html)은 model/view/delegate 분리를 설명한다. [QGraphicsView](https://doc.qt.io/qt-6.10/qgraphicsview.html)는 scene/item 좌표 변환·선택·view update 정책을 제공한다. [QAccessibleInterface](https://doc.qt.io/qt-6.10/qaccessibleinterface.html)의 role/state/name/관계/action은 custom-painted cells에도 별도 설계해야 한다. Qt 문서 버전은 6.10으로 고정 참조했으며 실제 배포 runtime에서의 동작 보증은 POC 이후다.

## 4. Selection / Interaction Contract — 제안, 미구현

### 4.1 단일 state owner와 여섯 domain

TimelineSessionState는 문서별 runtime-only 상태다. `active_edit_domain`은 Frames / Cels / Keys / Layers 중 하나이며, playhead와 time range는 독립 상태다. 다른 domain의 선택을 기억할 수 있지만 Copy/Delete/Properties는 활성 domain에만 전달한다. focus/selection/reveal/zoom/pan만으로 document dirty/Undo/render generation을 만들지 않는다. **실제 seek에 필요한 current-frame preview는 허용하되 selection-only render 0과 구별한다.**

1. FrameSelection: 논리 column index set, primary, anchor. 표시는 1-based, 내부는 0-based. 불연속 Ctrl 선택 허용.
2. CelSelection: (editable layer ID, document frame address) set. procedural Resource의 active span/source image와 raster cel을 같은 수정 대상으로 취급하지 않는다.
3. KeySelection: 기존 TimelineKey + selected/primary/anchor. property/scope 구분, locked/generated 규칙 유지.
4. LayerSelection: 기존 LayerSelectionState 및 hierarchy 표시 순서/lock/solo/parenting 계약 유지.
5. Playhead: owner의 document frame index. selection anchor나 clipboard anchor를 위해 자동 retime하지 않는다.
6. TimeRange: runtime 반개구간 [start,end), timeline kind/document/timebase 포함. frame selection·source loop·layer active range와 별개다.

Effect frame address는 기존 Frame.id를 활용할 수 있다. Resource는 frame 객체 ID가 없으므로 우선 (composition_id,index,document_revision) 주소를 사용하고 revision 변경 시 재검증한다. 영속 Resource frame ID 추가는 별도 모델 설계 대상이다. key reveal/filter 변경 시 숨은 선택을 보존할지 여부는 기존 `repair(visible_keys)`의 hidden-key 제거와 다른 동작이므로 migration parity 단계에서는 기존 정책을 유지한다.

### 4.2 입력 → 선택 → 명령 → Undo → refresh

다음 표의 새 Frame/Cel/Duration/Tag/Onion 기능은 현재 미구현이다. unavailable capability는 disabled와 이유를 표시하고 기존 key/layer 명령으로 fallback하지 않는다.

| 사용자 입력 | 선택 상태 변화 | 실행 명령 | Undo 단위 | 화면 갱신 |
| --- | --- | --- | --- | --- |
| frame 숫자 header L-click | Frames={n}, primary/anchor=n. Layers/Keys 기억만 보존 | SelectFrames; 별도 SeekFrame(n) | 0 | header/old-new playhead + 기존 owner preview. frame 선택만 하는 API는 seek 없음 |
| header Shift-click | anchor..n 연속 Frames 대체; Ctrl+Shift는 합집합 | SelectFrameRange | 0 | 바뀐 column header/범위. playhead는 명시 클릭 seek 외 불변 |
| header Ctrl-click | n 추가/제외; 마지막 제거 시 empty 허용, primary 재선정 | ToggleFrameSelection | 0 | 해당 header/범위만; playhead 불변 |
| 선택 frame header 경계 drag | threshold 이후 frozen frame block/insertion marker, 문서 불변 | release MoveFrames(plan) | 유효 변경이면 1, 취소/무효 0 | commit 후 topology/owner current repair/affected preview; production은 ripple 승인 전 disabled |
| cel click / Shift/Ctrl | Cels domain, layer×frame editable 주소 선택; source strip은 SourceFramePreview로 별도 routing | SelectCels 또는 PreviewSourceFrame | 0 | 해당 overlay/Inspector context. generated span은 read-only 이유 표시 |
| key click / Shift/Ctrl / 빈 property-row marquee | Keys domain; 기존 same-track range/toggle/marquee 의미 | 기존 selection helper | 0 | old/new key bounds. 숨은 keys 정책 유지 |
| key drag / Alt-drag / Alt-left/right | frozen key snapshot/shared delta; Alt는 drag 시작 시 copy latch | 기존 MoveKeys/DuplicateKeys/NudgeKeys bridge | gesture당 1 | ghost→기존 atomic command→revision/preview→key selection remap |
| row label click / Shift/Ctrl | Layers domain; current primary/anchor/ordered IDs | 기존 layer selection | 0 | row highlight/Inspector, seek 없음. eye/disclosure hit은 selection과 별개 |
| layer hierarchy drag | frozen selected IDs/parent/drop zone | 기존 hierarchy move/group 명령 | 유효 drop 1 | hierarchy/rows refresh, cycle/lock 거부 시0 |
| Ctrl+C | 활성 domain snapshot 복사. 선택/문서 불변 | CopyKeys(기존 MIME) 또는 CopyFrameBlock/CopyCels(후속 별도 MIME) | 0 | status만. Frames/Cels clipboard는 capability 승인 전 unavailable |
| Ctrl+V | 활성 domain/context/revision/track compatibility 사전 검증 | PasteKeys(기존) / 후속 PasteFrameBlock 또는 PasteCels | 전체 batch 1 또는 거부0 | commit 결과 selection/owner/cache; invalid payload는 다른 domain 명령 실행 안 함 |
| context Duplicate | Keys/Layers는 현재 계약; Frames/Cels는 선택 snapshot 복제 | 기존 명령 또는 후속 DuplicateFrames/DuplicateCels | batch 1 | 새 block/key 선택, topology/preview. frame duration은 frame block에 포함 |
| context Insert Before/After | Frames anchor 기준, 명시 count/empty | 후속 InsertFrames; legacy Effect +Frame은 기존 동작 유지 | 전체 1 | topology/주소 repair/duration 상속. retime 규칙 승인 전 새 명령 disabled |
| Delete | 활성 Frames/Cels/Keys/Layers에만 dispatch | 후속 DeleteFrames/ClearCels 또는 기존 key/layer delete | batch 1 / min1·lock 등 거부0 | 삭제 선택 repair/preview. Key 삭제로 layer가 지워지지 않음 |
| header context Frame Properties | 선택 Frame snapshot, mixed 표시 | 우선 read-only 정보. Timing-2 후 SetFrameDurations | 열기/취소0, 유효 Apply1 | duration badge/총길이/schedule refresh; 표시만 바꿀 때0 |
| frame duration 정수 ms 입력 | 대상 Frame selection 고정, source clip은 수정 안 함 | 후속 SetFrameDuration(exact ms) | commit1; IME중/취소/무효0 | timing-only plan/배지. particle pixels 자동 retime 없음 |
| 다중 duration Set/Scale/Uniform Apply | 선택 snapshot/all 명시, mixed를 임의 평균으로 쓰지 않음 | 후속 atomic SetDurations/ScaleDurations/SetUniformTiming | 전부 validation 후1, 하나라도 오류면0 | 총길이/loop deadline/sidecar. 기존 UI 표시 반올림 역저장 금지 |
| ruler 빈 영역 press+drag / playhead handle drag | playhead만 변경, Frames/Keys/Layers 유지 | BeginScrub→SeekFrame(dedup)→EndScrub | 0 | 기존 owner current preview/Inspector. playback stop/prewarm 정책 유지 |
| Ctrl-wheel anchor zoom / Fit / reveal | ViewportState만 변경 | ZoomAt/SetVisibleSpan/RevealSelection | 0 | 좌표/visible paint/scrollbar만; source sampling/keys 불변 |
| Shift-wheel / MMB / scrollbar | horizontal offset만, 일반 wheel은 vertical | PanViewport / SetScrollOffset | 0 | header/body 같은 offset으로 paint; render 요청0 |
| 별도 range lane Shift-drag | TimeRange=[a,b), Frames 선택과 별개 | SetPreviewRange | 0 | range lane/preview loop 제한. source loop/layer End 변경 없음 |
| Preview Loop toggle | session preview loop/range state | SetPreviewLoop | 0 | playback session만. 기존 Resource.document loop 설정 명령은 별도 Undo 계약 유지 |
| range context Save Tag/Named Range | TimeRange에서 이름/방향 등 명시 | 후속 SetNamedRange(metadata schema 필요) | 저장 기능 승인 후1 | tag lane/dirty; imported clip tags는 읽기만, 자동 덮어쓰기 없음 |
| Onion Skin toolbar toggle/settings | editor overlay preference, prev/next 수/alpha | 후속 SetOnionSkinPreference | document Undo0 | editor canvas overlay만; output RGBA/PNG/cache에 합성 금지 |

Frame drag 제안 기본은 **insert-position 기반 block reorder**이며 overwrite/ripple은 암묵적으로 하지 않는다. 불연속 선택은 원래 순서를 유지해 한 block으로 모으되 대상 insertion이 자기 block 안이면 no-op이다. 이 정책은 synthetic POC에서 UX 검증할 안이지 기존 모델에 적용된 기능이 아니다. Cel move는 대상 충돌을 기본 거부하고 overwrite 확인은 별도 계약으로 둔다. Frame block copy는 duration 포함, cel-only copy는 column duration을 옮기지 않는다. import asset 원본 수정/문서 간 자동 FPS retime은 하지 않는다.

**Production frame 명령의 선행 결정:** raster frame reorder와 property key, source playback range, emitter birth/end, generated outputs, parenting tracks를 함께 옮길지 명시해야 한다. 기존 raster-only command를 일반 document ripple 명령으로 재사용하지 않는다. Resource procedural composition에는 cel 원본이 없으므로 해당 동작을 지원한다고 가장하지 않는다. 이 부분은 `TIMELINE-UX`/Timing schema 승인 전 production 연결 금지다.

### 4.3 단일 입력 상태 기계

우선순위: modal/popup/native text editor/IME 입력 보호 → MMB pan → playhead handle/ruler → frame header → key hit → cel/span → row header → empty area. 각 hit는 하나의 typed target만 반환한다. 공개 hit geometry를 paint와 공유해 시각 요소와 클릭 대상이 어긋나지 않게 한다.

상태는 Idle → Pressed(domain,address,snapshot) → Dragging(kind,threshold 통과) → Commit/Cancel이다. Qt drag distance는 DIP 좌표로 판단하고 Alt copy는 시작 순간에 고정한다. move는 immutable preview delta/ghost만 변경, release에서 capability/lock/revision/collision 재검증 후 명령 1회. Escape/focus loss/capture loss/document close/selection revision 변경 시 ghost와 임시 auto-scroll timer를 정리하고 commit0. 텍스트 editor focus 이동은 그 editor의 기존 commit/cancel 규칙을 먼저 존중한다. stale gesture를 다른 문서에 적용하지 않는다.

일반 body click의 legacy scrub은 Resource pilot parity 모드에서 유지한다. 새 header Frame selection과 body Cel selection 모드는 별도 opt-in 승인 뒤 연결한다. 한 번에 조작 의미와 widget 구현을 모두 교체하지 않는다. 범위 auto-scroll은 viewport 가장자리에서만 bounded timer로 수행하며 pointer release/창 닫기 때 중단한다.

## 5. Resource/Effect 데이터·시간 경계

### 5.1 현재 유지할 의미

| 값 | 소유권/의미 | 새 Timeline이 하면 안 되는 일 |
| --- | --- | --- |
| Resource FPS + frame_count | ResourceComposition의 독립 timebase. 현재 integer FPS | Effect 출력 FPS 변경을 Resource FPS 변경으로 대체 |
| Effect FPS | Project output sample rate와 기존 physical frame-time 계산 기준 | output FPS만 바꿨는데 source speed 자동2배 |
| Playback Speed | source sampling 배율. Particle에서 적용; Single의 현재 별도 제약 있음 | Single 저장 필드를 자동 활성화하여 기존 파일 의미 변경 |
| Imported clip durations | AnimationClipAsset.frame_durations_ms; source duration schedule | 이것을 Project/Composition output hold 편집과 동일시 |
| Output frame duration | 현재 Project/Composition에는 per-frame persistent 모델 없음 | view preference/PNG pixel buffer에 duration을 숨겨 저장 |
| Keyframe frame index | 기존 property track의 integer frame 주소 | FPS 표시 전환/hold 변경으로 key index 자동 이동 |

현재 composition source sampling의 핵심은 elapsed frame time×source FPS×speed의 floor이며 경로별 start/loop/once/hold를 적용한다. 정수 연산 기반 비율 처리를 되돌리지 않는다. 실제 계산은 기존 render services만 소유한다.

| 시나리오(개념상 uniform schedule) | 처음 source index, 1-based | 12 source frame 한 순회 길이 |
| --- | --- | --- |
| Resource 12 frames /12→24 FPS, frame/key index 보존 | Resource 자체 1..12 | 1초→0.5초 |
| Resource12FPS /Effect24FPS /speed1× | 1,1,2,2,…,12,12 | Effect24 frames=1초 |
| Resource12FPS /Effect24FPS /speed2× | 1,2,…,12 | Effect12 frames=0.5초 |
| Resource12FPS /Effect24FPS /speed0.5× | 1,1,1,1,2,2,2,2,… | Effect48 frames=2초 |

위 표는 자동 fixture의 의도된 계약이지 **사용자 원본 회전 문제가 정상이라는 판정이 아니다**. Single/Particle, FPS/frame count 변경 순서, actual source indices/rotation keys/cache 경로가 확인된 사용자 재현으로 별도 조사되어야 한다. 이전 rotation/Timing 보고서의 자동 PASS는 보존하되 사용자 FAIL을 덮어쓰지 않는다.

### 5.2 Timing-1/2 연결 interface — 설계 전용

기존 Timing audit의 **exact uniform rate + sparse rational-ms overrides**를 재사용한다. 24FPS=125/3ms, 30FPS=100/3ms, 60FPS=50/3ms. 화면의 41.667ms를 다시 저장해 원래 rate를 소실시키지 않는다. 다음 API 이름은 새 제안이며 현재 import 가능한 구현이 아니다.

| 제안 interface | 입출력/경계 |
| --- | --- |
| `TimingReadPort.snapshot(document_id, revision)` | immutable TimelineTimingSnapshot(uniform rational rate, sparse positive duration overrides, frame order, timing_revision). 현재 adapter는 기존 uniform값을 읽기만 |
| `duration_ms(frame)`, `frame_start_ms(frame)`, `total_duration_ms()` | 정규화 rational 반환, 표시 반올림은 presenter만 수행 |
| `frame_at_elapsed(exact_ms, loop_mode)` | prefix 반개구간 [S(n),S(n+1)), binary search. loop일 때만 modulo, once는 마지막 hold 완료 후 정지 |
| `TimingPresenter.format(value, unit, locale)` | ms/FPS preference, mixed/source/output 의미 표시. Timing-1: QSettings only, dirty0/Undo0/cache0 |
| `TimingEditPort.plan_set/plan_scale/plan_uniform(selection, exact_value)` | Timing-2 승인 후 bounds/문서 revision/override 처리 검증, atomic duration command로 전달. View에 쓰기 API 없음 |
| `PlaybackSeekPort.seek_frame(index, reason)` | 기존 Resource/Effect owner에 integer seek 전달. View는 RGBA renderer 직접 호출하지 않음 |
| `SourceSamplingReadPort.describe_context()` | source FPS/duration kind/speed/mode 설명용. sampler 계산/수정 API를 노출하지 않음 |

Timing-2의 새 persistent 필드에는 별도 FORMAT/migration/down-save/sidecar 설계 승인이 필요하다. 현재 FORMAT22는 그대로 둔다. ms 입력 bounds 1..65535와 scale 1..10000%는 기존 audit의 **제안 범위**이지 현 앱 validation 보장이 아니다. frame block insert는 이전 duration 상속(첫 위치는 다음, 없으면 uniform fallback), duplicate는 exact duration 복사, delete는 override 제거, reorder는 document frame identity와 schedule 동행이다.

**Frame Hold와 Particle physical time을 분리한다.** Mode A에서는 output hold만 바꿔도 기존 integer frame N의 birth/age/physics/key/source sample/RGBA는 그대로다. prefix elapsed lookup 결과를 particle simulation age에 넣지 않는다. Resource output hold가 Effect source에 자동 적용되는 것도 아니다. `honor_source_schedule` 같은 source opt-in은 별도 승인/픽셀 변화 테스트가 필요하다.

pixel revision과 timing-plan revision을 분리하고, timing-only command는 pixels 전체 재생성을 요청하지 않게 Timing-2에서 설계한다. QTimer는 wake-up, monotonic clock/deadline이 authoritative elapsed를 소유하며 full-prebuffer와 elapsed 두 경로 모두 검증한다. PNG는 무시간 image이므로 timing 전달은 exact sidecar 후속 설계로 남긴다. 이번에는 어느 수학/스케줄러도 변경하지 않는다.

## 6. 자체 Timeline UI 디자인 시스템 — 제안

### 6.1 정보 우선순위와 layout

Canvas의 작업 이미지가 주인공이다. Timeline은 compact transport → ruler/frame header → 선택적 tag/range lane → layer/cel rows와 subordinate property tracks 순서다. source asset strip은 별도 source-preview context label을 갖는다. 대형 thumbnail을 기본으로 매 칸 그리지 않고 cel occupancy와 sparse keys를 우선한다. 필요 시 선택 frame의 bounded thumbnail만 nearest-neighbor로 캐시한다. renderer 호출을 paintEvent 안에 넣지 않는다.

fixed left row header와 top ruler는 같은 `TimelineGeometry`/scroll offsets를 사용한다. native horizontal/vertical scrollbar는 각각 하나, frozen header가 body와 다른 scroll origin을 갖지 않게 한다. Frame-index grid를 기본으로 유지하며 duration badge로 hold 길이를 보여준다. ms 표시 전환만으로 variable-width columns를 만들지 않는다. 시간 비례 ruler는 별도 mode/제품 승인 대상이다.

좁은 폭에서는 덜 쓰는 명령을 overflow menu로 보내고 icon-only에는 KO/EN tooltip/accessibleName을 제공한다. text label을 hardcoded pixel width로 자르지 않고 font metrics/elide + full tooltip을 쓴다. row name 영역은 사용자가 resize, 최소 시인성 유지. 중요한 play/stop/current frame/output FPS/source speed 의미는 overflow로 숨기지 않는다.

### 6.2 Semantic tokens와 상태

| token/규칙 | 제안 기준 |
| --- | --- |
| geometry | DIP 기반 row main 24/property 22/ruler 28, key glyph8/hit14, playhead line1~2/hit 최소10. 이 숫자는 POC 시작값이며 hardcoded HFW 파괴용 fixedHeight가 아님 |
| frame grid | minor grid는 낮은 대비, 5/10 등 major stride는 zoom/font에 따라 계산. frame labels 충돌 시 stride 증가; 인덱스는 항상 같은 frame을 가리킴 |
| Frames 선택 | header fill + column outline, Keys 선택은 diamond outline/fill, Layers는 row-name accent, TimeRange는 ruler bracket/얕은 band |
| playhead | accent line + ruler handle + current index label. selection fill로 표시하지 않아 중첩 시 구별 가능 |
| cel/generated | editable cel solid occupancy, generated/procedural span은 hatch/chain badge+read-only tooltip; source preview는 별도 context |
| feedback | hover는 약한 outline, keyboard focus dotted/solid ring, drag ghost dashed, snap guide 별색/label, invalid drop 금지 기호. 색 하나로 의미 전달하지 않음 |
| palette | background/surface/grid/text-muted/selection/playhead/warning tokens를 palette theme에서 resolve. Light/Dark 각각 대비 검증, 시스템 native highlight로 전체 파란 면을 덮지 않음 |
| text/icons | KO/EN 번역 key, 숫자/tabular 가독성, 일반 텍스트 ClearType; pixel thumbnail만 smoothing off. 긴 이름·mixed·disabled 상태도 읽히게 함 |
| DPI | Qt logical coordinates 유지, geometry/hit에서 DPR 중복 곱 금지. raster cache key에 DPR/theme/font/zoom/revision 포함; physical pixel stroke 정렬은 paint boundary에서만 |

100/125/150% DPI × Light/Dark × KO/EN × 좁은/넓은 창 × 큰 frame count를 테스트 matrix로 둔다. 합성 offscreen은 glyph/hit/overlap/scroll 정렬을 확인하지만 실제 Windows font/IME/접근성/다중 모니터 이동 승인을 대신하지 않는다. [Qt High DPI](https://doc.qt.io/qt-6.10/highdpi.html)의 device-independent 좌표 체계를 따른다.

### 6.3 다른 편집기에서 가져올 원칙만

- Aseprite: [Timeline](https://www.aseprite.org/docs/timeline/)의 frame/layer/cel 구분, [Copy Frames](https://www.aseprite.org/docs/copy-frames/)의 범위 경계 조작, [Onion Skinning](https://www.aseprite.org/docs/onion-skinning/)의 editor ghost를 참고한다. PEM procedural layers를 raster cels로 오인하거나 단축키/타문서 복사 의미를 그대로 복제하지 않는다.
- Blender 4.4(2025) [Dope Sheet Editing](https://docs.blender.org/manual/en/4.4/editors/dope_sheet/editing.html): key 선택/시간 column/range 탐색을 분리하는 패턴을 참고한다. PEM frame selection과 property key selection을 합치지 않는다.
- Godot 4.5 [Animation introduction](https://docs.godotengine.org/en/4.5/tutorials/animation/introduction.html): track list/key 영역/transport의 역할 분리를 참고한다. Godot의 보간/초 단위 모델을 가져오지는 않는다.
- Unity [Clip Edit modes](https://docs.unity3d.com/kr/Packages/com.unity.timeline%401.6/manual/clp_about.html)는 주변 clip에 미치는 효과를 명시적으로 구분한다. 참고 가능한 공식 설명은 package1.6 문서이며 2025~2026 최신 기능 검증이라고 주장하지 않는다. PEM에서는 ripple/overwrite를 숨기지 말자는 원칙만 채택한다.

외부 문서는 이번 감사에서 확인한 공식 primary 자료다. 위 패턴을 PEM에 적용하는 판단은 본 문서의 제안이며 다른 제품의 동작 보증이나 최신 버전 비교가 아니다.

## 7. POC 클래스·파일 책임과 단계적 migration

### 7.1 제안 파일/클래스 — 현재 생성하지 않음

독립 POC는 `tools/timeline_poc/` 또는 별도 승인된 실험 디렉터리에서 synthetic adapter만 사용한다. 아래 `app/ui/custom_timeline/`는 production pilot에서의 **예상 위치**이며 이번에 만들지 않았다.

| 예상 파일 / 클래스 | 책임 / 금지 |
| --- | --- |
| `types.py`: TimelineRow, FrameAddress, HitTarget, Capability, EditIntent | immutable DTO, stable IDs/kind/revision. QWidget/renderer/model mutation 의존 금지 |
| `geometry.py`: TimelineGeometry | visible bounds, index↔DIP, row prefix search, hit rect, frozen header offset. paint/command 호출 없음 |
| `selection.py`: TimelineSessionState | 6 domain/active domain/anchor/repair, 기존 key/layer state와 명시 bridge. persistent Project에 넣지 않음 |
| `interaction.py`: TimelineInteractionController | pointer/key state machine, threshold/capture/cancel/drag preview, typed intent 생성. Undo/document 직접 쓰기 금지 |
| `view.py`: TimelineViewport(QAbstractScrollArea) | viewport paint, native scrollbars, dirty rect, focus/accessibility event 연결. data 읽기는 adapter, edit는 controller intent만 |
| `adapters.py`: TimelineReadAdapter protocol | revision/frame count/row topology/visible span/sparse keys/capabilities/timing read. 조회 중 repair/mutation/render 금지 |
| `resource_adapter.py`, `effect_adapter.py` | composition vs project/logical-generated mapping, 다른 row topology/offset 흡수. Effect source FPS와 output FPS를 섞지 않음 |
| `command_bridge.py`: TimelineCommandBridge | typed intent→기존 editor commands/QUndoStack; plan 검증/atomic commit/selection remap. release당 최대1command |
| `playback_bridge.py`: TimelineNavigationPort | 기존 editor seek/scrub/playback 연결. scheduler/particle sampler 새 구현 금지 |
| `timing_presenter.py` | Timing-1 exact 표시/후속 TimingReadPort 연결. roundtrip 데이터 수정 금지 |
| `accessibility.py`: TimelineAccessibleAdapter | visible/virtual cell role/name/state/action/table navigation/focus 전달. screen reader gate 필수 |
| synthetic fixture/POC runner/tests | fake rows/keys/durations/command recorder. 원본 프로젝트/이미지 자동 수집 금지 |

View는 visible row interval과 frame interval에 대해서만 그린다. sparse key query는 row/track별 정렬 index로 bounds search한다. 전체 empty grid/수천 thumbnail/접근성 객체를 매번 materialize하지 않는다. geometry 변경/topology revision이면 layout 갱신, playhead/selection만 바뀌면 old+new bounds invalidate. 한 gesture 동안 데이터 snapshot은 고정하고 renderer는 outside paint의 기존 owner에서만 구동한다. 정수 scrollbar 최대 범위를 넘는 매우 긴 timeline은 logical origin+bounded window mapping을 별도 POC로 검증한다.

### 7.2 단계별 gate와 rollback

| 단계 | 범위 | 통과 조건 / 중단 경계 |
| --- | --- | --- |
| 1 Synthetic POC | 별도 승인 후 B의 paint/hit/scroll/selection/drag/key command recorder | app model/renderer import0, synthetic 12/512/10k/100k frames. 접근성/keyboard/DPI 예산 미달이면 A 대안 평가. 원본 파일 쓰기0 |
| 2 Resource Pilot | 별도 승인 후 읽기 adapter + 기존 navigation/key/layer commands 연결, feature flag | 기존 UI 남김, composition/source strip 구별, frame editing/duration 새 기능 disabled. 실제 app limit512 유지 |
| 3 Legacy parity | 양 UI에 동일 action trace, 동일 initial model; output/Undo/lifecycle 비교 | key snapshots/easing/clipboard/domain/lock/group/parenting/reveal/snap/Undo/dirty/seek/Save/Reload 모두 일치. mismatch면 legacy로 rollback |
| 4 Timing-1/2 연동 설계 | exact display 먼저, persistent duration/schema/migration 별도 승인 | Mode A RGBA 불변, source sampling 분리, both playback branches/export sidecar 설계. ARCH 완료가 Timing 구현 승인은 아님 |
| 5 Effect Pilot | Resource parity 후 Effect adapter + existing command/navigation bridge | 사용자 rotation 문제의 재현/수정/재확인 및 FPS checkpoint gate 해소가 선행. generated/raster mapping/physical time/Current-Full-Generated-Playback-PNG parity |
| 6 Native 승인 후 교체 | 사용자가 실제 제작 흐름/입력/DPI/theme/KO/EN 확인 | feature flag fallback 유지 기간/rollback 문서화 후 legacy 활성 UI 제거 별도 승인. 숨은 table cleanup도 별도 검토 |

독립 synthetic POC는 unresolved rotation과 무관한 합성 UI 실험으로 별도 승인할 수 있다. 그러나 그것을 이용해 CP2/Effect pilot/생산 checkpoint 의존성을 우회하지 않는다. 기존 queue의 TIMING-1/2/Single speed/ASE-IMPORT/Timeline-UX/Effect Backlog는 유지한다.

## 8. 테스트·DevEx 계획, 남은 결정과 감사 검증

### 8.1 새 테스트 설계 — 아직 미구현

| 계층 | 최소 계약과 실패 관찰 |
| --- | --- |
| pure geometry | 0/마지막 frame/metadata origin/frozen header/negative outside/clamp, fractional zoom/scroll/DPI 좌표 왕복, row collapse/resize 이후 hit 결과 |
| pure selection | six domain 독립, Shift anchor/Ctrl toggle/discontiguous range/empty selection/document close/revision repair, active-domain command가 다른 선택을 변경하지 않음 |
| pure interaction | threshold 직전/직후, same-frame duplicate move 억제, Alt latch, Escape/focus loss/capture loss, auto-scroll stop, release1command/no-op0, stale revision 거부 |
| Qt offscreen | ruler/body/header 정렬, narrow/KO/EN/Light/Dark/font/DPI geometry, key glyph와 hitbox 일치, no per-cell widget, clipboard/focus/IME guard, pending timer/window teardown |
| command parity | 동일 trace→legacy/new model snapshots, Undo count1/redo exact, lock/group/hierarchy/parent cycle, collision atomic rejection, dirty0 navigation vs required seek rendering 분리 |
| timing/render | Resource12/Effect24/speed0.5/1/2 실제 source index+RGBA, imported ms vs output schedule 구별, 360/720/음수 회전/loop/end/direct seek/save/reload/cache invalidation, mode A hold edit RGBA 불변 |
| large viewport | synthetic sparse/dense keys×12/512/10k/100k frames×20/200/2000 rows, cold/warm/scroll/zoom/marquee/drag/resize, peak RSS/object count/paint counts/visible query size/p95 input latency |
| native manual | 100/125/150% multi-monitor, KO IME 중 Enter/CtrlZ/숫자 입력, keyboard-only/screen reader, mouse/trackpad/capture loss, Light/Dark/high contrast 실제 제작 |

POC 성능 **제안 gate**: 동일 기계/동일 visible workload에서 frame count만 늘릴 때 empty-cell 객체 수가 R×F에 비례하지 않음; view-only frame/selection 변화에서 full document rebuild0/renderer request0(명시 seek 제외); interaction p95 33ms 이내를 초기 목표로 삼되 조건/분포/환경을 먼저 기록하고 승인한다. 현재 실측 수치가 아니다. 큰 합성 fixture는 production 제한 확대 근거가 아니다.

DevEx-1은 승인된 기존 pytest node 재사용을 우선한다. 이후 새 pure/view/parity nodes를 registry에 추가할 때 stable case ID, phase(hit/intent/command/owner refresh), redacted expected/actual, bounded counters, timing metadata만 JSON으로 남긴다. 사용자 모델/이미지/절대 경로/traceback locals 자동 수집 금지. completion-condition wait + 명확한 timeout, 고정 sleep으로 flaky test를 가리는 방식 금지. scheduler/worker 종료와 QApplication fixture 격리도 결과에 포함한다.

### 8.2 미해결 결정과 위험

1. **사용자 회전 재생 문제:** 현재 미해결. 실제 source/frame/FPS/mode/speed/변경 순서/키/end/캐시 재현을 별도 요청 범위로 진단하고 사용자 재확인 전 CP2/의존 checkpoint 차단 유지.
2. **Document frame ripple:** frame block reorder/insert/delete가 raster/key/emitter/generated/time metadata에 미치는 영향 및 discontiguous 정책 승인 필요. 현재 command를 일반 ripple이라고 부르지 않음.
3. **Resource frame identity/cels:** index+revision의 한계, persistent ID 필요 여부, procedural span 편집 capabilities, imported asset read-only 경계 결정.
4. **Timing schema:** sparse rational ownership/FORMAT migration/down-save/export sidecar와 duration-only invalidation. TIMING-1 표기와 TIMING-2 데이터 변경 분리.
5. **Source schedule opt-in:** output hold와 source sampling은 독립. Single speed 및 honor_source_schedule는 별도 승인; 기존 파일 자동 변환 금지.
6. **Input UX:** Frame header click seek 여부/불연속 frame move/새 shortcut registry/domain switching을 synthetic 사용자 검토로 확정. parity 기간에는 기존 동작 유지.
7. **Accessibility/DPI:** B 구현 비용과 PySide runtime API 검증, 가상 접근성 focus/navigation/스크롤 예산 실패 시 A 전환. 합성 geometry PASS는 native 승인 아님.
8. **기술적 vs 사용자 완료:** 자동 PASS, 구조 감사 DONE, 실제 UI 승인, checkpoint 승인 네 가지를 각각 추적한다. 새 UI로 unresolved renderer 문제를 숨기지 않는다.

### 8.3 이번 감사에서 실제 수행한 검증

- 기존 focused timeline/keyboard tests 12개 모듈 **93 passed in 7.50s**. 확인된 최종 실행: `C:\Dev\pem_timeline_arch_confirmed_tests_20261030` basetemp. 앞선 동일 계열 실행의 결과 출력은 보존되지 않아 집계 근거에 포함하지 않는다. 전체 pytest 반복은 하지 않았다.
- 실행: offscreen, `python -m pytest tests/test_timeline_scrubbing.py tests/test_timeline_multi_key_model.py tests/test_timeline_multi_key_editing.py tests/test_timeline_multi_key_clipboard.py tests/test_timeline_multi_key_alt_duplicate.py tests/test_timeline_snapping.py tests/test_timeline_navigation_reveal.py tests/test_timeline_navigation_performance.py tests/test_timeline_multi_key_performance.py tests/test_timeline_command_bar_layout.py tests/test_frame_shortcuts_and_localization.py tests/test_playback_shortcut_regressions.py -q -p no:cacheprovider --basetemp=C:\Dev\pem_timeline_arch_confirmed_tests_20261030 --tb=short`.
- 문서만 변경했으므로 full pytest/통합 진단은 재실행하지 않았다. 직전 full **1971 passed /1 skipped** 및 checkpoint preparation의 **UI90/Rotation49/Groups13/Render23=175 PASS**는 과거 검증 근거이며 이번 재실행 결과가 아니다.
- 종료 확인: HEAD/staged0/v0.0.25/FORMAT22/보호 PNG 일치, 기존 변경 Python53개 hash 불변, `git diff --check` 통과. 현재 Git 상태는 tracked modified29/untracked42이며 직전 상태 대비 새 경로는 이 감사 문서1개, 기존 경로 소실0이다. 이번 편집은 queue+감사 문서뿐이다. 옛 checkpoint 시작 inventory와 다른 DEVEX1_DIAGNOSTICS/UX2_VERIFY_CHECKPOINT_REPORT 두 문서는 직전 작업에서 수정된 이력이며 이번에 수정하지 않았다. Window Use0, Python 테스트 프로세스 잔류0. 새 Timeline 성능/native QA/사용자 회전 재생 해결 여부를 이번93 PASS로 추정하지 않는다.
