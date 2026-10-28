# UI / UX Principles

향후 UI 변경을 위한 짧고 안정적인 기준이다. 설계 근거는 UI_UX_ARCHITECTURE_AUDIT.md, UX-1 적용·검증 범위는 UX1_INSPECTOR_FOUNDATION.md를 참조한다. 공통 부품은 app/ui/inspector_components.py, token은 기존 layout_metrics.py에 둔다. 현재 pilot은 Trail/Sub-emitter 두 곳뿐이다.

- 새 기능은 Source / Emit / Motion / Lifetime / Trail / Events / Rendering / Transform의 기존 workflow 안에 둔다. 새 top-level category에는 작업상 이유가 필요하다.
- 화면 접기와 feature enable/bypass를 분리한다. 표시만 바꾸는 조작은 document·dirty·Undo를 변경하지 않는다.
- 접기 API는 미확정 numeric text를 확정하거나 버리지 않고 보류한다. 마우스/Tab 이동이 먼저 기존 focus-out 확정을 일으키면 그 numeric edit의 Undo1은 유지한다. disclosure 자체는 Undo0이며 기존 Enter/focus-out·ScrollSafe 정책을 우회하지 않는다.
- OFF는 summary와 enable 입구를 남기고 무관한 상세를 숨긴다. 값을 폐기하지 않는다. 닫힌 active/invalid/호환 기능도 발견할 수 있어야 한다.
- Inspector 상단에 대상·mode·lock/multi-edit 범위·중요 warning 입구를 둔다. 대상별 category/scroll/focus는 view state로 보존한다.
- UX-1 접기 상태는 (inspector kind, selection ID, section ID)별 세션 메모리다. 기본은 펼침이며 OFF 상세는 숨긴다. Project JSON·Undo·QSettings에 쓰지 않는다. 향후 영속 UI preference 도입은 별도 사양이다.
- 같은 의미의 row/command는 공통 부품·기존 numeric spec·tooltip/접근성 규약을 재사용한다. 임의 spacing/style 대신 semantic token을 확인한다.
- 단위·범위·작용 대상·Undo/commit 조건을 명시한다. Lifetime age와 Timeline key, System과 Surface, RGB와 alpha를 구별한다.
- 외관 변경으로 Undo/Auto-Key·숫자 text commit·IME·Ctrl-wheel·locked/parent/multi-selection 계약을 깨지 않는다.
- 거부 이유는 입력 가까이, 중요 상태는 section summary와 상단 입구, 성공은 statusbar에 둔다. 색과 짧은 알림만으로 설명하지 않는다.
- toolbar/context/menu는 동일 command id·대상·가능 이유를 공유한다. library 자산과 document layers를 구분한다.
- EN/KO·280/320/360폭·font100/125/150 자동 geometry와 실제 Windows DPI/keyboard/mouse QA를 구분해 기록한다. tooltip/bounds만으로 사용성 합격을 선언하지 않는다.
- toolkit 이전은 측정된 고유 제약에 따른 별도 결정이다. IA 문제를 QML이나 padding만으로 해결했다고 보지 않는다.
