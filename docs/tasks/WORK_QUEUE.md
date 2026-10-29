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

| Stable ID | 상태 / 우선순위 | 목적 | 선행 조건 | 완료 조건 | 관련 문서/테스트 | 남은 사용자 수동 QA |
| --- | --- | --- | --- | --- | --- | --- |
| DEVEX-1 | DONE / P0 | Integrated Diagnostics Foundation; 기존 검사를 콘솔/JSON으로 통합 | 기존1888 baseline·UX2 보존 | registry4범주, exit/schema/timeout/tree cleanup/privacy/output 보호 검증 완료; core126 PASS, full1922 PASS/1 SKIP; 아래 근거 참조 | DEVEX1_DIAGNOSTICS.md; test_diagnostics_cli.py; tools/diagnose_editor.py | native 수동 미실행; 실제 symlink 생성 검사1개는 계정 권한으로 SKIP, CLI 실행 체감 |
| UX2-VERIFY | NEXT / P0 | 실제 Windows에서 UX-2 최종 확인 | 기존 회귀 수정 + DEVEX-1 | 사용자 Lifetime 중첩 조건 재확인, selection/commands/입력·시인성 확인; 재현 조건과 근거 기록 | UX2_NATIVE_REGRESSION_REPAIR_REPORT.md; test_native_regression_repair.py | 실제 자료 Lifetime, DPI/다중 모니터/IME/dark/gizmo |
| UX2-CHECKPOINT | BLOCKED / P0 | UX-2 및 회귀 수정의 Local Checkpoint | UX2-VERIFY 및 명시적 commit 승인 | 범위별 diff·보호파일·전체검증 확인 후 승인된 local commit | UX2_PARTICLE_INSPECTOR_REPORT.md; 회귀 보고들 | 실제 native 승인; 현재 작업은 production commit을 승인하지 않음 |
| TIMING-1 | BACKLOG / P1 | ms/frame 기본 표시와 FPS 전환 preference | UX2 안정화; Timing 설계 재확인 | 표기 preference와 실제 FPS 데이터 분리, exact roundtrip; Undo/dirty/cache0 | ASEPRITE_TIMING_TIMELINE_ARCHITECTURE_AUDIT.md; test_rotation_revolution_display.py | 단위 이해, 숫자 입력/IME/locale |
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

## 검증/완료 이력

- 2026-10-29 DEVEX-1 시작. 모든 기존 보류 항목을 유지했다. UI/Effect/Timing 신규 기능을 이 작업에 포함하지 않는다.
- 2026-10-29 DEVEX-1 완료. `python tools/diagnose_editor.py --check all`은 core126 cases / 4 PASS / 0 FAIL·SKIP·ERROR; `--list`, 각 범주, optional UI screenshot, bounded metadata trace, timeout ERROR2, 기존 output 거부2를 확인했다. 보고서: `C:\Dev\pem_devex_all_verified\report.json` 및 `docs/DEVEX1_DIAGNOSTICS.md`.
- 최종 full: `python -m pytest -q --basetemp=C:\Dev\pem_devex_full_verified --tb=short` → 1922 passed, 1 skipped, 1 warning / 186.49s. SKIP은 symlink 생성 권한, warning은 기존 pytest cache ACL이다. compileall, app --version/--check, run_app.bat --check, git diff --check 통과. v0.0.25/FORMAT22 및 보호 PNG SHA256 유지.
- 이 완료는 UX2-VERIFY/Timing/Aseprite/Timeline/Effect 후속 작업 완료가 아니다. production 변경·DevEx 구현은 미커밋으로 남기며 이 파일만 documentation checkpoint 대상이다.
