# Pixel Effect Maker v0.0.20 — Analytic Drag 작업 보고

2026-09-22. 이 문서는 자동 검증과 코드 감사 기록이다. Windows 네이티브 GUI 수동 QA는 수행하지 않았다. v0.0.20 작업 트리는 의도적으로 unstaged/uncommitted이며, `테스트소스.png`는 보호 대상이다.

## Baseline / v0.0.19 Checkpoint

1. 시작 HEAD: `b2e26956693378ef6a124816a015fca0357cb91a`.
2. 시작 Version: `Pixel Effect Maker v0.0.19`.
3. 시작 FORMAT_VERSION: `16`.
4. 시작 전체 pytest: `1268 passed in 77.69s`.
5. Gravity checkpoint: `d00e9781bb655370e226294db486fad4e5420011` (`Add particle gravity`).
6. Stage: v0.0.19 승인 범위 49개 파일만 명시적으로 추가했다. `git add -A`는 쓰지 않았다.
7. 제외: 보호 PNG, 사용자 프로젝트, build/dist/exe/zip/cache/log/temp/backup.
8. Checkpoint 직후: staged 0, 보호 PNG만 untracked; tag/push/build 없음.

## Motion Architecture

9. 실제 age: `render_particle_frame()`의 `frame_index - instance.birth_frame`, 0-based frame 수.
10. Normalized lifetime: 실제 age를 `normalized_lifetime_age()`에 전달한다.
11. Motion 시간 단위: frame; Drag 강도는 `1/frame`. FPS 변경은 초당 경로 속도를 바꾸지만 프레임별 경로를 바꾸지 않는다.
12. Linear: instance의 초기 위치 + velocity(px/frame) × age.
13. Orbit: lifetime-normalized 경로의 반지름·각도와 instance별 위상.
14. Helix: Orbit형 회전에 선택 축의 시작→끝 진행을 합성.
15. Gravity: `gravity_displacement()`의 `0.5 × g × actual_age²`.
16. 좌표계: Particle/System local XYZ.
17. 순서: base motion + Gravity → local perspective → Layer/Parent 2.5D → Surface → composition.
18. Direct seek: 프레임과 deterministic instance를 직접 평가하며 과거 프레임 상태가 필요 없다.
19. Guide: Orbit/Helix는 공용 evaluator; Linear 대표 guide는 같은 analytic effective age를 사용한다.
20. Cache: spawn key는 motion/Gravity/Drag를 제외하며 render key는 전체 설정, playback revision은 Drag 필드를 포함한다.

## Drag Contract

21. 모델: `ParticleEmitterSettings.drag_enabled`, `drag_strength`.
22. Enabled 기본값: `False`.
23. Strength 기본값: `0.0`.
24. Minimum: `0`.
25. Maximum: `10`.
26. Inspector decimals: `5`.
27. Inspector step: `0.01`.
28. Unit: `1/frame`.
29. 공식: `effective_age = (1 - exp(-d × actual_age)) / d`.
30. 구현: cancellation을 피하는 `-math.expm1(-d × actual_age) / d`.
31. `d = 0`: 실제 age를 정확히 반환한다.
32. `age = 0`: 정확히 0을 반환한다.
33. 의미: 이동/경로 진행에만 쓰는 effective age이며 생존 시간은 아니다.

## Linear / Orbit / Helix

34. Linear 기존: `start + velocity × actual_age`.
35. Linear Drag: `start + velocity × effective_age`.
36. 방향: velocity 벡터는 변경하지 않는다.
37. 감속: 이동 간격은 age 증가에 따라 감소하고 총 이동은 유한 값에 접근한다.
38. Orbit radius: 실제 normalized lifetime parameter로 평가해 기존 radius_start/end geometry를 유지한다.
39. Orbit phase: effective age/lifetime으로 각도 진행을 감쇠한다.
40. Orbit center: 기존 start/origin 기반 중심을 유지한다.
41. Orbit 결과: 처음 위상/방향을 유지하며 점차 회전이 느려진다.
42. Helix radius: 실제 normalized lifetime parameter로 유지한다.
43. Helix axis: 선택 축과 axis_start/end 값은 그대로다.
44. Helix phase: effective age/lifetime으로 감쇠한다.
45. Helix 축 진행: effective age/lifetime으로 감쇠한다.
46. Helix 결과: 경로 설정은 그대로이며 회전과 축 진행만 함께 느려진다.

## Gravity / Lifetime

47. Gravity는 실제 age를 유지한다.
48. Drag는 Gravity 가속도 자체를 감쇠시키지 않는다.
49. 최종 위치는 damped base motion + `0.5 × g × actual_age²`이다.
50. 수평 파편은 옆 방향이 느려져도 Gravity에 의해 계속 아래로 가속한다.
51. Particle lifetime 길이는 변경하지 않는다.
52. Lifetime normalized age는 실제 age다.
53. Scale over Lifetime은 실제 age다.
54. Color over Lifetime은 실제 age다.
55. Opacity/Alpha easing은 실제 age다.
56. Sprite animation frame 및 Playback Speed는 실제 age/기존 clip 규약을 유지한다.

## Version / UI / Undo

57. Version: `0.0.20`.
58. FORMAT_VERSION: `17`.
59. FORMAT ≤16: 누락된 Drag는 OFF/0으로 materialize하며 open만으로 파일을 다시 쓰지 않는다.
60. Old project: OFF/0 identity render 계약을 신규 migration 테스트로 확인했다.
61. Inspector 섹션: 기존 Natural Motion.
62. Label: Gravity와 분리된 Drag/Strength.
63. 한국어: `움직임 감쇠`, `강도`.
64. English: `Drag`, `Strength`.
65. Tooltip: Linear/Orbit/Helix 기본 움직임 감쇠, Gravity/수명은 불변이라고 명시한다.
66. Strength: 비음수 실수, 0.001/0.01 수준 입력 가능.
67. Drag OFF: Strength 입력만 비활성화하고 값은 보존한다.
68. Gravity와 인접한 별도 체크박스로 서로 다른 기능을 발견할 수 있다.
69. Inspector refresh/set selection은 signal-blocked이며 모델을 바꾸지 않는다.
70. Toggle 수락은 한 Undo command.
71. Strength 수락은 한 Undo command.
72. 동일 값은 Undo/Dirty를 만들지 않는다.
73. Refresh도 Undo를 만들지 않는다.

## Determinism / Cache

74. Sequential playback은 같은 프레임을 직접 계산하는 renderer를 사용한다.
75. Direct seek는 같은 evaluator와 instance를 사용한다.
76. Frame step 역시 프레임 번호만 바꾸고 상태를 적분하지 않는다.
77. Export도 대상 프레임을 직접 평가한다.
78. 같은 설정/seed/frame의 결과는 exact deterministic하다.
79. Drag는 random draw를 추가하지 않는다.
80. Particle IDs와 birth frames는 바뀌지 않는다.
81. Spawn positions 및 cached instances는 Drag toggle 전후 동일하다.
82. Random direction/scale/playback sampling도 동일하다.
83. OFF→ON: render 설정/revision 변경으로 새 preview.
84. Strength 변경: render 설정/revision 변경으로 새 preview.
85. ON→OFF: 기존 OFF trajectory 복원.
86. Spawn cache는 Drag를 key에서 제외해 재추첨을 피한다.
87. 신규 cache 전환 테스트는 stale frame 부재를 확인한다.

## Transform / Blend / Guide / Export

88. Parenting은 기존 transform 파이프라인을 통과한다.
89. parent_offset은 변경하지 않았다.
90. Keep World는 변경하지 않았다.
91. System Transform은 변경하지 않았다.
92. Surface Transform은 변경하지 않았다.
93. 2.5D projection은 변경하지 않았다.
94. Rotation Revolution은 변경하지 않았다.
95. Normal Blend 경로에서 Drag는 position만 바꾼다.
96. Additive Blend 경로에서도 position만 바꾼다.
97. Gravity는 별도 actual-age 항이다.
98. Scale lifetime은 독립이다.
99. Color lifetime은 독립이다.
100. Gravity+Drag+Scale+Color+Additive pixel parity를 테스트했다.
101. Motion guide는 설정된 path의 시각 보조다.
102. Drag ON guide는 실제 생존 age에 맞는 effective motion을 사용한다.
103. Gravity+Drag guide는 Gravity 실제 age 항을 유지한다.
104. Drag OFF guide는 기존 endpoint 규약을 보존한다; Drag ON 끝점은 renderer 평가와 일치한다.
105. Current frame render를 확인했다.
106. Full render를 확인했다.
107. Generated output materialization을 확인했다.
108. PNG decode pixel/dimension을 확인했다.
109. 이 네 경로의 같은 프레임 RGBA parity를 확인했다.
110. Resource Editor Overscan 코드/계약은 변경하지 않았다.
111. 최종 출력 strict clipping과 크기를 테스트했다.

## Performance

동일 32×32, 반투명 1×1 sprite, age 4/8, 각각 3회 median. 단위 ms; 환경/작업 부하에 따른 변동이 있으므로 절대 성능 보장은 아니다.

| Count | OFF | Drag | Gravity only | Gravity+Drag | Gravity+Drag+Scale+Color+Additive |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 100 | 6.764 | 5.708 | 6.405 | 5.852 | 8.117 |
| 500 | 32.341 | 30.551 | 28.870 | 30.561 | 37.074 |
| 1000 | 61.004 | 60.522 | 60.660 | 58.947 | 73.909 |
| 5000 | 300.711 | 305.810 | 318.679 | 304.125 | 402.560 |

112. 100개 OFF/ON: 6.764/5.708ms.
113. 500개 OFF/ON: 32.341/30.551ms.
114. 1000개 OFF/ON: 61.004/60.522ms.
115. 5000개 OFF/ON: 300.711/305.810ms (ON/OFF 1.017×).
116. Gravity+Drag: 5.852/30.561/58.947/304.125ms.
117. 전체 조합: 8.117/37.074/73.909/402.560ms.
118. Hot path에 mutable history, deepcopy, filesystem 작업을 추가하지 않았다.

## Representative Effects / Tests

119. Explosion Debris: Linear+Drag+Gravity의 수평 감쇠/낙하 계약을 수식 테스트로 확인; GUI 시각 QA는 미수행.
120. Dust: 저속 Linear+Drag+Scale 조합 가능; GUI 시각 QA는 미수행.
121. Hit Spark: Drag+Gravity+Scale+Color+Additive 조합을 픽셀 테스트로 확인; GUI 시각 QA는 미수행.
122. Orbit Slowdown: phase 진행 감쇠/반지름 유지 수식 테스트.
123. Helix Slowdown: phase/axis 진행 감쇠/반지름 유지 수식 테스트.
124. 표현력: 기존 일정 속도 대비 감속 파편/먼지/불꽃의 기반 표현이 생겼다; 시각적 품질은 사용자 GUI 확인 필요.
125. 신규 테스트: `tests/test_particle_drag.py`, `tests/test_particle_drag_serialization.py`.
126. 집중 테스트: Drag 신규 32 passed, Drag+Gravity+Version 65 passed, guide 회귀 포함 59 passed.
127. Analytic: identity, `expm1`, 작은 d, 최대 d, 큰 age, 유한성/단조성 테스트.
128. Direct seek: 이력 없는 evaluator와 current/full/generated/PNG 동일 프레임 테스트.
129. Linear/Orbit/Helix: 수식/기하/guide 테스트.
130. Gravity: actual-age 항 분리 테스트.
131. Lifetime: age/tint/scale/alpha/sprite frame isolation 테스트.
132. Serialization: format16 defaults, format17 roundtrip, invalid 값 거부 테스트.
133. Cache: OFF→ON→strength 변경→OFF와 spawn instance identity 테스트.
134. Transform: parent/system/surface/2.5D/revolution 회귀 테스트.
135. Export: generated/current/full/PNG RGBA parity와 dimensions 테스트.
136. Full pytest: 최종 `1300 passed in 75.72s`, exit 0.
137. compileall: `app tests tools` exit 0.
138. `--version`: `Pixel Effect Maker v0.0.20`, exit 0.
139. `--check`: exit 0; sandbox의 AppData 로그 권한 경고만 발생했다.
140. `run_app.bat --check`: 테스트 Python override 사용, exit 0; 동일한 로그 권한 경고.
141. `git diff --check`: exit 0.

## Audit / Git / Manual / Final

142. Capability Audit의 좁은 end-to-end analytic Drag: COMPLETE.
143. Natural Motion 전체: PARTIAL.
144. 남은 주요 gap: Noise/Turbulence 및 범용 force stack.
145. 최종 HEAD: v0.0.19 Gravity checkpoint `d00e9781bb655370e226294db486fad4e5420011`.
146. v0.0.20 staged: 0 (`git diff --cached --name-only` 빈 출력).
147. v0.0.20 commit: 0.
148. Tag/push/build/PyInstaller/ZIP: 모두 수행하지 않음.
149. Windows native GUI manual: **수행하지 않음**. 별도 수동 체크리스트 제공.
150. Drag는 stateful simulation이 아닌 analytic 함수다.
151. Direct seek는 같은 입력에서 deterministic하다.
152. Gravity는 actual age를 유지한다.
153. Lifetime channels는 actual age를 유지한다.
154. Orbit/Helix geometry 설정은 보존된다.
155. FORMAT ≤16은 Drag OFF/0 identity를 유지한다.
156. 실제 Effect 표현력은 감속 base motion만큼 개선되지만 GUI 사용성/시각 품질은 미검증이다.
157. 다음 추천: deterministic Noise/Turbulence의 명확한 시간·seed·seek 계약부터 설계한다.

## 최종 자동 검증 기록

- Full pytest: 최종 `1300 passed in 75.72s` (exit 0).
- `compileall -q app tests tools`: exit 0.
- `python -m app.main --version`: `Pixel Effect Maker v0.0.20`.
- `python -m app.main --check`, `run_app.bat --check`: exit 0. 두 실행 모두 AppData 로그 파일의 sandbox 권한 `PermissionError` 경고가 있으나 자체 진단은 성공했다.
- `git diff --check`: exit 0. 최종 HEAD `d00e9781bb655370e226294db486fad4e5420011`; staged 0. v0.0.20 변경은 unstaged/uncommitted.
- `테스트소스.png` SHA-256: `8524F543BAA550EFF0385A27F3060659DF478B7B1CF51B33C554661B90B35564` (기준과 일치).
