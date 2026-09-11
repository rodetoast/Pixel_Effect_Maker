# Pixel Effect Maker v0.0.17 완료 보고

작성일: 2026-09-11. 자동화 검증 결과이며 Windows 네이티브 GUI 수동 QA는 수행하지 않았다.

## v0.0.16 Checkpoint

1. v0.0.16 checkpoint commit hash: `3c4df009665e544ed9cca58a899f2fce7c7e46dc` (`Add particle scale over lifetime`).
2. 포함 파일: Alpha Easing integrity fix, lifetime scalar foundation, Scale over Lifetime model/render/UI/localization, FORMAT 13/version, 관련 tests/docs/benchmark 총 46개 파일.
3. 제외 파일: `테스트소스.png`, 기존 build/dist, exe/zip/cache/log/temp/backup, 사용자 project 파일. `git add -A`는 사용하지 않았다.
4. 작업 시작 pytest: 1181 passed in 86.30s, 0 failed. compileall/check/launcher exit 0.

## Color Pipeline Audit

5. 기존 base tint 위치: 별도 Particle/Layer RGB tint 모델은 없었다. imported Resource/AnimationClip의 source RGBA artwork가 유일한 base color다.
6. 기존 alpha 위치: source pixel Alpha, Particle `opacity_start/end/easing`, Layer Space opacity, 상위 Effect/Layer opacity가 각각 별도다.
7. Renderer tint 적용 위치: v0.0.17에서 nearest-sampled source RGB에 lifetime RGB factor를 곱한 뒤 기존 opacity Alpha와 straight source-over를 적용한다.
8. Preview/export path: current-frame preview, full render, generated output, PNG export가 공용 particle/effect renderer를 사용한다.
9. Premultiplied alpha 여부: internal/output 배열은 straight-alpha `uint8 RGBA`. source-over 계산 중에만 float alpha-weighting 후 straight RGB로 복원한다.

## Lifetime Foundation

10. v0.0.16 재사용: `normalized_lifetime_age`, 공용 clamp/easing, enabled identity, model serialization pattern, Inspector `_loading`, MainWindow equality/no-op와 merge-ID Undo 패턴.
11. Scale-specific assumption: scalar start/end 값은 RGB에 직접 재사용할 수 없어 `LifetimeColorModulation`을 추가했지만 normalized age와 easing system은 복제하지 않고 공유했다.
12. Color channel model: strict Boolean `enabled`, RGB3 `start_rgb/end_rgb`, 네 easing을 가진 최소 persistent dataclass.
13. Normalized age reuse: birth 0.0, last visible frame 1.0인 기존 `age/(lifetime-1)` convention.
14. Easing reuse: Linear, Ease In, Ease Out, Ease In/Out과 공용 `eased_lifetime_amount`.

## Color Semantics

15. Start Color: 0..255 정수 RGB3, 기본 white `(255,255,255)`.
16. End Color: 0..255 정수 RGB3, 기본 white `(255,255,255)`.
17. RGB interpolation: 각 채널을 독립적으로 start→end 보간하고 0..1 tint factor로 source RGB에 곱한다.
18. Interpolation color space: 기존 8-bit sprite convention과 맞춘 encoded sRGB channel arithmetic. HSV/HSL/linear-light/HDR은 도입하지 않았다.
19. Base Tint 결합: 별도 base tint가 없으므로 `final RGB = source artwork RGB × lifetime RGB / 255`인 component-wise modulation이다.
20. Alpha isolation: color model/serialization/picker/evaluator에는 Alpha가 없고 raster tint helper도 RGB 3채널만 쓴다.
21. Disabled identity: false + white→white + Linear이며 기존 source RGBA bytes/render와 동일하다.

## Schema

22. Version: Pixel Effect Maker v0.0.17.
23. FORMAT_VERSION: 14.
24. Bump 이유: `ParticleEmitterSettings.color_over_lifetime`이라는 새 persistent field와 RGB schema가 추가됐다.
25. Migration: FORMAT <=13에서 field가 없으면 disabled white identity로 materialize하며 source 파일을 자동 rewrite하지 않는다.
26. Old project compatibility: FORMAT 13 fixture의 migration 전후 render exact 검증.

## UI

27. Over Lifetime 구조: 기존 Alpha Easing/Scale controls 아래에 Color enable, Start swatch, End swatch, Color Easing을 배치했다.
28. Color enable: `Color over Lifetime / 수명별 색상` checkbox.
29. Start picker: 현재 `■ #RRGGBB`가 보이는 standard Qt QColorDialog button.
30. End picker: 동일한 swatch/hex button.
31. Easing: 공용 네 easing combo.
32. Alpha UI 차단: QColorDialog에 ShowAlphaChannel을 요청하지 않으며 반환 QColor의 RGB만 읽는다. Alpha 값은 저장하지 않는다.
33. Tooltip: 각 Particle birth-to-death RGB tint이고 opacity는 바꾸지 않는다고 명시한다.
34. Korean/English: group, labels, picker title, 네 control tooltip을 양 언어로 추가했다.
35. Selection/refresh integrity: sentinel RGB/Easing 반복 refresh 및 A→B→A에서 model/Undo/dirty/revision mutation 0.

## Undo

36. Toggle: accepted user action 1회 = Undo 1개.
37. Start: 최종 color 선택 1회 = Undo 1개.
38. End: 최종 color 선택 1회 = Undo 1개.
39. Easing: selection 1회 = Undo 1개.
40. Dialog cancel: invalid QColor 반환 시 mutation/Undo 0.
41. No-op: 같은 RGB 재선택 시 mutation/Undo/dirty/revision 0.
42. Refresh: `_loading`과 settings equality guard로 mutation/Undo 0.

## Runtime

43. Independent birth ages: 같은 composition frame의 birth 0/2 particle이 각각 lifetime 0.5/0.0 색을 가짐을 검증.
44. Scale+Color coexistence: scale multiplier와 RGB factor를 별도로 계산하고 둘 다 동시에 render arguments에 전달한다.
45. Linear: RGB만 바뀌고 position trajectory exact.
46. Orbit: RGB만 바뀌고 radius/angle trajectory exact.
47. Helix: RGB만 바뀌고 radius/angle/axis trajectory exact.
48. Seed: Color field를 spawn cache key에서 제외하고 random draw를 추가하지 않아 instance sequence exact.
49. Trajectory isolation: color disabled/enabled diagnostics의 local/world projected position을 frame별 비교해 exact.

## Alpha Integrity

50. Particle Alpha: 기존 source alpha와 `opacity_start/end` 결과 유지.
51. Layer opacity: Layer Space static/keyframed opacity 모델을 변경하지 않는다.
52. Alpha track: opacity track과 easing의 직렬화/model 값은 render 전후 exact.
53. Alpha easing: v0.0.16 `ParticleEmitterSettings.easing` Inspector fix 유지.
54. Save/Reload: Color RGB/Easing round-trip과 별개로 기존 Alpha fields가 settings reconstruction에서 유지된다.

## Rendering

55. Operation order: source frame 선택 → nearest transform sample → lifetime RGB multiply → Particle opacity를 Alpha에 적용 → straight source-over → Layer Space opacity → 상위 Effect composition.
56. Transparent pixels: tint는 Alpha를 쓰거나 늘리지 않아 fully transparent source가 보이지 않는다.
57. Premultiplied regression: semi-transparent sentinel에서 RGB tint와 Alpha opacity의 straight-alpha 결과를 byte 단위 검증했다.
58. Base tint interaction: 별도 static base tint는 아직 없으며 source artwork RGB 자체를 보존한 multiplier 합성이다.

## Preview / Export

59. Preview: Inspector accepted commit이 현재 frame invalidation/materialization 경로에 즉시 반영된다.
60. Export: PNG frame/sequence가 canonical Effect renderer 결과를 사용한다.
61. Parity: current-frame/full/materialized/project compose/decoded PNG exact.
62. Overscan: Resource Editor outside-output artwork 표시 의미를 변경하지 않는다.
63. Strict clipping: color가 적용돼도 preview/export 배열과 PNG dimensions는 project output bounds로 제한된다.

## Performance

64. 100: OFF 8.109 ms / Color Linear 9.759 / Color Ease In/Out 9.208 / Scale+Color 9.585.
65. 500: OFF 43.818 ms / Color Linear 47.980 / Color Ease In/Out 48.580 / Scale+Color 47.201.
66. 1000: OFF 82.358 ms / Color Linear 99.954 / Color Ease In/Out 93.722 / Scale+Color 93.154.
67. 5000: OFF 421.436 ms / Color Linear 486.353 / Color Ease In/Out 472.513 / Scale+Color 467.699.
68. Per-particle allocations: lifetime evaluator는 primitive float만 반환하고 QColor/dict/deepcopy를 만들지 않는다. RGB 적용은 기존 sampled ROI buffer에 in-place로 수행하며 NumPy channel conversion temporary만 사용한다.
69. Scale+Color ON: 32×32, opaque 1×1 sprite, age 4/8, 실제 frame render 3회 median에서 Color-only와 같은 범위이며 추가 seed/cache rebuild 없음.

## Representative Effects

70. Fire: Yellow→Red와 Scale을 함께 평가.
71. Magic: White→Blue.
72. Poison: Bright Purple→Dark Purple.
73. Hit Spark: White→Orange.
74. 표현력 평가: source frame을 색별로 다시 만들지 않고 2-point lifetime tint를 제작할 수 있어 개선됐다. 3색 stop, palette random, additive glow는 아직 직접 지원하지 않는다.

## Tests

75. 신규 tests: `tests/test_particle_color_over_lifetime.py`, `tests/test_particle_color_lifetime_serialization.py`.
76. Focused count: 신규 Color 전용 38 passed; Color+Scale+Alpha+raster 묶음 87 passed; version/project 포함 broad 145 passed.
77. Alpha integrity regression: refresh/selection/save/Undo 및 color와의 독립성 통과.
78. Scale lifetime regression: evaluator/UI/serialization/render/export 통과.
79. Color lifetime regression: evaluator/RGB/Alpha/motion/seed/UI/Undo/fixtures 통과.
80. Serialization: FORMAT 13 migration, FORMAT 14 네 easing exact, corrupt payload rejection 통과.
81. Export: preview/full/materialized/PNG parity와 dimensions/clip 통과.
82. Full pytest: 1219 passed in 79.41s, 0 failed.
83. compileall: 최종 `python -m compileall app`로 확인.
84. --version: `Pixel Effect Maker v0.0.17`.
85. --check: exit 0; sandbox AppData log 권한 경고는 별도 기록.
86. run_app.bat: 지정 venv로 `--check` exit 0; 같은 sandbox log 권한 경고.
87. git diff --check: exit 0, Windows LF→CRLF 안내만 있음.

## Audit

88. Color over Lifetime 최종 상태: PARTIAL. 2-point RGB/easing end-to-end는 완성됐으나 multi-stop/HSV/static tint/random palette가 없다.
89. 아직 없는 기능: 3+ color stops, gradient editor, lifetime color timeline key, HSV/HSL/HDR, static/random tint palette, blend modes.
90. Alpha over Lifetime 필요성: 기존 Particle opacity start/end/easing은 있으나 독립 module/multi-point curve는 없다. Color와 분리한 후속 범위로만 검토한다.
91. Additive 필요성: Fire/Magic/glow 겹침 표현의 가장 큰 남은 공백이며 다음 독립 버전 1순위다.

## Git

92. 최종 HEAD: v0.0.16 checkpoint `3c4df009665e544ed9cca58a899f2fce7c7e46dc` 유지.
93. Staged: 0. `테스트소스.png`도 계속 untracked/unstaged.
94. v0.0.17 commit: 0; 변경은 unstaged/uncommitted.
95. Tag: 0.
96. Push/build: 0. 새 Build/PyInstaller/ZIP/Release를 수행하지 않았다.

## Manual

97. Windows native GUI manual 수행 여부: **수행하지 않음**. `docs/MANUAL_TEST_CHECKLIST.md`에 사용자 확인 항목만 작성했다.

## Final

98. Lifetime Foundation multi-channel 확장: 성공. normalized age/easing/identity/persistence/Inspector principles를 Scale과 Color가 공유한다.
99. Scale와 Color 독립성: 성공. 별도 model/state/merge-ID/evaluator이며 동시 ON fixture 통과.
100. Alpha 완전 분리: 성공. RGB3만 저장·보간·곱하고 source/Particle/Layer Alpha를 건드리지 않는다.
101. 기존 프로젝트 render 보존: FORMAT 13 missing-field migration과 disabled identity render exact.
102. 가장 큰 남은 표현력 병목: Additive blend, 그 다음 natural force/drag/noise와 multi-point lifetime curve.
103. 다음 추천 기능: **Additive Blend 최소 end-to-end contract**. 모든 compositor와 preview/export의 straight-alpha 계약을 한 독립 버전에서 reference-image tests와 함께 다뤄야 한다.

보호 대상 `테스트소스.png`의 기준 SHA256은 `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564`이다.
