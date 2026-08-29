# ISO 25010 보안 하위 특성 기반 QA/QS 제안

> 본 문서는 ISO/IEC 25010:2023의 보안(Security) 하위 품질 특성 6개(기밀성, 무결성, 부인방지, 책임추적성, 인증성, 저항성) 각각에 대해,
> 본 과제(Secure Vision AI Platform)에 해당하는 QA(품질 속성 요구)와 QS(6-파트 품질 속성 시나리오)를 하나씩 제안한다.
> 시나리오 형식은 [`03_quality_attribute_specification.md`](03_quality_attribute_specification.md)를 따르고,
> 응답 측정치는 [`03_utility_tree.md`](03_utility_tree.md)의 게이트/KPI 구분을 사용한다.
>
> 관련 문서: [`03_qa_quality_scenarios.md`](03_qa_quality_scenarios.md), [`99_security_qa_metrics.md`](99_security_qa_metrics.md), [`TCB.md`](TCB.md)
>
> 수치 목표는 가정치이며, 로봇 제조사 협의 및 PoC 결과에 따라 보정한다.

---

## 1. ISO/IEC 25010 보안 하위 특성 개요

| 하위 특성 | 정의 (ISO/IEC 25010:2023) | 비고 |
|-----------|--------------------------|------|
| 기밀성 (Confidentiality) | 인가된 주체만 데이터에 접근할 수 있도록 보장하는 정도 | |
| 무결성 (Integrity) | 시스템/데이터가 비인가 변경으로부터 보호되는 정도 | |
| 부인방지 (Non-repudiation) | 행위나 사건의 발생을 사후에 부인할 수 없도록 증명 가능한 정도 | |
| 책임추적성 (Accountability) | 주체의 행위를 그 주체에게 유일하게 귀속시켜 추적할 수 있는 정도 | |
| 인증성 (Authenticity) | 주체나 자원의 신원이 주장된 것과 같음을 증명할 수 있는 정도 | |
| 저항성 (Resistance) | 악의적 행위자의 공격을 견디고, 대응하고, 복구하는 정도 | 2023 개정판에서 추가 |

주의: 가용성(Availability)은 ISO 25010에서 신뢰성(Reliability)의 하위 특성으로 분류되므로 본 문서 범위에서 제외한다(기존 AVL-01 pVM 장애 격리에서 다룸).

### 하위 특성 - 제안 QA/QS - 기존 시나리오 매핑

| ISO 하위 특성 | 제안 QA | 제안 QS | 연관 기존 시나리오 | 연관 DP |
|--------------|---------|---------|-------------------|---------|
| 기밀성 | QA-S01 | QS-S01 | SEC-01, SEC-05 | DP1, DP6 |
| 무결성 | QA-S02 | QS-S02 | SEC-04 | DP2 |
| 부인방지 | QA-S03 | QS-S03 | (신규) | DP2, DP5 |
| 책임추적성 | QA-S04 | QS-S04 | SEC-07 | - |
| 인증성 | QA-S05 | QS-S05 | SEC-06 | DP5 |
| 저항성 | QA-S06 | QS-S06 | SEC-01, SEC-03 | DP1, DP4 |

---

## 2. 기밀성 (Confidentiality)

### QA-S01

| ID | 품질 속성 요구 |
|----|---------------|
| QA-S01 | Host가 완전히 침해되어도 pVM 생명주기 전 구간(할당/운용/회수)과 저장 상태를 포함하여, 영상 원본, AI 모델 가중치, 추론 중간 데이터, 암호화 키가 비인가 주체에 노출되지 않아야 한다. |

### QS-S01: Host 침해 시 pVM 데이터 비노출

| Field | Specification |
|-------|---------------|
| Description | Host 루트 권한 침해 상황에서도 pVM 격리 메모리와 저장 데이터의 평문이 노출되지 않아야 한다. |
| Source | Host OS 루트 권한을 탈취한 공격자 |
| Stimulus | `/proc/kcore`, `/dev/mem`, DMA 경로를 통한 pVM 메모리 덤프 및 저장 blob 평문 스캔 시도 |
| Environment | Secure Vision AI 파이프라인 동작 중(pVM 메모리 할당/회수 시점 포함) |
| Artifact | pVM 격리 메모리 내 영상/모델/추론 데이터, 저장 상태 데이터와 암호화 키 |
| Response | Stage-2/S2MPU 격리에 의해 모든 접근이 차단되고, 저장 매체에는 암호문만 존재하며, 비정상 접근 시도가 기록된다. |
| Response Measure | **게이트**: 격리 메모리/평문 노출 0건 / **KPI**: 공격 벡터 자동화 커버리지 100%, 기밀성 TCB 규모(KLoC) 릴리스당 증가율 5% 이내 |
| 연관 | SEC-01, SEC-05, DP1, DP6 |

---

## 3. 무결성 (Integrity)

### QA-S02

| ID | 품질 속성 요구 |
|----|---------------|
| QA-S02 | 비신뢰 주체(침해된 Host 포함)가 pVM 부트 체인, 보안 Workload 이미지, 도메인 간 전달 데이터를 변조할 수 없어야 하며, 변조 시도는 해당 산출물이 사용되기 전에 탐지·거부되어야 한다. |

### QS-S02: 변조 Workload/부트 체인 사용 전 차단

| Field | Specification |
|-------|---------------|
| Description | Host 파일시스템과 로딩 경로가 침해되어도 변조된 Workload 이미지나 pVM 부트 구성요소가 실행되지 않아야 한다. |
| Source | Host 파일시스템과 Workload 로딩 경로를 장악한 공격자 |
| Stimulus | 서명/manifest/버전/해시가 변조된 Workload 이미지 또는 pVM 커널/initrd의 탑재·부팅 요청 |
| Environment | 보안 Workload 동적 탑재 및 pVM 부팅 수행 중(UC-03, UC-05) |
| Artifact | pVM 부트 체인(pvmfw 검증 대상), Workload 이미지/패키지, 서명 검증 경로 |
| Response | Host 침해와 독립인 신뢰 주체(pvmfw/검증 컴포넌트)가 서명과 무결성을 검증하고, 변조 산출물은 실행 전에 거부되며 거부 사유가 기록된다. |
| Response Measure | **게이트**: 미검증 산출물 실행 0건, 변조 이미지 탐지율 100% / **KPI**: 검증 소요 p99, IEC 62443-4-2 EDR 무결성 요구항목 충족률 |
| 연관 | SEC-04, DP2 |

---

## 4. 부인방지 (Non-repudiation)

### QA-S03

| ID | 품질 속성 요구 |
|----|---------------|
| QA-S03 | 보안에 영향을 주는 행위(Workload 탑재 승인, 보안 정책 변경, TEE 키 사용)는 수행 주체의 서명이 포함된 증거가 생성·보존되어, 수행 주체가 해당 행위를 사후에 부인할 수 없어야 한다. |

### QS-S03: 보안 행위의 서명 증적에 의한 부인 차단

| Field | Specification |
|-------|---------------|
| Description | Workload 벤더나 운영 주체가 자신이 수행한 탑재/정책 변경 행위를 사후에 부인하더라도, 서명된 증거로 행위 사실을 제3자가 검증할 수 있어야 한다. |
| Source | 배포한 Workload 또는 수행한 정책 변경을 부인하는 Workload 벤더/운영 주체(또는 이를 감사하는 규제 기관) |
| Stimulus | 보안 사고 조사 과정에서 특정 Workload 탑재/정책 변경 행위의 수행 주체에 대한 이의 제기 |
| Environment | 제품 상용 운용 단계, 보안 사고 사후 조사 시점 |
| Artifact | Workload 서명 체인(벤더 서명 + 탑재 승인 레코드), 정책 변경/키 사용 이력의 서명 레코드 |
| Response | 각 행위에 대해 수행 주체의 개인키로 서명된 레코드가 위·변조 방지 저장소에 보존되어 있어, 제3자가 공개키 체인으로 행위 주체를 검증할 수 있다. |
| Response Measure | **게이트**: 부인방지 대상 행위의 서명 증적 커버리지 100% / **KPI**: 증적 검증 성공률 100%, 증적 보존 기간 규제 요구 충족(CRA 등) |
| 연관 | DP2, DP5, SEC-07 |

---

## 5. 책임추적성 (Accountability)

### QA-S04

| ID | 품질 속성 요구 |
|----|---------------|
| QA-S04 | 격리 경계에 대한 모든 보안 관련 행위(pVM 생성/종료, HW 주체 전환, 메모리 공유/해제, 비정상 접근 시도)가 행위 주체(도메인/프로세스) 단위로 유일하게 귀속되어 사후 추적 가능해야 한다. |

### QS-S04: 침해 시도 행위의 주체 귀속 추적

| Field | Specification |
|-------|---------------|
| Description | 침해 시도 발생 후 포렌식 조사에서 어떤 주체가 언제 어떤 격리 경계에 어떤 행위를 했는지 감사 로그만으로 재구성할 수 있어야 한다. |
| Source | 침해 시도 공격자, 그리고 사후 조사를 수행하는 보안 운영 조직 |
| Stimulus | 격리 경계 비정상 접근 시도 발생 후 행위 이력 재구성 요구 |
| Environment | 제품 상용 운용 단계(fleet 운용 중), 다중 pVM 동시 운용 |
| Artifact | 감사 로그(주체 ID, 시각, 대상 자원, 행위, 결과), 로그 수집·보존 체계 |
| Response | 모든 보안 관련 행위가 행위 주체 식별자와 함께 기록되고, 로그 자체의 변조가 탐지 가능하며, 기한 내 포렌식 증적이 확보된다. |
| Response Measure | **게이트**: 보안 이벤트의 주체 귀속률 100% / **KPI**: 로그 변조 탐지 커버리지 100%, 포렌식 로그 확보 24h 이내, 비정상 접근 탐지 MTTD |
| 연관 | SEC-07, CRA, GDPR |

---

## 6. 인증성 (Authenticity)

### QA-S05

| ID | 품질 속성 요구 |
|----|---------------|
| QA-S05 | TEE/pVM/Host 간 상호작용에서 통신 상대와 실행 이미지의 신원이 주장된 것과 같음이 검증되어야 하며, 위장 주체의 요청은 성립하지 않아야 한다. |

### QS-S05: 위장 Host의 pVM 신원 도용 차단

| Field | Specification |
|-------|---------------|
| Description | 침해된 Host가 승인된 pVM으로 위장하여 TEE 자산이나 보안 채널에 접근을 시도해도, 신원 검증(attestation)에 의해 요청이 성립하지 않아야 한다. |
| Source | 승인된 pVM의 신원으로 위장한 침해된 Host |
| Stimulus | 위조 신원 또는 무결성 미확인 상태로 pVM→TEE RPC 호출 또는 도메인 간 보안 채널 수립 시도 |
| Environment | pVM→TEE 연동 경로 및 도메인 간 보안 채널 운용 중, 기존 Host→TEE SMC 경로 동시 운용 |
| Artifact | TEE 세션/키 자산, pVM 신원 증명(attestation 증거), 도메인 간 보안 채널 |
| Response | 신뢰 주체가 호출자의 신원·부팅 무결성을 attestation으로 검증하여 위장 요청을 거부하고, 기존 Host→TEE 기능은 회귀 없이 동작한다. |
| Response Measure | **게이트**: 비인가/위장 주체의 TEE 호출 및 채널 수립 성립 0건 / **KPI**: 호출자 신원·무결성 검증 커버리지 100% |
| 연관 | SEC-06, DP5 |

---

## 7. 저항성 (Resistance)

### QA-S06

| ID | 품질 속성 요구 |
|----|---------------|
| QA-S06 | 격리 경계(Stage-2, S2MPU/SMMU, 보안 채널)는 고숙련 공격자의 공격에 견뎌야 하며, 부분 침해가 발생해도 피해가 해당 도메인으로 한정되고 정의된 시간 내 복구되어야 한다. |

### QS-S06: 고공격 잠재력 공격에 대한 경계 유지와 복구

| Field | Specification |
|-------|---------------|
| Description | AVA_VAN.5급(고숙련/충분한 자금/내부 지식) 공격자의 침투 시험에서도 격리 경계가 유지되고, 단일 pVM 침해 시 피해가 격리·복구되어야 한다. |
| Source | 고공격 잠재력(CC CEM 기준)을 가진 침투 시험 조직 또는 버그바운티 공격자(pKVM Boundary Defeat급) |
| Stimulus | 하이퍼바이저 경계 돌파, DMA 우회(Thunderclap형), 부채널을 포함한 복합 공격 캠페인 수행 |
| Environment | 침투 시험 단계 및 상용 운용 단계(버그바운티 상시 운영) |
| Artifact | 격리 메커니즘(Stage-2, S2MPU/SMMU, 보안 채널), 침해 도메인의 복구 절차 |
| Response | 경계 돌파가 발생하지 않고, 단일 도메인 침해를 가정한 시험에서도 타 도메인 자산이 보호되며, 침해 도메인은 정의된 절차로 재프로비저닝된다. |
| Response Measure | **게이트**: 경계 돌파 0건(공격 잠재력 25점 이상 조건) / **KPI**: SESIP/CC AVA_VAN 목표 등급 달성, DMA 공격 벡터 차단율 100%, 침해 pVM 복구(재프로비저닝) 시간, EL2 TCB KLoC 예산 준수 |
| 연관 | SEC-01, SEC-03, DP1, DP4, `99_security_qa_metrics.md` |

---

## 8. 참고

- 명명 규칙: 기존 QA-01~ 및 SEC-01~ 번호와의 충돌을 피하기 위해 본 문서의 제안 항목은 QA-S / QS-S 접두어를 사용한다.
- TCB 크기(KLoC)는 품질 속성이 아니라 기밀성(QS-S01)·저항성(QS-S06)의 KPI(아키텍처 메트릭)로 배치하였다. 근거는 [`99_security_qa_metrics.md`](99_security_qa_metrics.md) 및 [`TCB.md`](TCB.md) 참조.
- 부인방지(QA-S03)는 기존 SEC-01~07이 다루지 않던 영역으로, ISO 25010 관점 정렬 과정에서 신규 식별되었다.

### 출처

1. [ISO/IEC 25010:2011 (ISO Online Browsing Platform)](https://www.iso.org/obp/ui/#iso:std:iso-iec:25010:ed-1:v1:en)
2. [ISO/IEC 25010:2023 개정 요약 (Codacy)](https://blog.codacy.com/iso-25010-software-quality-model)
3. [ISO/IEC 25023:2016 측정치 (iTeh preview)](https://cdn.standards.iteh.ai/samples/35747/34b91bc957f647ce8bbb2093907d7bc0/ISO-IEC-25023-2016.pdf)
4. [Android pKVM SESIP Level 5 인증 (Google Security Blog)](https://security.googleblog.com/2025/08/Android-pKVM-Certified-SESIP-Level-5.html)
