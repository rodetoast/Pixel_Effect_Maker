# Pixel Effect Maker v0.0.18 완료 보고

## Preflight / v0.0.17 Checkpoint

1. v0.0.17 checkpoint hash: `dd4cb4359efa7798236b2c81ca8fe19ee611eb9c` (`Add particle color over lifetime`).
2. checkpoint 포함 파일: Color over Lifetime 모델·직렬화·렌더·UI·문서·테스트·benchmark의 명시적 47개 파일.
3. 제외 파일: 사용자 소유 `테스트소스.png`; stage/commit 대상에서 제외했다.
4. 작업 시작 pytest: v0.0.17에서 `1219 passed`, failures 0.

## Compositor Audit

5. renderer RGBA format: 모든 canonical buffer는 RGBA8 straight-alpha, 중간 최종 레이어 합성 canvas는 float32 straight-alpha다.
6. straight/premultiplied policy: 저장은 straight, 계산 기여도만 premultiplied로 변환한다.
7. source-over helper: 기존 `_source_over` 및 float32 Normal 연산 순서를 보존했다.
8. Particle→Layer boundary: `render_transformed_source`가 각 Particle을 emitter RGBA에 선택 모드로 합성한다.
9. Layer→Effect boundary: generated layer ID를 logical Particle Resource Layer로 역조회해 Additive를 적용한다.
10. Effect→Final boundary: `Project.compose_frame`과 exact playback이 동일 resolver/compositor를 사용한다.
11. PNG boundary: `export_png_frames`는 `Project.compose_frame`의 baked RGBA를 저장한다.
12. opacity 적용 순서: source alpha → Particle opacity → emitter 합성 → Layer Space opacity → generated Layer opacity다.
13. color 적용 순서: sampled source RGB에 Color Lifetime tint를 먼저 적용하고 Alpha 기여도를 계산한다.

## Blend Contract

14. BlendMode model: `BLEND_NORMAL`, `BLEND_ADDITIVE`, 폐쇄형 `BLEND_MODES`, strict validator를 추가했다.
15. Normal: 기존 source-over path다.
16. Additive: premultiplied light contribution 합산 path다.
17. property scope: `ParticleEmitterSettings.blend_mode`; Single placement와 일반 Layer UI에는 노출하지 않는다.
18. default: `normal`.
19. Additive RGB equation: `Po = clamp(Cd*Ad + Cs*As, 0, 1)`.
20. Additive Alpha equation: `Ao = clamp(Ad + As, 0, 1)`.
21. straight↔premultiplied conversion: `Co = Po/Ao` when `Ao>0`, otherwise RGB 0으로 복원한다.
22. clamp policy: premultiplied RGB와 Alpha를 각각 `[0,1]` clamp해 overflow/wrap을 막는다.
23. rounding policy: RGBA8 내부 경계는 기존과 같은 `np.rint`; float32 final 경계는 기존 truncating uint8 conversion을 유지한다.

## Reference Math

24. transparent destination: 첫 visible source의 straight RGBA가 보존됨을 확인했다.
25. zero-alpha source: 숨은 RGB가 destination에 기여하지 않음을 확인했다.
26. opaque black: Alpha는 누적되되 RGB light contribution은 0이다.
27. opaque color: premultiplied contribution이 channel별 clamp된다.
28. semi-transparent destination: 독립 float64 reference equation과 `2e-7` 이내로 일치한다.
29. overlap: 동일 emitter 두 Particle의 Alpha/기여도가 누적된다.
30. saturation: RGB와 Alpha가 1.0에서 포화되고 uint8 wraparound가 없다.

## Layer Semantics

31. same-emitter overlap: Additive branch가 per-particle raster composite에 연결됐다.
32. Additive layer vs lower Normal layer: 실제 `Project.compose_frame`에서 lower layer premultiplied contribution과 더해진다.
33. Normal foreground over Additive: 위쪽 opaque Normal layer가 기존 source-over 의미로 결과를 덮는 테스트가 통과했다.
34. two Additive layers: 두 logical Additive layer가 project order대로 reference 결과와 일치한다.
35. Layer Order: list top/front의 기존 순서와 stable Z sort를 변경하지 않았다.

## Opacity

36. source alpha: `As`의 첫 입력으로 사용된다.
37. particle opacity: sampled source alpha에 먼저 곱해진다.
38. layer opacity: final additive source alpha에 곱해 premultiplied contribution도 함께 줄인다.
39. zero opacity: compositor가 destination mutation 없이 skip한다.

## Schema

40. Version: `0.0.18`.
41. FORMAT_VERSION: `15`.
42. migration: FORMAT 14 이하에서 필드가 없으면 `normal` 기본값으로 로드된다.
43. old render exact: Normal float32 path를 역사적 reference 연산과 byte equality로 비교했다.
44. invalid payload: 대소문자 변형, multiply/screen, empty, null, number를 reject한다.

## UI

45. section: Over Lifetime과 분리된 Rendering/렌더링 group.
46. label: Blend Mode/블렌드 모드.
47. Normal: English `Normal`, Korean `일반`.
48. Additive: English `Additive`, Korean `가산`.
49. Korean: group, label, option, tooltip 번역을 추가했다.
50. English: group, label, option, tooltip 원문을 추가했다.
51. tooltip: 내부 Particle 겹침과 lower Layer 합성, premultiplied RGB, Alpha/opacity 존중을 설명한다.
52. refresh safety: `_loading`과 signal blocking 흐름에서 refresh는 edit을 만들지 않는다.
53. selection safety: 반복 selection/load가 settings, Dirty, Undo를 바꾸지 않는 테스트가 통과했다.

## Undo

54. Normal→Additive: dropdown 1회 선택이 merge ID 730의 한 명령이다.
55. Undo: 정확히 Normal로 복원한다.
56. Redo: 정확히 Additive로 복원한다.
57. no-op: 같은 persistent value는 `update_particle_draft`에서 반환해 명령을 만들지 않는다.
58. refresh: 세 번의 Inspector refresh 후 Undo count 0을 확인했다.

## Lifetime

59. Scale coexistence: Scale channel 필드/평가 순서를 변경하지 않았다.
60. Color coexistence: tint가 Additive contribution 계산 전에 적용된다.
61. Alpha independence: Color는 RGB만 바꾸고 Alpha Easing/Opacity를 바꾸지 않는다.
62. Scale+Color+Additive: combined full/current/baked/playback/PNG fixture가 통과했다.

## Motion

63. Linear: 기존 위치 평가를 그대로 사용한다.
64. Orbit: 기존 deterministic orbit 평가를 그대로 사용한다.
65. Helix: 기존 deterministic helix 평가를 그대로 사용한다.
66. trajectory exact: blend mode는 ParticleInstance 및 position evaluation 입력이 아니다.
67. seed exact: Normal/Additive의 `build_particle_instances` 결과가 동일하다.

## Transform

68. Parenting: world-affine resolution 코드를 변경하지 않았다.
69. parent_offset: 저장·평가 순서를 변경하지 않았다.
70. 2.5D: billboard projection 및 depth sort 뒤 raster composite만 분기한다.
71. System Transform: Layer Space path를 유지한다.
72. Surface Transform: 최종 transformed RGBA path를 유지한다.
73. Rotation Revolution: rotation total-degree 값과 sampling path를 변경하지 않았다.

## Cache

74. blend mode cache key/invalidation: settings repr 기반 base key와 playback relevant revision에 blend mode가 포함된다.
75. Normal→Additive stale frame 여부: cached full render가 Additive로 즉시 달라지는 테스트가 통과했다.
76. Additive→Normal stale frame 여부: 다시 Normal로 바꾼 결과가 최초 Normal bytes와 동일하다.

## Preview / Export

77. current-frame preview: `render_effect_resource_layer_current_frame` Additive 결과를 확인했다.
78. full render: `render_effect_resource_layer`와 모든 fixture frame이 일치한다.
79. generated output: apply된 frame pixels와 full render가 동일하다.
80. PNG: Pillow decoded PNG와 composed frame을 byte 비교했다.
81. parity: current/full/generated/exact playback/PNG가 동일하다.
82. export dimensions: project canvas `8×8×4`를 유지한다.
83. output clipping: 기존 destination ROI/canvas clipping path를 유지한다.
84. checkerboard isolation: 합성은 투명 RGBA canvas에서 수행되고 Qt checkerboard는 계산 후 화면 배경이다.

## PNG Contract

85. Additive bake 의미: PNG pixel에는 Pixel Effect Maker가 계산한 최종 Additive 결과가 들어간다.
86. PNG blend metadata 여부: reusable Blend Mode instruction은 저장되지 않는다.
87. future engine/runtime metadata 범위: sprite sheet/manifest/engine material 지시는 후속 기능이며 v0.0.18 범위 밖이다.

## Performance

88. 100 Normal/Additive: `6.303 ms / 5.466 ms`, Additive ratio `0.867×`.
89. 500: `27.758 ms / 26.370 ms`, Additive ratio `0.950×`.
90. 1000: `57.330 ms / 62.220 ms`, Additive ratio `1.085×`.
91. 5000: `285.498 ms / 269.889 ms`, Additive ratio `0.945×`.
92. Scale+Color+Additive: 100/500/1000/5000은 `7.146/34.224/76.367/356.012 ms`, Normal 대비 `1.134/1.233/1.332/1.247×`.
93. Normal regression: 기존 Normal branch 수식/연산 순서는 그대로이며 benchmark 변동은 단일 측정 환경의 noise를 포함한다.
94. allocations: hot path에 QColor/QImage/deepcopy/filesystem 작업은 없고 Additive ROI에만 bounded float temporaries가 생긴다.

## Representative Effects

95. Magic Glow: 반투명 blue/yellow tint의 겹침 누적이 가능한 기반이 됐다.
96. Hit Spark: 짧은 고Alpha sprite의 밝은 중심 포화를 표현할 수 있다.
97. Fire/Energy: Color over Lifetime과 Additive를 함께 써 밝은 core와 색 진행을 만들 수 있다.
98. Normal-vs-Additive 비교: 같은 seed/trajectory/source에서 합성 결과만 달라진다.
99. 표현력 개선 평가: 밝은 overlap과 glow 계열의 핵심 공백을 실제 final output까지 해소했다; 시각 평가는 native GUI QA가 남았다.

## Tests

100. 신규 files: blend model, Additive test, benchmark, 이 보고서.
101. focused tests: `tests/test_particle_additive_blend.py` 19개 통과.
102. math reference tests: transparent/hidden RGB/semi-alpha/saturation/reference equation 포함.
103. layer composition tests: lower Normal, upper Normal, two Additive 포함.
104. opacity tests: source, Particle, Layer, zero opacity 포함.
105. lifetime regression: 기존 Color/Scale/Alpha suite와 combined fixture 통과.
106. motion/seed: spawn state equality 및 전체 기존 motion suite 통과.
107. serialization: FORMAT 14 migration, FORMAT 15 round-trip, invalid payload 포함.
108. cache: Normal→Additive→Normal stale-frame 검증 포함.
109. export: current/full/generated/playback/PNG decoded byte parity 포함.
110. full pytest: 최종 `1238 passed`, failures 0.
111. compileall: app/tests/tools 성공.
112. --version: `Pixel Effect Maker v0.0.18`.
113. --check: exit 0.
114. run_app.bat: `--check` exit 0.
115. git diff --check: errors 0.

## Audit

116. Blend Mode final status: Normal/Additive 최소 end-to-end 범위 COMPLETE.
117. 남은 Blend gaps: Multiply/Screen/custom shader, per-particle material, engine manifest는 미구현.
118. PNG/runtime limitation: baked pixels만 제공하며 runtime blend semantics를 전달하지 않는다.
119. 다음 가장 큰 Effect gap: deterministic Gravity/Force/Drag/Noise 계열 자연 motion.

## Git

120. 최종 HEAD: `dd4cb4359efa7798236b2c81ca8fe19ee611eb9c`.
121. staged: v0.0.18 파일 0개; `테스트소스.png` 포함 모두 unstaged/untracked 상태를 유지한다.
122. v0.0.18 commit: 0.
123. tag: 0.
124. push/build: push, build, PyInstaller, ZIP 모두 0.

## Manual

125. Windows native GUI manual 여부: **수행하지 않음**.

## Final

126. Additive가 실제 lower Effect Layer와 합성되는지: 예, project/playback final compositor와 reference test로 확인했다.
127. Particle overlap도 밝아지는지: 예, same-emitter Additive Alpha/premultiplied contribution 누적을 확인했다.
128. Normal byte compatibility: 예, 역사적 reference 수식과 byte exact다.
129. Alpha contract 보존: 예, straight 저장·premultiplied 계산·source/Particle/Layer opacity 계약을 보존했다.
130. Scale+Color+Additive 조합 성공 여부: 성공.
131. Preview/Export parity: current/full/generated/playback/decoded PNG byte parity 성공.
132. 기존 프로젝트 보존: FORMAT 14 이하는 Normal identity로 migration하며 로드가 원본 파일을 rewrite하지 않는다.
133. 실제 Effect 표현력 개선 평가: glow, energy, spark의 밝은 겹침을 재료 재작업 없이 만들 기반이 크게 개선됐다.
134. 가장 큰 남은 병목: seek-safe natural force/noise motion과 engine-ready sprite sheet/metadata.
135. 다음 추천 기능: deterministic Gravity + Drag의 최소 end-to-end 모듈을 우선 구현하고, 이어 engine export manifest를 설계한다.
