# 과제 소개

## 과제명: 로봇용 Secure Vision AI를 위한 Linux pKVM 기반 가상화 보안 Framework 개발

---

## 1. 배경 및 필요성

### 1.1 타겟 산업군: 커스텀 SoC 사업의 로봇 확장

차별화된 성능·전력 효율을 위해 ISP(영상 처리)·NPU(AI 추론) 등 전용 HW IP를 집적한 **커스텀 SoC** 사업은 모바일·자동차를 거쳐 **로봇 산업으로 확장**되고 있다. 지능형 로봇은 카메라 영상 인식과 온디바이스 AI 추론을 핵심 기능으로 하며, 이를 실시간·저전력으로 처리하기 위해 전용 HW IP를 집적한 커스텀 SoC를 채택한다. 즉 **로봇은 커스텀 SoC 사업의 핵심 성장 타겟군**이다.

여기서 주목할 구조적 특징은 OS 환경이다. Android가 지배하는 스마트폰과 달리, 로봇 제품의 대부분은 **Linux(Yocto, Ubuntu 등) 기반**으로 개발된다. 따라서 로봇용 커스텀 SoC 사업에 진입하려면 Android가 아닌 **Linux 환경에서 동작하는 솔루션**을 SoC와 함께 제공해야 한다.

> 핵심: 로봇은 커스텀 SoC 사업의 핵심 성장 타겟군이며, 그 주 OS는 Linux다.

### 1.2 보안 위협의 현실화

로봇은 가정·공장 내부의 영상과 행동 데이터를 상시 수집하는 특성상, 보안 사고 발생 시 피해가 직접적이다. 그리고 이러한 침해는 이미 다수 보고되고 있다.

- 2024년 Ecovacs Deebot X2 로봇 청소기 해킹 — 카메라·스피커 무단 원격 제어로 가정 내부 영상 노출 [A]
- 2025년 국내 IP카메라 12만 대 해킹 — 가정 내 영상 무단 접근·유출 [C]
- 스마트 디바이스 대상 공격 하루 평균 82만 건(2025년 기준), 제조 분야 침해 사고당 평균 비용 $5.56M [F][G]

데이터 침해는 더 이상 잠재적 위험이 아니라 이미 현실화된 위협이며, 기업 이미지 실추와 직접적 금전 손실로 이어진다.

> 핵심: 데이터 침해는 이미 현실이다.

### 1.3 고객의 보안 요구와 핵심 요구사항

이런 위협을 배경으로 로봇 제조 고객사들은 두 갈래의 보안 요구를 제기하고 있다.

**첫째, 영상·AI 자산 보호 요구.** 카메라 영상 원본과 AI 모델 가중치·추론 데이터는 로봇 제품의 핵심 자산이자 개인정보·영업기밀의 집약체다. 고객사는 Host OS가 침해되더라도 이 자산이 노출되지 않는 강한 격리를 요구하며, GDPR·개인정보보호법 등 규제 또한 영상·생체 데이터 처리 과정의 기술적 격리를 요구한다. 즉 영상·AI 자산 보호는 단순 부가 기능이 아니라 **제품 출시의 전제 조건**이다.

**둘째, 기존 보안 자산과의 호환(GP API Backward Compatibility) 요구.** 고객사는 이미 ARM TrustZone 기반 Secure OS 위에서 GlobalPlatform(GP) TEE API로 키 관리·인증 등 Trusted Application(TA)을 개발·운용하고 있다. 업계 주요 SoC 벤더(퀄컴·엔비디아) 역시 **순수 Linux 환경에서는 Android Secure HAL로 대체하지 않고 GP 표준 클라이언트 API(`libteec`, `optee_client` 등)를 유지**하는 기조다. 따라서 신규 보안 프레임워크는 기존 GP API 자산을 폐기시키는 것이 아니라, **기존 TrustZone Secure OS·GP API 기반 자산과 공존·연동**해야 한다.

이 두 요구를 본 과제의 핵심 요구사항으로 정리하면 다음과 같다.

| # | 핵심 요구사항 | 내용 |
|---|--------------|------|
| **핵심요구-1** | **Host 비신뢰 가상화 격리** | Host OS(Linux 커널 포함) 침해 시에도 영상·AI 모델·추론 데이터가 노출되지 않는 가상화 기반 강한 격리 |
| **핵심요구-2** | **기존 TrustZone/GP API 자산과 공존** | 기존 ARM TrustZone Secure OS와 GP TEE API 기반 보안 자산을 유지·연동 |

> 핵심: 가상화 보안 플랫폼을 사용한 영상 및 AI 자산 보호는 제품의 핵심 경쟁력이다.

---

## 2. 기존 보안 솔루션의 공백

핵심요구-1·2를 충족하려면 "Host를 신뢰하지 않는 강한 격리"와 "기존 TrustZone 자산과의 공존"을 동시에 만족하는 Linux 보안 실행 환경이 필요하다. 그러나 현재 Linux 솔루션 지형에는 이를 충족하는 프레임워크가 존재하지 않는다.

### 2.1 기존 Linux 가상화 솔루션의 한계

가장 먼저 떠올릴 수 있는 접근은 기존 Linux 가상화·격리 기술의 활용이다. 그러나 대표 솔루션들은 로봇 커스텀 SoC의 보안 격리 요구를 충족하지 못한다.

| 솔루션 | 구조 | 한계 |
|--------|------|------|
| Hypervisor (Xen) | Type-1 하이퍼바이저 | Runtime에 VM 동적 생성 불가 — 로봇 기능 추가에 따른 동적 워크로드 수용에 부적합 |
| KVM / QEMU | Host 커널 기반 가상화 | Host OS와 VM 간 메모리 격리가 보장되지 않음 — Host 침해 시 VM 노출(핵심요구-1 미충족) |
| Docker / LXC | 컨테이너(Host 커널 공유) | Host Linux 커널을 공유하며, 커널은 공격 표면이 넓어 비신뢰 영역 — 강한 격리 불가 |
| AWS Nitro | 가상화 전용 HW + CPU/메모리 전량 제공 | 서버용 전용 하드웨어를 전제 — 임베디드 로봇 SoC에 적용 불가 |

> 참고: Linux 서버/클라우드용 Confidential Computing(AMD SEV, Intel TDX 등)은 Host 비신뢰 격리를 제공하지만 서버용 CPU 전용이라 임베디드 SoC에는 적용할 수 없다.

### 2.2 ARM TrustZone 단독 구조의 한계

현재 Linux 환경에서 사용 가능한 하드웨어 보안 격리는 ARM TrustZone이 사실상 유일하며, 핵심요구-2(기존 자산 공존)의 기반이 된다. 그러나 단독으로는 핵심요구-1의 다중·고성능 격리 요구를 구조적으로 충족하지 못한다.

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

| 한계 | 설명 |
|------|------|
| **이진 격리 구조** | REE/TEE 두 영역만 존재. Secure Camera·Secure AI 등 다수의 독립 보안 도메인을 동시에 생성 불가 |
| **TEE 자원 제약** | S-EL1 환경은 메모리·연산 자원이 제한적이어서 AI 추론 등 고수준 작업 처리에 부적합 |
| **HW IP의 REE 종속** | ISP·NPU 등 HW 가속 IP가 REE 영역에서만 사용 가능하여 격리 도메인에서 활용할 방법이 없음 |
| **동적 확장 불가** | TEE 펌웨어 바이너리로만 배포되어, 신규 요구 발생 시 펌웨어 수정·재배포 필요 |

### 2.3 Host-VM 메모리 격리 솔루션의 공백

Host를 신뢰하지 않는 강한 메모리 격리를 임베디드 Linux SoC에서 제공하는 메커니즘 자체는 이미 존재한다 — **pKVM(Protected KVM)의 Stage-2 메모리 격리**다. 문제는 이를 제품에 활용할 수 있는 완성된 솔루션이 부재하다는 점이다.

| 구분 | 격리 메커니즘 | 한계 |
|------|--------------|------|
| **Android AVF** | pKVM 기반 (Android 12+, Pixel 6~) | VirtualizationService 등 핵심 컴포넌트가 Android 시스템 서비스에 종속 — Linux(Yocto 등) 로봇 SoC에 사용 불가. 또한 Microdroid 중심 설계로 다양한 Secure OS 수용·TrustZone 완전 공존 구조를 제공하지 않음 |
| **Protected KVM 패치** | pKVM Stage-2 격리 (mainline 공개) | 커널 메커니즘은 공개되어 있으나, 이를 user 단에서 활용할 프레임워크(pVM 생명주기 관리·HW IP 공유·워크로드 탑재)가 부재 |

종합하면, Linux 커스텀 SoC 환경에는 pKVM의 격리 메커니즘 위에서 동작하는 **보안 실행 프레임워크가 부재**하다. 본 과제는 이 공백을 메우는 프레임워크를 개발한다.

> 핵심: Linux Custom SoC용 보안 Framework가 부재하다.

---

## 3. 타겟 레퍼런스 시나리오: Secure Vision AI

1·2절로 "Linux 커스텀 SoC용 보안 프레임워크 부재"라는 문제와 두 핵심 요구를 확인했지만, 이것만으로는 프레임워크가 갖춰야 할 구체적 기술 요구사항을 도출할 수 없다. "어떤 보안 실행 환경이 필요한가"는 실제 제품 기능을 기준으로만 답할 수 있기 때문이다. 따라서 타겟 산업군(로봇)을 대표하는 **레퍼런스 시나리오를 선정하고, 그 구현에 필요한 시스템 요구사항을 도출**한다.

### 3.1 선정 기준

레퍼런스 시나리오는 다음 기준으로 선정하였다.

| 선정 기준 | Secure Vision AI가 충족하는 이유 |
|----------|--------------------------------|
| **산업군 대표성** | 카메라 영상 인식과 AI 추론은 가정용·산업용을 막론한 로봇 제품군의 공통 핵심 기능임 |
| **보안 요구 대표성** | 1.2절의 실제 사고 사례(로봇 카메라 해킹, 영상 유출)와 직결되는 최우선 보호 대상임 |
| **HW IP 포괄성** | ISP·NPU 등 커스텀 SoC의 핵심 HW IP를 모두 사용하므로, HW 자원 할당·공유에 대한 요구사항까지 빠짐없이 도출 가능함 |
| **기존 구조 한계 노출성** | 다중 격리 도메인, 고성능 연산, HW IP 접근을 동시에 요구하여 2절의 기존 구조(특히 TrustZone 이진 격리)의 한계가 가장 분명하게 드러남 |
| **확장 구조 검증성** | 두 보안 도메인(Camera, AI)을 결합한 파이프라인이므로, 본 과제의 핵심 키워드인 다중 도메인 확장 구조를 검증하는 출발점이 됨 |

이에 따라 Secure Camera와 Secure AI를 별개 시나리오로 나열하는 대신, 두 도메인을 결합한 단일 파이프라인 **Secure Vision AI**를 레퍼런스 시나리오로 선정한다.

### 3.2 시나리오 정의

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

단, ISP·NPU 등 HW IP는 보안 파이프라인 전용이 아니다. Host의 일반 기능(일반 촬영, 일반 AI 추론 등)도 동일한 HW IP를 사용하므로, 보안 파이프라인이 HW IP를 독점해서는 안 되며 **Host와 격리 도메인이 HW IP를 동시에 사용**할 수 있어야 한다.

### 3.3 시나리오가 요구하는 시스템 요구사항

| ID | 요구사항 | 설명 |
|----|---------|------|
| R-1 | **Host 비신뢰 격리** | Host OS(Linux 커널 포함)가 침해되어도 영상·모델·추론 데이터에 접근 불가해야 함 |
| R-2 | **HW 고성능 연산 지원** | 실시간 영상 처리와 AI 추론을 위해 격리 도메인에서 ISP·NPU 등 HW IP 가속을 안전하게 사용할 수 있어야 함 (SW 처리만으로는 실시간성·연산량 미충족). HW IP는 Host의 일반 기능도 함께 사용하는 공유 자원이므로, 격리 도메인 독점 할당이 아니라 Host와 격리 도메인의 동시 사용을 지원해야 함 |
| R-3 | **다중 격리 도메인 동시 운용** | Secure Camera 도메인과 Secure AI 도메인을 독립적으로 동시에 생성·운용해야 함 |
| R-4 | **동적 확장성** | 로봇 기능 추가에 따라 새로운 보안 워크로드를 펌웨어 재배포 없이 동적으로 추가할 수 있어야 함 |
| R-5 | **기존 Secure OS 상호운용** | 키 관리·인증 등 기존 TrustZone Secure OS 기반 기능과 공존·연동해야 함 (1.3절 핵심요구-2의 구체화) |

### 3.4 요구사항 충족 매트릭스

2절의 기존 솔루션을 R-1~R-5 기준으로 평가하면, 어느 것도 모든 요구를 충족하지 못함이 분명해진다.

| 요구사항 | TrustZone 단독 | Linux KVM (VHE) | Android AVF | **본 과제** |
|---------|:---:|:---:|:---:|:---:|
| R-1 Host 비신뢰 격리 | 충족 | **미충족** | 충족 | 충족 |
| R-2 HW 고성능 연산 지원 | **미충족** | 부분 | 부분 | 충족 |
| R-3 다중 격리 도메인 | **미충족** | 충족 | 충족 | 충족 |
| R-4 동적 확장성 | **미충족** | 충족 | **부분** (Microdroid 중심) | 충족 |
| R-5 Secure OS 상호운용 | 충족 | 충족 | **제한적** | 충족 |
| Linux 커스텀 SoC 적용 | 가능 | 가능 | **불가** | 가능 |

> 핵심: 로봇용 Secure Vision AI 레퍼런스 시나리오를 사용하여 설계 및 검증을 진행한다.

---

## 4. 해결 방향: 확장성 중심의 pKVM 기반 보안 프레임워크

### 4.1 pKVM 도입의 기술적 근거

Linux의 표준 가상화인 KVM은 일반적으로 VHE 모드로 동작하며, Host 커널이 EL2 권한을 직접 보유한다. 이 구조에서는 Host 커널이 침해되면 Hypervisor와 모든 VM의 메모리가 함께 노출되어 R-1을 구조적으로 충족할 수 없다.

| 구분 | VHE (일반 KVM) | nVHE (pKVM) |
|------|----------------|-------------|
| 도입 | ARMv8.1 (FEAT_VHE) | ARMv8.0 |
| Host OS 실행 위치 | EL2 (Host Kernel이 EL2 권한 직접 보유) | EL1 (Host OS는 EL1에서만 실행) |
| Hypervisor TCB | 크다 (Host OS 코드가 EL2 포함) | 작다 (소형 HV 코드만 EL2에 상주) |
| 보안 격리 | **Host 침해 시 HV도 침해됨** | Host OS가 EL2 코드·레지스터에 접근 불가 |
| 주 목적 | VM Entry/Exit 오버헤드 감소 (성능 우선) | Hypervisor 신뢰 경계 유지 (보안 우선) |

pKVM은 nVHE 모드에서 소형 Hypervisor만 EL2에 상주시키고 Stage-2 Page Table 변환(IPA→PA)을 Hypervisor가 독점 제어하므로, Host가 침해되어도 pVM(protected VM)의 메모리 격리가 유지된다. 이것이 기존 Linux KVM이 아닌 **pKVM을 도입해야 하는 기술적 근거**이며, 핵심요구-1(R-1)을 구조적으로 보장하는 메커니즘이다.

> 근거: ARM Architecture Reference Manual ARMv8-A — D1.2.2 Virtualization Host Extensions (FEAT_VHE); Will Deacon et al., "Protecting the Protected: Building a Protected KVM Hypervisor", Linux Security Summit NA 2021

### 4.2 프레임워크 구성요소

pKVM이 제공하는 것은 Stage-2 기반 메모리 격리라는 **메커니즘**뿐이다. 레퍼런스 시나리오를 실현하려면 그 위에 다음을 갖춘 프레임워크가 필요하며, 이것이 본 과제의 개발 대상이다.

| 구성요소 | 역할 | 대응 요구사항 |
|---------|------|--------------|
| pVM 생명주기 관리 프레임워크 | pVM 생성·실행·종료·자원 관리를 담당하는 Linux 네이티브 미들웨어 | R-1, R-3 |
| HW IP 할당·공유 구조 | ISP·NPU 등 HW IP를 Host와 격리 도메인이 함께 사용할 수 있도록 안전하게 할당·공유(SW 중재)하는 커널 드라이버 및 인터페이스 | R-2 |
| 워크로드 확장 구조 | 신규 보안 워크로드·서드파티 Secure OS를 프레임워크 수정 없이 pVM으로 탑재하는 플러그인형 구조 | R-4 |
| TrustZone 공존 계층 | 기존 Secure OS 기반 기능(키 관리·인증)과 GP API 자산을 연동하는 인터페이스 | R-5 |

핵심 설계 키워드는 **확장성(Extensibility)** 이다. 단일 시나리오 전용 솔루션이 아니라, Secure Vision AI를 첫 레퍼런스로 검증하되 이후 시나리오(개인정보 처리, 펌웨어 보호 등)를 프레임워크 수정 없이 수용하는 구조를 목표로 한다. 또한 본 과제는 AVF의 Linux 포팅이 아니라, **AVF가 제공하지 못하는 기능 — Linux 네이티브 동작, 다양한 Secure OS 수용, TrustZone 완전 공존 — 을 갖춘 독자 프레임워크**를 설계·구현하는 것이다.

> 핵심: Linux pKVM 기반 가상화 보안 프레임워크 개발로 공백을 해소한다.

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
| **포함** | 기존 Secure OS를 pVM 격리 도메인에서 동작·확장시키기 위한 SW 이식·수정 (R-4 동적 확장성, R-5 Secure OS 상호운용 충족에 필요) |
| **제외** | pKVM 커널(EL2 Hypervisor) 자체 포팅 — 기 포팅된 pKVM 커널을 전제로 함 |
| **제외** | 신규 Secure OS의 처음부터의 개발(from scratch), HW IP(ISP·NPU) 하드웨어 설계 |

> 2026-05-29 리뷰 회의 결정: pKVM 포팅은 범위에서 제외하고, 이를 제어하는 상위 커널 드라이버·미들웨어·프레임워크 개발에 집중한다.
>
> 단, R-4(동적 확장성)·R-5(Secure OS 상호운용)를 격리 도메인에서 충족하려면 기존 Secure OS를 pVM 환경에 맞게 이식·수정하는 작업이 불가피하므로, Secure OS의 신규 개발은 제외하되 기존 Secure OS의 이식·수정은 범위에 포함한다.

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

### 6.3 핵심 개발 기술

세부 목표(G-1~G-4)와 시나리오 요구사항(R-1~R-5)을 달성하기 위해 본 과제에서 개발·확보해야 할 핵심 기술은 다음과 같다.

| # | 핵심 기술 | 내용 | 대응 목표/요구사항 |
|---|----------|------|------------------|
| T-1 | **pVM 생명주기 관리 기술** | Stage-2 메모리 격리를 활용한 pVM 생성·실행·종료·자원 회수와 다중 pVM 스케줄링을 담당하는 Linux 네이티브 미들웨어 | G-1, R-1, R-3 |
| T-2 | **HW IP 보안 공유 기술** | 다중 컨텍스트를 지원하지 않는 ISP·NPU 등 HW IP를 Host와 pVM이 동시에 사용할 수 있도록 SW 중재로 공유하고, pVM 사용 구간에는 Stage-2 및 SMMU/IOMMU로 DMA 경로를 격리하며 사용 주체 전환 시 잔류 데이터를 소거하는 커널 드라이버·인터페이스 | G-2, R-2 |
| T-3 | **격리 도메인 간 보안 통신 기술** | Secure Camera↔Secure AI 도메인 간, 그리고 pVM↔Host 간에 데이터를 노출 없이 전달하는 저오버헤드 보안 채널(공유 메모리·RPC) | G-2, R-1, R-3 |
| T-4 | **워크로드 확장 프레임워크 기술** | 신규 보안 워크로드·서드파티 Secure OS를 프레임워크 수정 없이 pVM으로 탑재하는 플러그인형 패키징·로딩 구조 | G-3, R-4 |
| T-5 | **Secure OS 이식 및 TrustZone 공존 기술** | 기존 Secure OS를 pVM 격리 도메인에서 동작하도록 이식·수정하고, 기존 TrustZone TEE 경로(SMC·GP API 등)와 공존시키는 연동 계층 | G-4, R-5 |

> 핵심 개발 기술의 세부 설계 항목과 우선순위는 Bottom-up 설계 접근(Design Point 추출 → 핵심 DP 선정)을 통해 구체화한다.

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
- GlobalPlatform TEE Client API Specification; OP-TEE(`optee_client`) — 오픈소스 GP TEE API 구현
- Confidential Computing Consortium, "Confidential Computing as a Strategic Imperative for Secure AI" (https://confidentialcomputing.io/2025/12/03/new-study-finds-confidential-computing-emerging-as-a-strategic-imperative-for-secure-ai-and-data-collaboration/)
