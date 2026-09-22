# Pixel Effect Maker v0.0.19 완료 보고

1. 작업 시작 실제 HEAD: `dd4cb4359efa7798236b2c81ca8fe19ee611eb9c`.
2. 시작 Version: `Pixel Effect Maker v0.0.18`.
3. 시작 FORMAT_VERSION: `15`.
4. 시작 pytest: `1238 passed in 78.52s`.
5. v0.0.18 commit hash: `b2e26956693378ef6a124816a015fca0357cb91a` (`Add particle additive blend`).
6. stage 파일: 승인된 v0.0.18 소스·테스트·문서·benchmark 52개만 명시 staging했다.
7. 제외 파일: `테스트소스.png`, build/dist/exe/zip/cache/log/temp/backup와 사용자 프로젝트를 제외했다.
8. checkpoint 후 Git: staged 0, 보호 PNG만 untracked, v0.0.18 checkpoint 뒤 v0.0.19 작업을 시작했다.
9. Particle age 정의: `frame_index - birth_frame`인 0-based integer frame이다.
10. normalized age와 차이: base Orbit/Helix와 lifetime channel용 비율이며 Gravity는 raw age를 사용한다.
11. Motion time unit: frame 기반이다.
12. Linear speed unit: `px/frame`이다.
13. Linear evaluator: `evaluate_particle_motion`, start + velocity × age이다.
14. Orbit evaluator: 같은 함수에서 normalized lifetime으로 radius/angle/phase를 평가한다.
15. Helix evaluator: 같은 함수에서 Orbit과 선택 axis travel을 결합한다.
16. Motion coordinate space: Particle/System local XYZ이다.
17. Transform 적용 순서: base motion + Gravity → local perspective → System/Parent Layer 2.5D → Surface → composition이다.
18. direct seek 구조: 해당 frame의 age를 직접 계산하며 이전 frame 상태가 없다.
19. motion guide 구조: Orbit/Helix는 renderer evaluator를 표본화하고 Linear는 representative endpoint primitive를 사용한다.
20. cache 구조: spawn cache는 spawn/RNG 설정만, base render cache는 전체 particle settings·transform·parenting·FPS를 포함한다.
21. model: `ParticleEmitterSettings.gravity_enabled/gravity_strength`를 추가했다.
22. enabled: 기본값 `False`이다.
23. strength: 기본값 `0.0`, signed float이다.
24. positive direction: screen-local +Y, 아래 방향이다.
25. negative direction: screen-local -Y, 위 방향이다.
26. unit: `px/frame²`이다.
27. formula: pure helper `gravity_displacement = 0.5 × g × age²`이다.
28. birth-frame result: age 0에서 정확히 0이다.
29. coordinate space: 기존 base motion과 같은 Particle/System local space이다.
30. base motion 결합 지점: Linear/Orbit/Helix position 완성 뒤 local Y에 더한다.
31. Version: `Pixel Effect Maker v0.0.19`.
32. FORMAT_VERSION: `16`.
33. migration: format 15 이하 누락 필드는 OFF/0으로 기본화된다.
34. old project render exact: Gravity OFF identity fixture로 byte-exact 검증했다.
35. section 위치: Over Lifetime과 분리된 `Natural Motion`이다.
36. Gravity toggle: localized checkbox이며 static emitter setting이다.
37. Strength: signed double spinbox이다.
38. min/max: `-1024..1024`.
39. decimals: 3.
40. step: 0.125.
41. unit: UI suffix `px/frame²`.
42. tooltip: per-particle birth와 signed 방향을 설명한다.
43. Korean: `자연스러운 움직임 / 중력 / 강도`를 제공한다.
44. English: `Natural Motion / Gravity / Strength`를 제공한다.
45. disabled behavior: Strength control만 비활성화하고 저장 값은 보존한다.
46. refresh integrity: set/refresh/selection에서 signal edit·값 mutation이 없다.
47. toggle: 사용자 toggle 한 번은 Undo 한 번이다.
48. strength: accepted strength edit 한 번은 merge-safe Undo 한 번이다.
49. negative value: -0.625 입력·Undo·round-trip을 검증했다.
50. no-op: 같은 값 commit은 Undo 0이다.
51. refresh: refresh/set_settings는 Undo 0이다.
52. birth age: 각 particle birth가 독립 age 0이다.
53. direct seek: exact current-frame evaluator로 deterministic하다.
54. sequential playback: 같은 frame은 direct seek와 같은 evaluator를 호출한다.
55. frame step: history가 없어 같은 frame 결과가 같다.
56. export direct render: full/current/generated/PNG가 같은 RGBA 경로를 사용한다.
57. FPS/time contract: trajectory는 frame 기반이므로 FPS 변경 시 기존처럼 real-time 속도가 변한다.
58. Linear: 기존 velocity path에 Gravity Y만 더한다.
59. Orbit: 기존 orbit path 전체가 Y로 drift한다.
60. Helix: 기존 helix path 전체가 Y로 drift한다.
61. radius preservation: Gravity가 radius 입력/evaluator를 변경하지 않는다.
62. phase preservation: phase와 seed-derived phase unit을 변경하지 않는다.
63. axis preservation: Helix axis와 axis interpolation을 변경하지 않는다.
64. Scale coexistence: independent multiplier로 동시 fixture를 통과했다.
65. Color coexistence: independent RGB tint로 동시 fixture를 통과했다.
66. opacity independence: 기존 alpha/easing 계산을 변경하지 않았다.
67. Normal: 기존 source-over 경로에서 Gravity position을 사용한다.
68. Additive: 동일 position 뒤 additive raster/composition을 사용한다.
69. Scale+Color+Additive+Gravity: deterministic combined fixture를 통과했다.
70. random draw count: Gravity evaluator는 RNG를 호출하지 않는다.
71. spawn identity: OFF/ON/strength 변경 전후 ParticleInstance tuple이 같다.
72. deterministic output: 같은 project/seed/frame은 byte-exact하다.
73. Parenting: world affine pipeline을 그대로 통과한다.
74. parent_offset: 읽기/렌더 후 exact 보존된다.
75. Keep World: parenting 수학과 mutation 경로를 변경하지 않았다.
76. System: Gravity local point가 existing Layer Space transform을 통과한다.
77. Surface: 최종 RGBA compatibility transform이 기존 순서로 적용된다.
78. 2.5D: Position Z, Rotation X/Y, Perspective fixture가 안전하다.
79. Rotation Revolution: Z 720/-360 sentinel을 보존한다.
80. guide actual-trajectory 의미 여부: Orbit/Helix path는 actual evaluator, Linear는 representative primitive다.
81. Gravity 반영 여부: Orbit/Helix samples와 Linear endpoint에 Gravity를 반영한다.
82. guide/render 일치: representative lifetime age를 동일 evaluator에 전달한다.
83. Gravity ON invalidation: full base key에 enabled/strength가 포함된다.
84. Strength change: 1→2에서 다른 exact base frame을 확인했다.
85. OFF invalidation: ON→OFF가 원본 frame으로 복원된다.
86. spawn cache 영향: Gravity 필드를 key에서 제외해 같은 tuple 객체를 재사용한다.
87. stale preview 여부: OFF→ON→strength→OFF 전환 fixture에서 stale 0이다.
88. current frame: full sequence의 같은 index와 byte-exact하다.
89. full render: analytic evaluator를 각 요청 frame에 적용한다.
90. generated output: apply 후 full render RGBA와 byte-exact하다.
91. PNG: decoded PNG와 Project composition이 byte-exact하다.
92. parity: current/full/generated/PNG dimensions와 pixels를 검증했다.
93. overscan: editor 의미나 buffer size를 변경하지 않았다.
94. strict clip: Gravity가 밖으로 이동해도 output은 고정 Composition 크기다.
95. 100 OFF/ON: median 6.264 / 5.431 ms.
96. 500 OFF/ON: median 27.936 / 27.285 ms.
97. 1000 OFF/ON: median 54.960 / 56.023 ms.
98. 5000 OFF/ON: median 286.975 / 276.430 ms.
99. Scale+Color+Additive+Gravity: 100/500/1000/5000 median 7.638/33.756/69.331/358.911 ms.
100. allocations/state history 여부: Gravity helper에 Qt 객체, dict, deepcopy, filesystem, history가 없다.
101. Falling Debris: positive Gravity + outward velocity 계약을 formula fixture로 검증했다.
102. Hit Spark: Gravity+Scale+Color+Additive 조합을 검증했다.
103. Rising Ember: negative Gravity 방향을 검증했다.
104. Orbit Drift: radius/phase 보존과 additive Y drift를 검증했다.
105. 제작 표현력 개선 평가: ballistic debris/spark/ember와 drifting orbit이 가능해졌다.
106. 신규 files: natural-motion service, 두 Gravity test files, benchmark, 이 보고서다.
107. focused tests: Gravity 및 관련 core focused suite를 통과했다.
108. formula tests: OFF/zero/birth/signed/half-at-squared를 포함한다.
109. direct-seek tests: current/full/generated frame equality를 포함한다.
110. motion tests: Linear/Orbit/Helix와 guide를 포함한다.
111. lifetime/blend regression: Scale/Color/Alpha/Normal/Additive 조합을 포함한다.
112. serialization: format 15 migration, format 16 round-trip, negative/corrupt 값을 포함한다.
113. cache: spawn reuse와 render OFF/ON/strength/OFF를 포함한다.
114. transform: parent_offset/System/Surface/2.5D/revolutions를 포함한다.
115. export: PNG decode parity와 fixed dimensions를 포함한다.
116. full pytest: `1268 passed`, 0 failures.
117. compileall: `app`, `tests`, `tools` 성공.
118. --version: `Pixel Effect Maker v0.0.19`.
119. --check: exit 0.
120. run_app.bat: 지정 Python override에서 `--check` exit 0.
121. git diff --check: exit 0.
122. Gravity capability 최종 상태: 정의된 signed constant Gravity end-to-end는 COMPLETE다.
123. Natural Motion 전체 상태: PARTIAL이다.
124. 남은 Drag gap: 감속/공기 저항은 구현하지 않았다.
125. 남은 Noise gap: Noise/Turbulence는 구현하지 않았다.
126. 최종 HEAD: `b2e26956693378ef6a124816a015fca0357cb91a`.
127. staged: 0.
128. v0.0.19 commit: 0; 변경은 unstaged/uncommitted다.
129. tag/push/build: Tag 0, Push 0, Build/PyInstaller/ZIP 0.
130. Windows native GUI manual 여부: **수행하지 않음**.
131. Gravity가 normalized lifetime이 아닌 실제 age 기반인지: 예, raw integer frame age 기반이다.
132. direct seek deterministic인지: 예, analytic pure contribution이라 history가 없다.
133. 기존 Motion trajectory 계약이 보존되는지: 예, base path를 변경하지 않고 Y contribution만 더한다.
134. Scale+Color+Additive와 공존하는지: 예, combined fixture와 regression으로 확인했다.
135. 기존 프로젝트 render 보존 여부: 예, format 15 누락 필드는 OFF/0 identity다.
136. 실제 Effect 표현력 개선 평가: 낙하 파편, 휘는 스파크, 상승 불씨, 궤도 drift를 단일 Emitter에서 표현할 수 있다.
137. 다음 추천 기능: 같은 frame-unit/direct-seek 계약을 유지하는 analytic Drag다.
