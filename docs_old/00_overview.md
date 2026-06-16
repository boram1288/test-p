# 과제 소개

## 과제명: Linux pKVM 기반 가상화 보안 플랫폼 개발

---

## 1. 배경 및 필요성

### 1.1 로봇/스마트 디바이스/자동차 분야의 사이버보안 위협 현황

지능형 로봇, 연결형 스마트 디바이스, 자동차의 확산으로 사이버 공격의 규모와 피해가 급증하고 있다.

#### 주요 보안 사고 사례

| 연도 | 분야 | 사례 | 피해 | 출처 |
|------|------|------|------|------|
| 2024 | 로봇 | Ecovacs Deebot X2 로봇 청소기 해킹 — 카메라·스피커 무단 원격 제어 | 사생활 침해, 제품 신뢰도 손상 | [A] |
| 2025 | 자동차 | 차량 원격 제어 공격 — 텔레매틱스 취약점 통해 차량 제어권 탈취, 랜섬 요구 | 차 문·창문·시동 원격 조작 | [B] |
| 2025 | 스마트 디바이스 | 국내 홈캠 12만 대 해킹 — 가정집 IP카메라 무단 접근, 성 착취물 제작·해외 사이트 판매 | 피해 기기 **12만 대**, 피해 장소 58곳 확인, 일당 4명 검거 | [C] |

#### 공격 규모

- 2025년 기준 스마트 디바이스 대상 공격: **하루 평균 82만 건** [F]
- 전 세계 사이버범죄 피해 규모: **연간 $10.5조** (2025년 전망) [E]

---

### 1.2 보안사고 비용과 사업적 영향

보안사고로 인한 피해 비용은 단순 IT 복구 비용을 훨씬 초과하며, 사업 매출 대비 무시할 수 없는 비중을 차지한다.

#### 로봇/스마트 디바이스/자동차 분야 보안사고 비용

| 분야 | 사고당 평균 비용 | 출처 |
|------|----------------|------|
| 스마트 디바이스 침해 (일반) | **$5M ~ $10M** (전통 IT 사고 대비 2배 이상) | [F] Forrester Research, DeepStrike 2024 |
| 제조업 로봇/IIoT 침해 | **$5.56M** (2024, 산업 분야 평균) | [G] IBM Cost of a Data Breach Report 2024 |
| 자동차 공급망 사고 (CDK Global) | **$10.2억** (2024, 단일 공급망 사고) | [H] Breached.company, Automotive Industry Siege Report 2025 |
| 글로벌 평균 (전 산업) | **$4.88M** (2024) | [I] IBM Cost of a Data Breach Report 2024 |
| 미국 평균 | **$10.22M** (법적·규제 페널티 포함) | [I] IBM Cost of a Data Breach Report 2024 |

#### 사업 매출 대비 보안사고 비용 비중

```
보안 사고 1건 발생 시 항목별 예상 손실 (연 매출 1조 원 기준):

  직접 피해(복구·보상):   연 매출의 약 0.75%
    (IBM Cost of a Data Breach 2024 — 산업 분야 평균 $5.56M)

  생산 중단:              연 매출의 약 2.8%
    (Comparitech 2024 — 제조업 랜섬웨어 $1.9M/일 × 평균 11일)

  공급망 손실:            직접 손실 대비 최대 4배
    (SOCRadar, Hidden Cost of Supply Chain Breaches 2025 — NotPetya 공급망 피해 연구 인용)

  브랜드 신뢰도 손상:     연 매출의 약 3~7%
    (IBM Cost of a Data Breach 2024 — 침해 후 고객 이탈 3~7% 증가)

  → 합산 시 연 매출의 약 6.5% 이상,
    공급망 포함 대형 사고 시 22% 이상으로 급등 가능
```

> 로봇·스마트 디바이스·자동차 분야의 보안사고는 **생산 라인 중단, 제품·차량 리콜, 개인정보 유출에 따른 법적 제재, 브랜드 신뢰 붕괴**로 연결되어 단발성 IT 사고를 훨씬 초과하는 사업적 손실을 유발한다.

---

### 1.3 다양화되는 보안 시나리오

로봇·스마트 디바이스·자동차가 처리하는 데이터와 연산의 민감도가 높아짐에 따라, 보호해야 할 보안 시나리오가 복잡·다양화되고 있다.

#### 주요 보안 시나리오

**① Secure AI (기밀 AI 연산)**
- 로봇·모바일 내 AI 모델이 추론(Inference) 과정에서 모델 가중치·사용자 데이터 노출 위험
- 의료·금융 데이터 기반 AI 학습 시 PII(개인식별정보) 포함 데이터의 기밀성 보장 필요
- 실례: 제조 로봇의 품질 검사 AI가 고객 제품 설계 데이터를 처리할 때 격리 실행 환경 필요

**② Secure Camera (영상 스트림 보호)**
- 로봇·스마트 디바이스 카메라 영상이 메모리에서 무단 접근되거나 가로채지는 시나리오
- 실례: 가정용 로봇 청소기 카메라 해킹으로 내부 영상이 무단 전송된 사례 (2024)
- 카메라 드라이버부터 AI 처리 파이프라인 전 구간에 걸친 격리 환경 필요

**③ 개인정보 활용 보호 (Privacy-Preserving Computation)**
- 로봇·스마트 디바이스·자동차가 수집하는 생체 정보(지문, 홍채, 음성), 위치 정보의 안전한 처리 필요
- GDPR, 국내 개인정보보호법 등 규제 강화로 데이터 처리 과정의 법적 격리 요건 증가

**④ 펌웨어 역분석 및 런타임 탈취 방지**
- 펌웨어 바이너리가 Host OS에 노출될 경우 독점 알고리즘, 인증 로직 탈취 위험
- 런타임 메모리·시스템 로그·디버그 출력을 Host OS로부터 격리하여 실행 중 민감 데이터 노출 차단 필요
- 실례: 자동차 ECU 펌웨어 리버싱으로 인증 우회 키 추출 시도
- pVM 격리 실행 환경으로 바이너리·런타임 상태·로그를 Host OS 접근으로부터 완전 차단

---

### 1.4 기존 Linux 솔루션의 한계

현재 Linux 환경에서는 ARM TrustZone 기반의 보안 아키텍처가 사용되고 있으나, 다양화되는 보안 시나리오를 완전히 수용하기에는 구조적 한계가 존재한다.

#### 기존 ARM TrustZone 기반 보안 아키텍처

```
┌───────────────────────────────────────────────────────────────┐
│                     ARM Exception Level 구조                   │
│                                                               │
│  Normal World (REE)              │  Secure World (TEE)        │
│───────────────────────────────────────────────────────────────│
│  EL0: App /                      │  S-EL0: Secure OS          │
│       Secure OS Client Library   │         Internal Library   │
│  ──────────────────────────────  │  ────────────────────────  │
│  EL1: Linux Kernel +             │  S-EL1: Secure OS Firmware │
│       Secure OS Kernel Driver    │                            │
│       (baremetal / pv-front /    │                            │
│        pv-backend)               │                            │
│  ──────────────────────────────  │  ────────────────────────  │
│  EL2: Hypervisor                 │                            │
│                                  │                            │
│  ───────────────────────────────────────────────────────────  │
│                   S-EL3: Secure OS EL3 SPD                    │
│                       (Secure Monitor)                        │
│  ──────────────────────────────  │                            │
│  HW IP                           │                            │
│    ┌──────────┐  ┌──────────┐    │                            │
│    │ ISP      │  │ NPU      │    │                            │
│    │ HW IP    │  │ HW IP    │    │                            │
│    └──────────┘  └──────────┘    │                            │
└───────────────────────────────────────────────────────────────┘
```

- Hypervisor가 REE EL2에 위치하며, Secure OS가 TEE를 담당
- Secure OS는 GP Client/Internal API를 REE·TEE 양측에서 지원
- 어플리케이션의 HW가속을 위한 HW IP는 REE영역에서 사용

#### 기존 구조의 한계

| 한계 | 설명 |
|------|------|
| **이진 격리 구조** | REE/TEE 두 영역만 존재. Secure AI·Secure Camera 등 다수의 독립 보안 도메인을 **동시에 생성 불가** |
| **TEE 자원 제약** | S-EL1 환경은 메모리·연산 자원이 제한적. AI 추론 등 **고수준 작업 처리 부적합** |
| **동적 확장 불가** | TEE 펌웨어 바이너리로만 배포. 새로운 요구사항으로 변경 필요할 시에 TEE 펌웨어 수정·재배포 필요. **유연성 부족** |

> ARM TrustZone 단독으로는 다양한 보안 시나리오에 대응할 수 없다.

---

## 2. 기술 현황

### 2.1 Android AVF vs. Linux 현황 비교

| 구분 | Android (AVF) | Linux (현재) |
|------|---------------|-------------|
| HV 위치 | EL2 (pKVM, nVHE) | EL2 (Hypervisor) |
| Stage-2 기반 메모리 격리 | 지원 (pVM 단위) | **미지원** |
| 가상화 플랫폼 | AVF (통합 관리) | **없음** |
| 동적 워크로드 격리 | 지원 | **미지원** |
| 기존 TrustZone 연동 | 제한적 | 완전 지원 |

### 2.2 pKVM 기술 개요

- ARM Cortex-A의 EL2에서 **nVHE(Non-VHE) 모드**로 동작
- nVHE 모드: Host OS(EL1)가 Hypervisor(EL2)에 직접 접근 불가 — Hypervisor 자체가 신뢰 경계
- **Stage-2 Page Table**: IPA(Intermediate Physical Address) → PA(Physical Address) 변환을 HV가 독점 제어, pVM 간·pVM↔Host 간 물리 메모리 접근 완전 차단
- Android 12 (Pixel 6, ARM) 부터 상용 적용

#### nVHE 모드 부가 설명

ARM Cortex-A는 EL2 동작 방식으로 VHE와 nVHE 두 가지를 제공한다.

| 구분 | VHE (Virtualization Host Extensions) | nVHE (Non-VHE) |
|------|--------------------------------------|----------------|
| 도입 | ARMv8.1 (FEAT_VHE) | ARMv8.0 |
| Host OS 실행 위치 | EL2 (Host Kernel이 EL2 권한 직접 보유) | EL1 (Host OS는 EL1에서만 실행) |
| Hypervisor TCB | 크다 (Host OS 코드가 EL2 포함) | 작다 (소형 HV 코드만 EL2에 상주) |
| 보안 격리 | Host 침해 시 HV도 위협받음 | Host OS가 EL2 코드·레지스터에 접근 불가 |
| 주 목적 | VM Entry/Exit 오버헤드 감소 (성능 우선) | Hypervisor 신뢰 경계 유지 (보안 우선) |

pKVM은 Host OS로부터 pVM을 격리하는 보안 목적을 위해 **성능보다 보안을 우선하여 nVHE를 채택**하였다. EL2에는 pKVM 코드만 상주하며, Host OS(Android)가 침해되더라도 EL2의 신뢰 경계와 pVM 메모리 격리가 유지된다.

> 근거: ARM Architecture Reference Manual ARMv8-A — D1.2.2 Virtualization Host Extensions (FEAT_VHE); Will Deacon et al., "Protecting the Protected: Building a Protected KVM Hypervisor", Linux Security Summit NA 2021

---

## 3. 과제 개요

| 항목 | 내용 |
|------|------|
| 과제명 | Linux pKVM 기반 가상화 보안 플랫폼 개발 |
| 과제목적 | Hypervisor의 Stage-2 Page Table 기반 메모리 격리를 제공하는 가상화 Linux 플랫폼 개발 |
| 참여인력 | Security파트 9명, HV파트 3명, 해외 SRCX연구소 5명 |
| 기간 | 2026-01-07 ~ 2026-10-30 (10개월) |
| 역할 | Sub Leader, SW Architect |

---

## 4. 과제 목표

### 4.1 최종 목표

**ARM TrustZone의 이진 격리 구조 한계를 극복하고, Linux 환경에서 Stage-2 Page Table 기반 다중 격리 도메인을 통해 다양한 보안 시나리오에 대응하는 가상화 플랫폼을 개발한다.**

> ※ 본 과제는 Android AVF를 Linux로 포팅하는 작업이 아니며, Linux에 최적화된 독자적인 가상화 Framework를 설계·구현하는 것이다.

### 4.2 세부 목표

| # | 목표 | 상세 |
|---|------|------|
| G-1 | **Linux 전용 가상화 Framework 개발** | pKVM 기반으로 Linux에서 동작하는 pVM 생명주기 관리 Framework 개발 |
| G-2 | **가상화 플랫폼 역할 수행** | Secure AI, Secure Camera 등 다양한 보안 워크로드를 가상화 환경에서 동작 지원하는 플랫폼 |
| G-3 | **Android AVF 대비 품질 우위 확보** (TBD) | 성능, 가용성, 보안, 변경 용이성 4개 품질 지표에서 AVF를 상회 |
| G-4 | **기존 ARM TrustZone 완전 지원** | 기존 Secure OS 기반 TEE 기능과의 상호운용성 보장 |

### 4.3 주요 품질 목표 (TBD)

| 품질 속성 | 세부 지표 | 목표 | AVF 대비 | 근거 |
|----------|----------|------|----------|------|
| **성능** | CPU/메모리 집약 워크로드 오버헤드 | 네이티브 Linux 대비 **5% 이내** | 동등 | ACM SAC 2024 — AVF pVM은 CPU/메모리 워크로드에서 이미 오버헤드 낮음 |
| **성능** | I/O 집약 워크로드 오버헤드 | 네이티브 Linux 대비 **10% 이내** | 우세 | ACM SAC 2024 — SWIOTLB 최적화 시 8~22% 개선 확인 |
| **성능** | pVM 부팅 시간 | **1초 이내** | 우세 | Android Blog 2022 — AVF Microdroid 부팅 시간 측정 참고 |
| **성능** | Host-pVM RPC 레이턴시 | **100μs 이내** | 동등 | Linux vsock 기반 IPC 레이턴시 수준 |
| **가용성** | pVM 장애 격리 | pVM 장애 시 Host 및 타 pVM 무중단 | 동등 | Stage-2 메모리 격리의 기술적 특성상 단일 pVM 장애가 타 영역에 전파되지 않음 |
| **보안** | 메모리 격리 | Host OS → pVM 메모리 접근 차단 | 동등 | Stage-2 Page Table 기반 메모리 격리 보장 |
| **변경 용이성** | 시나리오 확장 | 신규 보안 시나리오 추가 시 Framework 무수정 | 우세 | Linux 전용 Framework로 Android보다 종속성 없이 자유로운 확장 가능 |

> 성능 목표 근거: Wei et al., "Measuring and Optimizing the Performance of the Android Virtualization Framework", ACM SAC 2024 — [https://dl.acm.org/doi/abs/10.1145/3605098.3636097](https://dl.acm.org/doi/abs/10.1145/3605098.3636097)

---

## 참고 자료

### 보안 사고 사례 출처

| 기호 | 출처 |
|------|------|
| [A] | Malwarebytes, "Robot vacuum cleaners hacked to spy on, insult owners" — Ecovacs Deebot X2 카메라·스피커 무단 원격 제어 사례 (2024.10) (https://www.malwarebytes.com/blog/news/2024/10/robot-vacuum-cleaners-hacked-to-spy-on-insult-owners) |
| [B] | Autoblog, "Ransomware in Cars: Why Automotive Cyberattacks Are Spiking in 2025" — 차량 원격 제어 공격 (https://www.autoblog.com/news/ransom-automotive-cyber-attacks-increase-2025) |
| [C] | 경향신문, "'혹시 우리집 홈캠 영상도?'···12만대 해킹해 성 착취물 제작·판매한 4명 검거" — 국내 홈캠 해킹 사건 (https://www.khan.co.kr/article/202511301029001) |
| [D] | Bitdefender, "2025 IoT Security Landscape Report" — 2025년 IoT 보안 위협 동향 보고서 (https://blogapp.bitdefender.com/hotforsecurity/content/files/2025/10/2025_iot_security_report.pdf) |
| [E] | Varonis, "139 Cybersecurity Statistics and Trends" — 사이버범죄 연간 피해 전망 (https://www.varonis.com/blog/cybersecurity-statistics) |

### 보안사고 비용 출처

| 기호 | 출처 |
|------|------|
| [F] | DeepStrike, "Compromised Devices Statistics 2024–2025: Breach Costs" — Forrester Research 인용 (https://deepstrike.io/blog/compromised-devices-statistics-2024-2025) |
| [G] | IBM, "Cost of a Data Breach Report 2024" — 산업 분야 평균 침해 비용 $5.56M (https://www.ibm.com/reports/data-breach) |
| [H] | Breached.company, "The Automotive Industry Under Siege" — CDK Global 피해액 (https://breached.company/the-automotive-industry-under-siege-how-ransomware-and-supply-chain-attacks-devastated-major-carmakers-in-2024-2025/) |
| [I] | IBM, "Cost of a Data Breach Report 2024" — 글로벌/미국 평균 침해 비용 (https://www.ibm.com/reports/data-breach) |

### 기술 참고

- Android Virtualization Framework (AVF) — Android Open Source Project
- ARM Architecture Reference Manual — EL2 / Stage-2 Address Translation
- ARM Architecture Reference Manual ARMv8-A — D1.2.2 Virtualization Host Extensions (FEAT_VHE)
- Will Deacon et al., "Protecting the Protected: Building a Protected KVM Hypervisor", Linux Security Summit NA 2021
- Android Blog, "Android Virtualization Framework: Microdroid boot time measurements" (2022)
- Confidential Computing Consortium, "Confidential Computing as a Strategic Imperative for Secure AI" (https://confidentialcomputing.io/2025/12/03/new-study-finds-confidential-computing-emerging-as-a-strategic-imperative-for-secure-ai-and-data-collaboration/)
