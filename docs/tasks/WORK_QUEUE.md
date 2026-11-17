# Persistent Work Queue

현재 작업 상태의 기준은 대화 기억이 아니라 이 파일이다. 완료 항목도 삭제하지 않는다.
상태는 NOW / NEXT / BLOCKED / BACKLOG / DONE, 우선순위는 P0(신뢰성)~P3(후속 확장)이다.
자동 실행·외부 변경 권한이나 일정 약속을 뜻하지 않는다. 새로운 사용자 요청이 우선한다.

## 작업 규약

1. 작업 시작 전에 이 파일과 연결된 관련 문서를 읽는다.
2. 현재 NOW를 확인하고 이번 작업을 표시한다. 보류된 항목은 삭제하지 않고 상태·의존성을 유지한다.
3. 완료 시 결과·명령·테스트·남은 수동 QA를 갱신한다. 자동 테스트와 native 수동 QA를 구분한다.
4. 범위/선행 조건이 달라지면 이유를 기록한다. 새 기능을 진단 기반 구축에 끼워 넣지 않는다.
5. checkpoint는 별도 권한이다. 이 문서의 NEXT가 commit/push/build 승인이라는 뜻은 아니다.

## 현재 기준과 문서 차이

- 2026-10-29 시작: v0.0.25 / FORMAT22, HEAD `ca9ed1c287022a653b96c2d75f81ea737b94d5f1`, full pytest1888, UX-2와 수정은 미커밋이다.
- [ROADMAP](../ROADMAP.md)은 v0.0.03 기준의 역사적 방향이며 현재 완료 상태와 다르다. 기존 범위/장기 계획을 삭제하지 않는다. 실행 순서·상태는 이 queue가 소유한다.
- 예: ROADMAP의 Composition/keyframe 복제·재정렬·다중 선택 일부는 이미 구현되었지만 그래프/Timing/프레임 블록 작업은 남아 있다. Aseprite GIF bridge는 원본 timing/metadata exact 보존 완료를 뜻하지 않는다.
- [Timing 설계](../ASEPRITE_TIMING_TIMELINE_ARCHITECTURE_AUDIT.md), [UX 원칙](../UI_UX_PRINCIPLES.md), [최근 회귀 보고](../UX2_NATIVE_REGRESSION_REPAIR_REPORT.md), [DevEx-1](../DEVEX1_DIAGNOSTICS.md).

## 작업 목록

현재 준비 결과: **UX2-FINAL-PREP / DONE / P1** — 자동 검증·파일/hunk 의존성·격리 후보 계획 작성 완료.
이는 UX2/native 승인이나 실제 checkpoint 완료가 아니다. 상세: [최종 준비 보고서](../UX2_FINAL_VERIFICATION_CHECKPOINT_PREPARATION.md), [파일 manifest](../UX2_CHECKPOINT_FILE_MANIFEST.md).

| Stable ID | 상태 / 우선순위 | 목적 | 선행 조건 | 완료 조건 | 관련 문서/테스트 | 남은 사용자 수동 QA |
| --- | --- | --- | --- | --- | --- | --- |
| DEVEX-1 | DONE / P0 | Integrated Diagnostics Foundation; 기존 검사를 콘솔/JSON으로 통합 | 기존1888 baseline·UX2 보존 | 구현/자동 검증 완료; 독립 checkpoint는 미추적 UX2 의존성으로 BLOCKED, 아래 분리안 참조 | DEVEX1_DIAGNOSTICS.md; UX2_VERIFY_CHECKPOINT_REPORT.md; test_diagnostics_cli.py; tools/diagnose_editor.py | native 수동 미실행; 실제 symlink 생성 검사1개는 계정 권한으로 SKIP, CLI 실행 체감 |
| DEVEX1-CHECKPOINT | BLOCKED / P0 | DevEx 파일만의 완결된 local checkpoint | 실제 CP1(UX2+B)→CP2(FPS)→CP3(SpinBox) 및 사용자 승인 | 누적 격리 CP4 core175 PASS·CLI35 PASS/1 SKIP 검증됨; 실제 선행 commit 후 명시 목록 검토/승인 필요 | UX2_FINAL_VERIFICATION_CHECKPOINT_PREPARATION.md; UX2_CHECKPOINT_FILE_MANIFEST.md | HEAD에 DevEx-only 독립 아님; 실제 commit은 미실행 |
| DEVEX-ERROR-REASON | BACKLOG / P2 | 미존재 pytest 파일/node의 ERROR 설명 보강 | 별도 수정 범위 승인; DevEx 기존 schema/exit 유지 | pytest exit4에서도 reason이 비지 않고 재현 node/원인을 민감 정보 없이 보고; timeout/cleanup/exit 회귀 유지 | UX2_VERIFY_CHECKPOINT_REPORT.md; C:\Dev\pem_checkpoint_candidate_result\report.json; tools/diagnostics/worker.py | Native QA 없음; 이번 검증에서는 발견·기록만 수행 |
| UX2-VERIFY | BLOCKED / P0 | 실제 Windows에서 UX-2 최종 확인 | 기존 회귀 수정 + DEVEX-1 | 자동175 PASS/직전full1971 PASS와 사용자 QA 분리; 회전 사용자 미해결로 전체 승인 아님 | TIMELINE_CUSTOM_ARCHITECTURE_AUDIT.md; UX2_FINAL_VERIFICATION_CHECKPOINT_PREPARATION.md | 2026-10-30 사용자 Lifetime/Group/Gizmo/한글 UI 정상 확인; Resource→Effect 회전 미해결; 나머지 DPI/IME 등은 포괄 승인 아님 |
| UX2-GIZMO-SYNC | DONE / P1 | 기즈모→Inspector 콜백 완료 전 assertion race 수정 | 기존 경로 자연 재현2/24; 생산 코드 변경0 | 조건 대기1000ms·정확한 값/필드·layout<=3 유지; 선행102 tests 후24/24·UI74 PASS·최종 full 대상 PASS | UX2_GIZMO_SYNC_REPAIR_REPORT.md; test_interactive_transform_proxy.py::test_gizmo_updates_only_changed_inspector_field_without_layout | offscreen 검증 완료; 2026-10-30 사용자 Gizmo 정상 확인. 모든 DPI/IME 조합 승인과는 별개 |
| UX2-LIFECYCLE-ISOLATION | DONE / P1 | UI navigation과 다른 Qt 작업의 render 통계 격리 | 기존 UX2/DevEx/Gizmo 변경 보존 | closed-window idle prewarm 호출 재현·정리 수정; bounded 완료 후 Dirty0/Render0 각각 검사; UI78·full1928 PASS/1 SKIP | test_v9_editor_lifecycle_integration.py; test_lifecycle_prewarm_isolation.py; UX2_LIFECYCLE_ISOLATION_REPORT.md | Window Use0; native QA 기존 대기 유지 |
| UX2-CHECKPOINT | BLOCKED / P0 | UX-2 및 회귀 수정의 Local Checkpoint | UX2-VERIFY 및 명시적 commit 승인; 전체 회귀 FAIL 해소 | 범위별 diff·보호파일·전체검증 확인 후 승인된 local commit | UX2_PARTICLE_INSPECTOR_REPORT.md; 회귀 보고들 | 실제 native 승인; 현재 작업은 production commit을 승인하지 않음 |
| TIMING-1 | NEXT / P1 | ms/frame 기본 표시와 FPS 전환 preference; 다음 기능 후보 | UX2-VERIFY → UX2-CHECKPOINT 선행; Timing 설계 재확인 | 표기 preference와 실제 FPS 데이터 분리, exact roundtrip; Undo/dirty/cache0 | ASEPRITE_TIMING_TIMELINE_ARCHITECTURE_AUDIT.md; test_rotation_revolution_display.py | 단위 이해, 숫자 입력/IME/locale |
| TIMING-FPS-PLAYBACK | DONE / P1 (자동 범위만) | Resource FPS / Effect FPS / source speed 자동 계약 검증 | 기존 UX2/DevEx 보존; Single opt-in은 별도 보류 | A/B/C32 PASS 및 source index/RGBA 자동 완료 이력 유지; 사용자 회전 재생 승인 아님 | TIMING_FPS_PLAYBACK_REPORT.md; test_fps_playback_semantics.py; TIMELINE_CUSTOM_ARCHITECTURE_AUDIT.md | 2026-10-30 사용자 Resource→Effect 회전 문제 확인·미해결; 별도 TIMING-ROTATION-USER 추적 |
| TIMING-ROTATION-USER | BLOCKED / P1 | 사용자 원본 Resource→Effect 회전 재생 문제 미해결 | 실제 원본 조건/재현 자료와 별도 진단 범위 확정 필요; 자동 fixture PASS로 대체 금지 | 사용자 경로의 FPS/frame count/mode/speed/cache/sampling 재현·실제 원인 수정·사용자 재확인 | TIMELINE_CUSTOM_ARCHITECTURE_AUDIT.md; TIMING_FPS_PLAYBACK_REPORT.md | 사용자 FAIL 확인. 이번 ARCH에서 renderer/FPS 수학 수정하지 않음 |
| TIMING-FPS-CHECKPOINT | BLOCKED / P0 | CP2 FPS checkpoint 사용자 승인 | TIMING-ROTATION-USER 해결·사용자 승인 및 명시 파일/hunk 승인 | 자동 후보134 PASS는 기술 근거일 뿐; CP2/관련 선행 의존 checkpoint 임의 승인 금지 | UX2_CHECKPOINT_FILE_MANIFEST.md; TIMELINE_CUSTOM_ARCHITECTURE_AUDIT.md | 회전 사용자 미해결 보존 |
| UI-SPINBOX-AUTOREPEAT | BACKLOG / P2 | 재발 시 재조사; 테스트 계약 보강 완료 | 제품 결함 미재현·과거 직접 원인 미확정은 보존 | native 반복/Release 계약 및 full1971 PASS, 이번 core175 PASS; 실제 재발의 phase/focus/timer 로그로 조사 재개 | test_native_spinbox_buttons.py::test_mouse_press_hold_uses_qt_native_auto_repeat; UI_SPINBOX_AUTOREPEAT_REPORT.md | 원인 확정/DONE 주장 아님; 사용자 native 입력 체감은 별도 |
| TIMING-SINGLE-SOURCE-SPEED | BACKLOG / P2 | Single의 명시적 원본 속도/출력 FPS 맞춤 편집 계약 | 별도 범위 승인; 기존 저장 의미 보존 설계 | 현재 저장 playback_speed/resource_start_frame/playback_mode가 Single adapter에 미전달임을 전제로 versioned opt-in/마이그레이션·cache·Undo 설계; schema 필요 여부 별도 결정 | TIMING_FPS_PLAYBACK_REPORT.md; effect_resource_layer.py; effect_composition_layer_render_service.py | 기존 파일 자동 활성화 금지; 이번에 구현하지 않음 |
| TIMING-2 | BACKLOG / P1 | 프레임별 ms 및 일괄 편집 | TIMING-1; 별도 schema/마이그레이션 승인 | rational duration·atomic bulk Undo1·양 playback 분기·seek/export parity | Timing 설계; test_effect_playback 관련 suite | hold/loop/재생 중 편집·timer jitter |
| ASE-IMPORT | BACKLOG / P1 | Aseprite 원본 frame 시간·metadata 보존 | source timing 계약·CLI/metadata 범위 결정 | GIF 양자화와 구분한 원본 ms/tags 등 지원 범위, fixtures/roundtrip | Timing 설계; services/aseprite_import_service.py | 실제 ase/aseprite 자료 및 CLI 설치 환경 |
| TIMELINE-UX | BACKLOG / P1 | Aseprite 스타일 frame/timeline 조작 | TIMING-1/2; key/frame selection domain·ripple 승인 | header selection/Frame Properties/clipboard/domain 충돌 없이 frame actions, 이후 drag/tags/onion skin 분리 | Timing 설계; 기존 multi-key/snap suite | mouse/trackpad·Ctrl/Shift/Alt·단축키 충돌 |
| UX-3 | BACKLOG / P1 | Main Workspace와 Library/Layers 정보구조 | UX2-VERIFY; 작업 흐름 범위 승인 | 자산/문서 레이어 구분·문맥·검색·명령 discoverability 검증 | UI_UX_ARCHITECTURE_AUDIT.md; UI_UX_PRINCIPLES.md; audit_editor_ux.py | 실제 제작 task·좁은 창·선택 전환 |
| UI-VISUAL | BACKLOG / P1 | 가독성·시인성·gizmo·실화면 품질 | UX2-VERIFY; 실제 화면 결함 수집 | 숫자 bounds가 아닌 이미지/조작 검토; overlay는 출력 pixels와 분리 | UX2_NATIVE_GUI_CORRECTIONS_REPORT.md; test_gizmo_visual_overlay.py | DPI/dark/고대비·실제 아트 위 overlay |
| FX-CONTACT | BACKLOG / P2 | Local Flat-ground Contact Foundation | 최신 capability audit 재확인; deterministic event 계약 | 지면 crossing/death origin/변동높이·속도 재사용성, bounded seek/Undo/Save/export | recheck_post_v25_capabilities.py; particle_sub_emitter suite | 튜닝한 lifetime와 진짜 접촉 구분·제작 체감 |
| FX-RIBBON | BACKLOG / P2 | Continuous Ribbon | Contact/후속 우선순위 재결정; geometry budget | stamp Trail과 다른 연속 geometry·gap·정확 RGBA/seek/예산 | capability audit; particle_trail suite | 급곡선/빠른 이동/픽셀 edge |
| FX-FORCE | BACKLOG / P2 | Spatial Force/Turbulence | 공간장/Noise 구분·determinism 계약 | field의 공간 의존성·bounded evaluation·random seek/export parity | capability audit; smooth noise/drag/gravity suites | smoke/dust 실제 motion 튜닝 |
| FX-VARIATION | BACKLOG / P2 | Sub-emitter Per-event Variation | stable event/child identity 및 seed 계약 | event별 variation과 재현성·canonical spawn 보존·budget | capability audit repetition; test_particle_sub_emitter.py | 반복감·원점/색/속도 variation 조절 |
| FX-GRAPH | BACKLOG / P2 | Lifetime Graph Editor | 기존2~8 point 데이터/Undo 유지 | scalar/RGB/alpha 구분·endpoint/easing/Undo1·색상 취소 보존 | test_lifetime_multi_point_ui.py; lifetime modulation service | 그래프 hit/drag/색상·확대 화면 |
| DEVEX-2 | BACKLOG / P2 | 앱 내부 진단 보고서 생성 UI | DEVEX-1 schema/privacy/cleanup 안정화 | 명시적 opt-in, redacted report, 사용자 아트 자동 포함 금지, CLI와 같은 결과 | DEVEX1_DIAGNOSTICS.md; test_diagnostics_cli.py | 대화상자·복사/저장·개인정보 동의 |
| PERF-1 | BACKLOG / P1 | 실사용 Particle/Trail/Sub-emitter 성능 | DEVEX-1; 재현 workload/품질·budget 명시 | explicit benchmark, cold/warm/seek/메모리·추가 instrumentation 비용 구분 | tools/benchmark_particle_*; 기존 deterministic render suite | 실사용 프로젝트·입력 응답·프레임 드롭 |

## 추가 후속 설계 Backlog

| Stable ID | 상태 / 우선순위 | 범위 / 선행 조건 | 완료 조건 |
| --- | --- | --- | --- |
| TIMELINE-ARCH | DONE / P1 (설계 감사만) | 활성 Resource/Effect 경로·6 selection domain·Qt A/B/C/D 비교 | TIMELINE_CUSTOM_ARCHITECTURE_AUDIT.md; B viewport 가상화 권장/A model-delegate 보조; interaction·exact timebase·POC/migration/diagnostics 설계. 기존 focused93 PASS; 구현0 |
| TIMELINE-CUSTOM-POC | DONE / P2 (Phase1 자동 범위) | 독립 tools/timeline_poc; app/UI/registry 연결·수정0 | geometry/selection/paint/interaction/synthetic adapter 분리. 신규66 PASS·기존 관련 포함159 PASS; 최종 JSON DPR3 probes PASS/36 workload/36 PNG. 10k frame에서도 visible약21×14·QWidget5. 상세 TIMELINE_CUSTOM_POC_PHASE1_REPORT.md; mutation/Undo/clipboard/duration 미구현. Native/접근성 gate 미통과, rotation/CP2 승인 아님 |
| TIMELINE-CUSTOM-POC-1.5 | DONE / P2 (구현·자동 검증만) | Navigation/Edge Auto-Scroll/명시적 CellRange/소규모 시각 개선 | TIMELINE_CUSTOM_POC_PHASE15_REPORT.md; float scroll/pixel axes/zoom 왕복, selection-owned QTimer16ms·elapsed/상한·frozen body, intervals/CellRange. 기존 Phase1 assertion 유지·최종 관련214 PASS/24.91s, 독립3DPR21 nav checks 각각 PASS/42 PNG. 한글/색상/key 및 새 navigation Native 승인은 아래 BLOCKED |
| TIMELINE-POC15-NATIVE | BLOCKED / P1 | 사용자 직접 Phase1.5 Navigation/Auto-Scroll/가독성 확인 | Phase1 번호/위치·Frame/Shift/Ctrl·Playhead 분리는 사용자 정상 확인. 새 wheel/pan/화면 밖 stationary drag/상하·대각선 CellRange/release/실제 capture/DPI/IME·한글/색상/key는 NOT VERIFIED. 이번 완료는 구현·자동 범위만; production pilot 승인 아님 |
| TIMELINE-POC-A11Y-NATIVE | BACKLOG / P1 | Phase1 이후 별도 승인; B 유지/보조 A 판단 | virtual-cell accessibility·layer/key keyboard-only·Native DPI/IME/trackpad/screen reader 및 UI 실사용 QA. 현재 offscreen/font/DPR 통과와 구별; production pilot 착수 전 gate 검토 |
| TIMELINE-MIGRATION | BACKLOG / P2 | POC gate→Resource pilot→기존 동작/Undo parity→Timing1/2 연동 설계→Effect pilot→Native 승인; 단계별 별도 승인 | 기존 UI 유지/feature flag rollback. Effect pilot은 TIMING-ROTATION-USER 해결·사용자 재확인 및 CP2 gate 선행; frame ripple/schema/source speed 임의 활성화 금지 |
| UI-DESIGN-SYSTEM | BACKLOG / P2 | 전문 편집 UI 공통 규칙; 기존 Inspector/UX 원칙 및 별도 승인 | density/spacing/labels/focus/keyboard/accessibility 규칙과 회귀 기준 |

TIMELINE-ARCH는 설계 감사 완료, TIMELINE-CUSTOM-POC는 독립 Phase1 자동 범위만 완료다. Production Migration/Design System은 미구현이며 ARCH 및 POC 보고서의 Native/접근성/parity gate를 따른다. 기존 TIMELINE-UX/TIMING-1/2의 selection·ripple·schema 승인 및 checkpoint 의존성은 유지하며 ASE/Effect 작업을 대체하지 않는다.

Phase1.5는 독립 POC 개선의 구현·자동 검증만 완료했다. 사용자 평가가 좋았던 번호/Frame 선택/Playhead 분리는 보존했으며 한글·색상·key 가독성 및 개선 Navigation은 TIMELINE-POC15-NATIVE에서 승인 대기한다.

## 검증/완료 이력

- 2026-10-30 TIMELINE-CUSTOM-POC Phase1.5 구현·자동 검증 완료. 작은 가로 angle10회의 Phase1 per-event round가0 DIP를 만드는 표현 재현과 pixel-only horizontal 축 경로를 확인했다. fractional geometry를 authoritative로 유지하고 native bar만 정수 표시, OS pixel/angle 분리·배율 표시/zoom controls, 명시 Cells 모드, selection-owned elapsed Qt auto-scroll을 구현했다. 기본1D body/strip·Shift/Ctrl·Key/Layer/Playhead 독립 의미 유지. intervals+4필드 CellRange로2M logical cell 선택, visible21×14/QWidget5 유지.
- 기존 Phase1 테스트/assertion 수정0. 최종 관련 **214 PASS/24.91s** (`C:\Dev\pem_poc15_regression_final_20261030`), 신규 pure33/Qt22 포함. 독립 `--verify --compare-table` (`C:\Dev\pem_timeline_poc15_verified_20261030\report.json`)은3 DPR 모두 PASS, 각각21 navigation cases·기존3checks,36 workloads/42 PNG. 실제 native Timer stationary ticks≥3, release/Esc/focus/capture/hide/close 등록 해제·후속 불변, pan/scrub 배제·min/max zoom 검사. full/core175 반복 없음. 상세 수치·입력 감사·Native 체크리스트는 TIMELINE_CUSTOM_POC_PHASE15_REPORT.md.
- 사용자 기존 정상 평가3건과 새 Native 승인을 구분한다. TIMELINE-POC15-NATIVE BLOCKED/P1; 한글/색상/key 가독성을 완료 승인하지 않았다. Migration/CP1·2·3·4/Timing/ASE/Effect Backlog 보존. TIMING-ROTATION-USER 미해결/CP2 및 의존 checkpoint BLOCKED 유지. Production/기존 테스트/과거 보고서 보호, staged0·미커밋, Window Use/Commit/Tag/Push/Build/PyInstaller/ZIP0.
- Phase1.5 종료 hash guard: 시작394개 중 변경은 POC7모듈+queue뿐, 신규6개로400개. 범위 밖 변경0·기존 Phase1 테스트 assertion 변경0·보호 PNG/HEAD/v0.0.25/FORMAT22 동일. compileall/diff/POC whitespace PASS, 잔류 Python0.

- 2026-10-30 TIMELINE-CUSTOM-POC Phase1 완료. 독립10개 Python 모듈 + 신규 tests2개 + 보고서 추가, 기존 파일은 queue만 수정했다. QAbstractScrollArea/QPainter visible drawing, ruler/frame strip/key/layer/playhead 독립 상태, Shift/Ctrl·threshold range drag·scrub·keyboard·zoom/pan/scroll·KO/EN·Light/Dark 구현. Windows offscreen 기본 font tofu를 합성 PNG에서 확인하고 POC 전용 설치 font read fallback/glyph 검사로 보완했다. mutation/Undo/clipboard/duration/production 연결0.
- 검증: 초기62 PASS/4 FAIL은 frozen dataclass 예외의 테스트 기대 오류였으며 정정 후66 PASS. 관련 기존93개 포함 **159 PASS/12.35s**. 최종 독립 `python -m tools.timeline_poc --verify --compare-table --output C:\Dev\pem_timeline_poc_final_20261030`은 DPR1/1.25/1.5 모두 PASS,36 workload/36 PNG/36,000 hit queries, zoom 오차0.5 DIP 이하·종료 후 widgets0. 최소 table baseline과 init/grab/Python trace memory를 측정했으며 제품 전체 속도 배수/RSS/Native 승인으로 해석하지 않는다. full/core175 재실행 없음. `TIMELINE_CUSTOM_POC_PHASE1_REPORT.md`에 수치·재현 명령·한계 기록.
- 가상 cell 접근성/layer-key keyboard-only/Native DPI·IME·trackpad는 미확인 gate로 별도 BACKLOG. Migration·CP1/2/3/4·Timing/ASE/Effect 상태·의존성 보존. 사용자 회전 미해결/CP2 차단 유지. 기존 source/보호 PNG/HEAD/v0.0.25/FORMAT22/staged0 보존, 모든 신규 변경 unstaged/uncommitted, Window Use/Commit/Tag/Push/Build/PyInstaller/ZIP0.

- 2026-10-30 TIMELINE-ARCH 읽기 전용 감사 완료. 실제 활성 QTableWidget 경로, QTableWidgetItem의 R×F allocation/visual scan, 분산 입력·선택 owner, 기존 명령/Undo/refresh/source sampling 경계를 추적했다. 커스텀 B(QAbstractScrollArea+QPainter)/보조 A(model-delegate), 6 domain interaction과 exact timing read/edit 경계, synthetic POC→Resource parity→Timing 설계→Effect→Native migration 및 테스트/DevEx 계획을 TIMELINE_CUSTOM_ARCHITECTURE_AUDIT.md에 기록했다. 구현0/생산·테스트 수정0; 기존 timeline/keyboard focused12모듈 **93 PASS/7.50s**, full/통합 진단 재실행 없음. 직전 full1971 PASS/1 SKIP은 과거 근거로 구별한다.
- 이번 사용자 Native QA Lifetime/Group/Gizmo/한글 UI 정상 확인을 반영했다. Resource→Effect 회전 재생은 사용자 FAIL·미해결로 TIMING-ROTATION-USER BLOCKED/P1 분리; TIMING-FPS-PLAYBACK 자동 완료는 유지하되 사용자 승인으로 취급하지 않는다. CP2용 TIMING-FPS-CHECKPOINT BLOCKED/P0 및 UX2/DevEx 의존 checkpoint 차단 유지. 남은 DPI/IME/실제 source 조건은 미확인. queue+새 audit 문서만 변경, 기존 미커밋/보호 PNG/v0.0.25/FORMAT22/HEAD/staged0 보존. Window Use/Commit/Tag/Push/Build/ZIP/권한·Git 설정 변경0.

- 2026-10-30 UX2-FINAL-PREP 완료. 실제 HEAD/staged0/v0.0.25/FORMAT22/보호 PNG 일치. working tree `--check all` **UI90/Rotation49/Groups13/Render23=175 PASS, 4 checks PASS/exit0**. 생산/테스트 source 변경0 및 기존 Python53개 시작 hash 일치로 직전 full1971 PASS/1 SKIP을 유지하고 전체 재실행은 하지 않았다. 사용자 원본 Lifetime 등 native는 NOT VERIFIED, Window Use0.
- 변경68개(29 tracked M/39 untracked, 보호 PNG1 포함)를 A/B/C/D/E/F로 파일별 감사했다. MainWindow/workflow/Native Regression의 혼합3파일을 원 작업 트리에서 건드리지 않고 외부 HEAD-object export에서 분리했다. CP1 UX2+B167 PASS·전체 import collection1876, CP2 FPS134 PASS, CP3 SpinBox/Numeric52 PASS, CP4 DevEx core175 PASS·CLI35 PASS/1 SKIP. D만 HEAD에 더한 별도 사본도22 PASS. 현재 DevEx는 CP1/2/3 선행 후 검증됐으며 기존 HEAD+DevEx-only 독립은 아니다.
- 권장 순서 CP1 UX2+B → CP2 FPS → CP3 SpinBox test contract → CP4 DevEx → F 문서 검토. 사용자 native 확인·파일/hunk 승인·실제 선행 commit 미충족으로 UX2-VERIFY/CHECKPOINT·DEVEX1-CHECKPOINT BLOCKED 유지. SpinBox는 미확정 이력을 보존한 BACKLOG/P2/재발 시 조사로 조정, TIMELINE-ARCH는 다음 읽기 전용 감사 후보 NEXT/P1. TIMING1/2/Single speed/ASE/Timeline-UX/POC/Migration/Design System/Effect Backlog 보존. Stage/Commit/Tag/Push/Build/PyInstaller/ZIP 및 파괴적 Git 명령0.

- 2026-10-30 UI-SPINBOX-AUTOREPEAT 조사/테스트 강화. default Fusion6/windows11 4/Native75 tests 후12/Inspector70 tests 후16의 자연38회는 모두 정상, 실측threshold500/rate150ms였다. controlled threshold900ms에서는 기존800ms 코드가2/2회92로 끝나는 취약성을 확인했다. GUI 지연 주입은93으로 반복돼 과거92 실패의 재현이 아니었다. 따라서 과거 원인을 timing/style/production 중 하나로 확정하지 않고 NEXT/P1로 남긴다.
- 생산 코드 변경0. 기존>=93 assertion을 유지하고 초기1+native timer 반복2회, Release 뒤 등록 timer 제거/추가변경0 검증 및 failure cleanup을 추가했다. controlled style/int/double/up/down·missing repeat/release negative tests11개. 모듈22 PASS; 관련77 tests 후 대상12/12 PASS; 관련171 PASS/1 SKIP; UI v4 **90 PASS/30.38s**. 변경 완료 뒤 full 정확히1회 **1971 passed/1 skipped/1 warning/193.11s**, `C:\Dev\pem_repeat_full_final`. 이 PASS를 과거 원인 확정으로 해석하지 않는다. compileall/app/batch/diff check 통과. TIMELINE-ARCH/CUSTOM-POC/MIGRATION/UI-DESIGN-SYSTEM은 BACKLOG 등록만 했고 구현0. 기존 Backlog·BLOCKED·완료 상태, 버전/FORMAT/HEAD/보호 PNG 보존, staged0·미커밋·Window Use0.

- 2026-10-30 TIMING-FPS-PLAYBACK 완료(범위 내). Resource12/Effect24/1×의1,1,2,2는 시간 보존 매핑이며 기존 계산을 유지했다. Resource FPS 입력/초 표시 및 KO/EN 원본 배율 안내를 추가하고, Resource FPS 변경 뒤 이전 snapshot 결과가 수락되는 결함을 red→green으로 수정했다. 해당 source의 draft revision/session/pending만 무효화하며 사용자 draft와 다른 source는 보존한다. Resource FPS24 및 Particle speed2×로12 source frames/0.5초를 실제 source index·all-path RGBA·PNG·Save/Reload·Undo·seek로 확인했다. Single 저장 speed 필드의 자동 활성화는 금지하고 TIMING-SINGLE-SOURCE-SPEED로 보류했다.
- 검증: 신규32 PASS, 관련141 PASS/1 SKIP, 통합 UI78/Rotation49/Render23 총150 PASS/exit0. 최종 full은 정확히1회 **1959 passed/1 failed/1 skipped/2 warnings/229.04s**, `C:\Dev\pem_fps_full_final`. 실패는 기존 SpinBox hold test의92>=93 assertion; 단독1 PASS/1.37s이나 원인 미확정으로 별도 P1 기록, 전체 재실행/범위 외 수정 없음. FPS/Gizmo/lifecycle 대상은 PASS. compileall/실행/diff check 통과, v0.0.25/FORMAT22·HEAD·PNG 보존, unstaged/uncommitted, Window Use0.

- 2026-10-30 UX2-LIFECYCLE-ISOLATION 완료. 단독12회 통계0과 달리 Gizmo/Inspector44 tests 후12회 중11회 통계 변화(10회 정확히 hit/hit/render +1)를 관찰했다. 계측 스택은 다른 프로젝트(owner_current=false)의 idle prewarm worker였다. 선택→close 뒤 prewarm pending 유지도 최소 회귀1 FAIL로 재현했다. 생산 close에서 예약 취소/poll·playback 정리, 테스트는 최초 선택 동기 render0 및 정상 prewarm 완료 뒤 반복 navigation Dirty0/Render0을 분리했다. 불필요한 render 주입 시 실패하는 negative control 유지.
- 검증: lifecycle+companion7 PASS, 관련48 tests 뒤 대상12/12 PASS, 추가109 PASS/1 SKIP, UI v3 **78 PASS/28.28s**, 최종 full 정확히1회 **1928 passed/1 skipped/1 warning/195.62s** (`C:\Dev\pem_lifecycle_full_final`). symlink 권한 SKIP 및 cache ACL warning은 기존 사항이다. compileall/diff check 통과. Gizmo DONE 유지; UX2-VERIFY/CHECKPOINT는 사용자 native 승인, DEVEX1-CHECKPOINT는 기존 의존성으로 BLOCKED 유지. TIMING/ASE/Timeline/UX3/Effect Backlog 보존. HEAD·보호 PNG 동일, staged0, unstaged/uncommitted, Window Use0, Commit/Tag/Push/Build/ZIP 없음.

- 2026-10-29 UX2-GIZMO-SYNC 완료: 선행102 tests 후24회 중 기존 records=[]2회 자연 재현. pending/active timer의 callback이 assertion보다0.196/0.109ms 늦었다. 신호19/start1/stop0으로 누락·취소가 아니라 완료 대기 race임을 확인했다. 조건 기반 Qt 대기로 수정 후 같은 순서24/24 PASS; UI v2 진단74 PASS, 정확한 fields/value/layout3 JSON 확인. production 변경0.
- 이번 최종 전체 pytest는 정확히1회: **1924 passed, 1 failed, 1 skipped, 2 warnings / 211.19s**. 기즈모 대상은 PASS. 별도 `test_ui_navigation_state_does_not_dirty_project`에서 generation은 같지만 current_frame_renders/spawn_cache_hits/resource_cache_hits가 각각1 증가해 FAIL했다. 단독1 PASS/0.85s이나 원인 미확정; 이번 범위에서 수정하거나 전체 재실행으로 덮지 않았다. UX2-VERIFY/CHECKPOINT는 전체 실패·사용자 승인 대기, DEVEX1-CHECKPOINT는 기존 의존성으로 BLOCKED 유지. 기존 Backlog 보존, Window Use0, unstaged/uncommitted, HEAD·보호 PNG 유지.

- 2026-10-29 DevEx-1 Checkpoint & UX2-VERIFY 시작. DevEx core가 미추적 UX2 테스트/보조 모듈에 의존하므로 현 상태의 독립 checkpoint는 보류한다. stage/commit 없이 clean HEAD 기반 검증 사본과 현재 working tree 진단을 구분하여 확인한다.
- 같은 작업의 검증: HEAD와 index가 동일함을 확인해 외부 `C:\Dev\pem_devex_index_snapshot_ea8ff47_20261029`에 tracked 파일을 export하고 DevEx 후보11개만 복사했다(원래 checkout/index 변경 없음). 이 사본의 core는 UI/rotation/groups ERROR, render PASS, exit2였다. 일반 git clone은 Git/MSYS named-object 접근 오류로 실행되지 않아 이를 완전한 Git clone 성공으로 기록하지 않는다. 필수 미추적 테스트 부재와 HEAD timing hook 부재는 별도로 확인했다.
- 현재 작업 트리의 `--check all`은4 PASS/126 cases, `C:\Dev\pem_ux2_verify_20261029\report.json`; 추가 focused44 passed/1 skipped. symlink SKIP을 PASS로 바꾸지 않았다. Window Use0. 새로운 기능 결함을 고치거나 독립 checkpoint를 강행하지 않았다.
- 이번 최종 full1회는 **1 failed, 1921 passed, 1 skipped, 2 warnings / 193.18s**, `C:\Dev\pem_ux2_checkpoint_full`. 기즈모 changed-field sync test의 records=[]가 실패했다. 별도 프로세스3회는 PASS였으나 간헐 원인 미확정(P1)으로 남긴다. 이전1922 PASS 이력을 이번 결과로 오인하지 않으며, 자동 검증 전체 완료로 선언하지 않는다. 컴파일/실행/diff check 및 보호 PNG는 통과·보존했다.
- 다음 순서는 **UX2-VERIFY(사용자 승인) → UX2-CHECKPOINT → TIMING-1**을 유지한다. UX2 checkpoint 승인이 나면 runtime+회귀 테스트+보조 모듈을 먼저 묶고, 그 위에 DevEx-only commit을 별도로 검증하는 분리를 권장한다. 다른 Backlog와 우선순위는 보존한다.

- 2026-10-29 DEVEX-1 시작. 모든 기존 보류 항목을 유지했다. UI/Effect/Timing 신규 기능을 이 작업에 포함하지 않는다.
- 2026-10-29 DEVEX-1 완료. `python tools/diagnose_editor.py --check all`은 core126 cases / 4 PASS / 0 FAIL·SKIP·ERROR; `--list`, 각 범주, optional UI screenshot, bounded metadata trace, timeout ERROR2, 기존 output 거부2를 확인했다. 보고서: `C:\Dev\pem_devex_all_verified\report.json` 및 `docs/DEVEX1_DIAGNOSTICS.md`.
- 최종 full: `python -m pytest -q --basetemp=C:\Dev\pem_devex_full_verified --tb=short` → 1922 passed, 1 skipped, 1 warning / 186.49s. SKIP은 symlink 생성 권한, warning은 기존 pytest cache ACL이다. compileall, app --version/--check, run_app.bat --check, git diff --check 통과. v0.0.25/FORMAT22 및 보호 PNG SHA256 유지.
- 이 완료는 UX2-VERIFY/Timing/Aseprite/Timeline/Effect 후속 작업 완료가 아니다. production 변경·DevEx 구현은 미커밋으로 남기며 이 파일만 documentation checkpoint 대상이다.


## 2026-11-17 개발 맥락 지속 보존 규칙

- RECORD-POLICY / DONE: 기존 작업 큐·보류 항목을 유지하고 AGENTS.md에 새 세션 진입 문서와 결정/검증/버전/commit/push 기록 규칙 추가. 제품 코드·아이콘·기획 내용은 변경하지 않음.
- 검증: 문서 링크 존재·기존 바이트 보존·명시 문서만 격리 커밋 확인. 제품 자동/GUI 회귀는 이번 문서 작업에서 실행하지 않음. 기존 native QA 및 체크포인트 의존성은 그대로이며 과거 사실을 완료로 변경하지 않음.
- 원격 보존: 이 정책 추가분은 rodetoast 인증/공개 범위/브랜치 검토 후 push 전까지 로컬 상태임. 운영 Release·Latest 권한을 부여하지 않음.


## 2026-11-17 소스 저장소 이전·원격 보존

- MIGRATION-SOURCE / DONE(문서/연결 준비): 실제 rodetoast 소유권과 기존 Git/자산 보존 확인, 기존 코드와 UX/DevEx 결정·보류 항목 유지. 최신 개발 브랜치는 codex/migration-checkpoint-20261117. main은 기존 코드를 유지하는 문서 진입점.
- 새 세션은 AGENTS의 실제 URL/브랜치와 Git 상태 확인. 기존 UX/native QA·CP 의존성은 이번 보존 커밋으로 승인/완료 처리하지 않음. 제품 빌드·기능/전체 회귀는 미실시. push 완료 여부는 실제 원격 ref와 인계 보고서의 commit 재조회 결과로 확인.
