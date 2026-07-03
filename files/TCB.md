# EL2 TCB 최소화 원칙

## 개요

**TCB(Trusted Computing Base, 신뢰 컴퓨팅 기반)** 란 시스템의 보안을 보장하기 위해 반드시 안전해야 하는 하드웨어/펌웨어/소프트웨어의 총합이다.

**EL2 TCB 최소화 원칙**은 ARMv8/v9 아키텍처 기반 가상화 환경에서, 하이퍼바이저가 실행되는 고권한 계층(EL2)의 코드 크기와 역할을 최소한으로 유지해야 한다는 설계 원칙이다.

---

## 1. 배경 및 목적

ARM 아키텍처에서 EL2는 EL0(앱)/EL1(OS)보다 높은 권한을 가진다. EL2가 침해될 경우 시스템 전체가 영향을 받으므로, EL2에 상주하는 코드를 최소화하는 것이 보안의 핵심이다.

| 구분 | 내용 |
|------|------|
| 취약점 노출 감소 | 코드 규모가 클수록 버그/취약점 발생 확률이 높아짐. EL2 코드 최소화로 공격 표면(Attack Surface) 축소 |
| 복잡도 제거 | Type-1 Full Hypervisor를 EL2에 그대로 올리면, 스케줄링/디바이스 에뮬레이션 등 신뢰 불필요한 코드까지 고권한을 가지게 됨 |

---

## 2. 구현 방식

### EL2 잔존 기능 (Micro-hypervisor / RMM)

- Stage-2 페이지 테이블 관리 및 메모리 격리
- CPU 가상화 및 컨텍스트 스위칭
- VM 간 하드웨어 수준 격리 보장

### EL1 이관 기능 (Host OS)

- 스케줄링
- 디바이스 드라이버 제어
- 가상 디바이스 에뮬레이션 등 복잡 기능

**원칙 요약**: 고권한 계층(EL2)의 코드는 최소한으로 유지하고, 복잡한 기능은 하위 계층(EL1)으로 이관한다.

**효과**: EL2 버그로 인한 전체 시스템 마비 위험 최소화, 코드 경량화로 형식 검증(Formal Verification) 적용이 현실적으로 가능해진다.

---

## 3. ARM CCA Realm과의 연계

ARM CCA(Confidential Compute Architecture)는 ARMv9에서 도입된 기밀 컴퓨팅 아키텍처로, EL2 TCB 최소화 원칙이 하드웨어 수준까지 구현된 대표 사례다.

기존 가상화에서는 하이퍼바이저(EL2)가 Guest VM(EL1)의 모든 메모리에 접근 가능했으므로, 하이퍼바이저 침해 시 Guest 데이터가 유출되는 구조적 한계가 있었다. ARM CCA는 "하이퍼바이저조차 신뢰하지 않는다"는 설계 철학으로 이 한계를 극복한다.

### Realm 아키텍처: 보안 세계 확장

| 보안 세계 | 계층 | 설명 |
|-----------|------|------|
| Normal World | EL0/EL1/EL2 | 일반 앱/OS/Host Hypervisor |
| Secure World | S-EL0/S-EL1/S-EL2 | 기존 TrustZone 영역. S-EL2는 ARMv8.4-A부터 추가되어 Secure Partition Manager(SPM, 예: Hafnium)가 실행됨 |
| Realm World | R-EL0/R-EL1/R-EL2 | 기밀 컴퓨팅 전용 격리 환경 |
| Root World | EL3 | TF-A(Trusted Firmware-A). RMM 로드 및 검증 담당 |

### EL2 역할 이원화

| 구성 요소 | 계층 | 역할 | TCB 포함 여부 |
|-----------|------|------|--------------|
| Host Hypervisor | Non-secure EL2 | VM 자원(CPU/메모리) 할당 및 스케줄링 | 제외 (침해되어도 Realm 내부 접근 불가) |
| RMM (Realm Management Monitor) | Realm EL2 | Realm VM 생명주기 관리, 메모리 보호/격리 전담 | 포함 (최소 코드로 구성) |

### TCB 최소화가 Realm에서 작동하는 방식

- Host Hypervisor가 침해되더라도, Realm VM의 메모리 제어권과 암호화 키는 RMM이 보유하므로 데이터 접근이 불가하다.
- Host Hypervisor는 RMM에 SMC/RMI 호출로 메모리 할당을 요청할 수 있을 뿐, RMM이 설정한 격리 경계를 넘을 수 없다.
- RMM 자체의 코드가 극도로 작고 단순하므로, RMM 자체를 공격하기 어렵다.
- 전체 TCB는 RMM(EL2) + TF-A(EL3)로만 구성된다.

---

## 4. TrustZone과 Realm 비교

### 핵심 차이점

| 구분 | TrustZone (기존 TEE) | Realm (ARM CCA) |
|------|----------------------|-----------------|
| 주요 목적 | 디바이스 하드웨어 제어 및 고정된 보안 기능 보호 | 가상화 환경에서 다중 VM 데이터 보호 |
| 보안 세계 수 | 2개 (Normal / Secure) | 4개 (Normal / Secure / Realm / Root) |
| 신뢰 주체 | 디바이스 제조사 | VM을 사용하는 고객 (인프라 관리자도 불신) |
| 격리 구조 | 단일 Secure OS 운영 (정적 구조) | 독립 보안 VM 동적 생성/삭제 (동적 구조) |
| 주요 활용처 | 지문 인식, 모바일 결제, 암호 키 보관 | 클라우드 AI 연산, 금융 VM, 기밀 데이터 처리 |

### 구조적 패러다임 차이

**TrustZone (정적 격리)**
- 시스템을 Normal World / Secure World 두 영역으로 분리한다.
- 제조사가 사전에 탑재한 고정 Trusted OS만 Secure World에서 실행된다.
- 일반 개발자나 클라우드 고객이 동적으로 보안 VM을 생성할 수 없다.

**Realm (동적 격리)**
- 클라우드 사용자가 필요에 따라 하드웨어 격리된 Realm VM을 동적으로 수십/수백 개 생성 및 삭제할 수 있다.
- Hypervisor 위에 독립된 Realm VM들이 각각 완전히 격리된 상태로 실행된다.

### TCB 관점 비교

| 구분 | TrustZone | Realm |
|------|-----------|-------|
| TCB 범위 | Secure World 전체 (Trusted OS + TA 포함) | RMM + TF-A 만 |
| 취약점 전파 | TA 하나의 취약점이 Secure World 전체에 영향 가능 | Realm VM A 침해 시 Realm VM B는 영향 없음 |
| 격리 대상 | Normal World로부터의 격리 | Normal World + Host Hypervisor로부터의 격리 |

---

## 5. NPU 가속기 연계: Split Driver 구조 (ARM CCA Realm 기준)

> 본 섹션은 ARMv9 기반 ARM CCA Realm 환경 기준이다. ARMv8 nVHE 기반 Android AVF pVM 환경은 6절에서 별도 서술한다.

### 드라이버를 통째로 넣을 수 없는 이유

NPU 드라이버는 메모리 할당(커널 모드), 컴파일러 런타임, 대규모 스케줄링 등 수십만 줄 규모의 소프트웨어다. 이를 Realm 내부에 통째로 올리면 다음 문제가 발생한다.

- **TCB 비대화**: 드라이버 버그 하나가 Realm 전체의 기밀성을 훼손할 수 있다.
- **호환성 문제**: NPU 제조사(Qualcomm, ARM, NVIDIA 등)마다 드라이버가 상이하여 Realm 내부 가상화가 현실적으로 불가하다.

### Split Driver 구조

| 구성 요소 | 위치 | 역할 |
|-----------|------|------|
| Front-end 드라이버 | Realm / pVM 내부 | NPU에 연산 명령(커맨드 큐) 전달 및 결과 수신. 코드 규모 최소화 |
| Back-end 드라이버 | Host OS (비보안 영역) | 메모리 스케줄링, NPU 초기화, 전력 관리 등 복잡한 제어 담당 |

Host OS가 침해되어 NPU 스케줄링을 방해할 수는 있으나, NPU에서 처리 중인 Realm의 AI 모델 가중치나 입력 데이터에는 접근할 수 없다.

### 하드웨어 수준의 기밀 I/O (Confidential I/O)

- **서버/데이터센터 환경 (외장 NPU/GPU)**: PCIe IDE(Integrity & Data Encryption)를 통해 Realm 메모리와 NPU 사이의 데이터 통로가 하드웨어 고유 키로 암호화된다.
- **모바일/임베디드 SoC 환경 (스마트폰/차량용 AP)**: PCIe IDE 대신 SoC 내부 버스 암호화(MEE, Memory Encryption Engine), SMMU 기반 메모리 접근 제어, TrustZone Media Protection(TZMP2) 등이 사용된다.
- **NPU Realm 모드**: NPU 자체가 Realm 물리 주소 영역에 접근 시 Host OS가 가로채더라도 암호화된 데이터만 노출된다.

---

## 6. pVM에서의 NPU 드라이버 분리

안드로이드 AVF(Android Virtualization Framework)의 pVM도 동일한 TCB 최소화 딜레마를 가지며, VirtIO 기반의 Split Driver 구조로 해결한다.

### pVM에서 드라이버를 통째로 넣을 수 없는 이유

- **커널 비대화**: 무거운 NPU 독점 드라이버(Qualcomm QNN/Hexagon 등) 전체를 Microdroid 커널에 내장하면 pVM 경량화 원칙이 무너진다.
- **중복 구현**: NPU 로우 레벨 제어 코드는 Host Linux 커널(EL1)에 이미 존재하며, pVM 내부에 재빌드하는 것은 메모리 낭비다.

### pVM NPU 드라이버 분리 구조

| 구성 요소 | 위치 | 역할 |
|-----------|------|------|
| VirtIO-NPU Front-end | pVM 내부 | AI 연산 명령을 패키징하여 Host로 전달. 하드웨어 직접 제어 없음 |
| NPU Back-end 드라이버 | Android Host OS | 스케줄링, 메모리 할당, 컴파일러 최적화, 전력 제어 등 담당 |

### 데이터 보호 방식

- **Hypercall 기반 메모리 공유**: pVM은 연산에 필요한 특정 메모리 페이지만 Hypercall로 임시 공유하고, 연산 완료 후 즉시 공유를 해제한다.
- **IOMMU/SMMU 격리**: pKVM이 NPU의 접근 가능 메모리 주소를 하드웨어 수준으로 제한하여, pVM 내 비허용 영역(암호화 키 등)에 대한 접근을 차단한다.

---

## 7. AI 프레임워크 분리 (Split Inference)

NPU 드라이버 분리에 성공하더라도, ONNX Runtime/TensorFlow Lite/PyTorch 등 수백만 줄 규모의 AI 프레임워크를 Realm/pVM 내부에 통째로 올리면 TCB가 재차 비대해진다. 이를 해결하기 위해 AI 프레임워크 역할을 이원화한다.

### Split Inference 구조

| 구성 요소 | 위치 | 역할 |
|-----------|------|------|
| Full Framework | Host OS (비보안 영역) | 모델 파싱, 연산 그래프 컴파일, NPU 명령어 스트림 생성 |
| Micro-runtime | Realm / pVM 내부 | 호스트가 생성한 커맨드 스트림 검증(Validation) 후 NPU에 전달. 수천~수만 줄 수준으로 최소화 |

### 동작 시나리오 (안드로이드 pVM 기준)

1. **모델 준비 (Host)**: 외부 AI 프레임워크가 모델 아키텍처를 분석하여 NPU 바이너리 명령어 스트림을 생성한다.
2. **보안 메모리 로딩 (pVM)**: 암호화된 AI 모델 가중치(Weight)와 입력 데이터를 pVM 내부에서만 복호화하여 보안 메모리에 로드한다.
3. **명령 검증 (pVM 내부)**: Micro-runtime이 호스트 전달 커맨드 스트림의 악성 여부를 검증한다.
4. **NPU 실행**: 검증 완료 후 pVM이 NPU에 명령을 전달하고, NPU는 암호화 채널을 통해 보안 메모리에 접근하여 연산을 수행한다.

### 이점

- **TCB 최소화 유지**: Realm/pVM 내부에 대형 C++ 프레임워크가 없으므로 공격 표면이 최소로 유지된다.
- **AI 업데이트 유연성**: AI 프레임워크 업데이트 시 보안 영역 펌웨어를 재배포할 필요 없이 Host 프레임워크만 갱신하면 된다.

---

## 8. Secure Camera 시나리오 (DMS)

DMS(Driver Monitoring System)와 같이 운전자 시선/졸음 등 생체 정보를 실시간 처리하는 Secure Camera 시나리오에서도, 카메라 드라이버/ISP 프레임워크를 Realm/pVM 내부에 넣지 않는 동일한 원칙이 적용된다.

해결 방식: **Protected Media Path** (미디어 파이프라인 하드웨어 암호화 격리)

### 하드웨어 수준 데이터 흐름 격리

**Secure DMA (이미지 센서 → 보안 메모리)**
- 카메라 센서가 촬영한 영상 데이터는 Host OS가 접근할 수 없는 보안 메모리(Realm Memory)로 직접 DMA 전송된다.
- Host OS의 카메라 드라이버는 "캡처 시작" 명령(제어)만 내릴 수 있으며, 실제 픽셀 데이터에는 ARM MEE(Memory Encryption Engine) 수준에서 차단된다.

**ISP 하드웨어 보안 모드**
- Raw 영상 처리를 담당하는 ISP를 소프트웨어로 Realm/pVM 내부에서 처리하는 것은 불가능하다.
- 현대 SoC는 ISP 하드웨어 자체에 보안 모드를 탑재하여, 제어 명령은 Host OS에서 수신하되 데이터 접근은 암호화된 보안 메모리 버퍼만 허용한다.

### Realm / pVM 내부 구성

- Host OS의 Camera HAL/바인더 서비스 등 대형 카메라 프레임워크는 모두 보안 영역 외부에 위치한다.
- pVM 내부에는 "보안 메모리에 영상이 적재되었음"을 수신하는 초경량 인터페이스만 존재한다.
- 보안 메모리에 적재된 영상 데이터는 pVM 내 Micro-runtime 검증을 거쳐 NPU로 전달되어 졸음 분석 등 AI 연산이 수행된다.

### 동작 흐름

| 단계 | 주체 | 동작 |
|------|------|------|
| 1 | Host OS (Android) | DMS 카메라 캡처 명령 하달 (무거운 카메라 드라이버 스택 사용) |
| 2 | HW (센서 및 AP) | 영상 데이터를 pVM 전용 보안 메모리에 암호화하여 직접 저장 |
| 3 | Host OS (Android) | pVM에 "메모리 주소 0x123에 데이터 준비됨" 알림 전달 (Host는 해당 주소 내용 복호화 불가) |
| 4 | pVM (보안 영역) | 보안 메모리 복호화 후 AI 연산 수행. 결과 메타데이터(예: "졸음 위험 레벨: 3")만 Host로 출력 |

### 설계 원칙 요약

| 계층 | 처리 위치 | 내용 |
|------|-----------|------|
| 제어(Control Line) | Host OS (비보안 영역) | 드라이버, ISP 제어, 카메라 프레임워크 등 복잡 기능 |
| 데이터(Data Line) | Realm / pVM (보안 영역) | 암호화된 영상 데이터 복호화 및 AI 연산 |

이 구조를 통해 초당 60프레임 고화질 영상 처리 환경에서도 Realm/pVM은 TCB 최소화 상태를 유지하면서 운전자 프라이버시를 보호하고 AI 연산을 수행할 수 있다.
