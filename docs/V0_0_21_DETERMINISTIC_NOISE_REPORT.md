# Pixel Effect Maker v0.0.21 — Deterministic Smooth XY Noise 작업 보고

2026-09-22. 자동 검증 및 코드 감사 기록. Windows 네이티브 GUI 수동 QA는 수행하지 않았다. v0.0.21 변경은 사용자 GUI 승인 전 unstaged/uncommitted로 유지한다.

## Baseline / v0.0.20 checkpoint

1. 시작 HEAD: `d00e9781bb655370e226294db486fad4e5420011`.
2. 시작 Version: `0.0.20`.
3. 시작 FORMAT_VERSION: `17`.
4. 시작 전체 pytest: `1300 passed in 82.44s`.
5. Drag 로컬 커밋: `d0173ef799b6776ff7d9ebd98ceefd8ca3397bed` (`Add analytic particle drag`).
6. 승인 범위 50개 파일만 명시적으로 stage; `git add -A` 미사용.
7. 보호 PNG, 사용자 프로젝트, build/dist/exe/zip/cache/log/temp/backup 제외.
8. Checkpoint 직후 staged 0, 보호 PNG만 untracked, tag/push/build 없음.

## Stable identity and noise math

9. Identity는 기존 `ParticleInstance.particle_id`이며 emitter `settings.seed`와 결합한다.
10. `particle_noise_service.mix64()`는 고정 상수·명시적 64-bit mask를 쓰는 SplitMix64 finalizer다.
11. Python built-in `hash()`는 사용하지 않는다.
12. Noise 계산은 새 RNG draw나 per-sample RNG 객체를 사용하지 않는다.
13. X seed는 mixed particle seed와 `_X_SALT`를 다시 mix한다.
14. Y seed는 별도 `_Y_SALT`로 mix한다.
15. Lattice index는 `_LATTICE_SALT`와 mix하여 상위 53비트를 scalar로 변환한다.
16. Lattice 출력은 `[-1,+1]`이며 index 0은 정확히 0이다.
17. index 0 특별 규칙이 particle birth 원점을 보장한다.
18. Noise type은 시간축 1D smooth value noise × 독립 X/Y 채널이다.
19. 입력 age는 실제 `frame - birth_frame`이다.
20. Frequency 단위는 lattice intervals/frame이다.
21. Coordinate는 `actual_age × frequency`이다.
22. `floor(coordinate)`와 다음 lattice 값을 보간한다.
23. Fade는 `6u⁵ − 15u⁴ + 10u³`와 동등한 quintic 식이다.
24. Strength는 Particle/System local X/Y 각 축의 최대 픽셀 진폭이다.
25. Offset은 `(strength × value_x, strength × value_y, 0)`이다.
26. Z Noise는 0이며 구현하지 않았다.
27. Birth age 0은 exact `(0,0)`.
28. Frequency 0은 exact `(0,0)`.
29. Strength 0은 exact `(0,0)`.
30. 각 축 절댓값은 Strength 이내; vector magnitude를 반경 Strength로 주장하지 않는다.

## Motion composition

31. Actual age는 0-based frame 수다.
32. Drag effective age는 기존 `-expm1(-d×age)/d`다.
33. Base Motion은 Linear/Orbit/Helix를 Drag effective age로 진행한다.
34. Gravity는 실제 age의 `0.5×g×age²`다.
35. Noise는 실제 age와 stable particle seed다.
36. 최종 local position은 Base + Gravity + Noise다.
37. Noise 좌표계는 Particle/System local XY다.
38. 이후 local perspective → Layer/Parent 2.5D → Surface → Composition 순서를 유지한다.
39. Linear 기존 velocity 설정과 초기 방향은 그대로다.
40. Drag는 Linear의 기본 이동 거리만 감쇠한다.
41. Noise는 그 결과에 XY 위치 변위만 더한다.
42. Orbit radius 설정/평가를 Noise는 바꾸지 않는다.
43. Orbit phase 설정/평가를 Noise는 바꾸지 않는다.
44. Drag의 Orbit 각도 진행 의미를 유지한다.
45. Noise는 완성된 Orbit path 뒤에 더한다.
46. 최종 pixel path가 완벽한 원에서 벗어나는 것은 의도된 위치 변화다.
47. Helix radius는 변경하지 않는다.
48. Helix axis 및 axial setting은 변경하지 않는다.
49. Helix phase setting은 변경하지 않는다.
50. Drag의 Helix phase/axial 감속을 유지한다.
51. Noise는 완성된 Helix 위치에만 더한다.

## Determinism / seed isolation

52. 같은 seed와 설정이면 같은 offset.
53. 같은 실제 age면 같은 offset.
54. 같은 particle ID면 같은 path.
55. 다른 particle ID는 일반적으로 다른 X/Y seed와 path.
56. 순차 렌더는 동일 순수 evaluator를 호출한다.
57. Direct seek도 과거 상태 없이 같은 evaluator를 호출한다.
58. Frame step은 frame index만 달라지며 상태 적분은 없다.
59. Full render의 N과 current-frame N을 비교한다.
60. Generated output은 full render를 materialize한다.
61. PNG decode는 compose frame과 비교한다.
62. 고정 integer mixer와 sentinel로 process-independent 값을 고정했다.
63. Noise 함수는 particle iteration order에 독립이다.
64. Spawn RNG draw 순서는 변경하지 않았다.
65. Particle ID는 변경하지 않았다.
66. Birth frame은 변경하지 않았다.
67. Spawn position은 변경하지 않았다.
68. Random direction/velocity는 변경하지 않았다.
69. Random scale은 변경하지 않았다.
70. Resource playback random sampling도 변경하지 않았다.

## Version / UI / Undo

71. Version: `0.0.21`.
72. FORMAT_VERSION: `18`.
73. Model: `noise_enabled`, `noise_strength`, `noise_frequency`.
74. Defaults: `False`, `1.0 px`, `0.1 intervals/frame`.
75. FORMAT ≤17은 Noise OFF/default로 load하며 open만으로 원본을 rewrite하지 않는다.
76. Noise OFF의 old render identity를 migration 테스트로 확인한다.
77. bool type, 음수, 상한 초과, NaN/Inf payload를 거부한다.
78. Inspector 섹션은 기존 Natural Motion이다.
79. Label은 Noise / 노이즈다.
80. Strength는 축별 최대 위치 변위(px)다.
81. Frequency는 변화 속도(intervals/frame)다.
82. Strength 범위 `0..4096`.
83. Frequency 범위 `0..1`.
84. Strength decimals 3, Frequency decimals 4.
85. Strength step .25, Frequency step .01.
86. 한국어 label/tooltip 제공.
87. English label/tooltip 제공.
88. Tooltip은 독립 XY, seed 재현, birth, 속도, Gravity/Drag 시간 불변을 설명한다.
89. OFF면 두 숫자 입력만 disable하고 값을 보존한다.
90. Inspector refresh/selection은 모델·Undo를 변경하지 않는다.
91. Toggle 편집은 한 Undo command.
92. Strength 편집은 한 Undo command.
93. Frequency 편집은 한 Undo command.
94. 동일 값은 Undo를 추가하지 않는다.
95. Refresh도 Undo를 추가하지 않는다.

## Lifetime / composition / transforms

96. Particle lifetime/death frame은 불변이다.
97. Scale over Lifetime은 실제 age를 유지한다.
98. Color over Lifetime은 실제 age를 유지한다.
99. Opacity/Alpha easing은 실제 age를 유지한다.
100. Sprite frame 및 Playback Speed는 기존 규약을 유지한다.
101. Gravity는 actual age다.
102. Drag는 base-motion effective age에만 적용한다.
103. Noise는 Drag와 무관한 actual age다.
104. `Base(drag_age)+Gravity(age)+Noise(age,id)` 계약을 테스트한다.
105. Normal Blend 경로의 trajectory가 동일하다.
106. Additive Blend는 pixel composition만 바꾸며 Noise seed/path는 동일하다.
107. Gravity+Drag+Noise+Scale+Color+Additive 조합을 테스트한다.
108. Parenting 기존 pipeline을 통과한다.
109. parent_offset은 변경하지 않는다.
110. Keep World는 변경하지 않는다.
111. System Transform은 변경하지 않는다.
112. Surface Transform은 변경하지 않는다.
113. 2.5D projection은 변경하지 않는다.
114. Rotation Revolution은 변경하지 않는다.
115. 기존 Motion Guide는 대표 Particle/path의 보조 표시다.
116. 대표 seed는 emitter seed와 고정 particle ID 0이다.
117. Noise ON에서는 대표 Particle의 deterministic Noise를 표시한다.
118. Guide 재평가는 같은 설정에서 정확히 같은 path다.

## Cache / Preview / Performance

119. Noise OFF→ON은 render/playback key를 바꾼다.
120. Strength 변경도 key를 바꾼다.
121. Frequency 변경도 key를 바꾼다.
122. ON→OFF는 원래 OFF output을 복원한다.
123. Spawn cache key는 Noise 3개 필드를 제외해 기존 instances를 재사용한다.
124. Cache 전환 테스트는 stale preview frame 부재를 확인한다.
125. Current-frame render를 확인한다.
126. Full render를 확인한다.
127. Generated output을 확인한다.
128. PNG decode를 확인한다.
129. 같은 frame의 RGBA parity를 확인한다.
130. Editor Overscan 코드는 변경하지 않았다.
131. Final strict clip/PNG dimensions는 유지된다.

벤치마크: 32×32, 반투명 1×1 sprite, age 4/8, 각 3회 median. 단위 ms. 시스템 부하에 따른 변동이 있는 참고 수치다.

| Count | OFF | Noise | Gravity+Drag+Noise | Full stack |
| ---: | ---: | ---: | ---: | ---: |
| 100 | 5.675 | 5.862 | 5.557 | 7.074 |
| 500 | 28.309 | 27.788 | 29.222 | 36.120 |
| 1000 | 57.713 | 57.116 | 57.918 | 71.890 |
| 5000 | 278.710 | 285.701 | 286.686 | 362.873 |

132. 100 OFF/ON: 5.675/5.862ms.
133. 500 OFF/ON: 28.309/27.788ms.
134. 1000 OFF/ON: 57.713/57.116ms.
135. 5000 OFF/ON: 278.710/285.701ms.
136. Gravity+Drag+Noise: 5.557/29.222/57.918/286.686ms.
137. Full stack: 7.074/36.120/71.890/362.873ms.
138. Noise ON/OFF ratio: 1.033/0.982/0.990/1.025.
139. Hot path에 RNG 객체, deepcopy, filesystem, 이력 배열을 추가하지 않았다.

## Effects / Tests / Audit / Git

140. Smoke: 상승+Drag+저주파 Noise+Scale/Opacity 조합 가능; 시각 QA 미수행.
141. Dust: 저속 Linear+Drag+소진폭 Noise 가능; 시각 QA 미수행.
142. Ember: 음수 Gravity+Noise+Color+Additive 가능; 시각 QA 미수행.
143. Magic Wisp: Orbit+Noise+Color+Additive 가능; 시각 QA 미수행.
144. Hit Spark: Gravity+Drag+소진폭 Noise+Scale/Color+Additive 테스트; 시각 QA 미수행.
145. 표현력: 파티클별 부드러운 유영 경로 기반이 생겼지만 최종 미감은 GUI에서 검증해야 한다.
146. 신규 files: noise service, noise 테스트 2개, benchmark, 이 보고서.
147. Focused 테스트: Noise+Drag+Orbit/Helix 91 passed.
148. Fixed mix/lattice/axis sentinel 테스트.
149. Quintic endpoint와 lattice 경계 연속성 테스트.
150. 동일 seed/age/id 및 다른 id/iteration order 테스트.
151. 직접 프레임/full/generated/PNG parity 테스트.
152. Linear/Orbit/Helix 최종 위치 차분 테스트.
153. Gravity/Drag 시간 분리 테스트.
154. Lifetime diagnostic isolation 테스트.
155. Spawn instance/cache identity 테스트.
156. FORMAT 17 migration, FORMAT 18 roundtrip, invalid payload 테스트.
157. OFF→ON→strength→frequency→OFF cache 테스트.
158. Parent/System/Surface/2.5D/revolution 테스트.
159. PNG RGBA/dimensions 및 final clip 테스트.
160. Full pytest: 최종 `1335 passed in 76.82s`, exit 0.
161. `compileall -q app tests tools`: exit 0.
162. `--version`: `Pixel Effect Maker v0.0.21`, exit 0.
163. `--check`: exit 0; sandbox AppData 로그 권한 경고만 발생했다.
164. `run_app.bat --check`: 테스트 Python override 사용, exit 0; 같은 로그 경고.
165. `git diff --check`: exit 0.
166. 좁은 Deterministic Smooth Positional Noise: COMPLETE.
167. Natural Motion 전체: PARTIAL.
168. True turbulence/acceleration noise는 없다.
169. 범용 Force Stack은 없다.
170. 다음 큰 gap은 force/turbulence와 multi-point lifetime curve다.
171. 최종 HEAD는 v0.0.20 Drag checkpoint `d0173ef799b6776ff7d9ebd98ceefd8ca3397bed`이어야 한다.
172. v0.0.21 staged는 0 (`git diff --cached --name-only` 빈 출력).
173. v0.0.21 commit은 0.
174. Tag/push/build/PyInstaller/ZIP은 수행하지 않는다.
175. Windows native GUI manual QA: **수행하지 않음**.
176. Noise는 frame RNG가 아닌 pure deterministic function이다.
177. Birth offset은 exact `(0,0)`이다.
178. Quintic interpolation은 lattice 경계에서 부드럽다.
179. 다른 Particle는 독립적인 stable path를 가진다.
180. 고정 정수 mixer/sentinel은 Python process에 독립적이다.
181. Direct seek는 상태 이력 없이 deterministic하다.
182. Drag는 Noise 시간을 감쇠시키지 않는다.
183. Gravity는 actual age를 유지한다.
184. Lifetime channels는 영향을 받지 않는다.
185. FORMAT ≤17 Noise OFF identity로 기존 render를 보존한다.
186. Smoke/Dust/Ember/Wisp/Spark의 움직임 표현 범위가 넓어졌지만 GUI 미감은 미검증이다.
187. 다음 추천은 seek-safe deterministic force/turbulence의 제품 의미와 성능 예산 설계다.

## 최종 자동 검증 기록

- Full pytest: `1335 passed in 76.82s` (exit 0).
- `compileall -q app tests tools`: exit 0.
- `python -m app.main --version`: `Pixel Effect Maker v0.0.21`.
- `python -m app.main --check`, `run_app.bat --check`: exit 0. 두 명령에서 AppData 로그 파일의 sandbox 권한 `PermissionError` 경고가 있으나 자체 진단은 성공했다.
- `git diff --check`: exit 0. 최종 HEAD `d0173ef799b6776ff7d9ebd98ceefd8ca3397bed`; staged 0. v0.0.21 변경은 unstaged/uncommitted.
- `테스트소스.png` SHA-256: `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564` (기준과 일치).
