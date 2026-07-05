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
| **QA (품질)** | Quality Attribute Specification과 Utility Tree에서 우선순위가 높은 핵심 QA를 선정한다. 새 QA 번호 체계에서는 1~5순위가 QA-01~QA-05에 해당한다. |
| **CONST (제약)** | 전체를 선정한다. 제약은 협상 불가능한 전제로서 모든 설계 결정의 선택지를 한정한다. |

---

## 2. 후보 요구사항 요약

### 2.1 기능 요구사항(FR)

| ID | 요구사항 |
|----|---------|
| FR-01 | pVM 생성/시작/정지/종료 |
| FR-02 | 다중 pVM 동시 운용 |
| FR-03 | Camera/AI HW 공유 사용 |
| FR-04 | 도메인 간 보안 데이터 전송 |
| FR-05 | 보안 Workload 동적 탑재 |
| FR-06 | Secure OS ENC/DEC 명령 전송 |

### 2.2 품질 속성(QA)

| ID | 품질 속성 (시나리오) | 우선순위 |
|----|--------------------|:--------:|
| QA-01 | 보안 — Host 침해 기밀성 (QS-01) | 1순위 |
| QA-02 | 보안 — HW 접근 격리 (QS-02) | 2순위 |
| QA-03 | 성능 — 실시간 처리 (QS-03) | 3순위 |
| QA-04 | 확장성 — Workload 수용 (QS-04) | 4순위 |
| QA-05 | 성능 — 통신 오버헤드 (QS-05) | 5순위 |
| QA-06 | 가용성 — pVM 장애 격리 (QS-06) | 6순위 |
| QA-07 | 자원 효율 (QS-07) | 7순위 |
| QA-08 | 시험 용이성 (QS-08) | 8순위 |
| QA-09 | 변경 용이성 — Secure OS 교체 (QS-09) | 9순위 |

### 2.3 제약사항(CONST)

| ID | 제약사항 |
|----|---------|
| CS-01 | Linux 네이티브 |
| CS-02 | pKVM 커널 전제 (EL2 수정 불가) |
| CS-03 | GP 표준 규격 준수 |
| CS-04 | 개인정보/규제 고려 |
| CS-05 | 단일 Context HW IP |
| CS-06 | 서명된 Workload만 탑재 |

---

## 3. QA 선정 평가

Quality Attribute Specification(`03_quality_attribute_specification.md`)과 Utility Tree(`03_utility_tree.md`)의 우선순위 평가 결과를 따른다.

| ID | 품질 속성 | 우선순위 | 선정 여부 | 근거 |
|----|----------|:--------:|----------|------|
| QA-01 | 보안 — Host 침해 기밀성 (QS-01) | 1순위 | **선정** | 신뢰 경계와 보호 범위를 결정하는 최상위 driver |
| QA-02 | 보안 — HW 접근 격리 (QS-02) | 2순위 | **선정** | S2MPU 기반 배타적 HW 접근 제어와 주체 전환 구조를 결정 |
| QA-03 | 성능 — 실시간 처리 (QS-03) | 3순위 | **선정** | 격리 경계 통과 최소화, 데이터/제어 경로 분리 등 런타임 구조를 결정 |
| QA-04 | 확장성 — Workload 수용 (QS-04) | 4순위 | **선정** | Workload 패키징/검증/탑재 구조와 Framework 확장 경계를 결정 |
| QA-05 | 성능 — 통신 오버헤드 (QS-05) | 5순위 | **선정** | zero-copy 공유 메모리 채널과 격리 보장의 양립 구조를 결정 |
| QA-06 | 가용성 — pVM 장애 격리 (QS-06) | 6순위 | **선정** | pVM 생명주기 관리 설계 안에서 충족 여부를 확인 |
| QA-07 | 자원 효율 (QS-07) | 7순위 | 제외 | 메모리/전력 footprint 제약으로 작용하되 독자적 구조 결정성은 낮음 |
| QA-08 | 시험 용이성 (QS-08) | 8순위 | 제외 | 침해 모사 도구/시험 훅은 구조 결정 후 검증 설계에서 대응 |
| QA-09 | 변경 용이성 — Secure OS 교체 (QS-09) | 9순위 | 제외 | 표준 인터페이스와 어댑터 경계로 대응하며 초기 핵심 driver에서는 제외 |

**선정 결과: QA-01, QA-02, QA-03, QA-04, QA-05, QA-06 (6건)**

---

## 4. Architectural Driver 목록

| 구분 | 선정 Driver | 제외/후속 확인 |
|------|-------------|----------------|
| 기능 (FR) | FR-01, FR-02, FR-03, FR-04, FR-05, FR-06 | 없음 |
| 품질 (QA) | QA-01, QA-02, QA-03, QA-04, QA-05, QA-06 | QA-07, QA-08, QA-09 |
| 제약 (CONST) | CS-01, CS-02, CS-03, CS-04, CS-05, CS-06 | 없음 |

---
