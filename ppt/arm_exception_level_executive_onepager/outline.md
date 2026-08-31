# ARM Exception Level 임원용 1장 슬라이드 구성안

## Slide 1 — ARM Exception Level: CPU 권한과 격리를 나누는 4단계 실행 계층

- ARM은 Application부터 보안 Firmware까지 CPU 실행 권한을 EL0~EL3의 4단계로 분리한다.
- EL0는 Service, EL1은 OS 자원, EL2는 VM 격리, EL3는 Platform 보안을 담당한다.
- 낮은 EL은 `SVC`·`HVC`·`SMC` 또는 Hardware Exception으로 통제된 상위 EL Service에 진입한다.
- 높은 EL은 `ERET`으로 복귀하며, 비동기 알림은 Event Queue와 `IRQ/vIRQ`를 결합해 전달한다.
- 권한이 높을수록 장애 영향과 전환 비용이 커지므로 EL2·EL3의 코드와 호출 빈도를 최소화한다.

### Visual idea

- 왼쪽: EL3→EL0 4단 Stack. 위로 갈수록 권한·통제 범위·장애 영향이 커지는 Gradient로 표현한다.
- 가운데: 주황색 상향 경로(`SVC`/`HVC`/`SMC`)와 청록색 하향 비동기 경로
  (`Queue + IRQ/vIRQ`, 최종 실행 전환은 `ERET`)를 한눈에 대비한다.
- 오른쪽: `보안·신뢰`와 `성능·확장성`을 두 개의 짧은 Executive Insight 카드로 묶는다.
- 하단: “상위 EL에는 최소 격리 기능만 배치”라는 의사결정 원칙을 한 줄로 강조한다.

### Layout role and intent

- 역할: 개념 설명 + Architecture Decision Summary
- 의도: ARM을 처음 접하는 임원이 30초 안에 네 계층의 책임, 전환 방향, 설계 Trade-off를 이해하게 한다.
- 화면 비율: 16:9 단일 슬라이드
- 정보 비율: 계층 Stack 40% / 전환 흐름 32% / 보안·성능 28%

### Required source images

- 없음. 기존 PPT/PPTX의 Content나 Graphic은 재사용하지 않는다.
- 시각 스타일은 구성안 승인 후 별도 확인한다.

### 발표 핵심 문장

> 권한은 위로 갈수록 강해지고 전환 비용과 실패 영향도 커진다. Application은 EL0, OS 자원 관리는
> EL1, VM 격리 집행은 EL2, Platform 보안만 EL3에 배치하고 상위 EL 호출 빈도와 코드 크기를 최소화한다.
