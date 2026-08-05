# Effect Editor 직접 조작과 편집 가이드

Effect Editor는 선택된 Effect Layer만 편집한다. Composition Layer는 Resource Composition 하나를 프로젝트 프레임에 직접 렌더하며 Start/End 위치를 선형 보간한다. 이전 v5 파일에는 `effect_composition_layers`가 없으므로 빈 목록으로 읽고, 새 항목은 호환 식별자 `layer_type: animation_clip`을 사용한다.

Particle System 가이드는 Renderer의 `velocity_from_direction_speed()`와 `representative_particle_guide()`를 공유한다. 대표 Speed와 Lifetime은 각 Range의 중간값이고, 실제 렌더처럼 마지막 표시 위치는 `velocity × (lifetime - 1)`이다. Point는 Origin, Line은 끝점, Circle은 Radius, Box는 반 크기 Handle을 편집한다. Direction과 Spread Cone은 같은 degree 값을 사용한다.

Handle은 Zoom과 무관한 화면 크기로 hit-test한다. Mouse Press에서 시작값을 저장하고 Move 동안 Inspector와 Canvas를 갱신하며 Release에서 Undo Command 하나를 만든다. Shift는 Direction을 15°에 맞추고 Escape는 시작값을 복원한다.

최대 세 장의 Resource Ghost는 Resource Composition revision별 캐시를 사용한다. `편집 가이드 표시`는 `ui/show_effect_editing_guides`에 저장하며 프로젝트 JSON에는 기록하지 않는다. 모든 선·Handle·Ghost는 Canvas overlay이므로 Preview Worker를 만들지 않고 Project compose, Bake, PNG Export 결과에도 포함되지 않는다.

Effect Timeline의 `선택한 이펙트 레이어 삭제`는 Composition Layer, Particle System, 기존 Transform Emitter와 해당 생성 출력 레이어를 함께 제거한다. Layer 메뉴와 타임라인 이름 열 컨텍스트 메뉴도 같은 명령을 사용한다. 삭제 시 Guide·Ghost·Preview를 즉시 정리하며, 연결된 Resource Composition·Source Asset·Animation Clip 원본은 수정하거나 삭제하지 않는다. Undo/Redo는 동일 모델 객체, 생성 레이어 픽셀과 이전 선택을 복원한다. Delete 키는 Timeline 스크러빙 및 편집 포커스 충돌을 피하기 위해 이번 정책에 포함하지 않는다.

형식 6부터 활성 사용자 모델은 Resource Layer 하나다. Single은 기존 시작·끝 경로와 Ghost를, Particle Emission은 방출 원점·방향·예상 도달점·Shape·Spread를 재사용한다. Placement Mode 전환은 Drag 상태와 오래된 Guide를 지운 뒤 해당 모드 Guide만 표시하며 두 모드 설정은 모두 모델에 남는다.
