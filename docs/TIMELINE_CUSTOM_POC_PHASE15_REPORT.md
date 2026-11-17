# TIMELINE-CUSTOM-POC Phase 1.5

2026-10-30 — Navigation UX / Edge Auto-Scroll / Explicit CellRange / Visual Refinement.

**구현·자동 검증 보고서다. 사용자 Native 품질 승인이 아니며 기존 Resource/Effect Editor를 교체하지 않는다.**

## 1. Baseline / Git 보호

- 실제 HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`, v0.0.25, FORMAT22, staged0. 시작 시 tracked+untracked 관리 대상394개를 SHA-256 inventory로 기록했다.
- `AGENTS.md`, WORK_QUEUE, TIMELINE_CUSTOM_ARCHITECTURE_AUDIT, Phase1 보고서 및 POC 전체 구현/테스트를 확인했다. 기존 UX-2/Timing/FPS/DevEx/Phase1 변경은 보존한다.
- 사용자 Native 평가: **번호·현재 위치 좋음 / Frame 및 Shift·Ctrl 선택 좋음 / Playhead 분리 좋음**. 세 계약은 유지한다. Wheel/Scroll/Zoom은 개선 요구, 한글·색상·key 모양은 미확인이다.
- 보호 PNG SHA-256 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`. 이미지 로드·수정·이동·stage 없이 hash만 확인한다.
- 변경 허용 범위는 `tools/timeline_poc`, 신규 POC tests, 이 보고서, WORK_QUEUE다. app/ui·모델·renderer·FPS·Undo·Clipboard·core175 registry·FORMAT/버전은 수정하지 않는다.

## 2. 기존 Scroll / Zoom / Pan 경로 분석

| Phase1 경로 | 실제 동작 | 판정 |
| --- | --- | --- |
| wheelEvent, 일반 angleDelta | bar.singleStep×3×angle/120, 매번 round해 정수 bar에 기록 | 보통120단위 wheel의 세로 이동은 동작. 작은 delta의 정수화 편향/누락 경로 있음 |
| Shift-wheel | 동일 식으로 horizontal bar 변경 | 방향 자체는 정상. 작은 zoom 폭에서 fractional 이동이 사라질 수 있음 |
| pixelDelta | pixel을 우선 사용하지만 축 판단은 angleDelta 기준, `pixels.x() or pixels.y()` 선택 | pixel-only 수평 입력이 vertical bar로 잘못 갈 수 있는 코드 경로 확인 |
| Ctrl-wheel | cursor anchored geometry.zoom_at 후 bar에 round, `_read_scroll`로 정수 재수집 | anchor 계산 자체는 이미 존재. geometry의 fractional 위치가 보존되지 않아 왕복 양자화 위험 |
| MMB | press 시 scroll origin, move에서 Grab-and-Pan, release/기존 focus/capture 처리 | 기존 기능 유지. 새 Selection Auto-Scroll과 소유권 분리 필요 |
| scrollbar / resize | native bar ranges와 geometry를 동기화 | native scrollbar 유지. 새 fractional geometry와 bar의 정수 표현을 명시적으로 분리해야 함 |
| drag | frame range/scrub/key click/layer click 상태 기계 | Timer 없음. MouseMove 없이 정지한 pointer는 범위를 더 확장할 수 없음 |
| painting / DPR | visible rows/frames, DIP 좌표, nearest sparse key lookup | 유지. DPR을 좌표에 다시 곱하지 않음 |

이 감사는 기존 POC의 입력 경로 분석이다. Production Timeline이나 사용자 회전 결함의 원인을 이 코드로 판정하지 않는다. 기존의 모든 wheel/zoom/pan이 고장났다고 주장하지 않는다.

## 3. 확인된 Navigation 문제와 수정

### 재현 근거

`test_phase1_small_horizontal_wheel_rounding_reproducer`는 Phase1 식을 그대로 재현한다. min zoom8에서 angle1의 가로 이동은0.2 DIP. 정수 scrollbar1000에10번 각각 더해 round하면 **1000 그대로**, fractional 위치를 유지하면 **1002**다. 이는 과거 식의 bounded 재현이며 원본 production GUI를 복제 실행한 것은 아니다.

pixel-only horizontal 입력은 Phase1의 `abs(angle.x)>abs(angle.y)`가 false인 경우 vertical bar로 분기한다. 새 실제 QWheelEvent probe는 pixel(-3,0)이 가로로만3 DIP 이동하는지 검사한다.

### 현재 구현

- 신규 `navigation.py:wheel_motion`: pixelDelta가 있으면 angleDelta를 더하지 않는다. native horizontal/two-axis pixel 입력을 구별하고 Shift는 가로로 제한한다. 기본 angle wheel은 세로, horizontal wheel은 가로다. OS가 넘긴 delta 부호를 그대로 소비하며 `inverted()`를 다시 뒤집지 않는다.
- geometry의 float scroll offset이 authoritative다. native scrollbar는 round한 정수 표현이며 오차는0.5 DIP 이하. 프로그램 갱신 guard로 feedback 재수집을 막고, 사용자 bar 이동만 해당 축의 authoritative offset을 바꾼다.
- 작은 angle/pixel 입력은 float 위치에 누적한다. angle 입력은 Qt styleHints의 wheelScrollLines, 프레임 폭/행 높이를 사용한다. 한 이벤트의 과대한 이동은 해당 viewport span으로 제한한다. 인위적인 smoothing/inertia queue는 추가하지 않았다.
- zoom은 기존 `TimelineGeometry.zoom_at`을 공유하며 rounding된 bar 위치를 계산 원점으로 재사용하지 않는다. 실제 QWheelEvent50회 왕복에서 x offset 오차0.0 DIP 관측. min8/max160 경계의 추가 zoom은 위치 불변을 검사했다. 경계 clamp가 필요한 경우까지 cursor 아래 위치 보존을 보장하지는 않는다.
- `−/+ / Fit / Reset`도 같은 zoom 경로를 사용한다. 표시를100% 기준 배율로 변경했다. Fit은8..160 DIP 제한 내 맞춤이며 10k frame 전부를 한 화면에 맞출 수는 없다. tooltip에 제한을 남겼다.
- MMB Pan은 선택·playhead를 바꾸지 않는다. Escape/Release/focus/capture/hide/close로 종료한다. Resize 뒤 range/position/좌표를 재검증한다.

## 4. Edge Auto-Scroll / Frame×Track 선택

### 명시적 조작 계약

| 시작 위치 / 모드 | 선택 | 자동 스크롤 | 변경하지 않는 상태 |
| --- | --- | --- | --- |
| frame 번호 strip | 기존1D Frame 범위 | 좌/우만 | Key/Layer/CellRange/Playhead |
| body 기본 ‘프레임 범위’ | Phase1과 같은1D Frame 범위 | 좌/우만 | Key/Layer/CellRange/Playhead |
| body **‘셀 범위’ 명시 모드**, 빈 셀 | 독립2D CellRange | 좌/우/위/아래/대각선 | Frame/Key/Layer/Playhead |
| key diamond | 기존 key click/Ctrl 선택 | 없음 | 다른 domain |
| layer header | 기존 layer click/Ctrl 선택 | 없음 | 다른 domain |
| ruler / playhead handle | scrub | Selection Auto-Scroll 없음 | Frame/Key/Layer/CellRange |
| MMB | Pan | Selection Auto-Scroll 없음 | 모든 selection / Playhead |

본체의 기존 조작을 조용히 바꾸지 않았다. 상단 mode combo 기본값은 ‘프레임 범위’다. 2D 선택은 **셀 범위 모드를 고른 후 빈 본체에서 drag**한다. key hit 우선순위는 유지한다. layer header 자체의 range drag/reorder는 새로 구현하지 않았다. 화면 밖 트랙 선택은 CellRange로 수행하며 LayerSelection set으로 바꾸지 않는다.

### 구현 경계

- `selection.py:FrameIntervals`: sorted disjoint half-open intervals, contiguous10k frame은 interval1개. Ctrl toggle은 split/merge, Shift는 기존 anchor 의미 유지. 임의 sparse toggles의 비용은 interval 수에 비례한다.
- `CellRange`: anchor_frame/row + active_frame/row, 필드4개. 범위와 크기를 계산할 뿐 frame×track 객체를 열거하지 않는다. 순수 UI 상태이며 실제 데이터 mutation은 없다.
- `interaction.py`: threshold 전 Pressed, 이후 Dragging. anchor 고정, geometry에 따른 endpoint만 갱신. Escape 및 취소는 press 이전 snapshot을 복원한다. frame strip은 CellRange에 영향을 주지 않는다.
- 신규 `autoscroll.py:EdgePolicy`: frozen header를 제외한 body bounds 기준. edge band 기본28 DIP(매우 좁은 body에서는 축소), 거리별 연속 증가, 최대24 frames/rows per second. unit은 현재 frame width/row height다.
- `view.py`: view 소유 precise QTimer16ms **하나**. 실제 nsecs elapsed로 이동량을 적분하며50ms보다 긴 backlog는 버린다. 첫 tick부터 고정 큰 pixel jump를 넣지 않는다. active selection drag/held left button/visible viewport일 때만 동작한다.
- 포인터 좌표는 마지막 mouse event를 보존한다. 포인터가 멈춰 있어도 timer가 scroll을 갱신하고 **새 geometry로 endpoint를 다시 계산**한다. MouseMove 빈도로 속도가 결정되지 않는다.
- scroll 경계에 도달하거나 body 내부로 돌아오면 timer가 멈춘다. release 즉시 stop/commit. Escape/focus/capture loss/hide/close는 stop/cancel. native Qt의 implicit mouse grab에 의존하며 global event filter/실제 OS 마우스 제어는 없다.
- timer callback 비용 표본은 최대128개만 유지한다. tick마다 추가 timer/worker/대기열/model rebuild를 생성하지 않는다.

## 5. 스크린샷 기반 소규모 시각 개선

요청서의 화면 관찰 항목 및 기존 Phase1 합성 PNG와 비교했다. 별도의 사용자 Native 원본 이미지 파일이 이번 첨부에 제공된 것으로 취급하지 않는다.

- major/minor stride를1/2/5 계열 helper로 통합했다. 주요 ruler 간격은 minor의5배다. frame 번호는 계속1-based, label 폭에 따라 밀도를 줄이고 viewport 끝에서 잘린 숫자는 그리지 않는다.
- 기존 노란 handle/수직선과 key diamond를 유지했다. handle hit width20 DIP는 좁은8 DIP frame에서도 이웃 frame으로 튀지 않는 실제 click probe를 추가했다.
- Frame 범위는 dashed 경계, CellRange는 별도 얕은 tint/dashed rectangle와 끝점 사각 marker를 사용한다. 선택이 화면 밖으로 이어지면 방향 marker를 그린다. Key는 그 위에서 계속 그리며 선택 key outline도 유지한다.
- 긴 label elide 유지, 실제 QHelpEvent로 전체 한글 원문 tooltip을 검사했다. 고정 header는 기존 compact 폭 계산을 유지했다.
- 작은 zoom controls와 mode selector를 추가했고, 확대율과 CellRange F/T 범위를 상태 줄에 표시한다. screenshot에서 KO Dark/EN Light 좁은 shell과 native controls를 함께 확인했다.
- layout/색상 체계를 전면 재설계하거나 gradient를 추가하지 않았다. 한글·색상·key 가독성 **사용자 승인은 여전히 NOT VERIFIED**다.

최종 합성 예시:

![KO Dark cell range](C:/Dev/pem_timeline_poc15_verified_20261030/scale-125/navigation-shell-ko-dark.png)

![EN Light narrow](C:/Dev/pem_timeline_poc15_verified_20261030/scale-125/navigation-shell-en-light-narrow.png)

## 6. 테스트 / 기존 회귀 / 독립 진단

- Phase1 기존 두 테스트 파일과 assertion은 변경하지 않았다. 기존66 PASS 유지.
- 신규 `test_timeline_poc_navigation_logic.py`:33 cases. wheel source/axis/fractional input, Phase1 rounding 재현, zoom roundtrip/limits, edge 방향/거리/속도 상한/dt/bounds/비선택 배제, interval와 independent CellRange, ruler density.
- 신규 `test_timeline_poc_navigation_offscreen.py`:22 cases. 기존 QApplication과 공유하지 않는 fresh `--verify` subprocess에서3 DPR의21 navigation cases를 재사용한다. direct `_auto_tick()` 호출이 없는지도 검사한다.
- 실제 Qt probes: stationary pointer에서3tick 이상 진행, frame-only 수평, cell 상하·좌우·대각선, edge 진입/이탈/시작·끝,8/160 zoom, frozen header, anchor 불변/domain 독립, release/취소5경로, Pan/Scrub 배제, mode/zoom native controls/tooltip/handle/resize.
- Timer 검증은 직접 callback을 부르지 않는다. event loop+bounded completion deadline, 종료 후 `registeredTimers(auto_timer)==[]`, 별도 native marker timer2회 동안 scroll/selection/tick 불변을 확인한다. fixed sleep으로 성공을 추정하지 않는다.
- 관련 기존93개 포함213 PASS/27.86s, 최종 label edge 보완 뒤 POC120 PASS/18.38s, 추가 rounding 표현 재현을 포함한 pure33 PASS/0.13s. **최종 동일 소스 누적 회귀214 PASS/24.91s** (`C:\Dev\pem_poc15_regression_final_20261030`): Phase1 기존66 + Phase1.5 신규55 + 기존 Timeline/keyboard93. 전체 pytest/core175는 재실행하지 않았다.
- 독립 진단 `C:\Dev\pem_timeline_poc15_verified_20261030\report.json`: **DPR1/1.25/1.5 모두 PASS**, 기존 checks3 + navigation checks21 각각 PASS.36 workload metrics/36,000 hit queries, 기본 PNG36 + shell PNG6 =42장. 종료 후 top-level widgets0.
- core175 registry는 그대로다. 기존 report schema1에 별도 navigation 결과를 추가했으며 production pytest/registry에 강제로 묶지 않았다. JSON에는 합성 상태/관측 수치/상대 PNG 이름만 기록하며 사용자 모델·이미지/traceback locals를 수집하지 않는다.

실행 예:

```powershell
Set-Location -LiteralPath 'C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker'
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' -m tools.timeline_poc --verify --compare-table --output C:\Dev\pem_poc15_review_new
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' -m pytest tests/test_timeline_poc_logic.py tests/test_timeline_poc_offscreen.py tests/test_timeline_poc_navigation_logic.py tests/test_timeline_poc_navigation_offscreen.py -q -p no:cacheprovider
```

## 7. 성능 관측과 한계

Windows / Python3.12.14 / PySide6 6.11.1 / Fusion offscreen. 아래24 tracks, DPR1,900×440 logical widget,32 DIP/frame.9 grabs의 median/nearest-rank p95이며 native 화면 latency/60FPS 보장이 아니다.

| Frames | Init ms | Grab median / p95 ms | Phase1의 grab median ms(별도 과거 실행) |
| --- | --- | --- | --- |
| 12 | 0.490 | 1.315 /1.736 | 1.059 |
| 120 | 0.503 | 1.146 /1.599 | 1.023 |
| 1000 | 0.493 | 1.284 /1.797 | 1.271 |
| 10000 | 0.816 | 1.170 /1.487 | 1.177 |

Phase1과 새 동작/paint 비용이 달라졌고 실행 세션도 다르므로 직접 인과적 speedup/퇴행 배수로 해석하지 않는다. raw JSON에는12/120/1000/10000 frames×4/24/200 tracks가 있다. 최소 generic QTableWidget baseline도 별도 측정했다(1000×24 init58.646ms/grab median3.124ms). production 기능 parity가 없으므로 제품 성능 비교가 아니다.

10k×200 = **2,000,000 logical cell 선택**은 Frame interval1개 + CellRange 필드4개로 유지된다. 선택 구성0.0285ms, Python traced peak1104 bytes 관측(선택 구성 구간만, Qt native/RSS 제외). QWidget descendants5, paint 방문21 frames×14rows/key20개, CellRange rectangle1개였다. pure test는100k contiguous frame도 interval1개로 확인한다.

DPR1의 실제 timer callback 표본: mode/direction별 median 약0.096~0.173ms, 최대0.230ms. 각 case에서 최소3개 정상 tick의 작은 표본이며 paint는 별도 event에서 수행된다. 실제 input-to-screen latency나 load 중 스케줄러 성능을 측정한 값이 아니다. recorder128개 상한, 종료 후 추가 tick/scroll/selection 변화0을 검사했다.

선택 중 viewport 밖 데이터 셀을 만들지 않는다. 다만 매 갱신마다 전체 **visible viewport**를 다시 그리며, 많은 Ctrl toggle의 비용은 interval 수에 비례한다. native RSS/장시간 부하/실제 touchpad 관성/100k paint 검증은 하지 않았다.

공식 API 근거: [QWheelEvent](https://doc.qt.io/qt-6/qwheelevent.html)의 pixel/angle 입력·부호, [QTimer](https://doc.qt.io/qt-6/qtimer.html)의 이벤트 루프 timer, [QWidget mouse grab](https://doc.qt.io/qt-6/qwidget.html#grabMouse)의 native capture를 참고했다. API 문서 최신 페이지와 별개로 실제 검증 runtime은6.11.1이다.

## 8. 사용자 Native QA — 미확인

기존 정상 평가 세 가지를 유지했지만 아래 새 동작은 사용자가 직접 확인하기 전까지 **NOT VERIFIED**다. Window Use는0회다.

```powershell
Set-Location -LiteralPath 'C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker'
& 'C:\Dev\pixel_effect_test_venv\Scripts\python.exe' -m tools.timeline_poc --frames 10000 --tracks 200 --language ko --theme dark
```

1. 기본 모드에서 번호·Frame/Shift/Ctrl 선택·Playhead 분리가 그대로인지.
2. 일반 Wheel 세로 / Shift-wheel 가로 이동이 자연스러운지.
3. pixel/angle 실제 마우스·touchpad 방향·이동량과 Ctrl-wheel anchor가 적절한지.
4. 가운데 버튼 Grab-and-Pan, Escape/Release/포커스 전환이 편하고 안전한지.
5. frame strip에서 오른쪽/왼쪽 밖으로 drag한 채 멈춰도 범위가 계속 늘어나는지.
6. **셀 범위 모드**를 고르고 본체 빈 셀에서 아래/위/좌/우/대각선으로 drag하면 보이지 않는 frame·track까지 확장되는지.
7. release 즉시 중단하고 Esc/창 전환/숨김/닫기 후 남은 움직임이 없는지.
8. frame 번호/major-minor 눈금/긴 label tooltip/key diamond/선택 경계/확대율이 읽기 좋은지.
9. KO/EN, Light/Dark,100/125/150% 실제 Windows DPI·여러 모니터·IME/고대비 조합.

실제 OS mouse capture 전달과 touchpad 동작을 합성 QTest가 완전히 보장하지 않는다. virtual-cell accessibility 및 layer/key keyboard-only 전체 지원도 여전히 미구현이다. Resource Pilot/기존 UI 교체 승인은 별도다.

## 9. Work Queue / 회전 문제 / 종료 상태

Phase1 DONE 유지. Phase1.5는 구현·자동 검증만 완료하고 별도 Native QA 항목을 BLOCKED로 남긴다. 한글·색상·key 가독성을 완료 승인하지 않는다. TIMELINE-MIGRATION/Timing1·2/Single speed/ASE/Design System/Effect Backlog 및 CP1/2/3/4 계획은 보존한다.

**TIMING-ROTATION-USER는 여전히 미해결, CP2/의존 checkpoint는 BLOCKED다.** 이 POC의 성공은 사용자 Resource→Effect 회전 재생 승인과 무관하다.

종료 확인: 시작394개 파일의 hash 대조에서 변경은 POC 기존7모듈과 WORK_QUEUE뿐이다. 신규6개(POC3모듈/테스트2/이 보고서), 총 관리 대상400개다. Production/기존 테스트/과거 보고서 hash 변경0. HEAD/v0.0.25/FORMAT22/staged0·보호 PNG hash 일치, compileall/`git diff --check`/POC trailing-whitespace 검사 PASS, 잔류 Python 프로세스0.

모든 작업 unstaged/uncommitted. Stage/Commit/Tag/Push/Build/PyInstaller/ZIP/파괴적 Git/권한·Git 설정 변경0. Window Use0. 사용자 한글·색상·key 및 새 navigation 승인, production 전환, 사용자 회전 해결을 이번 자동 결과로 주장하지 않는다.
