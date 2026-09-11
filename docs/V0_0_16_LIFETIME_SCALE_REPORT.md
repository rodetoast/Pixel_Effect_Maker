# Pixel Effect Maker v0.0.16 완료 보고

작성일: 2026-09-10. 이 문서는 자동 검증 결과를 기록한다. Windows 네이티브 GUI 수동 QA는 수행하지 않았다.

## 기준

1. 프로젝트: `C:\Users\SOUTHPAW GAMES\Desktop\Pixel_Effect_Maker`.
2. 작업 전 HEAD: `1bfd865c6396565b9c43d541613b5a58ef590cd9`.
3. 작업 전 Version: Pixel Effect Maker v0.0.15.
4. 작업 전 FORMAT_VERSION: 12.
5. 작업 전 pytest: 1138 passed, 0 failed.

## Previous Checkpoint

6. Overscan stage 파일: `CHANGELOG.md`, `app/services/effect_render_service.py`, `app/services/resource_composition_render_service.py`, `app/ui/resource_editor_v2/composition_canvas.py`, `docs/MANUAL_TEST_CHECKLIST.md`, `docs/RESOURCE_OVERSCAN_AUDIT.md`, `tests/test_resource_composition_clip.py`, `tests/test_resource_editor_overscan.py`.
7. Audit stage 파일: `docs/EFFECT_AUTHORING_CAPABILITY_AUDIT.md`, `tools/audit_effect_authoring.py`.
8. 제외 파일: 사용자 `테스트소스.png` 및 cache/temp/build/dist/exe/zip/backup. `git add -A`는 사용하지 않았다.
9. Commit 구조: 구현/테스트와 감사 자료를 논리적으로 나눈 2개 local commit.
10. Commit hashes: `ca70bbc` (`Add resource editor overscan preview`), `baff65b` (`Audit effect authoring capabilities`).
11. Checkpoint 후 Git: staged 0, main은 origin/main보다 33 commits ahead, tag/push/build 없음.

## Alpha Easing Bug

12. 실제 Alpha property: `ParticleEmitterSettings.opacity_start`, `opacity_end`, `easing`.
13. 저장 easing field: `ParticleEmitterSettings.easing`, 직렬화 키 `easing`.
14. 재현: `Ease In`을 가진 emitter를 Inspector에 로드한 뒤 다른 Particle 값을 편집해 Inspector가 재구성한 settings를 적용하면 `Linear`로 바뀌었다.
15. Root Cause: `ParticlePropertiesPanel.settings()`가 새 `ParticleEmitterSettings`를 만들 때 `easing`을 전달하지 않아 dataclass 기본값 `Linear`가 저장값을 덮었다. refresh signal 자체가 직접 mutation한 문제는 아니었다.
16. Mutation 경로: 실제 사용자 control → `draft_changed` → `MainWindow.update_particle_draft()` → `EditorValueCommand`.
17. Guard: `set_settings()`는 기존 `_loading` guard 안에서 Alpha와 lifetime easing을 exact binding하며, loading 중 변경 signal은 command를 만들지 않는다.
18. 수정 파일: `app/ui/particle_properties_panel.py`, `app/ui/main_window.py`, `app/services/emitter_service.py`, 관련 model/localization/tests.
19. Refresh mutation: 네 sentinel easing에서 model, Undo, dirty, revision mutation 0으로 자동 검증.
20. Selection change: Ease Out인 A → Ease In인 B → A 후 두 값 exact 유지.
21. Save/Reload: 네 easing 모두 저장·재로드·Inspector refresh 후 exact.
22. Undo/Redo: 실제 사용자 easing 변경만 command 1개이며 양방향 exact.
23. 다른 Easing control 감사: Resource/Effect `AnimationTrack`은 검증된 set/load 경로를 사용한다. Particle motion radius/angle/axis Inspector도 반복 refresh 시 exact하고 mutation이 없음을 추가 테스트했다. 공용 evaluator의 누락된 `Ease In/Out` 계산도 수정했다.

## v0.0.16 Baseline

24. Version: Pixel Effect Maker v0.0.16.
25. FORMAT_VERSION: 13.
26. Migration policy: FORMAT 12 이하에서 새 키가 없으면 disabled, 1.0→1.0, Linear로 materialize한다. 기존 render를 바꾸지 않는다.

## Lifetime Foundation

27. Model type: `LifetimeScalarModulation`.
28. enabled: strict Boolean, 기본 `false`.
29. start: finite scalar, 기본 1.0.
30. end: finite scalar, 기본 1.0.
31. easing: Linear, Ease In, Ease Out, Ease In/Out.
32. normalized age: birth frame 0.0, last visible frame 1.0이 되도록 `age / (lifetime - 1)`을 clamp한다. 기존 Alpha의 visible-frame convention과 같다.
33. zero/invalid lifetime: lifetime <= 1은 안전한 end state 1.0으로 평가해 division-by-zero/NaN/Inf를 만들지 않는다.
34. Evaluator: easing된 정규화 age로 start/end를 선형 보간하는 pure scalar function.
35. Future reuse boundary: model/evaluator는 scalar lifetime channel까지만 일반화했다. node/graph/multi-point framework는 만들지 않았다.

## Scale Semantics

36. Uniform multiplier: 한 scalar를 particle local X/Y scale에 동일하게 곱한다.
37. Base scale interaction: `final instance scale = seeded base particle scale × lifetime multiplier`.
38. Non-uniform base ratio: 이후 System/Layer X/Y scale이 달라도 그 비율을 보존한다.
39. Random scale interaction: seeded base scale 값과 RNG draw sequence를 보존한다.
40. Disabled result: multiplier 1.0이며 v0.0.15 render와 bit/semantic equivalent.
41. Min/max policy: 0.0..16.0. 0은 완전 축소를 허용하고 16은 현재 UI/render에 맞춘 안전 상한이다.
42. Negative policy: mirror 의미가 섞이지 않도록 거부한다. NaN/Inf/범위 초과/잘못된 easing/비-Boolean enable도 거부한다.

## UI

43. Section location: Effect Editor의 Particle Inspector 내부 `Over Lifetime` group.
44. Enable control: `Scale over Lifetime` checkbox.
45. Start Scale: 0.0..16.0 numeric control.
46. End Scale: 0.0..16.0 numeric control.
47. Easing: 기존 네 easing을 쓰는 combo box.
48. Disabled state: checkbox OFF면 세 하위 control을 disable하지만 값은 보존한다.
49. Tooltip: composition timeline이 아니라 각 particle의 birth-to-death multiplier임을 설명한다.
50. Korean: `수명에 따른 변화`, `수명별 크기`, `시작 크기`, `끝 크기`, `이징` 및 한국어 tooltip 추가.
51. English: `Over Lifetime`, `Scale over Lifetime`, `Start Scale`, `End Scale`, `Easing` 및 영어 tooltip 추가.
52. Multi-selection policy: 현재 구조에 맞춰 primary logical Effect Resource Layer만 편집한다. 새 multi-edit 의미는 추가하지 않았다.

## Undo

53. Toggle: 사용자 commit 1회당 Undo 1개.
54. Start: 사용자 commit 1회당 Undo 1개.
55. End: 사용자 commit 1회당 Undo 1개.
56. Easing: 사용자 commit 1회당 Undo 1개.
57. No-op: settings equality guard로 Undo/dirty/revision 0.
58. Refresh: `_loading` guard로 Undo/dirty/model mutation 0.

## Runtime

59. Different birth times: 각 instance의 own `birth_frame`과 lifetime으로 서로 다른 progress를 계산한다.
60. Linear: 위치 계산은 그대로이고 lifetime scale만 곱한다.
61. Orbit: radius/angle trajectory는 그대로이고 lifetime scale만 곱한다.
62. Helix: radius/angle/axis trajectory는 그대로이고 lifetime scale만 곱한다.
63. Seed determinism: lifetime 설정을 spawn cache key에서 제외해 같은 seed의 spawn/random choices를 유지한다.
64. Motion isolation: 기존 motion normalization과 position 결과를 바꾸지 않는다.

## Transform Isolation

65. System Transform: scale multiplier 앞뒤의 기존 System transform 의미 유지.
66. Surface Transform: opacity/perspective/rotation 등 기존 Surface 의미 유지.
67. Parenting: hierarchy/world transform 로직 변경 없음.
68. parent_offset: persistent 값과 적용 결과 변경 없음.
69. Rotation Revolution: 720°, 1080°, -450° 등 누적값을 normalize하지 않는다.
70. Advanced: bypass flag와 Transform 모델을 변경하지 않는다.

## Serialization

71. FORMAT 12 load: missing `scale_over_lifetime`을 정상 허용.
72. Defaults: false, 1.0, 1.0, Linear.
73. FORMAT 13 save: enabled/start/end/easing 네 필드를 저장.
74. Round-trip: 전체 channel 값 exact.
75. Easing round-trip: 네 easing 모두 exact.
76. Old render compatibility: FORMAT 12 fixture의 migration 전후 frame exact 및 disabled seed/build 결과 exact.

## Preview / Export

77. Preview: Inspector commit이 기존 materialize/invalidation 경로를 통해 즉시 현재 frame에 반영된다.
78. Frame step: current-frame과 full materialized rendering이 같은 evaluator를 사용한다.
79. Export: PNG frame/sequence가 canonical Effect renderer를 통해 lifetime scale을 사용한다.
80. Preview/Export match: current/full/materialized/export pixels exact 자동 검증.
81. Overscan: Resource Editor의 editor-only outside-output artwork 가시성 의미 유지.
82. Strict output clip: Effect preview/export 배열과 PNG dimensions는 project output 크기를 넘지 않는다.

## Performance

83. 100 particles: OFF 10.925 ms / ON Linear 12.849 ms / ON Ease In/Out 12.147 ms.
84. 500 particles: OFF 62.270 ms / ON Linear 56.791 ms / ON Ease In/Out 51.859 ms.
85. 1000 particles: OFF 94.443 ms / ON Linear 87.752 ms / ON Ease In/Out 103.166 ms.
86. 5000 particles: OFF 417.179 ms / ON Linear 400.343 ms / ON Ease In/Out 403.206 ms.
87. Allocations: lifetime hot path는 scalar locals만 사용하며 channel별 collection을 만들지 않는다.
88. Deepcopy/serialization/filesystem: per-particle/per-frame evaluator에서 모두 사용하지 않는다. 위 값은 32×32, 1×1 sprite, age 4/8, 실제 frame render 3회 median이며 환경 잡음이 있으나 명백한 scale-dependent 증가 회귀는 보이지 않았다.

## Representative Effects

89. Hit Spark: 1.0→0.0 Ease In, 사라지며 축소.
90. Explosion: 0.2→1.4 Ease Out, 빠르게 팽창.
91. Smoke: 0.5→1.8 Ease Out, 수명 동안 확대. 기존 단순 opacity fade는 있으나 color/noise/drag/multi-point가 없어 완전한 smoke system은 아니다.
92. 표현력 개선 판단: grow/shrink/expand를 source artwork 재제작 없이 만들 수 있어 유의미하다. grow-then-shrink는 아직 직접 표현할 수 없다.

## Tests

93. 수정 파일: model, evaluator/render, Inspector/MainWindow, localization, version/format, docs와 format 기대값 테스트.
94. 생성 파일: `app/services/lifetime_modulation_service.py`, `tools/benchmark_particle_lifetime_scale.py`, 이 보고서.
95. 신규 tests: `tests/test_alpha_easing_integrity.py`, `tests/test_particle_scale_over_lifetime.py`.
96. Alpha Easing regression: refresh/selection/save-load/Undo/no-op/비-Alpha control 포함 통과.
97. Lifetime evaluator tests: disabled/boundary/clamp/zero-invalid lifetime/네 easing/입력 validation 통과.
98. UI/Undo tests: disable-preserve/toggle/four controls/no-op/primary-only/auto-key 없음 통과.
99. Serialization tests: FORMAT 12 default·old render, FORMAT 13 round-trip·네 easing 통과.
100. Export tests: preview/full/materialized/PNG sequence parity, dimensions, strict clip 통과.
101. Focused particle regression: 신규 두 파일 43 passed in 1.27s.
102. Full pytest: 1181 passed in 74.04s, 0 failed.
103. compileall: `python -m compileall -q app` exit 0.
104. --version: `Pixel Effect Maker v0.0.16`, exit 0.
105. FORMAT_VERSION: 13.
106. --check: exit 0. Sandbox에서 AppData log 파일 권한 경고가 있으나 application check는 성공.
107. run_app.bat: 지정 venv로 `--check` exit 0, 같은 sandbox log 권한 경고.
108. git diff --check: exit 0, 기존 Windows LF→CRLF 안내만 있음.

## Audit Update

109. Scale over Lifetime status: PARTIAL. start/end/easing의 end-to-end 경로는 완성됐지만 multi-point와 독립 X/Y가 없다.
110. 남은 Over Lifetime 한계: multi-point curve, X/Y 독립 scale, color/tint, 별도 alpha curve, rotation/speed channel, timeline parameter animation 없음.
111. 다음 Tier S/A Gap: Particle Tint/Color over Lifetime, Additive, Sprite Sheet metadata, Work Area, deterministic force/drag 순.

## Git

112. 최종 HEAD: `baff65b862739c7b607a17b4d26a24f956888539`.
113. Staged: 0. `테스트소스.png`도 untracked/unstaged 유지.
114. v0.0.16 commit: 0. 모든 P0/v0.0.16 변경은 unstaged/uncommitted.
115. Tag/push/build: 모두 0. PyInstaller/ZIP/release도 수행하지 않았다.

## Manual QA

116. Codex Windows native GUI manual 여부: **수행하지 않음**.
117. Alpha Easing checklist: Ease Out 저장 → A/B selection 왕복 → exact, Save/Reload → exact를 실제 GUI에서 확인할 것.
118. Grow checklist: ON, 0→1 Ease Out으로 particle별 birth 기준 확대 확인.
119. Shrink checklist: 1→0 Ease In으로 수명 끝까지 축소 확인.
120. Mixed birth-time checklist: 지속 emission particle들이 서로 다른 진행률인지 확인.
121. Random Scale checklist: 기존 무작위 initial scale 비율 위에 lifetime multiplier가 곱해지는지 확인.
122. Motion checklist: Linear/Orbit/Helix 각각에서 위치 경로 불변과 scale 진행 확인.
123. Undo checklist: Enable/Start/End/Easing 각각 Undo/Redo 한 단계인지 확인.
124. Save/Reload checklist: enabled/start/end/easing exact 확인.
125. Overscan/Export checklist: Resource Editor outside artwork 표시와 최종 Effect output strict clip을 구분해 확인.

## Final

126. Alpha Easing corruption: 해결. 누락된 settings reconstruction field가 근본 원인이었다.
127. Particle Lifetime Foundation: 최소 reusable scalar model/evaluator/persistence/UI/Undo/render 경로 완성.
128. Scale over Lifetime 제작 가능: uniform grow/shrink/expand 가능.
129. 기존 프로젝트 호환성: FORMAT 12 missing field는 disabled default, 기존 결과 유지.
130. Effect 표현력 개선: Hit Spark/Explosion/Smoke 계열의 핵심 size progression을 직접 제작할 수 있게 됐다.
131. 가장 큰 남은 병목: lifetime color/tint와 Additive blend. 자연 motion(force/drag/noise)도 후속 큰 공백이다.
132. 다음 추천: **Particle Tint / Color over Lifetime**. 이번 scalar normalized-lifetime 기반을 재사용할 수 있고 Fire/Heal/Poison/Magic 구분에 즉시 도움이 된다. 그 다음은 모든 compositor/transparent export 계약을 함께 다뤄야 하는 Additive Blend다.

사용자 파일 `테스트소스.png` 최종 SHA256은 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`이며 이름·내용·stage 상태를 보존했다.
