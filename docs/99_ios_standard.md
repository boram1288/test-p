# ISO/IEC 25010 / 25023 품질 속성 및 측정 방법 정리

본 문서는 ISO/IEC 25010(품질 모델)과 ISO/IEC 25023(제품 품질 측정)에 정의된 품질 속성(특성/부특성)과 각 품질 속성에 대한 측정 방법(측정 지표 및 측정 함수)을 정리한 참고 자료다.

- ISO/IEC 25010:2011, Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models
- ISO/IEC 25010:2023, SQuaRE — Product quality model (2011판의 기술적 개정판)
- ISO/IEC 25023:2016, SQuaRE — Measurement of system and software product quality

---

## 1. SQuaRE 시리즈에서 두 표준의 위치와 관계

SQuaRE(Systems and software Quality Requirements and Evaluation, ISO/IEC 25000 시리즈)는 다음 부문(division)으로 구성된다.

| 부문 | 표준 번호 | 내용 |
|---|---|---|
| Quality Management | ISO/IEC 2500n | 공통 모델, 용어, 정의 및 프로젝트 계획/관리 지침 |
| Quality Model | ISO/IEC 2501n | 제품 품질, 사용 품질(quality in use), 데이터 품질 모델 |
| Quality Measurement | ISO/IEC 2502n | 측정 참조 모델, 품질 측정 지표 정의 및 적용 지침 |
| Quality Requirements | ISO/IEC 2503n | 품질 요구사항 명세 지원 |
| Quality Evaluation | ISO/IEC 2504n | 품질 평가에 대한 요구사항, 권고, 지침 |
| Extension | ISO/IEC 25050~25099 | SQuaRE 확장 표준 |

두 표준의 역할 분담은 다음과 같다.

- **ISO/IEC 25010**: 품질 "무엇을" 평가할 것인가 — 품질 특성(characteristic)과 부특성(sub-characteristic)의 분류 체계(품질 모델)를 정의한다.
- **ISO/IEC 25023**: 품질을 "어떻게" 정량화할 것인가 — 25010의 각 특성/부특성에 대해 측정 지표(quality measure)와 측정 함수(measurement function)를 제공한다. ISO/IEC TR 9126-2(외부 측정), 9126-3(내부 측정)을 대체하며, 내부/외부 측정을 하나의 표 형식으로 통합하였다.

주의: ISO/IEC 25023:2016은 **ISO/IEC 25010:2011 품질 모델(8개 특성)** 을 기준으로 작성되었다. 2023년 개정된 25010(9개 특성)과는 특성 명칭과 구성에 차이가 있다(2.2절 참조).

### 1.1 측정 개념 구조 (ISO/IEC 25023 6장)

- **속성(property to quantify)**: 측정 대상 실체(시스템, 소프트웨어 제품 등)의 정량화 가능한 품질 관련 속성
- **측정 방법(measurement method)**: 속성을 특정 척도로 정량화하기 위한 논리적 연산 절차. 적용 결과가 품질 측정 요소가 된다
- **품질 측정 요소(QME, Quality Measure Element)**: 측정 방법을 적용해 얻는 기초 측정값 (ISO/IEC 25021에서 정의)
- **측정 함수(measurement function)**: 둘 이상의 QME를 결합하는 알고리즘/수식. 적용 결과가 품질 측정 지표가 된다
- **품질 측정 지표(quality measure)**: 측정 함수의 결과로서 품질 특성/부특성을 정량화한 값

측정 유형은 다음과 같이 구분된다.

- **내부 측정(internal measure)**: 소스 코드, 설계 명세 등 비실행 산출물의 정적 속성 측정. 리뷰, 인스펙션, 시뮬레이션, 자동화 도구로 검증. 개발 초기 단계에서 최종 제품 품질을 예측하는 데 사용
- **외부 측정(external measure)**: 시스템/소프트웨어를 실행하여 동작(behaviour)을 측정. 시험 단계 및 운영 단계에서 사용

품질 인과 체인: 프로세스 품질 → 내부 속성 → 외부 속성 → 사용 품질(quality in use). 앞 단계 품질은 뒷 단계 품질의 전제 조건이 된다.

---

## 2. ISO/IEC 25010 품질 모델 (품질 속성)

### 2.1 ISO/IEC 25010:2011 제품 품질 모델 — 8개 특성, 31개 부특성

ISO/IEC 25023이 측정 대상으로 삼는 기준 모델이다.

#### 2.1.1 기능 적합성 (Functional Suitability)

명시된 조건에서 사용될 때, 명시적/묵시적 요구를 충족하는 기능을 제공하는 정도.

| 부특성 | 정의 |
|---|---|
| 기능 완전성 (Functional completeness) | 기능 집합이 명시된 모든 과업과 사용자 목표를 포괄하는 정도 |
| 기능 정확성 (Functional correctness) | 제품/시스템이 필요한 정밀도로 올바른 결과를 제공하는 정도 |
| 기능 적절성 (Functional appropriateness) | 기능이 명시된 과업과 목표 달성을 촉진하는 정도 |

#### 2.1.2 성능 효율성 (Performance Efficiency)

명시된 조건에서 사용되는 자원의 양 대비 성능의 정도.

| 부특성 | 정의 |
|---|---|
| 시간 반응성 (Time behaviour) | 기능 수행 시 응답 시간, 처리 시간, 처리율(throughput)이 요구사항을 충족하는 정도 |
| 자원 활용성 (Resource utilization) | 기능 수행 시 사용하는 자원의 양과 유형이 요구사항을 충족하는 정도 |
| 용량 (Capacity) | 제품/시스템 파라미터의 최대 한계가 요구사항을 충족하는 정도 |

#### 2.1.3 호환성 (Compatibility)

동일한 하드웨어/소프트웨어 환경을 공유하면서, 다른 제품·시스템·컴포넌트와 정보를 교환하거나 요구 기능을 수행할 수 있는 정도.

| 부특성 | 정의 |
|---|---|
| 공존성 (Co-existence) | 공통 환경과 자원을 공유하는 다른 제품에 해로운 영향 없이 요구 기능을 효율적으로 수행하는 정도 |
| 상호운용성 (Interoperability) | 둘 이상의 시스템/제품/컴포넌트가 정보를 교환하고 교환된 정보를 사용할 수 있는 정도 |

#### 2.1.4 사용성 (Usability)

명시된 사용 맥락에서 특정 사용자가 효과성, 효율성, 만족도를 가지고 명시된 목표를 달성하기 위해 사용할 수 있는 정도.

| 부특성 | 정의 |
|---|---|
| 적절성 인식성 (Appropriateness recognizability) | 사용자가 제품/시스템이 자신의 요구에 적절한지 인식할 수 있는 정도 |
| 학습성 (Learnability) | 특정 사용자가 제품/시스템 사용법을 학습하여 목표를 달성할 수 있는 정도 |
| 운용성 (Operability) | 제품/시스템이 운용하고 제어하기 쉬운 속성을 갖는 정도 |
| 사용자 오류 방지 (User error protection) | 시스템이 사용자의 오류 유발을 방지하는 정도 |
| 사용자 인터페이스 심미성 (User interface aesthetics) | 사용자 인터페이스가 사용자에게 즐겁고 만족스러운 상호작용을 가능하게 하는 정도 |
| 접근성 (Accessibility) | 다양한 특성과 능력을 가진 사람들이 명시된 사용 맥락에서 제품/시스템을 사용할 수 있는 정도 |

#### 2.1.5 신뢰성 (Reliability)

명시된 기간 동안 명시된 조건에서 시스템/제품/컴포넌트가 명시된 기능을 수행하는 정도.

| 부특성 | 정의 |
|---|---|
| 성숙성 (Maturity) | 정상 운영 상태에서 신뢰성 요구를 충족하는 정도 |
| 가용성 (Availability) | 사용이 요구되는 시점에 운영 가능하고 접근 가능한 정도 |
| 결함 허용성 (Fault tolerance) | 하드웨어 또는 소프트웨어 결함에도 불구하고 의도된 대로 동작하는 정도 |
| 복구성 (Recoverability) | 중단이나 고장 발생 시, 직접 영향을 받은 데이터를 복구하고 시스템을 원하는 상태로 재확립할 수 있는 정도 |

#### 2.1.6 보안성 (Security)

사람 또는 다른 제품/시스템이 권한의 유형과 수준에 맞게 데이터에 접근할 수 있도록 정보와 데이터를 보호하는 정도.

| 부특성 | 정의 |
|---|---|
| 기밀성 (Confidentiality) | 접근 권한이 있는 자에게만 데이터 접근이 허용됨을 보장하는 정도 |
| 무결성 (Integrity) | 컴퓨터 프로그램 또는 데이터에 대한 비인가 접근/변경을 방지하는 정도 |
| 부인 방지 (Non-repudiation) | 행위나 사건의 발생을 사후에 부인할 수 없도록 입증할 수 있는 정도 |
| 책임 추적성 (Accountability) | 어떤 실체(entity)의 행위를 그 실체로 유일하게 추적할 수 있는 정도 |
| 인증성 (Authenticity) | 주체(subject)나 자원의 신원이 주장된 것과 일치함을 입증할 수 있는 정도 |

#### 2.1.7 유지보수성 (Maintainability)

의도된 유지보수자가 제품/시스템을 효과적이고 효율적으로 수정할 수 있는 정도.

| 부특성 | 정의 |
|---|---|
| 모듈성 (Modularity) | 한 컴포넌트의 변경이 다른 컴포넌트에 미치는 영향이 최소화되도록 시스템이 분리된 컴포넌트로 구성된 정도 |
| 재사용성 (Reusability) | 자산(asset)을 둘 이상의 시스템 또는 다른 자산 구축에 사용할 수 있는 정도 |
| 분석성 (Analysability) | 변경이 다른 부분에 미치는 영향 평가, 결함/고장 원인 진단, 수정 대상 식별을 효과적이고 효율적으로 할 수 있는 정도 |
| 수정성 (Modifiability) | 결함 유입이나 기존 품질 저하 없이 효과적이고 효율적으로 수정할 수 있는 정도 |
| 시험성 (Testability) | 시스템/제품/컴포넌트에 대한 시험 기준을 수립하고, 그 기준 충족 여부를 판정하는 시험을 효과적이고 효율적으로 수행할 수 있는 정도 |

#### 2.1.8 이식성 (Portability)

시스템/제품/컴포넌트를 하나의 하드웨어, 소프트웨어, 기타 운영/사용 환경에서 다른 환경으로 효과적이고 효율적으로 이전할 수 있는 정도.

| 부특성 | 정의 |
|---|---|
| 적응성 (Adaptability) | 상이하거나 진화하는 하드웨어/소프트웨어/운영 환경에 효과적이고 효율적으로 적응할 수 있는 정도 |
| 설치성 (Installability) | 명시된 환경에서 효과적이고 효율적으로 설치/제거할 수 있는 정도 |
| 대체성 (Replaceability) | 동일 환경에서 동일 목적의 다른 소프트웨어 제품을 대체할 수 있는 정도 |

### 2.2 ISO/IEC 25010:2023 개정판 — 9개 특성

2023년 개정판은 8개 특성을 9개로 재편하였다. 주요 변경 사항은 다음과 같다.

- **Usability → Interaction Capability(상호작용 능력)** 로 명칭 변경 및 부특성 재편
- **Portability → Flexibility(유연성)** 로 명칭 변경, **Scalability(확장성)** 부특성 추가
- **Safety(안전성)** 특성 신설
- Reliability의 Maturity가 **Faultlessness(무결함성)** 로 명칭 변경
- Security에 **Resistance(저항성)** 부특성 추가

| # | 특성 (2023) | 부특성 (2023) | 2011판 대비 |
|---|---|---|---|
| 1 | 기능 적합성 (Functional Suitability) | 기능 완전성, 기능 정확성, 기능 적절성 | 동일 |
| 2 | 성능 효율성 (Performance Efficiency) | 시간 반응성, 자원 활용성, 용량 | 동일 |
| 3 | 호환성 (Compatibility) | 공존성, 상호운용성 | 동일 |
| 4 | 상호작용 능력 (Interaction Capability) | 적절성 인식성, 학습성, 운용성, 사용자 오류 방지, 사용자 몰입(User engagement), 포용성(Inclusivity), 사용자 지원(User assistance), 자기 서술성(Self-descriptiveness) | Usability 개칭. 심미성 → 사용자 몰입, 접근성 → 포용성/사용자 지원으로 재편 |
| 5 | 신뢰성 (Reliability) | 무결함성(Faultlessness), 가용성, 결함 허용성, 복구성 | 성숙성 → 무결함성 |
| 6 | 보안성 (Security) | 기밀성, 무결성, 부인 방지, 책임 추적성, 인증성, 저항성(Resistance) | 저항성 추가 |
| 7 | 유지보수성 (Maintainability) | 모듈성, 재사용성, 분석성, 수정성, 시험성 | 동일 |
| 8 | 유연성 (Flexibility) | 적응성, 설치성, 대체성, 확장성(Scalability) | Portability 개칭, 확장성 추가 |
| 9 | 안전성 (Safety) | 운영 제약(Operational constraint), 위험 식별(Risk identification), 안전 고장(Fail safe), 위험 경고(Hazard warning), 안전 통합(Safe integration) | 신설 |

---

## 3. ISO/IEC 25023:2016 품질 측정 방법

### 3.1 측정 지표 문서화 형식 (7장)

25023의 8장은 각 품질 측정 지표를 다음 4개 항목의 표로 정의한다.

| 항목 | 내용 |
|---|---|
| ID | 측정 지표 식별 코드 |
| Name | 측정 지표 이름 |
| Description | 측정 지표가 제공하는 정보 |
| Measurement function | QME들을 결합하여 측정 지표를 산출하는 수식 |

**ID 체계**는 세 부분으로 구성된다.

1. 특성/부특성 약어 코드: 대문자 X(특성) + 소문자 x(부특성). 예: `FCp` = Functional suitability / Completeness, `PTb` = Performance efficiency / Time behaviour
2. 부특성 내 일련번호
3. 분류 코드: **G(Generic, 범용)** 또는 **S(Specific, 특정 상황용)**

**적합성(Conformance) 요건(2장)**: 25010에서 평가할 특성/부특성을 선정한 후, 해당 특성/부특성의 **모든 Generic(G) 지표는 반드시 사용**해야 하며(제외 시 근거 제시), Specific(S) 지표는 관련성이 있을 때 선택적으로 사용한다. 지표를 수정하면 근거를 제시하고, 추가 지표는 ISO/IEC 25021의 QME 규칙에 따라 정의한다.

**해석 규칙**: 대부분의 측정 함수는 결과를 0.0~1.0 범위로 정규화하며 1.0에 가까울수록 좋다(그렇지 않은 경우 NOTE로 해석 방법 명시). 평균 응답 시간처럼 단독 해석이 어려운 지표는 (a) 요구 기준과의 비교(conformance), (b) 유사 제품/기존 시스템과의 벤치마크, (c) 시계열 추이 비교 방식으로 해석한다. 일부 지표는 요구사항 명세에 정의된 목표값(target value)을 기준으로 정규화한다.

### 3.2 특성별 측정 지표 및 측정 함수 (8장)

이하 표는 25023 8장의 측정 지표 전체(총 86개)를 정리한 것이다. 측정 함수의 `A`, `B`, `T`, `N` 등은 각 지표의 QME를 나타내며, 수식과 함께 그 의미를 기술한다.

#### 3.2.1 기능 적합성 측정 (8.2)

| ID | 지표명 | 측정 함수 및 방법 |
|---|---|---|
| FCp-1-G | 기능 커버리지 (Functional coverage) | X = 1 − A/B. A: 누락된 기능 수, B: 명세된 기능 수. 명세 대비 구현된 기능의 비율 |
| FCr-1-G | 기능 정확성 (Functional correctness) | X = 1 − A/B. A: 부정확한 기능 수, B: 검토 대상 기능 수. 올바른 결과를 제공하는 기능의 비율 |
| FAp-1-G | 사용 목표에 대한 기능 적절성 (Functional appropriateness of usage objective) | X = 1 − A/B. A: 특정 사용 목표 달성에 필요한 기능 중 누락되었거나 부정확한 기능 수, B: 해당 목표에 필요한 기능 수 |
| FAp-2-S | 시스템의 기능 적절성 (Functional appropriateness of the system) | X = Σ(사용 목표별 FAp-1 값)/n. n: 사용 목표 수. 전체 사용 목표에 대한 기능 적절성의 평균 |

#### 3.2.2 성능 효율성 측정 (8.3)

| ID | 지표명 | 측정 함수 및 방법 |
|---|---|---|
| PTb-1-G | 평균 응답 시간 (Mean response time) | X = Σ(Bi − Ai)/n. Ai: i번째 과업 요청 시각, Bi: 응답 시작 시각, n: 측정 횟수 |
| PTb-2-S | 응답 시간 적정성 (Response time adequacy) | X = A/B. A: 실측 평균 응답 시간, B: 명세된 목표 응답 시간. 1 이하일수록 적정 |
| PTb-3-G | 평균 반환 시간 (Mean turnaround time) | X = Σ(작업 요청부터 작업 완료까지의 시간)/n. 작업(job) 완료 기준의 평균 소요 시간 |
| PTb-4-S | 반환 시간 적정성 (Turnaround time adequacy) | X = A/B. A: 실측 평균 반환 시간, B: 명세된 목표 반환 시간 |
| PTb-5-G | 평균 처리율 (Mean throughput) | X = Σ(단위 시간당 완료 작업 수)/n. 관측 구간별 처리율의 평균 |
| PRu-1-G | 평균 프로세서 사용률 (Mean processor utilization) | X = Σ(Ai/Bi)/n. Ai: 실제 사용한 프로세서 시간, Bi: 운영 시간. 낮을수록 좋음 |
| PRu-2-G | 평균 메모리 사용률 (Mean memory utilization) | X = Σ(Ai/Bi)/n. Ai: 실제 사용한 메모리 크기, Bi: 가용 메모리 크기. 낮을수록 좋음 |
| PRu-3-G | 평균 I/O 장치 사용률 (Mean I/O devices utilization) | X = Σ(Ai/Bi)/n. Ai: I/O 장치 점유(busy) 시간, Bi: I/O 작업에 요구되는 시간. 낮을수록 좋음 |
| PRu-4-S | 대역폭 사용률 (Bandwidth utilization) | X = A/B. A: 사용한 전송 대역폭, B: 가용(용량) 대역폭 |
| PCa-1-G | 트랜잭션 처리 용량 (Transaction processing capacity) | X = A/T. A: 완료된 트랜잭션 수, T: 관측 시간. 단위 시간당 처리 가능한 트랜잭션 수 |
| PCa-2-S | 사용자 접속 용량 (User access capacity) | X = 단위 시간 내 시스템이 정상 처리 가능한 최대 동시 사용자 수 |
| PCa-3-S | 사용자 접속 증가 적정성 (User access increase adequacy) | X = A/B. A: 수용 가능한 추가 동시 사용자 수, B: 요구되는 추가 동시 사용자 수 |

#### 3.2.3 호환성 측정 (8.4)

| ID | 지표명 | 측정 함수 및 방법 |
|---|---|---|
| CCo-1-G | 타 제품과의 공존성 (Co-existence with other products) | X = A/B. A: 환경 공유 중에도 품질 요구를 계속 충족하는 타 제품 수, B: 환경을 공유하는 타 제품 총수 |
| CIn-1-G | 데이터 형식 교환성 (Data formats exchangeability) | X = A/B. A: 타 시스템과 교환 가능한 데이터 형식 수, B: 교환이 요구되는 데이터 형식 수 |
| CIn-2-S | 데이터 교환 프로토콜 충분성 (Data exchange protocol sufficiency) | X = A/B. A: 지원되는 데이터 교환 프로토콜 수, B: 요구되는 데이터 교환 프로토콜 수 |
| CIn-3-S | 외부 인터페이스 적정성 (External interface adequacy) | X = A/B. A: 명세대로 구현된 외부 인터페이스 수, B: 명세된 외부 인터페이스 수 |

#### 3.2.4 사용성 측정 (8.5)

| ID | 지표명 | 측정 함수 및 방법 |
|---|---|---|
| UAp-1-G | 설명 완전성 (Description completeness) | X = A/B. A: 제품 설명(문서)에 기술된 사용 시나리오 수, B: 제품이 수행 가능한 사용 시나리오 수 |
| UAp-2-S | 데모 커버리지 (Demonstration coverage) | X = A/B. A: 데모/튜토리얼이 제공되는 과업 수, B: 데모가 필요한 과업 수 |
| UAp-3-S | 진입점 자기 서술성 (Entry point self-descriptiveness) | X = A/B. A: 목적과 내용을 스스로 설명하는 진입점(예: 웹사이트 랜딩) 수, B: 전체 진입점 수 |
| ULe-1-G | 사용자 안내 완전성 (User guidance completeness) | X = A/B. A: 사용자 문서/도움말이 제공되는 기능 수, B: 전체 기능 수 |
| ULe-2-S | 입력 필드 기본값 (Entry fields defaults) | X = A/B. A: 기본값이 제공되는 입력 필드 수, B: 기본값 제공이 가능한 입력 필드 수 |
| ULe-3-S | 오류 메시지 이해성 (Error messages understandability) | X = A/B. A: 원인과 해결 방법을 알려주는 오류 메시지 수, B: 전체 오류 메시지 수 |
| ULe-4-S | 자기 설명적 사용자 인터페이스 (Self-explanatory user interface) | X = A/B. A: 별도 설명 없이 이해 가능한 UI 요소 수, B: 전체 UI 요소 수 |
| UOp-1-G | 운용 일관성 (Operational consistency) | X = 1 − A/B. A: 유사 과업 간 조작이 일관되지 않은 상호작용 과업 수, B: 유사 조작을 갖는 상호작용 과업 수 |
| UOp-2-G | 메시지 명확성 (Message clarity) | X = A/B. A: 올바른 의미를 전달하는 메시지 수, B: 전체 메시지 수 |
| UOp-3-S | 기능 커스터마이즈 가능성 (Functional customizability) | X = A/B. A: 커스터마이즈 가능한 기능 수, B: 커스터마이즈가 요구되는 기능 수 |
| UOp-4-S | UI 커스터마이즈 가능성 (User interface customizability) | X = A/B. A: 커스터마이즈 가능한 UI 요소 수, B: 커스터마이즈가 요구되는 UI 요소 수 |
| UOp-5-S | 모니터링 능력 (Monitoring capability) | X = A/B. A: 구현된 상태 모니터링 기능 수, B: 요구되는 상태 모니터링 기능 수 |
| UOp-6-S | 실행 취소 능력 (Undo capability) | X = A/B. A: 실행 취소(undo)가 가능한 과업 수, B: 실행 취소가 필요한 과업 수 |
| UOp-7-S | 정보 분류 이해성 (Understandable categorization of information) | X = A/B. A: 사용자가 이해하기 쉽게 분류된 정보 카테고리 수, B: 전체 정보 카테고리 수 |
| UOp-8-S | 외관 일관성 (Appearance consistency) | X = 1 − A/B. A: 유사 UI 요소 중 외관이 일관되지 않은 요소 수, B: 유사 외관이 요구되는 UI 요소 수 |
| UOp-9-S | 입력 장치 지원 (Input device support) | X = A/B. A: 적합한 모든 입력 방식으로 시작 가능한 과업 수, B: 전체 과업 수 |
| UEp-1-G | 사용자 조작 오류 회피 (Avoidance of user operation error) | X = A/B. A: 시스템 오동작을 유발하지 않도록 보호된 사용자 행위/입력 수, B: 오동작을 유발할 수 있는 사용자 행위/입력 수 |
| UEp-2-S | 사용자 입력 오류 수정 (User entry error correction) | X = A/B. A: 수정값이 제안되는 입력 오류 수, B: 전체 입력 오류 수 |
| UEp-3-S | 사용자 오류 복구성 (User error recoverability) | X = A/B. A: 사용자 오류 후 복구(취소/되돌리기) 가능한 오류 수, B: 전체 사용자 오류 수 |
| UIn-1-S | UI 외관 심미성 (Appearance aesthetics of user interfaces) | X = A/B. A: 사용자에게 심미적으로 만족스러운 화면 수, B: 전체 화면 수. 설문 등 주관 평가 기반 |
| UAc-1-S | 장애 사용자 접근성 (Accessibility for users with disabilities) | X = A/B. A: 특정 장애를 가진 사용자가 사용 가능한 기능 수, B: 구현된 기능 수 |
| UAc-2-S | 지원 언어 적정성 (Supported languages adequacy) | X = A/B. A: 지원되는 언어 수, B: 요구되는 언어 수 |

#### 3.2.5 신뢰성 측정 (8.6)

| ID | 지표명 | 측정 함수 및 방법 |
|---|---|---|
| RMa-1-G | 결함 수정률 (Fault correction) | X = A/B. A: 설계/코딩/시험 단계에서 수정된 결함 수, B: 탐지된 결함 수 |
| RMa-2-G | 평균 고장 간격 (Mean time between failure, MTBF) | X = T/A. T: 운영 시간, A: 발생한 고장 수. 높을수록 좋음(0~1 정규화 아님) |
| RMa-3-G | 고장률 (Failure rate) | X = A/T. A: 관측 기간 내 고장 수, T: 관측 시간. 낮을수록 좋음 |
| RMa-4-S | 시험 커버리지 (Test coverage) | X = A/B. A: 실제 수행된 시험 케이스 수, B: 요구사항 커버에 필요한 시험 케이스 수 |
| RAv-1-G | 시스템 가용성 (System availability) | X = A/B. A: 실제 시스템이 운영 가능했던 시간, B: 운영이 계획된 시간 |
| RAv-2-S | 평균 다운 시간 (Mean down time) | X = T/N. T: 총 다운 시간(수리, 시정/예방 정비, 물류 지연 포함), N: 고장(중단) 횟수. 낮을수록 좋음 |
| RFt-1-G | 고장 회피 (Failure avoidance) | X = A/B. A: 치명적/중대한 고장으로 이어지지 않도록 통제된 결함 패턴 수, B: 고려한 결함 패턴 수. 결함 주입 시험 등으로 측정 |
| RFt-2-S | 컴포넌트 이중화 (Redundancy of components) | X = A/B. A: 이중화 설치된 컴포넌트 수, B: 시스템 고장 회피를 위해 이중화가 필요한 컴포넌트 수 |
| RFt-3-S | 평균 결함 통지 시간 (Mean fault notification time) | X = Σ(결함 발생 시각부터 시스템이 통지한 시각까지의 시간)/N. 낮을수록 좋음 |
| RRe-1-G | 평균 복구 시간 (Mean recovery time) | X = Σ(고장 후 복구 완료까지의 시간)/N. 낮을수록 좋음 |
| RRe-2-S | 백업 데이터 완전성 (Backup data completeness) | X = A/B. A: 정기적으로 백업되는 데이터 항목 수, B: 백업이 요구되는 데이터 항목 수 |

#### 3.2.6 보안성 측정 (8.7)

| ID | 지표명 | 측정 함수 및 방법 |
|---|---|---|
| SCo-1-G | 접근 통제성 (Access controllability) | X = A/B. A: 적절한 인가 절차를 통해서만 접근 가능하도록 통제된 기밀 데이터 항목 수, B: 접근 통제가 요구되는 기밀 데이터 항목 수 |
| SCo-2-S | 데이터 암호화 정확성 (Data encryption correctness) | X = A/B. A: 올바르게 암·복호화되는 데이터 항목 수, B: 암·복호화가 요구되는 데이터 항목 수 |
| SCo-3-S | 암호 알고리즘 강도 (Strength of cryptographic algorithms) | X = A/B. A: 충분히 강한(파훼되지 않은) 암호 알고리즘이 적용된 데이터 항목 수, B: 암호 알고리즘이 적용된 데이터 항목 수 |
| SIn-1-G | 데이터 무결성 (Data integrity) | X = A/B. A: 손상(corruption)이 방지된 데이터 항목 수, B: 손상 방지가 요구되는 데이터 항목 수 |
| SIn-2-S | 내부 데이터 손상 방지 (Internal data corruption prevention) | X = A/B. A: 구현된 데이터 손상 방지 방법 수, B: 가용/권고되는 데이터 손상 방지 방법 수 |
| SIn-3-S | 버퍼 오버플로 방지 (Buffer overflow prevention) | X = A/B. A: 경계 검사가 수행되는 사용자 입력 기반 메모리 접근 수, B: 사용자 입력 기반 메모리 접근 총수 |
| SNo-1-G | 전자 서명 사용률 (Digital signature usage) | X = A/B. A: 전자 서명 등으로 캡처되는 이벤트 수, B: 부인 방지가 요구되는 이벤트 수 |
| SAc-1-G | 사용자 감사 추적 완전성 (User audit trail completeness) | X = A/B. A: 로그에 기록되는 사용자 접근 수, B: 전체 사용자 접근 수 |
| SAc-2-S | 시스템 로그 보존성 (System log retention) | X = A/B. A: 안정적 저장소에 로그가 실제 보존되는 기간, B: 요구되는 로그 보존 기간 |
| SAu-1-G | 인증 메커니즘 충분성 (Authentication mechanism sufficiency) | X = A/B. A: 구현된 인증 메커니즘 수, B: 명세된 인증 메커니즘 수 |
| SAu-2-S | 인증 규칙 준수성 (Authentication rules conformity) | X = A/B. A: 구현된 인증 규칙 수, B: 명세된 인증 규칙 수 |

#### 3.2.7 유지보수성 측정 (8.8)

| ID | 지표명 | 측정 함수 및 방법 |
|---|---|---|
| MMo-1-G | 컴포넌트 결합도 (Coupling of components) | X = A/B. A: 다른 컴포넌트에 영향을 주지 않는(독립적인) 컴포넌트 수, B: 독립적이어야 하는 컴포넌트 수 |
| MMo-2-S | 순환 복잡도 적정성 (Cyclomatic complexity adequacy) | X = 1 − A/B. A: 허용 임계값을 초과하는 순환 복잡도를 갖는 모듈 수, B: 전체 모듈 수 |
| MRe-1-G | 자산 재사용성 (Reusability of assets) | X = A/B. A: 재사용 가능하도록 설계/구축된 자산 수, B: 전체 자산 수 |
| MRe-2-S | 코딩 규칙 준수성 (Coding rules conformity) | X = A/B. A: 코딩 규칙을 준수하는 모듈 수, B: 전체 모듈 수 |
| MAn-1-G | 시스템 로그 완전성 (System log completeness) | X = A/B. A: 실제 기록되는 로그 수, B: 감사(audit)에 필요한 것으로 요구되는 로그 수 |
| MAn-2-S | 진단 기능 유효성 (Diagnosis function effectiveness) | X = A/B. A: 원인 분석에 유용한 진단 기능 수, B: 구현된 진단 기능 수 |
| MAn-3-S | 진단 기능 충분성 (Diagnosis function sufficiency) | X = A/B. A: 구현된 진단 기능 수, B: 요구되는 진단 기능 수 |
| MMd-1-G | 수정 효율성 (Modification efficiency) | X = Σ(Ai/Bi)/n. Ai: i번째 수정의 예상(기대) 소요 시간, Bi: 실제 소요 시간. 수정별 기대 대비 실적의 평균 |
| MMd-2-S | 수정 정확성 (Modification correctness) | X = 1 − A/B. A: 수정 후 일정 기간 내 장애/품질 저하를 유발한 수정 수, B: 수행된 수정 수 |
| MMd-3-S | 수정 능력 (Modification capability) | X = A/B. A: 요구된 기간(time-box) 내 실제 구현된 수정 수, B: 요구된 수정 수 |
| MTe-1-G | 시험 기능 완전성 (Test function completeness) | X = A/B. A: 요구대로 구현된 시험 기능(테스트 지원 기능) 수, B: 요구되는 시험 기능 수 |
| MTe-2-S | 자율 시험성 (Autonomous testability) | X = A/B. A: 다른 (하위)시스템에 의존하지 않고 단독 수행 가능한 시험 수, B: 시뮬레이션으로 단독 시험이 가능해야 하는 시험 수 |
| MTe-3-S | 시험 재시작성 (Test restartability) | X = A/B. A: 중단 후 체크포인트에서 재개 가능한 시험 수, B: 일시 중지가 필요한 시험 수 |

#### 3.2.8 이식성 측정 (8.9)

| ID | 지표명 | 측정 함수 및 방법 |
|---|---|---|
| PAd-1-G | 하드웨어 환경 적응성 (Hardware environmental adaptability) | X = 1 − A/B. A: 새 하드웨어 환경에서 과업을 완료하지 못했거나 요구 수준에 미달한 기능 수, B: 새 하드웨어 환경에서 시험한 기능 수 |
| PAd-2-S | 시스템 소프트웨어 환경 적응성 (System software environmental adaptability) | X = 1 − A/B. A: 새 OS/미들웨어 등 시스템 소프트웨어 환경에서 과업을 완료하지 못한 기능 수, B: 시험한 기능 수 |
| PAd-3-S | 운영 환경 적응성 (Operational environment adaptability) | X = 1 − A/B. A: 기타 새로운 운영 환경에서 과업을 완료하지 못한 기능 수, B: 시험한 기능 수 |
| PIn-1-G | 설치 시간 효율성 (Installation time efficiency) | X = Σ(Ai/Bi)/n. Ai: 예상 설치 시간, Bi: 실제 설치 시간. 설치 작업별 기대 대비 실적의 평균 |
| PIn-2-S | 설치 용이성 (Ease of installation) | X = A/B. A: 사용자 편의에 맞게 커스터마이즈 가능한 설치 절차 수, B: 커스터마이즈가 요구되는 설치 절차 수 |
| PRe-1-G | 사용 유사성 (Usage similarity) | X = A/B. A: 추가 학습이나 우회 없이 기존 제품과 유사하게 수행 가능한 기능 수, B: 기존 제품의 대응 기능 수 |
| PRe-2-S | 제품 품질 동등성 (Product quality equivalence) | X = A/B. A: 기존 제품과 동등 이상인 품질 측정 지표 수, B: 비교한 품질 측정 지표 수 |
| PRe-3-S | 기능 포괄성 (Functional inclusiveness) | X = A/B. A: 기존 제품과 유사한 결과를 산출하는 기능 수, B: 대체 대상 기존 제품의 기능 수 |
| PRe-4-S | 데이터 재사용/가져오기 능력 (Data reusability/import capability) | X = A/B. A: 기존 제품 데이터 중 계속 사용(가져오기) 가능한 데이터 수, B: 재사용이 요구되는 기존 제품 데이터 수 |

### 3.3 측정 지표 요약 통계

| 특성 | 부특성 수 | 측정 지표 수 (G / S) |
|---|---|---|
| 기능 적합성 | 3 | 4 (3G / 1S) |
| 성능 효율성 | 3 | 12 (7G / 5S) |
| 호환성 | 2 | 4 (2G / 2S) |
| 사용성 | 6 | 22 (5G / 17S) |
| 신뢰성 | 4 | 11 (6G / 5S) |
| 보안성 | 5 | 11 (5G / 6S) |
| 유지보수성 | 5 | 13 (5G / 8S) |
| 이식성 | 3 | 9 (3G / 6S) |
| **합계** | **31** | **86** |

---

## 4. 적용 시 유의 사항

1. **지표 선정**: 25010에서 평가 대상 특성/부특성을 먼저 선정하고, 해당 부특성의 Generic 지표를 기본 적용한다. Specific 지표는 시스템 특성(웹, 임베디드, 안전 필수 등)에 따라 선택한다.
2. **목표값 설정**: 25023은 측정값의 등급/합격 기준을 정의하지 않는다. 목표값(target value)은 시스템 범주, 무결성 수준, 사용자 요구에 따라 요구사항 명세에서 별도로 정의해야 한다.
3. **내부/외부 측정의 병행**: 외부 측정과 강한 상관관계를 갖는 내부 측정을 함께 사용하여 개발 초기에 최종 품질을 예측하는 것이 권장된다.
4. **행동 수준 측정의 한계**: 25023의 지표는 대체로 소스 코드 수준이 아닌 시스템 행동(behaviour) 수준의 측정이다. 코드 수준의 정적 품질 측정이 필요하면 CISQ 등의 보완 표준을 병용할 수 있다.
5. **2023 개정판과의 매핑**: 25023:2016은 25010:2011 기준이므로, 25010:2023의 신설 특성(Safety, Scalability, Resistance 등)에는 대응 지표가 없다. 해당 특성은 ISO/IEC 25021의 QME 정의 절차에 따라 자체 지표를 정의하거나 도메인 표준(IEC 61508 등)을 참조해야 한다.

---

## 출처

- ISO/IEC 25010:2023 — https://www.iso.org/standard/78176.html
- ISO/IEC 25010 개요 (iso25000.com) — https://iso25000.com/en/iso-25000-standards/iso-25010
- ISO/IEC 25023:2016 표준 미리보기 (구조, 용어, 문서화 형식) — https://cdn.standards.iteh.ai/samples/35747/34b91bc957f647ce8bbb2093907d7bc0/ISO-IEC-25023-2016.pdf
- Karnouskos, S. et al. (2018), "The Applicability of ISO/IEC 25023 Measures to the Integration of Agents and Automation Systems", IECON 2018 (25023 전체 측정 지표 목록 및 해설) — https://arxiv.org/pdf/2108.02921
- CISQ, Related Standards and Guidelines — https://www.it-cisq.org/standards/related-standards-and-guidelines/
