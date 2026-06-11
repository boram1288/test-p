# 기초지식 정리: TCB (Trusted Computing Base)

> 일자: 2026-06-11
> 관련 문서: `05_design_points.md` DP-01(신뢰 모델 확정), `99_trust_boundary_qna.md`, `00_overview.md` 3.2절
> 성격: 설계 착수 전 공통 용어·개념 정리 (참고 자료)

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
| **trustworthy (신뢰할 만한)** | 검증·감사·형식 증명 등을 통해 실제로 올바르게 동작함이 *입증된* 상태 |

이상적인 시스템은 "trusted한 것들이 모두 trustworthy한" 시스템이다. trusted인데 trustworthy하지 않은 컴포넌트가 TCB 안에 있는 것이 전형적인 보안 사고의 구조다. Host 커널 전체를 TCB에 두는 일반 KVM(VHE) 구조가 그 예다 — 수천만 LoC의 Linux 커널을 trustworthy하게 만드는 것은 현실적으로 불가능하다(`00_overview.md` 3.2절).

---

## 3. TCB 설계의 고전 원칙

### 3.1 TCB 최소화 (Minimization)

TCB가 작을수록 검증할 코드가 적고, 공격 표면이 줄고, trustworthy함을 입증하기 쉬워진다. Saltzer & Schroeder(1975)의 보호 메커니즘 설계 원칙 중 **economy of mechanism**(메커니즘의 단순성)이 근거가 된다. pKVM이 소형 hypervisor만 EL2에 상주시키는 것이 이 원칙의 적용 사례다.

### 3.2 Reference Monitor 개념

TCB의 핵심부는 모든 접근을 중재하는 reference monitor로 모델링되며, 다음 세 요건을 만족해야 한다(Anderson Report, 1972).

| 요건 | 의미 | 본 과제에서의 대응물 |
|------|------|---------------------|
| **Tamper-proof** | 비신뢰 주체가 변조할 수 없어야 함 | Host가 EL2 코드·레지스터에 접근 불가 (nVHE) |
| **Always invoked** | 모든 접근이 우회 없이 중재를 거쳐야 함 | 모든 메모리 접근이 Stage-2 변환을, 모든 디바이스 DMA가 SMMU를 경유 |
| **Verifiable** | 충분히 작고 단순하여 분석·검증 가능해야 함 | 소형 EL2 hypervisor (Host 커널 대비 수십분의 일 규모) |

### 3.3 권한 최소화와 계층화

TCB 내부에서도 모든 코드가 같은 권한을 가질 필요는 없다. 권한 수준(ARM의 Exception Level)에 따라 TCB를 계층화하면, 상위 권한 계층(EL3, EL2)을 최소로 유지하고 덜 중요한 기능을 낮은 권한으로 밀어낼 수 있다.

---

## 4. TCB와 신뢰 경계(Trust Boundary)

**신뢰 경계는 TCB의 안과 밖을 가르는 선**이다. 경계를 넘는 모든 상호작용(호출, 데이터 전달, 공유 메모리)은 검증 대상이 된다.

- 경계 밖에서 들어오는 입력은 모두 비신뢰 입력으로 취급하고 검증해야 한다.
- 경계 안에서 밖으로 나가는 데이터는 노출해도 되는 것만 나가야 한다.
- 신뢰 경계가 늘어날수록 격리는 강해질 수 있으나 경계 통과 비용(성능)이 증가한다 — `03_quality_attribute_workshop.md` 4.3절의 보안 vs 성능 상충이 이 지점이다.

같은 시스템이라도 **공격자 모델에 따라 TCB가 달라진다.** "Host 커널 권한까지 가진 공격자"를 가정하면 Host 커널은 TCB가 될 수 없고, "물리 접근 공격자"까지 가정하면 DRAM조차 신뢰할 수 없게 되어 메모리 암호화가 필요해진다. TCB 정의와 공격자 모델 정의가 항상 한 쌍으로 움직이는 이유다(DP-01의 설계질문 1·2번).

---

## 5. ARM 플랫폼에서의 TCB 구조

본 과제 타겟(ARM 기반 커스텀 SoC)에서 TCB 후보가 되는 권한 계층은 다음과 같다.

| 계층 | 구성 요소 | TCB 포함 여부 (pKVM 전제) |
|------|----------|--------------------------|
| EL3 (Secure Monitor) | Secure OS EL3 SPD, SMC 라우팅 | 포함 — 최고 권한, 세계(world) 전환 담당 |
| S-EL1 (Secure World) | TrustZone Secure OS Firmware | 포함 — 키 관리·인증 등 기존 TEE 기능 담당 |
| EL2 (Normal World) | pKVM hypervisor | 포함 — Stage-2 변환 독점 제어, pVM 격리의 신뢰 주체 |
| EL1 (Normal World) | Host Linux 커널 (프레임워크 커널 드라이버 포함) | **비포함** — Host 비신뢰 전제(R-1) |
| EL0 (Normal World) | Host 미들웨어·프레임워크·앱 | **비포함** — 동일 |
| pVM 내부 EL1/EL0 | 게스트 OS·보안 워크로드 | 해당 pVM 자신에 대해서만 신뢰 (도메인 간 상호 비신뢰, QA-02) |

두 가지 주의점이 있다.

1. **TCB는 단일 집합이 아니라 보호 속성별로 다를 수 있다.** 예컨대 pVM 메모리의 기밀성·무결성 TCB는 {EL3, EL2}이지만, 가용성은 Host의 스케줄링에 의존하므로 Host까지 신뢰하지 않으면 보장할 수 없다(`99_trust_boundary_qna.md` 논거 1). DP-01에서 "보호 속성별 의존 메커니즘"을 명시하라는 요구가 여기서 나온다.
2. **HW·펌웨어도 TCB다.** SMMU, Stage-2 MMU 같은 하드웨어 메커니즘과 부트 ROM·부트로더 체인은 암묵적으로 TCB에 포함된다. SW 설계 문서에서 생략되기 쉬우나, 규제 증빙(CONST-04)과 attestation(DP-07) 설계 시에는 명시적으로 드러내야 한다.

---

## 6. 본 과제와의 연결: 무엇이 결정으로 남아 있는가

pKVM 아키텍처가 "Host는 TCB 밖, EL2는 TCB 안"이라는 큰 틀을 결정해 두었지만, 다음은 본 과제의 설계 결정(DP)으로 남아 있다.

| 미결 사항 | 관련 DP |
|----------|---------|
| 본 과제가 개발하는 Host 측 프레임워크·커널 드라이버의 TCB 포함 여부 | DP-01 |
| 별도 서비스 pVM(중재자·검증자·로거 등)을 신설할 경우 그 pVM의 TCB 편입 여부 | DP-01, DP-03, DP-09, DP-11 |
| TrustZone TEE를 신규 구조(키 관리, 이미지 검증, 아이덴티티)의 신뢰 앵커로 쓸 것인지 | DP-06, DP-08, DP-09, DP-10 |
| 보호 속성 범위(기밀성·무결성·가용성)별 TCB 매핑 | DP-01 |
| 권한 집행 컴포넌트의 배치(집행자는 TCB여야 함) | DP-12 |

특히 마지막 항목이 중요하다. **보안 정책을 집행하는 컴포넌트는 정의상 TCB에 들어간다.** 따라서 DP-12에서 권한 집행을 어디에 두는가는 곧 TCB 크기를 얼마나 키우는가의 결정이며, "TCB 최소화" 원칙과 "EL2 수정 불가(CONST-02)" 제약 사이에서 집행 위치(TrustZone TEE, 별도 서비스 pVM 등)를 선택하는 문제가 된다.

---

## 참고 자료

- DoD 5200.28-STD, "Trusted Computer System Evaluation Criteria (TCSEC, Orange Book)", 1985 — TCB 정의의 원전
- J. P. Anderson, "Computer Security Technology Planning Study", ESD-TR-73-51, 1972 — reference monitor 3요건
- J. H. Saltzer, M. D. Schroeder, "The Protection of Information in Computer Systems", Proceedings of the IEEE, 1975 — economy of mechanism 등 보호 메커니즘 설계 원칙
- Will Deacon et al., "Protecting the Protected: Building a Protected KVM Hypervisor", Linux Security Summit NA 2021 — pKVM의 TCB 최소화 설계
- ARM Architecture Reference Manual — Exception Level, Stage-2 Address Translation, TrustZone
