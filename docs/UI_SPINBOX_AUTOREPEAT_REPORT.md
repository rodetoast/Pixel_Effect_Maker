# UI-SPINBOX-AUTOREPEAT — investigation and contract hardening

2026-10-30. HEAD `ea8ff478c12a9b1032982476f84da62f4009d095`, v0.0.25 / FORMAT22.
AGENTS/WORK_QUEUE 및 직전 FPS 실패 보고를 읽고 기존 UX2/DevEx/Timing 변경을 보존했다.

## 1. 정확한 실패 원인: 과거 전체 실패는 미확정

**이 작업을 과거 간헐 실패의 원인 확정/완전 해결로 선언하지 않는다.**
기존 전체 결과는800ms hold 뒤91→92, 기대>=93이었다. 당시 press/focus/timer 상태 로그는 없다.
이번 bounded 자연 재현은 아래38회 모두 정상이며, style 오염이나 제품 mouse handler 결함을 직접 재현하지 못했다.

| 조건 | 수정 전800ms 관찰 |
| --- | --- |
| fresh default Fusion6회 | 6 PASS, 보통94 |
| subtree windows11 style4회 | 4 PASS,94 |
| Native Regression + Native SpinBox75 tests 뒤12회 | 12 PASS |
| Inspector/components/visual/motion70 tests 뒤16회 | 16 PASS,94 또는95 |

모두 measured mouse threshold500ms/rate150ms, enabled/StepUp=true였다.
스핀박스의 timer event와 valueChanged, focus/hide, press/release 및 relative ms를 기록했다.
원래800ms 시점의 등록 타이머도 관찰했다. 결과는 `C:\Dev\pem_repeat_default`, `pem_repeat_windows11`,
`pem_repeat_native_order`, `pem_repeat_inspector_order`의 observations.json에 있다.
최근 테스트에서는 QApplication.setStyle 호출을 찾지 못했고, Native Repair는 fixture subtree에만 style를 적용한다.
이 사실이 과거 전체 실행의 모든 Qt 전역 상태 오염 부재를 증명하지는 않는다.

## 2. 확인된 취약점과 아닌 것

제품 `_ScrollSafeWheelMixin`은 wheelEvent와 keyboardTracking만 조절한다. mouse press/release/focus handler는 Qt 상속 그대로다.
Qt6.11.1의 [공식 QAbstractSpinBox 소스](https://raw.githubusercontent.com/qt/qtbase/v6.11.1/src/widgets/widgets/qabstractspinbox.cpp)를 확인했다.
mouse press는 stepEnabled/hit를 확인하고 초기 step 뒤 threshold timer를 시작한다.
threshold timer는 반복 타이머로 전환하며 stepBy를 수행한다. release뿐 아니라 focusOut/hide/close도 reset으로 두 타이머를 중단한다.
style는 threshold/rate를 결정하며 StyleChange에서 갱신된다. 따라서800ms 경과만으로 반복 완료나 취소 부재를 보장할 수 없다.

통제된 QProxyStyle threshold900ms(그 외 정상 Qt handler)에서는 기존800ms 코드가 **2/2회92**로 끝났다.
타이머는 여전히900ms로 등록되어 있었고 repeat event는0회였다. 이는 **테스트의 고정 시간 가정이 style 독립 계약이 아님**을 증명한다.
증거 `C:\Dev\pem_repeat_slow_style\observations.json`.
그러나 실측 default/windows11은500ms였다. 과거 실패가900ms style 때문이었다고 주장하지 않는다.

추가로 queued callback에서 GUI thread를750~850ms 막는 bounded probe도 수행했다.
이 조건은 repeat가 지연됐지만 release 전에93으로 증가했다. 따라서 이 probe로 과거92 실패를 재현한 것은 아니다.
`pem_repeat_blocked`, `pem_repeat_blocked_timer_batch`. 단순히 'GUI 지연이 유일한 원인'이라고 확정할 근거도 없다.

판정: **생산 버그 확인0 / 테스트의800ms 가정 취약성 확인 / 과거 간헐 실패의 직접 원인은 미확정**.
전체 실행을 반복해 우연한 red를 찾거나 단독PASS로 과거 실패를 지우지 않았다.

## 3. 수정 내용 (Production 변경0)

- `tests/test_native_spinbox_buttons.py`: 원래 대상 node와>=93 assertion을 유지한다.
  800ms sleep을 실제 초기 step+타이머 기반 반복2회(총 최소94) 완료 조건으로 바꿨다.
  fixture finally에서 close/deleteLater를 실행한다.
- `tests/spinbox_repeat_support.py`: Qt 활성 창/focus를 bounded condition으로 확인한 뒤 press한다.
  초기1 step, 신규 native timer 등록, timer event2회와 각1 step 증가를 검사한다.
  최대2500ms deadline 내 실제 조건이 충족되면 바로 진행한다. stepBy/Qt timer slot을 직접 호출하지 않는다.
  release는 실패 시에도 finally에서 수행하고, 기존 timer 집합으로 복귀했는지 구조적으로 검사한다.
  precise guard callback이 repeat rate2주기 뒤 실행될 때까지 추가 valueChanged0도 확인한다.
  모든 observer/signal/guard를 finally에서 정리한다. focus 취소는 재-press로 숨기지 않고 실패 로그에 남긴다.
  실패 snapshot은 phase/timer count/value-change count/focusOut/release 이후 count와 최근16개 event 이름/relative ms다.
- `tests/test_spinbox_repeat_conditions.py`: 두 local styles × int/double × up/down8 cases,
  threshold900ms1 case, Timer 차단/Release 미중단 negative controls2 cases, 총11개.
  QProxyStyle은 새로 만든 base style를 소유하고 subtree에만 적용한다. QApplication style identity 보존도 검사한다.
  Timer 차단은 timeout 실패 및 release cleanup을, 잘못된 release는 active timer 실패를 실제로 유발한다.
- `tools/probe_spinbox_autorepeat.py`: 최대16회 관찰/명시적 preceding modules/수정된 원래 test 재사용 모드.
  합성 값과 bool/count/event/relative time만 기록하며 사용자 프로젝트·이미지·절대 경로·locals는 수집하지 않는다.
- UI registry v4는 기존 대상 node와11 companion을 재사용한다(UI90/core175). assertion 사본/skip 없음.

## 4. 재현 전후 검증

통제된900ms style에서 기존 대기는2/2 실패했고 완료 기반 검사는 통과했다.
자연 실행에서 실제 원래92 실패는 재현되지 않았으므로 '자연 red→green'이라고 표현하지 않는다.

- 기존 모듈+companion:22 PASS/4.53s (`C:\Dev\pem_repeat_contracts`).
- Inspector/visual/native77 tests PASS 후 실제 수정 대상12회: **12/12 PASS**, `C:\Dev\pem_repeat_fixed_order`.
- SpinBox/Numeric/Inspector/Wheel/speed range/Undo/DevEx 묶음: **171 passed / 1 skipped / 27.26s**, `C:\Dev\pem_repeat_related`.
- UI v4 진단 **90 PASS / 30.38s / exit0**, `C:\Dev\pem_repeat_ui_final\report.json`.
  JSON의90 cases/cleanup=owned process tree closed를 확인했다. 전체 core175를 이번 별도 진단에서 실행했다는 뜻은 아니다.
- compileall app/tests/tools, app --version(v0.0.25), app --check, run_app.bat --check, git diff --check: exit0.
- 최종 전체 pytest는 변경 완료 후 **정확히1회**:
  `python -m pytest -q --basetemp=C:\Dev\pem_repeat_full_final --tb=short`
  → **1971 passed / 1 skipped / 1 warning / 193.11s**, exit0.
  원래 hold test 및 새11 companion, 기존 Gizmo/lifecycle/FPS 대상 모두 PASS였다.
  SKIP은 기존 symlink 권한, warning은 pytest cache ACL이다. 전체를 반복하지 않았다.
  이 자동 PASS와 과거 간헐 실패의 직접 원인 확정은 별개다.

## 5. 남은 원인 조사

다음 실제 실패가 발생하면 helper snapshot의 phase와 focusOut/timer/value count를 먼저 확인한다.
focusOut/Hide로 타이머 취소인지, 활성 timer가 있지만 callback 지연인지, callback 후 value step이 없는지를 구분해야 한다.
현재 evidence만으로 특정 앞선 test 순서·OS scheduler·QStyle의 제품 결함을 지목하지 않는다.
자동 전체PASS가 나오더라도 과거 직접 원인까지 확정된 것은 아니므로 UI-SPINBOX-AUTOREPEAT는 DONE이 아니다.

## 6. Work Queue / Git / Window Use

UI-SPINBOX-AUTOREPEAT는 NEXT/P1로 남겼다. 테스트 강화/검증은 끝났지만 과거 직접 원인 미확정으로 DONE은 아니다.
TIMELINE-ARCH / TIMELINE-CUSTOM-POC / TIMELINE-MIGRATION / UI-DESIGN-SYSTEM은 별도 BACKLOG로 등록만 했다.
기존 TIMELINE-UX/Timing1·2/Single speed/ASE/Effect와 완료·BLOCKED 항목은 보존한다. 커스텀 타임라인 구현0.
Window Use0, 콘솔/offscreen/QTest만 사용. 모든 변경은 unstaged/uncommitted, Commit/Tag/Push/Build/ZIP/파괴적 Git 명령0.
보호 PNG SHA256 기준 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`.
최종 HEAD 동일/staged0/PNG hash 동일을 재확인하고, 소유 pytest/probe/diagnostic 프로세스 종료를 확인했다.
