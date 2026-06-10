# 과제 소개

## 과제명: 로봇용 커스텀 SoC를 위한 pKVM 기반 확장형 보안 프레임워크 개발

> 구 과제명: Linux pKVM 기반 가상화 보안 플랫폼 개발
> 2026-05-29 리뷰 회의 결정에 따라 타겟(커스텀 SoC), 타겟 산업군(로봇), 핵심 키워드(확장성)가 드러나도록 과제명을 변경함.

---

## 1. 배경 및 필요성

### 1.1 타겟 산업군: 로봇

지능형 로봇은 카메라 영상 인식과 온디바이스 AI 추론을 핵심 기능으로 하는 대표적인 Linux 기반 디바이스다. 로봇 제조사들은 차별화된 성능·전력 효율을 위해 ISP(영상 처리), NPU(AI 추론) 등 전용 HW IP를 탑재한 **커스텀 SoC**를 채택하고 있으며, 커스텀 SoC 사업의 주요 성장 분야로 로봇 산업이 부상하고 있다.

동시에 로봇은 가정·공장 내부의 영상과 행동 데이터를 상시 수집하는 특성상, 보안 사고 발생 시 피해가 직접적이다.

- 2024년 Ecovacs Deebot X2 로봇 청소기 해킹 — 카메라·스피커 무단 원격 제어로 가정 내부 영상 노출 [A]
- 2025년 국내 IP카메라 12만 대 해킹 — 가정 내 영상 무단 접근·유출 [C]
- 스마트 디바이스 대상 공격 하루 평균 82만 건(2025년 기준), 제조 분야 침해 사고당 평균 비용 $5.56M [F][G]

로봇 제조사 입장에서 **카메라 영상과 AI 모델·데이터의 보호는 제품 출시의 전제 조건**이 되고 있으며, GDPR·개인정보보호법 등 규제 또한 영상·생체 데이터 처리 과정의 기술적 격리를 요구하고 있다.

### 1.2 진입 장벽: Linux 커스텀 SoC용 보안 실행 환경 솔루션의 부재

로봇용 커스텀 SoC 시장에 진입하기 위해서는 위 보호 요구를 충족하는 보안 실행 환경을 SoC와 함께 제공해야 한다. 그러나 현재 솔루션 지형에는 공백이 존재한다.

| 환경 | 보안 실행 환경 | 비고 |
|------|---------------|------|
| Android 스마트폰 | AVF (pKVM 기반, Android 12+) | Android 스택에 종속 |
| Linux 서버/클라우드 | Confidential Computing (SEV, TDX 등) | 서버용 CPU 전용, 임베디드 SoC 미지원 |
| **Linux 기반 로봇 커스텀 SoC** | **ARM TrustZone 단독 (구조적 한계 존재)** | **본 과제의 대상 영역** |

로봇 제품의 대부분은 Android가 아닌 **Linux(Yocto, Ubuntu 등) 기반**으로 개발된다. 즉, Android AVF는 사용할 수 없고, TrustZone 단독으로는 후술할 구조적 한계(3.1절)로 요구를 충족할 수 없다.

> **문제 정의**: 로봇용 커스텀 SoC 사업 진입에 필요한 "Linux 환경의 확장 가능한 보안 실행 환경" 솔루션이 부재하다. 본 과제는 이 공백을 메우는 프레임워크를 개발한다.

---

## 2. 타겟 레퍼런스 시나리오: Secure Vision AI

### 2.1 시나리오 정의

타겟 산업군(로봇)의 핵심 기능인 **Secure Camera와 Secure AI를 결합한 단일 파이프라인**을 레퍼런스 시나리오로 선정한다.

**시나리오**: 로봇의 카메라 영상이 캡처부터 AI 추론·판단까지 전 구간에서 Host OS로부터 격리된 채 처리된다. Host OS가 침해되더라도 영상 원본, AI 모델 가중치, 추론 중간 데이터는 노출되지 않으며, 격리 영역 밖으로는 판단 결과만 전달된다.

```
┌─────────────────────────────────────────────────────────────────┐
│                  Secure Vision AI 파이프라인                      │
│                                                                 │
│  Camera        ┌──────────────────┐   ┌──────────────────┐      │
│  Sensor ─────► │ Secure Camera    │──►│ Secure AI        │      │
│                │ 격리 도메인       │   │ 격리 도메인       │      │
│                │  - ISP HW IP     │   │  - NPU HW IP     │      │
│                │  - 영상 캡처/전처리│   │  - 모델 가중치    │      │
│                └──────────────────┘   │  - AI 추론        │      │
│                                       └────────┬─────────┘      │
│   · 영상 원본, 모델, 중간 데이터:                 │ 판단 결과만     │
│     Host OS 접근 불가                            ▼               │
│                                       ┌──────────────────┐      │
│                                       │ Host OS (Linux)  │      │
│                                       │ 로봇 제어 App     │      │
│                                       └──────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

활용 예: 가정용 로봇의 실내 영상 기반 상황 인식, 제조 로봇의 고객 제품 설계 데이터를 다루는 품질 검사 AI 등.

### 2.2 시나리오가 요구하는 기술 요구사항

| ID | 요구사항 | 설명 |
|----|---------|------|
| R-1 | **Host 비신뢰 격리** | Host OS(Linux 커널 포함)가 침해되어도 영상·모델·추론 데이터에 접근 불가해야 함 |
| R-2 | **고성능 연산 자원** | 실시간 영상 처리와 AI 추론이 가능한 수준의 메모리·연산 자원을 격리 영역에서 사용 가능해야 함 |
| R-3 | **HW IP의 격리 도메인 할당** | ISP, NPU 등 HW IP를 격리 도메인에 안전하게 할당하여 HW 가속을 사용해야 함 (SW 처리로는 실시간성 미충족) |
| R-4 | **다중 격리 도메인 동시 운용** | Secure Camera 도메인과 Secure AI 도메인을 독립적으로 동시에 생성·운용해야 함 |
| R-5 | **동적 확장성** | 로봇 기능 추가에 따라 새로운 보안 워크로드를 펌웨어 재배포 없이 동적으로 추가할 수 있어야 함 |
| R-6 | **기존 Secure OS 상호운용** | 키 관리·인증 등 기존 TrustZone Secure OS 기반 기능과 공존·연동해야 함 |

---

## 3. 기존 기술의 한계

위 요구사항(R-1~R-6)을 기준으로 기존 기술을 평가한다.

### 3.1 ARM TrustZone 단독 구조의 한계

현재 Linux 환경에서는 ARM TrustZone 기반의 보안 아키텍처가 사용되고 있다.

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

| 한계 | 설명 | 위배 요구사항 |
|------|------|--------------|
| **이진 격리 구조** | REE/TEE 두 영역만 존재. Secure Camera·Secure AI 등 다수의 독립 보안 도메인을 동시에 생성 불가 | R-4 |
| **TEE 자원 제약** | S-EL1 환경은 메모리·연산 자원이 제한적. AI 추론 등 고수준 작업 처리 부적합 | R-2 |
| **HW IP의 REE 종속** | ISP·NPU 등 HW 가속 IP가 REE 영역에서 사용되어 격리 도메인에 할당 불가 | R-3 |
| **동적 확장 불가** | TEE 펌웨어 바이너리로만 배포. 신규 요구사항 발생 시 펌웨어 수정·재배포 필요 | R-5 |

### 3.2 일반 Linux KVM의 한계 — pKVM 도입의 기술적 근거

Linux의 표준 가상화인 KVM은 일반적으로 VHE 모드로 동작하며, Host 커널이 EL2 권한을 직접 보유한다.

| 구분 | VHE (일반 KVM) | nVHE (pKVM) |
|------|----------------|-------------|
| 도입 | ARMv8.1 (FEAT_VHE) | ARMv8.0 |
| Host OS 실행 위치 | EL2 (Host Kernel이 EL2 권한 직접 보유) | EL1 (Host OS는 EL1에서만 실행) |
| Hypervisor TCB | 크다 (Host OS 코드가 EL2 포함) | 작다 (소형 HV 코드만 EL2에 상주) |
| 보안 격리 | **Host 침해 시 HV도 침해됨** | Host OS가 EL2 코드·레지스터에 접근 불가 |
| 주 목적 | VM Entry/Exit 오버헤드 감소 (성능 우선) | Hypervisor 신뢰 경계 유지 (보안 우선) |

일반 KVM(VHE)에서는 Host 커널이 침해되면 Hypervisor와 모든 VM의 메모리가 함께 노출된다. 즉 **"Host OS를 신뢰하지 않는다"는 R-1을 구조적으로 충족할 수 없다.** 반면 pKVM은 nVHE 모드에서 소형 Hypervisor만 EL2에 상주시키고 Stage-2 Page Table 변환(IPA→PA)을 Hypervisor가 독점 제어하므로, Host가 침해되어도 pVM(protected VM)의 메모리 격리가 유지된다. 이것이 기존 Linux KVM이 아닌 **pKVM을 도입해야 하는 기술적 근거**다.

> 근거: ARM Architecture Reference Manual ARMv8-A — D1.2.2 Virtualization Host Extensions (FEAT_VHE); Will Deacon et al., "Protecting the Protected: Building a Protected KVM Hypervisor", Linux Security Summit NA 2021

### 3.3 Android AVF의 한계 — 본 과제의 차별화 지점

pKVM을 상용화한 Android AVF(Android 12+, Pixel 6부터 적용)가 존재하지만, 본 과제의 대상 영역에는 적용할 수 없다.

| 한계 | 설명 | 위배 요구사항 |
|------|------|--------------|
| **Android 스택 종속** | VirtualizationService 등 핵심 컴포넌트가 Android 시스템 서비스에 종속. Linux(Yocto 등) 기반 로봇 커스텀 SoC에 사용 불가 | 적용 자체 불가 |
| **Secure OS 확장 구조 부재** | Microdroid 중심 설계로, 다양한 서드파티 Secure OS를 pVM으로 탑재·교체하는 확장 구조를 제공하지 않음 | R-5 |
| **TrustZone 연동 제한** | 기존 Secure OS 기반 TEE 기능과의 상호운용이 제한적 | R-6 |

> 본 과제는 AVF의 Linux 포팅이 아니라, **AVF가 제공하지 못하는 기능 — Linux 네이티브 동작, 다양한 Secure OS 수용, TrustZone 완전 공존 — 을 갖춘 독자 프레임워크**를 설계·구현하는 것이다.

### 3.4 요구사항 충족 매트릭스

| 요구사항 | TrustZone 단독 | Linux KVM (VHE) | Android AVF | **본 과제** |
|---------|:---:|:---:|:---:|:---:|
| R-1 Host 비신뢰 격리 | 충족 | **미충족** | 충족 | 충족 |
| R-2 고성능 연산 자원 | **미충족** | 충족 | 충족 | 충족 |
| R-3 HW IP 격리 할당 | **미충족** | 부분 | 부분 | 충족 |
| R-4 다중 격리 도메인 | **미충족** | 충족 | 충족 | 충족 |
| R-5 동적 확장성 | **미충족** | 충족 | **부분** (Microdroid 중심) | 충족 |
| R-6 Secure OS 상호운용 | 충족 | 충족 | **제한적** | 충족 |
| Linux 커스텀 SoC 적용 | 가능 | 가능 | **불가** | 가능 |

---

## 4. 해결 방향: 확장성 중심의 pKVM 기반 보안 프레임워크

pKVM이 제공하는 것은 Stage-2 기반 메모리 격리라는 **메커니즘**뿐이다. 레퍼런스 시나리오를 실현하려면 그 위에 다음을 갖춘 프레임워크가 필요하며, 이것이 본 과제의 개발 대상이다.

| 구성요소 | 역할 | 대응 요구사항 |
|---------|------|--------------|
| pVM 생명주기 관리 프레임워크 | pVM 생성·실행·종료·자원 관리를 담당하는 Linux 네이티브 미들웨어 | R-1, R-4 |
| HW IP 할당·공유 구조 | ISP·NPU 등 HW IP를 격리 도메인에 안전하게 할당하는 커널 드라이버 및 인터페이스 | R-2, R-3 |
| 워크로드 확장 구조 | 신규 보안 워크로드·서드파티 Secure OS를 프레임워크 수정 없이 pVM으로 탑재하는 플러그인형 구조 | R-5 |
| TrustZone 공존 계층 | 기존 Secure OS 기반 기능(키 관리·인증)과의 연동 인터페이스 | R-6 |

핵심 설계 키워드는 **확장성(Extensibility)** 이다. 단일 시나리오 전용 솔루션이 아니라, Secure Vision AI를 첫 레퍼런스로 검증하되 이후 시나리오(개인정보 처리, 펌웨어 보호 등)를 프레임워크 수정 없이 수용하는 구조를 목표로 한다.

---

## 5. 과제 개요 및 범위

### 5.1 과제 개요

| 항목 | 내용 |
|------|------|
| 과제명 | 로봇용 커스텀 SoC를 위한 pKVM 기반 확장형 보안 프레임워크 개발 |
| 과제목적 | 로봇용 커스텀 SoC의 Linux 환경에서 Secure Vision AI 시나리오를 지원하는, Stage-2 메모리 격리 기반의 확장 가능한 보안 프레임워크 개발 |
| 타겟 | 커스텀 SoC (로봇 산업군), Linux 기반 |
| 레퍼런스 시나리오 | Secure Vision AI (Secure Camera + Secure AI 결합 파이프라인) |
| 참여인력 | Security파트 9명, HV파트 3명, 해외 SRCX연구소 5명 |
| 기간 | 2026-01-07 ~ 2026-10-30 (10개월) |
| 역할 | Sub Leader, SW Architect |

### 5.2 과제 범위

| 구분 | 항목 |
|------|------|
| **포함** | pVM 생명주기 관리 미들웨어·프레임워크 개발 |
| **포함** | pVM 제어 및 HW IP 할당을 위한 커널 드라이버 개발 |
| **포함** | Secure Vision AI 레퍼런스 시나리오 End-to-End 통합·검증 |
| **포함** | 기존 TrustZone Secure OS와의 공존 인터페이스 |
| **제외** | pKVM 커널(EL2 Hypervisor) 자체 포팅 — 기 포팅된 pKVM 커널을 전제로 함 |
| **제외** | Secure OS 자체 개발, HW IP(ISP·NPU) 하드웨어 설계 |

> 2026-05-29 리뷰 회의 결정: pKVM 포팅은 범위에서 제외하고, 이를 제어하는 상위 커널 드라이버·미들웨어·프레임워크 개발에 집중한다.

---

## 6. 과제 목표

### 6.1 최종 목표

**로봇용 커스텀 SoC의 Linux 환경에서, Secure Vision AI 시나리오를 시작으로 다양한 보안 워크로드를 프레임워크 수정 없이 수용할 수 있는 pKVM 기반 확장형 보안 프레임워크를 개발한다.**

### 6.2 세부 목표

| # | 목표 | 상세 |
|---|------|------|
| G-1 | **Linux 네이티브 pVM 관리 프레임워크 개발** | Android 스택 의존 없이 Linux에서 동작하는 pVM 생명주기 관리 프레임워크 개발 |
| G-2 | **Secure Vision AI 레퍼런스 시나리오 지원** | 카메라 캡처(ISP)부터 AI 추론(NPU)까지 전 구간이 Host OS로부터 격리된 End-to-End 파이프라인 동작 |
| G-3 | **확장 가능한 워크로드 수용 구조 확보** | 신규 보안 워크로드 및 다양한 Secure OS를 프레임워크 수정 없이 pVM으로 탑재 가능한 구조 (Android AVF 미제공 기능) |
| G-4 | **기존 ARM TrustZone 완전 지원** | 기존 Secure OS 기반 TEE 기능과의 상호운용성 보장 |

### 6.3 주요 품질 목표 (TBD — Design Point 도출 후 확정)

품질 목표의 세부 지표와 수치는 Bottom-up 설계 접근(DP 추출 → 핵심 DP 선정)에 따라 핵심 DP 확정 후 재정비한다. 현 시점의 방향은 다음과 같다.

| 품질 속성 | 방향 | 근거 |
|----------|------|------|
| **성능** | Secure Vision AI 파이프라인이 실시간 처리 요건 충족 (CPU/메모리 오버헤드 네이티브 대비 5% 이내, I/O 10% 이내 수준) | ACM SAC 2024 — pVM 워크로드 오버헤드 측정 연구 |
| **가용성** | 단일 pVM 장애 시 Host 및 타 pVM 무중단 | Stage-2 격리의 기술적 특성 |
| **보안** | Host OS 침해 시에도 pVM 메모리 접근 차단 유지 | Stage-2 Page Table 기반 격리 |
| **변경 용이성** | 신규 보안 워크로드 추가 시 프레임워크 코드 무수정 | 플러그인형 확장 구조 (G-3) |

> 성능 근거: Wei et al., "Measuring and Optimizing the Performance of the Android Virtualization Framework", ACM SAC 2024 — [https://dl.acm.org/doi/abs/10.1145/3605098.3636097](https://dl.acm.org/doi/abs/10.1145/3605098.3636097)

---

## 참고 자료

### 보안 사고 사례 출처

| 기호 | 출처 |
|------|------|
| [A] | Malwarebytes, "Robot vacuum cleaners hacked to spy on, insult owners" — Ecovacs Deebot X2 카메라·스피커 무단 원격 제어 사례 (2024.10) (https://www.malwarebytes.com/blog/news/2024/10/robot-vacuum-cleaners-hacked-to-spy-on-insult-owners) |
| [C] | 경향신문, "'혹시 우리집 홈캠 영상도?'···12만대 해킹해 성 착취물 제작·판매한 4명 검거" — 국내 홈캠 해킹 사건 (https://www.khan.co.kr/article/202511301029001) |
| [F] | DeepStrike, "Compromised Devices Statistics 2024–2025: Breach Costs" — Forrester Research 인용 (https://deepstrike.io/blog/compromised-devices-statistics-2024-2025) |
| [G] | IBM, "Cost of a Data Breach Report 2024" — 산업 분야 평균 침해 비용 $5.56M (https://www.ibm.com/reports/data-breach) |

### 기술 참고

- Android Virtualization Framework (AVF) — Android Open Source Project
- ARM Architecture Reference Manual — EL2 / Stage-2 Address Translation
- ARM Architecture Reference Manual ARMv8-A — D1.2.2 Virtualization Host Extensions (FEAT_VHE)
- Will Deacon et al., "Protecting the Protected: Building a Protected KVM Hypervisor", Linux Security Summit NA 2021
- Wei et al., "Measuring and Optimizing the Performance of the Android Virtualization Framework", ACM SAC 2024
- Confidential Computing Consortium, "Confidential Computing as a Strategic Imperative for Secure AI" (https://confidentialcomputing.io/2025/12/03/new-study-finds-confidential-computing-emerging-as-a-strategic-imperative-for-secure-ai-and-data-collaboration/)
