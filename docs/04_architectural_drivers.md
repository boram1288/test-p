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
| CONST-01 | Linux 네이티브 |
| CONST-02 | pKVM 커널 전제 (EL2 수정 불가) |
| CONST-03 | TrustZone 기능 무회귀 |
| CONST-04 | 개인정보/규제 고려 |
| CONST-05 | 단일 Context HW IP |
| CONST-06 | 서명된 Workload만 탑재 |

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
| QA-06 | 가용성 — pVM 장애 격리 (QS-06) | 6순위 | 제외 | pVM 생명주기 관리 설계 안에서 충족 여부를 확인 |
| QA-07 | 자원 효율 (QS-07) | 7순위 | 제외 | 메모리/전력 footprint 제약으로 작용하되 독자적 구조 결정성은 낮음 |
| QA-08 | 시험 용이성 (QS-08) | 8순위 | 제외 | 침해 모사 도구/시험 훅은 구조 결정 후 검증 설계에서 대응 |
| QA-09 | 변경 용이성 — Secure OS 교체 (QS-09) | 9순위 | 제외 | 표준 인터페이스와 어댑터 경계로 대응하며 초기 핵심 driver에서는 제외 |

**선정 결과: QA-01, QA-02, QA-03, QA-04, QA-05 (5건)**

---

## 4. Architectural Driver 목록

| 구분 | 선정 Driver | 제외/후속 확인 |
|------|-------------|----------------|
| 기능 (FR) | FR-01, FR-02, FR-03, FR-04, FR-05, FR-06 | 없음 |
| 품질 (QA) | QA-01, QA-02, QA-03, QA-04, QA-05 | QA-06, QA-07, QA-08, QA-09 |
| 제약 (CONST) | CONST-01, CONST-02, CONST-03, CONST-04, CONST-05, CONST-06 | 없음 |

---

## 5. 설계 작업으로의 전환

### 5.1 Driver별 설계 과제

| 순서 | 작업 | 관련 Driver | 후속 Decision Point |
|:---:|------|-------------|---------------------|
| 1 | 신뢰 모델 확정 — TCB 범위, 공격자 모델, 보호 범위 결정 | QA-01, CONST-02, CONST-04 | T-1~T-5 |
| 2 | 생명주기/다중 pVM 관리 골격 설계 | FR-01, FR-02, CONST-01 (QA-06 후속 확인) | T-1 |
| 3 | HW IP 중재 구조 실현 가능성 검증(PoC) | FR-03, QA-02, QA-03, CONST-05 | T-2 |
| 4 | 통신/데이터 경로(zero-copy 보안 채널) 구조 설계 | FR-04, QA-01, QA-05 | T-3 |
| 5 | 보안 Workload 실행 방식 결정 | FR-05, QA-04, CONST-06 | T-4 |
| 6 | Secure OS 실행 환경 및 TrustZone 연동 구조 배치 | FR-06, CONST-03, CONST-06 (QA-09 후속 확인) | T-4/T-5 |

### 5.2 핵심 후속 질문

| ID | 질문 | 근거 |
|----|------|------|
| Q-1 | Host 측 Framework를 TCB에 포함할 것인가, 아니면 비신뢰 중재자로 둘 것인가? | QA-01, CONST-02 |
| Q-2 | Camera/AI HW 주체 전환 시 S2MPU 권한 회수/부여를 어떤 계층에서 원자적으로 보장할 것인가? | QA-02, FR-03, CONST-05 |
| Q-3 | 실시간 경로에서 어느 구간까지 zero-copy를 보장하고, 어떤 메타데이터만 복사할 것인가? | QA-03, QA-05, FR-04 |
| Q-4 | 신규 Workload의 신뢰성은 서명 검증, manifest, 권한 정책 중 어디에서 확정할 것인가? | QA-04, FR-05, CONST-06 |
| Q-5 | Secure OS 교체 가능성을 초기 구조에서 어느 수준까지 인터페이스화할 것인가? | QA-09, FR-06 |

---

## 6. 다음 단계

선정된 Architectural Driver를 기준으로 후보 아키텍처를 도출하고, 각 후보를 신뢰 경계, HW 중재, 데이터 경로, Workload 탑재 방식 관점에서 비교한다.

신뢰 모델 문서(TCB 목록, 공격자 모델, 보호 속성별 의존 메커니즘)는 이후 후보 구조 평가의 기준이 된다. 상세 논거는 `99_trust_boundary_qna.md` 참조.
