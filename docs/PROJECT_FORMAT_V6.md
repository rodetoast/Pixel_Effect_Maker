# Project Format v6

> 형식 6은 계속 로드할 수 있는 Legacy 형식이다. 최신 저장 형식은 Pixel Payload를 압축한 [Project Format v7](PROJECT_FORMAT_V7.md)이다.

애플리케이션 버전은 `0.0.04`를 유지하며 프로젝트 `FORMAT_VERSION`만 6으로 변경한다.

`effect_resource_layers[].layer_transform`은 선택적인 v6 확장 필드다. 없는 기존 v6은 Identity로 읽는다. `position[3]`, `rotation[3]`, `scale[2]`, `opacity`, Canvas 중심 기준 `pivot[2]`, `perspective_strength`, 비어 있지 않은 `tracks`, `revision`을 저장한다. 기존 문서를 계속 읽을 수 있으므로 포맷 번호는 6을 유지한다.

## v5와 v6

v5는 직접 배치 `effect_composition_layers`와 `particle_emitters`를 별도 배열에 저장했다. v6는 `effect_resource_layers` 하나에 공통 Resource 참조와 `placement_mode`, `single_settings`, `particle_settings`를 저장한다. 비활성 모드 설정도 저장하므로 모드 왕복에서 값이 사라지지 않는다.

## 필드 대응

| v5 | v6 |
|---|---|
| EffectCompositionLayer | Resource Layer / `single` |
| ParticleEmitter | Resource Layer / `particle` |
| generated_layer_id | 동일 출력 레이어 참조 |
| start/end 경로 | `single_settings` |
| emission·shape·direction·range·seed | `particle_settings` |

마이그레이션은 생성 출력 레이어의 실제 인덱스로 사용자 순서를 복구하고 ID·이름·Visibility·Resource 참조·모든 기존 설정을 보존한다. Resource Composition 기반이 아닌 구형 Particle은 기존 Particle Resource 참조를 호환 설정에 유지한다.

## 저장 시점과 Legacy

구형 파일은 읽을 때 메모리에서만 변환하며 원본을 자동 저장하지 않는다. 사용자가 Save/Save As를 실행할 때 v6으로 기록한다. Legacy Transform Generator와 해당 렌더러는 이번 변환 대상이 아니며 `generators`에 계속 저장한다.
