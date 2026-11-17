# TIMELINE-CUSTOM-POC — Phase 1

2026-10-30. **독립 synthetic POC 구현·자동 검증 완료. Production 이식/교체 승인은 아님.**

## 1. 실제 구조와 실행 방법

기준 HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`, v0.0.25 / FORMAT22. 기존 Resource/Effect Timeline, app/ui, 사용자 모델/이미지, renderer/FPS/Undo, 175-case core registry는 수정하지 않았다. `TIMELINE_CUSTOM_ARCHITECTURE_AUDIT.md`의 B 안을 좁힌 구현이다.

| 신규 파일 | 실제 책임 |
| --- | --- |
| `tools/timeline_poc/__init__.py` | 독립 패키지 경계, app import 없음 |
| `geometry.py` | pure DIP 좌표, frame/row 왕복, 반개구간 visible range, frozen headers, typed hit, zoom anchor |
| `selection.py` | Frames/Keys/Layers/Playhead 독립 runtime state, anchor/primary/Ctrl/Shift |
| `interaction.py` | pure press/threshold/range/scrub/pan/keyboard/cancel, 데이터 이동/명령 없음 |
| `adapter.py` | immutable synthetic counts와 산술 sparse keys. frame/cell 배열·프로젝트 파일 입력 없음 |
| `paint.py` | QPainter viewport drawing, palette/KO/EN, grid/header/key/selection/playhead, 실제 paint 방문 수 |
| `view.py` | QAbstractScrollArea/native scrollbars/focus/tooltip, Qt events→pure interaction, visible paint/hit 측정 |
| `fonts.py` | Windows offscreen의 비어 있는 font database에 설치된 Malgun/Segoe를 application font로 읽기. 복사/번들/시스템 설정 변경 없음; QApplication 기본 폰트 변경 없음 |
| `diagnostics.py` | 독립 bounded Qt checks/visual matrix/성능/최소 table baseline, cleanup |
| `__main__.py` | GUI demo + 별도 `--verify`/JSON/새 DPR 자식 프로세스 |
| `tests/test_timeline_poc_logic.py` | pure geometry/selection/interaction/adapter/import 경계 |
| `tests/test_timeline_poc_offscreen.py` | fresh-process Qt/DPR/PNG/metrics/CLI output 보호 |

프로젝트 루트에서 PowerShell:

```powershell
# 사용자가 직접 실행하는 GUI demo (이번 작업에서 native 실행하지 않음)
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' -m tools.timeline_poc --frames 10000 --tracks 200 --language ko --theme dark

# Window Use 없이 별도 진단; output은 새 디렉터리 또는 빈 디렉터리만 허용
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' -m tools.timeline_poc --verify --compare-table --output C:\Dev\pem_timeline_poc_review_new

# 독립 pytest (Qt 검사는 fresh subprocess로 격리)
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' -m pytest tests/test_timeline_poc_logic.py tests/test_timeline_poc_offscreen.py -q -p no:cacheprovider
```

GUI는 합성 timeline, KO/EN와 Light/Dark 선택, 도움말/현재 상태만 제공한다. Project/Resource 파일을 여는 옵션 자체가 없다. frame count 1..1,000,000 / track count 1..10,000은 **POC 자체 제한**이며 production 제한을 확장하지 않는다.

`--verify`는 fresh child 3개를 순차 실행한다. 각 child에 `QT_QPA_PLATFORM=offscreen`, `QT_SCALE_FACTOR=1/1.25/1.5`, `QT_FONT_DPI=96`, rounding policy PassThrough를 설정하고 실제 DPR을 확인한다. child timeout30초, 부모 pytest timeout120초. timeout 시 subprocess.run이 해당 child를 종료·회수한다. JSON schema1/PASS·FAIL·ERROR, observed checks, metrics, PNG 이름, 한계를 기록하며 core registry에 등록하지 않는다. 기존 nonempty output은 exit2로 거부한다.

## 2. 구현된 UI와 interaction

| 영역/입력 | 실제 결과 |
| --- | --- |
| 위쪽 ruler | 1-based `f` 눈금 + 형태가 구별되는 playhead handle. press/drag는 playhead만 이동 |
| 아래 frame-number strip | 내부0-based/표시1-based. click 단일 선택, Shift anchor 범위, Ctrl 추가/제외(마지막 제거 허용), Ctrl+Shift 합집합 |
| frame strip/body drag | Qt threshold 이후 **범위 선택만**. 이동/복제/retime가 아님. key는 click-only, layer는 header click-only |
| body sparse key | diamond, 선택 시 별도 사각 outline. Frame/Layer/Playhead 유지 |
| left layer/track header | label elide + 원문 native tooltip, 선택 accent. Frame/Key/Playhead 유지 |
| Left/Right, Home/End | playhead만 변경/seek 위치 reveal. Shift와 결합하면 frame selection 확장, playhead 불변 |
| Ctrl-wheel | cursor anchored zoom 8..160 DIP/frame, native scrollbar 정수화 오차 최대0.5 DIP 검증 |
| 일반 wheel / Shift-wheel / MMB | vertical / horizontal / 양축 pan. native horizontal/vertical scrollbar 각1개 |
| Escape / focus loss / capture loss / close | 진행 중 tentative selection 취소·복원, gesture idle. worker/timer 없음 |
| KO/EN, Light/Dark | semantic palette/직접 번역 label, font metrics 기반 row/header 높이. 텍스트·선택·key·playhead가 서로 다른 모양 |

Frame 선택만으로 playhead를 움직이지 않는 정책을 채택했다. ruler와 별도 frame strip이라는 공간적 구분 및 도움말로 “선택인가 이동인가”를 명확히 한다. Cel selection/TimeRange/Tag/Onion/Playback scheduler는 Phase1 구현 대상이 아니다. 기존 ARCH의 전체6 domain 중 이번에는 Frame/Key/Layer/Playhead4개만 구현했다.

**미구현:** 실제 데이터 mutation, Undo, clipboard, frame insertion/delete/reorder, key 이동/복제, duration/timebase 편집, production adapter/command bridge. 지원하지 않는 동작을 기존 layer/key 명령으로 fallback하지 않는다. 기존 단축키 registry는 건드리지 않았다.

구조적으로 per-cell QWidget/QTableWidgetItem이 없다. native viewport + scrollbars 등 QWidget descendants는5개다. frame 범위/row 범위를 먼저 계산한 뒤 grid lines, visible selection, 해당 row/span의 sparse keys만 그린다. key hit도 해당 위치의 최대3개 frame 후보만 조회한다. Qt 폰트/paint 내부 cache는 Qt가 관리하며 그 native 메모리는 측정하지 않았다.

## 3. 좌표·상태 및 회귀 검증

- Pure 검증: 12/120/1000/10000 frame, widths8/31.5/160, fractional scroll, row mapping, endpoint/outside, zoom/clamp, Shift/Ctrl/anchor, drag threshold/취소, key/layer 이동 방지, immutable adapter, production import 부재.
- 각 DPR child의 geometry probe는 유효 center 좌표 **1125회 왕복** 검사. paint와 hit는 같은 logical geometry를 쓴다. DPR을 event 좌표에 다시 곱하지 않는다.
- QTest 실제 입력: frame click/Shift/Ctrl, range drag, ruler scrub, key/layer click, keyboard/plain vs Shift, Ctrl-wheel, pan, Escape snapshot 복원, Home/End/reveal. frame selection과 playhead를 각각 별도 oracle로 검사한다.
- scrollbar 정수화 후 zoom anchor 오차 **0.5 DIP**. DPR1/1.25/1.5 모두 같다. font size100/125/150%는 DPR과 별개로 교차 검사한다.
- 합성 screenshot **36장**: 3 DPR ×2언어 ×2테마 ×3폰트 크기. KO 좁은 폭620/EN900, header/row containment와 physical PNG 크기, 실제 resolved font 및 숫자/Latin/한글 glyph 지원 검사.
- 첫 PNG에서 Windows offscreen 기본 `Sans Serif`가 tofu로 보이는 것을 직접 관찰했다. 설치 font read fallback을 추가하고 새 PNG에서 Latin/숫자/한글이 정상인 것을 시각 확인했다. 이 수정은 POC 전용이며 production 폰트/시스템 설정을 변경하지 않는다.
- 신규 테스트 초기 실행은62 PASS/4 FAIL: immutable adapter 예외를 ValueError로 잘못 기대한 테스트 오류였다. FrozenInstanceError로 정정 후 **66 PASS/4.33s**. 이후 관련 기존 timeline/keyboard93개와 함께 **159 PASS/12.35s**.
- 진단 개발 중 zoom-error 메타데이터 계산이 pan 후 geometry를 참조하는 오류도 수정했다. 실제 zoom assertion은 통과하고 있었으며, 이제 zoom 직후 오차를 저장하고 JSON oracle도 검사한다. 위159 PASS에는 이 oracle이 포함된다. 최종 독립 진단은 아래 경로의 fresh run이 근거다.
- 최종 독립 진단 `C:\Dev\pem_timeline_poc_final_20261030\report.json`: **3 DPR probes PASS**, 각3 core checks, 12 workload metrics,12 PNG, 종료 후 top-level widgets0. 총36 workload/36,000 actual hit-test queries. 이는 production core175를 재실행했다는 뜻이 아니다.
- production 코드 변경이 없으므로 full pytest는 반복하지 않았다. 기존 full1971 PASS/1 SKIP은 과거 baseline이다. 이번159 PASS와 구별한다.

기존 테스트와 QApplication/font/style 상태를 공유하지 않도록 POC Qt 검사는 fresh subprocess로 실행한다. 별도 core registry 변경/자동 등록은 하지 않았다. wait는 조건+명확한 timeout이며 고정 sleep으로 완료를 추정하지 않는다.

## 4. 실측 성능과 해석

환경: Windows / Python3.12.14 / PySide6 6.11.1 / offscreen / Fusion. 900×440 logical widget, 32 DIP/frame, font 초기화 뒤 반복. 각 workload redraw9회 median/nearest-rank p95(9회에서는 최댓값). `QWidget.viewport().grab()`는 paint+image allocation이 포함되며 실제 모니터/입력 end-to-end latency가 아니다. init은 constructor와 구성 비용이며 first paint/process startup을 포함하지 않는다. init 동안 tracemalloc을 켰고 **Python 할당만** 관찰했다. RSS/Qt native 메모리 실측은 하지 않았다.

### 4.1 POC, DPR100%, 24 tracks

| Frames | Init ms | Grab median / p95 ms | 마지막 paint ms | 실제 hit1000회 ms | visible frame×row | keys | QWidget descendants |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 12 | 0.392 | 1.059 /1.705 | 0.704 | 1.626 | 12×14 | 11 | 5 |
| 120 | 0.507 | 1.023 /1.153 | 0.784 | 1.831 | 21×14 | 21 | 5 |
| 1000 | 0.398 | 1.271 /1.414 | 0.992 | 2.219 | 21×14 | 21 | 5 |
| 10000 | 0.463 | 1.177 /1.413 | 0.812 | 2.255 | 21×14 | 22 | 5 |

frame/track 전체 수가 아니라 visible span을 그리는 것을 **실제 header/query/key/grid 방문 수**로 검증했다. Qt descendants count와 QTableWidget descendants0도 조회했다. JSON의 per_cell_objects0/raster_cache_bytes0은 별도 cell/raster-cache 구조가 없다는 구조 선언이며 Qt native heap을 측정한 값은 아니다. selection set은 선택한 frame 수에 비례하고, paint 중 visible frame membership만 조회한다. 전체 데이터가 항상 O(1) 메모리라는 주장은 하지 않는다.

각 DPR에서4 frame counts×3 track counts(4/24/200)를 검사했다. 12 workloads 중 최대 grab p95는 DPR1 **1.798ms**, DPR1.25 **3.434ms**, DPR1.5 **3.668ms**였다. 단일 환경·작은 표본의 관측값이지33ms UI gate/60FPS/실제 production 성능 보장은 아니다.

### 4.2 최소 QTableWidget 기준과 동등 count 비교, DPR100%

| Frames×tracks | POC init ms | 최소 table init ms | POC grab median ms | 최소 table grab median ms | table items |
| --- | --- | --- | --- | --- | --- |
| 12×24 | 0.392 | 1.531 | 1.059 | 1.486 | 288 |
| 120×24 | 0.507 | 6.368 | 1.023 | 3.332 | 2880 |
| 1000×24 | 0.398 | 57.182 | 1.271 | 3.100 | 24000 |
| 10000×4 | 0.446 | 114.564 | 0.706 | 1.019 | 40000 |

비교 table은 동일 font/32px column/28px row로 `·` QTableWidgetItem을 모두 채운 **독립 synthetic 최소 기준**이다. production Timeline 클래스는 import/실행하지 않았다. header 공간/표시 내용/key/선택/이벤트/전체 refresh 기능이 동등하지 않으므로 end-to-end 제품 속도 배수로 환산하지 않는다. table 초기 full item allocation과 POC의 viewport 구조 비용 차이를 관찰한 것이다. table도 viewport redraw 자체는 전체 item을 매번 그리는 것이 아니다.

tracemalloc peak(24 tracks): POC 약4.9~5.3KB, table12/120/1000 frames 약17.8KB/163KB/1.346MB. native Qt allocations, 이미 로드된 font cache, RSS를 포함하지 않는다. 다른 세션/기계에서 이 숫자는 달라진다. 10000×200을 최소 table에 만들지 않았으며 측정한 것처럼 외삽하지 않는다.

최종 JSON/PNG는 위 C:\Dev 경로에 남겼고 repository에는 복사하지 않았다. 측정 workload/표본 수/환경과 전체 raw metrics를 JSON에서 확인할 수 있다.

## 5. 접근성·HiDPI·Native QA 한계

- native scrollbars, StrongFocus/Tab routing, standard tooltip, readable accessibleName/Description, native combo controls를 재사용한다. QWidget painted frame/key/layer의 개별 QAccessibleTable/Action/virtual-cell navigation은 **아직 미구현**이다. screen reader 승인 불가.
- keyboard frame navigation/Shift selection은 자동 검증됐다. 개별 layer/key를 keyboard-only로 탐색·선택하는 완전한 대체 경로, context command/IME editor는 Phase1에 없다. 실제 Windows IME/Tab/고대비/multi-monitor/capture loss·touchpad는 NOT VERIFIED.
- font scale과 process DPR 합성 검증은 실제 Windows 125/150% 모니터 전환을 대신하지 않는다. 설치 font fallback은 runtime 시스템 font 읽기이며 font 파일을 제품에 포함하지 않는다. 다른 OS에서 KO font가 없으면 visual 진단은 FAIL로 남기고 해결 전 합격시키지 않는다.
- paint는 전체 **visible viewport**를 다시 그린다. old/new playhead dirty rect 최적화, marquee auto-scroll, long-range selection의 압축 interval 모델, prefix row virtualization/hierarchy, 100k frame 및 OS RSS 측정은 후속이다.
- header resizing/실제 이미지 thumbnail/애니메이션 playback/Timing exact duration 모델은 없다. ruler는 frame 단위이고 독립 timebase 수학을 변경하지 않는다.
- B 구조의 Phase1 구현 가능성과 cell allocation 없이 확장할 가능성을 확인했다. **접근성/Native/production command parity 전체 gate를 통과한 것이 아니므로 Resource Pilot 자동 착수나 기존 UI 제거를 승인하지 않는다.** 필요하면 ARCH의 A(model/delegate) 대안을 유지한다.

공식 API 참고: [QAbstractScrollArea](https://doc.qt.io/qt-6/qabstractscrollarea.html), [Qt High DPI](https://doc.qt.io/qt-6/highdpi.html), [Qt for Python QAbstractScrollArea](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QAbstractScrollArea.html). 문서 API를 참고했으며 실측 runtime은 위6.11.1이다.

## 6. Git·작업 목록·기존 기능 보호

이번 추가는 `tools/timeline_poc/*.py`10개, 신규 테스트2개, 이 보고서이며 기존 파일 수정은 `docs/tasks/WORK_QUEUE.md`뿐이다. Python bytecode/test artifacts는 ignored 또는 외부 C:\Dev에 위치한다. 기존381개 tracked/untracked 시작 파일의 hash를 대조했으며 queue만 달랐다. 기존 production/테스트/도구/감사 문서는 byte-for-byte 보존됐다. 새 경로13개, 전체 관리 대상394개다.

TIMELINE-CUSTOM-POC는 **DONE(Phase1 자동 범위)**, 접근성/Native 미검증은 후속 gate로 남긴다. TIMELINE-MIGRATION은 BACKLOG, Resource/Effect production 연결은 별도 승인·parity 단계가 필요하다. 기존 CP1/CP2/CP3/CP4 계획과 TIMING-1/2/Single speed/ASE/Effect Backlog를 유지한다.

**사용자 Resource→Effect 회전 재생 문제는 여전히 미해결**이다. TIMING-ROTATION-USER와 CP2용 TIMING-FPS-CHECKPOINT 및 의존 checkpoint는 BLOCKED 유지. synthetic POC 성공/자동 FPS fixture PASS는 사용자 재생 승인이 아니다.

보호 PNG SHA-256 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`, HEAD/v0.0.25/FORMAT22/staged0 유지. Window Use0. Commit/Tag/Push/Build/PyInstaller/ZIP 및 파괴적 Git 명령/권한·Git 설정 변경 없음. 종료 시 compileall/`git diff --check` 통과, 기존 파일 hash 확인, 잔류 Python 프로세스0을 확인했다.
