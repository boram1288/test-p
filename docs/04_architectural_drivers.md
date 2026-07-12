# Architectural Driver 선정

> 본 문서는 앞 단계에서 도출한 FR/QA/CONST 중 아키텍처 구조를 직접 결정하는 핵심 동인(Architectural Driver)을 선정한다.
>
> 진행 순서: 요구사항 수집 → 요구사항 도출 → 품질 속성 선정 → **Architectural Driver 선정(본 문서)**

관련 문서: [`02_requirements.md`](02_requirements.md), [`03_quality_attribute_specification.md`](03_quality_attribute_specification.md), [`03_utility_tree.md`](03_utility_tree.md)

---

## 1. 선정 원칙

| 구분 | 선정 원칙 |
|------|----------|
| **FR (기능)** | 전체 FR 중 구조 결정성이 높은 중요 FR을 선별한다. 구조에 영향 없이 상위 구조 안에서 구현 가능한 FR은 제외한다. |
| **QA (품질)** | Quality Attribute Specification과 Utility Tree에서 우선순위가 높은 핵심 QA를 선정한다. |
| **CONST (제약)** | 전체를 선정한다. 제약은 협상 불가능한 전제로서 모든 설계 결정의 선택지를 한정한다. |

---

## 2. Architectural Driver–VOS 매핑

선정된 Architectural Driver가 어떤 이해관계자의 요구에서 도출되었는지 VOS ID와 연결한다. 하나의 Driver가 여러 VOS를 함께 충족하거나, 하나의 VOS가 여러 Driver로 구체화된 경우에는 관련 ID를 모두 표기한다.

### 2.1 기능 요구사항(FR)

| AD ID | 선정 Driver | 매칭 VOS ID | VOS 요구와의 연결 |
|-------|-------------|-------------|--------------------|
| FR-01 | pVM 생성/시작/정지/종료 | VOS-01, VOS-07 | 보호 대상 데이터를 격리하는 pVM의 생명주기를 관리하고, 독립 도메인의 생성과 운용 기반을 제공한다. |
| FR-02 | 다중 pVM 동시 운용 | VOS-07 | Secure Camera와 Secure AI 도메인을 서로 독립적으로 동시에 운용한다. |
| FR-03 | 보안 Workload 동적 탑재 | VOS-05 | Framework 코어 수정 없이 신규 보안 시나리오를 Workload 단위로 수용한다. |
| FR-04 | Camera/AI HW 공유 사용 | VOS-02, VOS-08 | Camera/AI HW를 보안·일반 기능이 공유하면서 DMA 격리와 잔류 데이터 소거를 보장한다. |
| FR-05 | 도메인 간 DMABUF 전송 | VOS-01, VOS-09 | 도메인 간 대용량 데이터를 비신뢰 Host에 노출하지 않고 빠르게 전달한다. |
| FR-06 | Secure OS ENC/DEC 명령 전송 | VOS-11, VOS-12 | 안정적인 Secure OS 연동 인터페이스를 제공하면서 기존 TrustZone TEE 기능과 SMC 경로를 유지한다. |

### 2.2 품질 속성(QA)

| AD ID | 선정 Driver | 우선순위 | 매칭 VOS ID | VOS 요구와의 연결 |
|-------|-------------|:--------:|-------------|--------------------|
| QA-01 | 보안 — 침해 기밀성 (QS-01) | 1순위 | VOS-01, VOS-10, VOS-15 | Host 침해 상황에서도 데이터 비노출을 보장하고, TCB를 작게 유지하며, 개인정보·규제 대응을 위한 기술적 격리 증빙을 제공한다. |
| QA-02 | 확장성 — 신규 시나리오 수용 (QS-02) | 2순위 | VOS-05 | Framework 수정 없이 신규 보안 Workload를 패키징하고 탑재할 수 있어야 한다. |
| QA-03 | 성능 — 실시간 처리 (QS-03) | 3순위 | VOS-02 | 격리 환경에서도 Camera/AI HW 가속을 활용해 영상 처리의 실시간 성능을 유지한다. |
| QA-04 | 강건성 — pVM 장애 격리 (QS-04) | 4순위 | VOS-16 | 한 pVM의 장애가 Host나 다른 pVM으로 전파되지 않도록 장애 영향을 격리한다. |

### 2.3 제약사항(CONST)

| AD ID | 선정 Driver | 매칭 VOS ID | VOS 요구와의 연결 |
|-------|-------------|-------------|--------------------|
| CS-01 | Linux 네이티브 | VOS-03 | Android 스택에 의존하지 않고 Yocto/Ubuntu 기반 Linux에서 네이티브로 동작해야 한다. |
| CS-02 | GP 표준 규격 준수 | VOS-11, VOS-12 | 기존 TrustZone TEE 기능과 SMC 경로의 호환성을 유지하기 위해 GlobalPlatform 표준 인터페이스를 준수한다. |

---

## 4. Architectural Driver 목록

| 구분 | 선정 Driver |
|------|-------------|
| 기능 (FR) | FR-01, FR-02, FR-03, FR-04, FR-05, FR-06 |
| 품질 (QA) | QA-01, QA-02, QA-03, QA-04 |
| 제약 (CONST) | CS-01, CS-02 |

---
