# 기초지식 정리: TCB (Trusted Computing Base)

> 일자: 2026-06-11
> 관련 문서: `05_design_points.md` DP-01(신뢰 모델 확정), `99_trust_boundary_qna.md`, `00_overview.md` 3.2절
> 성격: 설계 착수 전 공통 용어/개념 정리 (참고 자료)

---

## 1. 정의

**TCB(Trusted Computing Base)는 시스템의 보안 정책 집행에 책임이 있는 모든 하드웨어, 펌웨어, 소프트웨어 구성 요소의 총집합**이다. 다시 말해, "이 부분이 침해되거나 오동작하면 시스템의 보안 보장이 무너지는" 구성 요소들의 집합이다.

이 용어는 미 국방부의 보안 평가 기준 TCSEC(Trusted Computer System Evaluation Criteria, 1985, 통칭 Orange Book)에서 공식화되었다.

> "The totality of protection mechanisms within a computer system — including hardware, firmware, and software — the combination of which is responsible for enforcing a security policy." — TCSEC (DoD 5200.28-STD)

핵심 함의는 역방향에 있다. **TCB 밖의 구성 요소는 아무리 오동작하거나 악의적으로 행동해도 보안 정책을 위반할 수 없어야 한다.** 따라서 어떤 컴포넌트를 TCB에 넣는다는 것은 "그 컴포넌트를 믿는다"는 선언이 아니라, "그 컴포넌트가 뚫리면 전체 보안이 뚫린다는 위험을 수용한다"는 선언이다.

---

## 2. trusted와 trustworthy의 구분

| 용어 | 의미 |
|------|------|
| **trusted (신뢰되는)** | 시스템 설계상 그 컴포넌트의 올바름에 보안이 *의존하고 있는* 상태. 의존한다는 사실 자체이며, 실제로 안전한지와는 별개 |
| **trustworthy (신뢰할 만한)** | 검증/감사/형식 증명 등을 통해 실제로 올바르게 동작함이 *입증된* 상태 |

이상적인 시스템은 "trusted한 것들이 모두 trustworthy한" 시스템이다. trusted인데 trustworthy하지 않은 컴포넌트가 TCB 안에 있는 것이 전형적인 보안 사고의 구조다. Host 커널 전체를 TCB에 두는 일반 KVM(VHE) 구조가 그 예다 — 수천만 LoC의 Linux 커널을 trustworthy하게 만드는 것은 현실적으로 불가능하다(`00_overview.md` 3.2절).

---

## 3. TCB 설계의 고전 원칙

### 3.1 TCB 최소화 (Minimization)

TCB가 작을수록 검증할 코드가 적고, 공격 표면이 줄고, trustworthy함을 입증하기 쉬워진다. Saltzer & Schroeder(1975)의 보호 메커니즘 설계 원칙 중 **economy of mechanism**(메커니즘의 단순성)이 근거가 된다. pKVM이 소형 Hypervisor만 EL2에 상주시키는 것이 이 원칙의 적용 사례다.

### 3.2 Reference Monitor 개념

TCB의 핵심부는 모든 접근을 중재하는 reference monitor로 모델링되며, 다음 세 요건을 만족해야 한다(Anderson Report, 1972).

| 요건 | 의미 | 본 과제에서의 대응물 |
|------|------|---------------------|
| **Tamper-proof** | 비신뢰 주체가 변조할 수 없어야 함 | Host가 EL2 코드/레지스터에 접근 불가 (nVHE) |
| **Always invoked** | 모든 접근이 우회 없이 중재를 거쳐야 함 | 모든 메모리 접근이 Stage-2 변환을, 모든 디바이스 DMA가 SMMU를 경유 |
| **Verifiable** | 충분히 작고 단순하여 분석/검증 가능해야 함 | 소형 EL2 Hypervisor (Host 커널 대비 수십분의 일 규모) |

### 3.3 권한 최소화와 계층화

TCB 내부에서도 모든 코드가 같은 권한을 가질 필요는 없다. 권한 수준(ARM의 Exception Level)에 따라 TCB를 계층화하면, 상위 권한 계층(EL3, EL2)을 최소로 유지하고 덜 중요한 기능을 낮은 권한으로 밀어낼 수 있다.

---

## 4. TCB와 신뢰 경계(Trust Boundary)

**신뢰 경계는 TCB의 안과 밖을 가르는 선**이다. 경계를 넘는 모든 상호작용(호출, 데이터 전달, 공유 메모리)은 검증 대상이 된다.

- 경계 밖에서 들어오는 입력은 모두 비신뢰 입력으로 취급하고 검증해야 한다.
- 경계 안에서 밖으로 나가는 데이터는 노출해도 되는 것만 나가야 한다.
- 신뢰 경계가 늘어날수록 격리는 강해질 수 있으나 경계 통과 비용(성능)이 증가한다 — `03_quality_attribute_workshop.md` 4.3절의 보안 vs 성능 상충이 이 지점이다.

같은 시스템이라도 **공격자 모델에 따라 TCB가 달라진다.** "Host 커널 권한까지 가진 공격자"를 가정하면 Host 커널은 TCB가 될 수 없고, "물리 접근 공격자"까지 가정하면 DRAM조차 신뢰할 수 없게 되어 메모리 암호화가 필요해진다. TCB 정의와 공격자 모델 정의가 항상 한 쌍으로 움직이는 이유다(DP-01의 설계질문 1/2번).

---

## 5. ARM 플랫폼에서의 TCB 구조

본 과제 타겟(ARM 기반 커스텀 SoC)에서 TCB 후보가 되는 권한 계층은 다음과 같다.

| 계층 | 구성 요소 | TCB 포함 여부 (pKVM 전제) |
|------|----------|--------------------------|
| EL3 (Secure Monitor) | Secure OS EL3 SPD, SMC 라우팅 | 포함 — 최고 권한, 세계(world) 전환 담당 |
| S-EL1 (Secure World) | TrustZone Secure OS Firmware | 포함 — 키 관리/인증 등 기존 TEE 기능 담당 |
| EL2 (Normal World) | pKVM Hypervisor | 포함 — Stage-2 변환 독점 제어, pVM 격리의 신뢰 주체 |
| EL1 (Normal World) | Host Linux 커널 (Framework 커널 드라이버 포함) | **비포함** — Host 비신뢰 전제(R-1) |
| EL0 (Normal World) | Host Middleware/Framework/앱 | **비포함** — 동일 |
| pVM 내부 EL1/EL0 | 게스트 OS/보안 Workload | 해당 pVM 자신에 대해서만 신뢰 (도메인 간 상호 비신뢰, QA-02) |

두 가지 주의점이 있다.

1. **TCB는 단일 집합이 아니라 보호 속성별로 다를 수 있다.** 예컨대 pVM 메모리의 기밀성/무결성 TCB는 {EL3, EL2}이지만, 가용성은 Host의 스케줄링에 의존하므로 Host까지 신뢰하지 않으면 보장할 수 없다(`99_trust_boundary_qna.md` 논거 1). DP-01에서 "보호 속성별 의존 메커니즘"을 명시하라는 요구가 여기서 나온다.
2. **HW/펌웨어도 TCB다.** SMMU, Stage-2 MMU 같은 하드웨어 메커니즘과 부트 ROM/부트로더 체인은 암묵적으로 TCB에 포함된다. SW 설계 문서에서 생략되기 쉬우나, 규제 증빙(CONST-04)과 attestation(격리 증빙) 설계 시에는 명시적으로 드러내야 한다.

---

## 6. 본 과제에서 TCB 범위의 기준이 되는 보호 속성

5절 주의점 1에서 본 것처럼 TCB는 보호 속성마다 다르게 정의된다. 따라서 "무엇을 보호하는가(보호 속성)"를 먼저 확정해야 TCB 범위를 정할 수 있다. 본 과제의 Driver를 보호 속성 관점으로 환원하면 다음 네 가지가 도출된다.

### 6.1 기밀성 (Confidentiality)

**근거**: QA-01(Host 침해 시 영상/모델/추론 데이터 비노출), QA-02(도메인 간 격리), QA-03(DMA 경로 격리), FR-05(데이터 격리 영역 내 유지). VOS-01/16/17이 가리키듯 과제의 존재 이유 자체가 기밀성이다.

**TCB 범위에 주는 기준**: "Host 커널 권한 공격자에도 비노출"이라는 요구가 Host 전체(개발 대상 Framework 포함)를 TCB에서 배제하는 근거가 된다. 실행 중 기밀성 TCB는 Stage-2/SMMU를 통제하는 {EL2, 관련 HW}와 세계 전환을 담당하는 {EL3}로 최소화할 수 있다. 단 저장 시(at-rest) 기밀성은 키 관리 주체(DP-07 결정)가 TCB에 추가된다.

### 6.2 무결성 (Integrity)

**근거**: 무결성이 깨지면 기밀성이 우회된다는 점에서 기밀성과 분리할 수 없는 속성이다. 변조된 pVM 이미지/Workload(DP-09)는 정상 채널을 통해 데이터를 유출할 수 있고, 권한 정책/manifest의 변조(DP-02)는 권한 체계를 무력화하며, 로그의 변조(탐지/로깅)는 CONST-04의 증빙을 무효로 만든다. 또한 QA-01의 보호 자산인 AI 모델 가중치는 노출뿐 아니라 변조 시에도 추론 결과의 신뢰가 무너진다.

**TCB 범위에 주는 기준**: 실행 중 메모리 무결성은 기밀성과 같은 {EL2, HW} 집합으로 충분하지만, 부팅/로딩 시점의 코드 진위(authenticity)는 검증 주체(DP-09 결정), 기록 무결성은 로그 저장소(탐지/로깅 결정)가 TCB에 추가된다. 즉 무결성은 "어느 시점의 무결성인가"에 따라 TCB가 단계적으로 확장되는 속성이다.

### 6.3 가용성 (Availability) — 비대칭적 보장

가용성은 방향에 따라 보장 가능성이 갈린다.

- **(a) pVM 장애로부터 Host/로봇 기본 동작 보호**: QA-09(VOS-18)가 요구하며, 격리 구조 자체가 장애 전파를 차단하므로 기존 격리 TCB로 달성 가능하다. 보장 대상이다.
- **(b) Host 침해로부터 pVM의 가용성 보호**: 메모리 할당, 스케줄링, 전원 관리를 Host가 쥐고 있으므로 Host를 TCB에 넣지 않는 한 구조적으로 보장할 수 없다(`99_trust_boundary_qna.md` 논거 1). 보장하려면 Host가 TCB로 들어와야 하는데, 이는 6.1의 기밀성 전제와 정면으로 모순된다.

**TCB 범위에 주는 기준**: (b)를 보호 범위에서 제외(또는 거부 시도를 탐지/기록하는 수준으로 한정)하는 결정이 기밀성 중심의 최소 TCB를 유지하는 전제 조건이 된다. 이것이 DP-01 설계질문 3번("가용성(DoS)도 포함하는가")이 별도 결정 사항인 이유다.

### 6.4 책임 추적성 (Accountability)

**근거**: QS-01의 응답 요소("비정상 접근 시도가 기록된다")와 CONST-04(기술적 격리의 증빙). 차단(기밀성)만으로는 규제 요건을 충족하지 못한다 — GDPR 증빙은 "격리가 실제로 동작했고 침해 시도가 있었는지"를 사후에 제3자에게 증명할 수 있어야 하며, 이는 Host가 위/변조할 수 없는 기록을 전제로 한다(격리 증빙, 탐지/로깅).

**TCB 범위에 주는 기준**: 추적성은 이벤트 감지 경로(Stage-2/SMMU fault를 수신하는 주체)와 로그 저장소를 TCB에 추가시킨다. 탐지/로깅에서 저장소를 어디에 두는가(EL2 직접 기록, 로그 pVM, TrustZone TEE)가 곧 추적성 TCB의 크기를 결정한다.

### 6.5 정리: 왜 이 네 속성인가

- **도출 방법**: Architectural Driver를 속성으로 환원했다. QA-01/02/03/FR-05 → 기밀성, QA-01의 변조 측면/CONST-04/DP-09/11/12 → 무결성, QA-09 → 가용성(a), QS-01 응답/CONST-04 → 추적성.
- **제외한 속성**: 부인 방지(non-repudiation)는 본 과제에서 추적성에 흡수되고(서명된 감사 로그로 충족), 프라이버시는 별도 메커니즘이 아니라 기밀성 + 규제 증빙(CONST-04)의 조합으로 커버된다.
- **공격자 모델과의 쌍**: 속성별 보장 수준은 공격자 모델과 한 쌍으로만 의미가 있다(4절). 예컨대 물리 접근/부채널 공격자를 포함하면 모든 속성의 TCB에 메모리 암호화 HW가 필요해지는데, CONST-05(HW 변경 불가)에 의해 사실상 제외가 강제된다. 이 역시 DP-01에서 명시적으로 기록해야 한다.

| 보호 속성 | 근거 Driver | TCB에 요구하는 구성 요소 | 보장 수준 (예상 방향) |
|----------|------------|------------------------|---------------------|
| 기밀성 | QA-01, QA-02, QA-03, FR-05 | EL2(pKVM), Stage-2 MMU/SMMU, EL3. 저장 시 키 관리 주체(DP-07) 추가 | Host 커널 권한 공격자까지 전면 보장 |
| 무결성 | QA-01(변조 측면), CONST-04 | 기밀성 TCB + 이미지 검증 주체(DP-09) + 로그 저장소(탐지/로깅) | 실행 중/부팅/기록 전면 보장 |
| 가용성 | QA-09 | (a) 기존 격리 TCB로 충분 / (b) Host 편입 없이 불가 | (a) 보장, (b) 제외 또는 탐지 수준 — DP-01 결정 사항 |
| 책임 추적성 | QA-01(QS-01 응답), CONST-04 | 이벤트 감지 경로 + 변조 불가 로그 저장소(탐지/로깅) | 증빙 가능한 형태로 보장 |

---

## 7. 본 과제와의 연결: 무엇이 결정으로 남아 있는가

> 본 절의 미결 사항 목록은 DP-01 결정 과정의 결정 체크리스트로 이관되었다. `06_dp01_trust_model.md` 2.3절을 참조한다. 각 항목의 결정 결과는 같은 문서 7절(결정 요약)에 기록되어 있다.

---

## 참고 자료

- DoD 5200.28-STD, "Trusted Computer System Evaluation Criteria (TCSEC, Orange Book)", 1985 — TCB 정의의 원전
- J. P. Anderson, "Computer Security Technology Planning Study", ESD-TR-73-51, 1972 — reference monitor 3요건
- J. H. Saltzer, M. D. Schroeder, "The Protection of Information in Computer Systems", Proceedings of the IEEE, 1975 — economy of mechanism 등 보호 메커니즘 설계 원칙
- Will Deacon et al., "Protecting the Protected: Building a Protected KVM Hypervisor", Linux Security Summit NA 2021 — pKVM의 TCB 최소화 설계
- ARM Architecture Reference Manual — Exception Level, Stage-2 Address Translation, TrustZone
