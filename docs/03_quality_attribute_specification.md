# Quality Attribute Specification

> 본 문서는 `02_requirements.md`에서 도출한 품질 속성 요구사항을 Quality Attribute Specification으로 정리한다.

---

## QS-01: 보안 - Host 침해 시 기밀성

| Field | Specification |
|-------|---------------|
| Description | Host가 완전히 침해되어도 pVM 내 영상, 모델, 추론 데이터가 노출되지 않아야 한다. |
| Source | Host OS 루트 권한을 탈취한 공격자 |
| Stimulus | Host 커널 권한으로 pVM 메모리 읽기 시도 |
| Environment | Secure Vision AI 파이프라인 정상 동작 중 |
| Artifact | pVM 내 영상 원본, AI 모델 가중치, 추론 중간 데이터 |
| Response | Stage-2 격리에 의해 모든 접근이 차단되고, 비정상 접근 시도가 기록된다. |
| Response Measure | 침투 시험 전 케이스에서 격리 메모리 노출 0건 |


## QS-02: 성능 - 실시간 처리

| Field | Specification |
|-------|---------------|
| Description | 격리 환경에서도 Camera/AI HW 가속을 사용해 영상 파이프라인의 실시간 처리를 만족해야 한다. |
| Source | 카메라 센서 |
| Stimulus | 1080p 30fps 영상 스트림 지속 유입 |
| Environment | 격리 파이프라인(Secure Camera→Secure AI) 정상 동작, Host 통상 부하 |
| Artifact | End-to-End 파이프라인(캡처→Camera HW→AI HW 추론→판단) |
| Response | Camera/AI HW 가속으로 프레임 드롭 없이 처리한다. |
| Response Measure | 비격리 구성 대비 처리 성능 저하 10% 이내 |

## QS-03: 확장성 - 신규 Workload 수용

| Field | Specification |
|-------|---------------|
| Description | 신규 보안 Workload 추가 시 Framework 코어 수정 없이 패키징/탑재만으로 수용되어야 한다. |
| Source | 로봇 제조사 / Workload 개발자 |
| Stimulus | 신규 보안 Workload 추가 요구 |
| Environment | Framework가 제품에 배포/운용 중인 상태 |
| Artifact | Framework 본체(Middleware/커널 드라이버) |
| Response | 펌웨어 재배포/Framework 수정 없이 Workload 패키징/탑재만으로 수용된다. |
| Response Measure | Framework 코어 수정 0 LoC |

## QS-04: 성능 - 도메인 간 통신 오버헤드

| Field | Specification |
|-------|---------------|
| Description | 도메인 간 대용량 데이터 전달 시 통신 오버헤드가 파이프라인 실시간성을 해치지 않아야 한다. |
| Source | Secure Camera pVM |
| Stimulus | 프레임 단위 대용량 영상 데이터를 Secure AI pVM으로 전달 |
| Environment | 파이프라인 정상 동작 중 |
| Artifact | 도메인 간 보안 채널(공유 메모리/RPC) |
| Response | 데이터 노출 없이 전달되며 파이프라인 실시간성이 유지된다. |
| Response Measure | 도메인 간 dma-buf 버퍼 전달 시 memcpy 호출 횟수 0회 |

## QS-05: 가용성 - pVM 장애 격리

| Field | Specification |
|-------|---------------|
| Description | pVM 장애가 Host, 다른 pVM, 로봇 기본 동작으로 전파되지 않아야 한다. |
| Source | 오동작하는 보안 Workload |
| Stimulus | pVM 비정상 종료(크래시, 무응답) |
| Environment | 다중 pVM 운용 중인 로봇 통상 동작 상태 |
| Artifact | Host OS, 타 pVM, 로봇 기본 동작 |
| Response | 장애가 해당 pVM에 한정되고, Framework가 자원을 안전하게 회수해야 한다. |
| Response Measure | Host/타 pVM 다운타임 0초 |

## QS-06: 자원 효율

| Field | Specification |
|-------|---------------|
| Description | 보안 기능 활성화 시 메모리/전력 오버헤드가 제품 탑재 가능 한도 이내로 유지되어야 한다. |
| Source | 시스템 통합자(로봇 제조사) |
| Stimulus | 보안 Framework + pVM 2개(Camera, AI) 상시 운용 |
| Environment | 로봇 제품의 통상 동작 상태 |
| Artifact | SoC 메모리/전력 예산 |
| Response | 비격리 구성 대비 추가 자원 소모가 제품 탑재 가능 한도 이내로 유지된다. |
| Response Measure | 추가 메모리 256MB 이하, 전력 증가 5% 이내 |

## QS-07: 시험 용이성 - 격리 보장 검증

| Field | Specification |
|-------|---------------|
| Description | 격리 보장을 공격 벡터 기반 자동화 시험으로 객관적으로 검증할 수 있어야 한다. |
| Source | 품질/검증 조직 |
| Stimulus | 격리 요구사항별 공격 벡터에 대한 객관적 검증 요구 |
| Environment | 통합 시험 단계 및 회귀 시험 |
| Artifact | 격리 메커니즘(Stage-2, S2MPU, 보안 채널) |
| Response | Host 침해 모사 도구 등 재현 가능한 자동화 시험으로 격리 유지가 검증된다. |
| Response Measure | 격리 요구사항별 공격 벡터 자동화 시험 커버 100% |

## QS-08: 변경 용이성 - Secure OS 교체

| Field | Specification |
|-------|---------------|
| Description | Secure OS 교체 시 Secure OS 패키지 외부 SW를 수정하지 않아야 한다. |
| Source | 서드파티 Secure OS 벤더 / 로봇 제조사 |
| Stimulus | 탑재된 Secure OS를 다른 Secure OS로 교체 |
| Environment | 설계/통합 단계 또는 제품 유지보수 단계 |
| Artifact | Secure OS와 무관한 SW(Framework, Host Middleware, 타 Workload) |
| Response | Secure OS 패키지 교체만으로 완료되며 무관 SW는 수정되지 않는다. |
| Response Measure | Secure OS 패키지 외부 변경 파일 0개 |
