
ff-a 기술을 리눅스에서 채택하려는 움직임은?

---

리눅스(Linux) 진영에서 **Arm FF-A(Firmware Framework for Arm A-profile)** 기술을 채택하고 통합하려는 움직임은 **이미 메인라인 커널에 완전히 안착했으며, 현재는 생태계를 확장하는 고도화 단계**에 있습니다.

단순한 논의 수준을 넘어 리눅스 커널 소스 트리에 드라이버가 공식 통합되었고, 보안 하위 시스템(Subsystem)과의 연동이 활발하게 이루어지고 있습니다. 구체적인 움직임과 아키텍처적 변화는 다음과 같습니다.

---

## 1. 리눅스 메인라인 커널의 공식 지원 (이미 완료)

리눅스 커널은 **Linux 5.14(2021년) 버전부터 Arm FF-A 1.0 규격을 지원하는 공식 핵심 드라이버를 커널 메인라인에 통합**했습니다.

* **커널 설정:** 현재 리눅스 커널 소스에서 `CONFIG_ARM_FFA_TRANSPORT` 옵션을 통해 활성화할 수 있습니다. (`drivers/firmware/arm_ffa/` 디렉토리에 소스코드가 위치합니다.)
* **역할:** 리눅스 커널(Normal World EL1)이 Hypervisor나 Secure World(S-EL2/S-EL1)에 있는 다양한 Secure Partition(SP)들과 표준화된 방식으로 메시지를 주고받고(Direct/Indirect Messaging), 메모리를 공유(`FFA_RXTX_MAP`)할 수 있도록 돕는 통신 백본 역할을 합니다.

---

## 2. Linux TEE Subsystem 및 OP-TEE와의 연동

과거에는 리눅스 커널이 Secure World(예: OP-TEE OS)와 통신할 때 벤더 고유의 SMC(Secure Monitor Call) 인터페이스를 각자 구현해 썼습니다. 하지만 FF-A가 도입되면서 이 구조가 표준화되고 있습니다.

* **FF-A 기반 TEE 드라이버:** 리눅스 커널의 오픈소스 TEE 구동 Framework(`drivers/tee/`) 내에 FF-A 기반의 TEE 드라이버(FF-A TEE driver)가 추가되었습니다.
* **OP-TEE의 FF-A 채택:** 대표적인 오픈소스 TEE인 **OP-TEE** 역시 상위 버전(v3.14 이상 등)부터 규격에 FF-A를 지원하기 시작했습니다. 결과적으로 리눅스 커널은 하드웨어 종속적인 SMC 호출 대신 `FF-A ABI`를 호출하여 OP-TEE 내의 Trusted Application(TA)과 통신하게 됩니다.

---

## 3. 기밀 컴퓨팅(Confidential Computing) 및 가상화 인프라 확장

리눅스 진영이 FF-A를 적극적으로 받아들이는 가장 큰 이유 중 하나는 **가상화(KVM) 환경의 보안 및 기밀 컴퓨팅** 때문입니다.

* **구글의 pKVM (Android Virtualization Framework):** 구글은 안드로이드 리눅스 커널에서 pKVM(Protected KVM)을 구현하면서, 호스트 OS(리눅스)와 가상머신(VM), 그리고 Secure World(TrustZone) 간의 안전한 메모리 대여(Lending) 및 공유 제어를 위해 **FF-A 규격을 핵심 인프라로 사용**하고 있습니다.
* **Arm CCA (Confidential Compute Architecture) 대응:** Armv9의 핵심 보안 기술인 CCA와 Realm Management Extension(RME) 환경에서, 리눅스(호스트/게스트 OS)가 Realm(기밀 가상 머신) 및 Secure 파티션들과 안전하게 격리된 통신을 수행하기 위한 인터페이스 표준으로 FF-A가 강제되고 있습니다. 리눅스 커널 커뮤니티는 Arm CCA 표준 스택 지원을 위해 FF-A 드라이버를 지속적으로 업데이트하고 있습니다.

---

## 4. 유저스페이스(User-space) 지원 및 생태계 변화

리눅스 커널 내부 드라이버뿐만 아니라 응용 프로그램 레벨(유저스페이스)에서의 움직임도 명확합니다.

* **표준 시스템 콜 대응:** 유저스페이스 앱이 `/dev/tee*` 디바이스 노드를 통해 기존 GlobalPlatform(GP) 클라이언트 API 표준을 그대로 쓰더라도, 리눅스 커널 내부에서 이를 FF-A 메시지로 자동 변환(Mapping)하여 Secure World로 전달하는 구조가 정착되었습니다. 개발자는 하부 통신 방식이 SMC에서 FF-A로 바뀌어도 상위 소스코드를 고칠 필요가 없습니다.
* **U-Boot 등 부트로더 지원:** 리눅스 커널이 부팅되기 전 단계인 U-Boot나 UEFI 런타임 서비스 환경에서도 FF-A를 지원하려는 패치와 가이드라인이 지속적으로 리눅스 진영 부트 시퀀스에 통합되고 있습니다.

---

## 💡 요약하자면

현재 리눅스 진영에서 FF-A는 '도입을 고민하는 기술'이 아니라, **안드로이드, 임베디드 리눅스, 서버용 자율주행/기밀 컴퓨팅 환경에서 이미 대세로 자리 잡은 표준 통신 규격**입니다.

기존의 파편화된 벤더 고유 보안 인터페이스들이 리눅스 메인라인의 `arm_ffa` 드라이버를 중심으로 빠르게 통합되고 있는 추세입니다.

---

ff-a와 smc 비교 (특징, 설명, 다이어그램, 장점, 단점, 응용)

---

Armv8-A 및 Armv9-A 아키텍처 보안 시스템의 핵심 통신 메커니즘인 SMC(Secure Monitor Call)와 FF-A(Firmware Framework for Arm A-profile)를 다각도로 비교해 드리겠습니다.

---

## 1. 개요 및 개념 설명

* **SMC (Secure Monitor Call):**
* **개념:** 아키텍처 수준의 하드웨어 명령어(`smc`)이자, Normal World(Non-secure)에서 Secure World로 진입하기 위한 전통적인 진입점(Entry Point)입니다.
* **설명:** CPU가 EL1(OS) 또는 EL2(Hypervisor)에서 `smc` 명령어를 실행하면, 트랩(Trap)이 발생하여 최고 권한 레벨인 EL3(Secure Monitor/TF-A)로 실행 제어권이 넘어갑니다. 레지스터(W0~W7 등)를 통해 인자를 직접 전달하는 단순하고 직관적인 Point-to-Point 방식입니다.


* **FF-A (Firmware Framework for Arm):**
* **개념:** 가상화 및 멀티 파티션 환경을 위해 정의된 **소프트웨어 아키텍처 표준 Framework**입니다. (규격 명칭: DEN0077)
* **설명:** 하드웨어 명령어인 SMC를 포함하여 Hypervisor 호출(HVC) 등을 하부 기저층으로 활용하되, 그 위에 표준화된 소프트웨어 규격을 얹은 것입니다. 여러 개의 가상 머신(VM)과 여러 개의 보안 파티션(Secure Partition, SP)이 존재할 때 이들 간의 메시지 라우팅, 메모리 관리(대여/공유/기부), 인터럽트 처리를 표준 ABI(Application Binary Interface) 인터페이스로 규정합니다.



---

## 2. 아키텍처 비교 다이어그램

SMC 방식은 Normal World와 Secure World가 1:1로 직접 소통하는 반면, FF-A는 SPM(Secure Partition Manager)을 통해 다대다(N:M) 구조로 격리/통신하는 아키텍처적 차이가 있습니다.

```
[ 전통적인 SMC 방식 ]
  Normal World             Secure World
┌────────────────┐       ┌────────────────┐
│   Linux (EL1)  │       │  OP-TEE (S-EL1)│
└───────┬────────┘       └────────▲───────┘
        │ (SMC 호출)               │
 ┌──────▼─────────────────────────┴──────┐
 │          Firmware / TF-A (EL3)         │  <- 매번 직접 중재 및 파싱 필요
 └───────────────────────────────────────┘

[ 현대적인 FF-A 표준 방식 ]
  Normal World (Non-secure)             Secure World
┌────────────────┌────────────────┐   ┌────────────────┌────────────────┐
│ Guest VM (EL1) │   Host (EL1)   │   │  SP 1 (S-EL1)  │  SP 2 (S-EL1)  │  <- 독립된 파티션들
└───────┬────────┴───────┬────────┘   └────────▲───────┴────────▲───────┘
        │                │                     │                │
┌───────▼────────────────▼─────────────────────┴────────────────┴───────┐
│     Hypervisor (EL2)    ◀───[FF-A ABI]───▶     SPMC (S-EL2 / EL3)     │  <- 표준화된 메시지
└───────────────────────────────────────────────────────────────────────┘  림 및 메모리 관리

```

---

## 3. 핵심 특징 및 항목별 비교표

| 비교 항목 | SMC (Secure Monitor Call) | FF-A (Firmware Framework for Arm) |
| --- | --- | --- |
| **개념적 계층** | 하드웨어 명령어 / Low-level 통신 수단 | 고수준 펌웨어 아키텍처 Framework |
| **구조적 관계** | Point-to-Point (주로 1:1 대응) | Many-to-Many (멀티 파티션/VM 허브 구조) |
| **통신 규격** | 벤더마다 자체 정의 (구현 파편화) | Arm 표준 ABI 규정 (상호 운용성 보장) |
| **메모리 공유 방식** | 물리 주소를 레지스터로 직접 전달 (위험성 존재) | `FFA_MEM_SHARE`, `FFA_MEM_LEND` 등 안전한 API 사용 |
| **가상화 지원** | 복잡함 (Hypervisor가 SMC를 가로채서 수동 중재) | 태생적 지원 (VM과 Secure Partition 간 라우팅 인프라 내장) |
| **보안 격리 수준** | 하드웨어 TrustZone 기반 단일 격리 | Secure EL2(SPMC)를 통한 TEE 내 세부 격리 (샌드박싱) |

---

## 4. 장점과 단점

### SMC

* **장점:**
* **단순함 및 저지연(Low Overhead):** 복잡한 Framework 층이 없어 오버헤드가 적고 실행 속도가 빠릅니다.
* **구현 용이성:** 시스템 구조가 복잡하지 않은 소형 임베디드 장치나 RTOS 환경에서 아주 직관적으로 구현할 수 있습니다.


* **단점:**
* **파편화:** SoC 제조사(퀄컴, 엔비디아, 미디어텍 등)마다 SMC 소프트웨어 구현 인터페이스가 달라 소스코드 재사용이 어렵습니다.
* **확장성 부족:** Secure World 내부에 여러 벤더의 보안 기능(예: DRM, 생체인식, 암호화)이 독립적으로 상주해야 할 때, 상호 간섭을 격리하기 어렵습니다.



### FF-A

* **장점:**
* **표준화 및 호환성:** OS 및 칩셋 제조사가 달라도 표준 FF-A 규격을 준수하므로 보안 소프트웨어(TA, SP) 이식성이 극대화됩니다.
* **강력한 격리(Sandboxing):** Secure World 안에서도 가상화를 도입하여(S-EL2) 각 보안 기능을 파티션 단위로 안전하게 격리합니다. 한 파티션이 뚫려도 다른 보안 영역은 안전합니다.
* **안전한 자원 관리:** 메모리를 다른 영역에 빌려주고(`Lend`) 회수(`Retrieve`)하는 등의 동적 메모리 제어가 규격 수준에서 안전하게 통제됩니다.


* **단점:**
* **복잡성:** 소프트웨어 스택(SPMD, SPMC, 드라이버 등)이 무겁고 설계와 디버깅 난이도가 높습니다.
* **성능 오버헤드:** 다단계 레이어(가상화 및 매니저)를 거치기 때문에 단순 SMC 호출에 비해 메시지 전달 지연(Latency)이 소폭 증가할 수 있습니다.



---

## 5. 응용 분야 (Application)

* **SMC의 주요 응용:**
* **전통적인 모바일 TEE 및 RTOS:** 구형 스마트폰이나 단일 TEE OS(예: 가벼운 전용 OS)만 구동하는 임베디드 장치.
* **단순 전력/시스템 제어:** 가상화가 필요 없는 환경에서 커널이 펌웨어(ATF/TF-A)에 PSCI(Power State Coordination Interface) 명령을 내려 CPU 코어를 끄고 켤 때.


* **FF-A의 주요 응용:**
* **안드로이드 pKVM (Protected 가상화):** 안드로이드 기기에서 일반 가상머신(VM)과 호스트 OS, 그리고 Secure World 간에 중요한 암호화 키나 데이터를 실시간으로 안전하게 공유 및 격리할 때 활용됩니다.
* **Arm CCA (Confidential Compute Architecture):** 클라우드 서버 환경에서 Hypervisor조차 믿지 못하는 '기밀 가상 머신(Realm)'을 생성하고 관리하기 위한 하부 인프라로 필수 채택됩니다.
* **차세대 오토모티브 및 고성능 IoT:** 자율주행용 SoC(예: Qualcomm Ride, Nvidia DRIVE 등) 내에서 계기판 가상화, 인포테인먼트, ADAS 보안 모듈이 서로 섞이지 않도록 Secure World를 쪼개어 멀티 파티션으로 관리할 때 핵심 통신 백본으로 쓰입니다.

---

FF-A를 이용한 pVM 간 DMABUF 공유는 어떻게 가능한가?

---

FF-A의 메모리 관리 ABI(`FFA_MEM_SHARE`/`LEND`/`DONATE`)와 리눅스 DMABUF를 결합하면, pVM 간 프레임 버퍼를 **복사 없이(zero-copy), 하이퍼바이저가 소유권을 강제하는 방식**으로 전달할 수 있다. 핵심 아이디어는 "DMABUF의 페이지 목록(sg_table)을 FF-A 메모리 트랜잭션 디스크립터로 변환해 상대 pVM에 lend/share하고, 수신 측에서 retrieve한 영역을 다시 DMABUF로 import한다"는 것이다.

## 1. 전제: 역할 매핑

FF-A 스펙(DEN0077A)의 메모리 관리 모델은 파티션(endpoint) 간 소유권(Ownership)과 접근 권한(Access)을 상태 기계로 정의한다. pVM 간 공유에서는 각 역할이 다음과 같이 대응된다.

| FF-A 개념 | pVM 시나리오 대응 | 비고 |
|-----------|------------------|------|
| Sender / Owner | Camera pVM (프레임 생산자) | DMABUF exporter |
| Receiver / Borrower | AI pVM (프레임 소비자) | DMABUF importer |
| Relayer | 하이퍼바이저 (pKVM EL2) | NS world VM 간 트랜잭션의 중재자. 디스크립터 검증, Stage-2 매핑 변경, handle 발급 |
| Endpoint ID | 각 pVM에 하이퍼바이저가 부여하는 16-bit ID | `FFA_ID_GET`으로 조회 |
| Global Handle | 공유 트랜잭션을 식별하는 64-bit 값 | Relayer가 발급, 수신자에게 전달해야 할 유일한 토큰 |

FF-A가 "Secure World와의 통신 전용"이 아니라는 점이 중요하다. 스펙상 Normal World의 VM들도 FF-A endpoint이며, 이때 하이퍼바이저가 VM 간 트랜잭션의 relayer 역할을 수행하도록 정의되어 있다. 즉 pVM↔pVM 공유는 SPMC(Secure World) 개입 없이 하이퍼바이저 계층에서 완결된다.

## 2. 공유 방식 선택: SHARE vs LEND vs DONATE

| ABI | 송신자 접근 | 수신자 접근 | 소유권 | 프레임 파이프라인 적용 |
|-----|------------|------------|--------|----------------------|
| `FFA_MEM_SHARE` | 유지 | 획득 | 송신자 유지 | 상시 공유 버퍼 풀 — 구성 시 1회 호출, 이후 hypercall 없음 |
| `FFA_MEM_LEND` | **상실** (Stage-2 매핑 제거) | 획득 | 송신자 유지 | 프레임 단위 배타적 이전 — 어느 시점에도 접근자는 1개 도메인 |
| `FFA_MEM_DONATE` | 상실 | 획득 | **이전** | 반환 없는 영구 이전 (프레임 순환에는 부적합) |

- **SHARE**는 성능 우선(반복 구간 hypercall 0회), **LEND**는 기밀성 우선(노출 창 최소)이다. 이 선택은 `08_candidate_architectures.md`의 DP-C1 후보와 정확히 대응한다: SHARE 기반 상시 풀 = C1-1, LEND/RELINQUISH 왕복 = C1-3. 즉 FF-A는 두 후보를 **동일한 표준 ABI 집합 위에서 구성 차이로만** 구현할 수 있게 해준다.
- LEND는 수신자가 여럿일 수 있으나(multi-borrower), 프레임 파이프라인에서는 단일 수신자로 충분하다.

## 3. 단계별 흐름 (LEND 기준)

```
  Camera pVM (Owner)            pKVM (Relayer, EL2)            AI pVM (Borrower)
 ───────────────────           ─────────────────────          ───────────────────
 [0] FFA_VERSION/FEATURES 협상, FFA_RXTX_MAP으로 TX/RX 버퍼 등록,
     FFA_ID_GET으로 endpoint ID 확보          (양쪽 pVM 모두, 초기화 시 1회)

 [1] dma heap에서 버퍼 할당
     → dma-buf export
     → sg_table(페이지 목록) 확보
 [2] 메모리 트랜잭션 디스크립터 작성
     (수신자 = AI endpoint ID,
      권한 = RW, 캐시 속성,
      composite region = 페이지 범위 목록)
     → TX 버퍼에 기록
 [3] FFA_MEM_LEND ──────────▶ 디스크립터 검증
                              소유권 상태 갱신
                              Camera Stage-2 매핑 제거
                              64-bit handle 발급
     ◀────────────── handle
 [4] handle 전달 ────────────────────────────────────────────▶ (FFA_MSG_SEND_DIRECT_REQ
                                                               또는 기존 제어 채널)
 [5]                          영역 기술을 RX 버퍼로 반환 ◀──── FFA_MEM_RETRIEVE_REQ(handle)
                              AI Stage-2 매핑 생성 ──────────▶
 [6]                                                           retrieve된 IPA 범위를
                                                               dma-buf로 import
                                                               → 장치/추론 엔진 사용
 [7]                          AI Stage-2 매핑 제거 ◀────────── FFA_MEM_RELINQUISH
 [8] FFA_MEM_RECLAIM ───────▶ Camera 매핑 복원,
                              소유권 상태 원복
     (버퍼 풀로 반환, 다음 프레임에 재사용)
```

- **[0] RXTX 버퍼**: 트랜잭션 디스크립터가 레지스터에 담기지 않으므로, 각 endpoint는 `FFA_RXTX_MAP`으로 하이퍼바이저와 공유하는 TX/RX 버퍼 쌍을 등록해 둔다.
- **[2] composite region**: 버퍼가 물리적으로 조각나 있으면 디스크립터의 주소 범위 목록이 길어진다. TX 버퍼 크기를 넘으면 `FFA_MEM_FRAG_TX/RX`(v1.1)로 분할 전송한다. CMA/contiguous heap에서 할당하면 범위 1~수 개로 억제되어 디스크립터 비용이 최소화된다.
- **[4] handle 전달**: handle 자체는 비밀이 아니지만(하이퍼바이저가 retrieve 요청자의 endpoint ID를 디스크립터의 수신자 목록과 대조해 거부하므로), 전달 채널은 필요하다. FF-A 직접 메시지를 쓰면 스택이 FF-A로 단일화되고, 기존 vsock 제어 채널을 쓰면 DP-C1 C1-4(제어·데이터 분리)와 동형이 된다.
- **[6] 수신 측 import**: retrieve 응답의 IPA 범위로 sg_table을 구성해 dma-buf로 감싸는 importer 드라이버가 게스트 커널에 필요하다. 이후 게스트 내 장치(NPU 등)나 사용자 공간은 일반 DMABUF와 동일하게 사용한다.

SHARE 기반 풀이라면 [1]~[5]가 파이프라인 구성 시 1회만 수행되고, 반복 구간은 "링 인덱스 갱신 + 알림"만 남는다. 알림은 FF-A v1.1의 **notification** 메커니즘(`FFA_NOTIFICATION_SET/GET`)이나 직접 메시지로 처리할 수 있다.

## 4. 리눅스 구현 요소

| 계층 | 구성요소 | 상태 |
|------|----------|------|
| 게스트 커널 FF-A 전송 | `drivers/firmware/arm_ffa` — `ffa_mem_share/lend()`, 파티션 검색, 메시지/notification API | 메인라인 (5.14+) |
| 버퍼 할당 | dma-buf heaps (`/dev/dma_heap/*`, CMA/system heap) | 메인라인 |
| 송신 측 접합 | dma-buf의 sg_table → FF-A 메모리 트랜잭션 디스크립터 변환 + LEND/SHARE 호출 드라이버 | 신규 개발 필요. Linaro의 restricted/protected dma-buf heap(디코더 보안 버퍼를 FF-A로 Secure World에 lend) 패치가 동일 패턴의 선행 사례 |
| 수신 측 접합 | RETRIEVE 결과를 dma-buf로 export하는 importer 드라이버 | 신규 개발 필요 |
| 하이퍼바이저 | VM 간 FF-A relayer (디스크립터 검증, Stage-2 조작, handle 관리) | **핵심 확인 사항** — 아래 5절 |

## 5. 제약과 확인 사항 (본 과제 관점)

1. **pKVM의 relayer 지원 범위 (CS-02 관문)**: 현재 AVF의 pKVM은 host↔Secure World FF-A 중재(EL2 FF-A proxy)와 pKVM 고유 hypercall(`MEM_SHARE` 0xc6000003 등, `99_pvmfw.md` 3.4절)을 제공하며, **pVM을 FF-A endpoint로 취급하는 guest-to-guest relayer는 스펙상 정의만 있고 upstream 구현이 완결되어 있지 않다**. 따라서 실제 채택 전에는 (a) 대상 커널의 pKVM이 VM 간 FF-A 트랜잭션을 지원하는지, (b) 미지원 시 pKVM 고유 lend/share hypercall로 동일 의미론을 구성할 수 있는지(EL2 수정 불가 제약 내에서)를 확인해야 한다. 이 확인은 DP-C1 C1-3의 "hypercall 의미론 실현 가능성 선행 확인"과 동일한 관문이다.
2. **캐시 일관성**: 디스크립터의 메모리 속성(Normal WB, shareability)이 양쪽 매핑에서 일치해야 하며, non-coherent 장치(카메라 ISP, NPU)가 개입하면 소유권 이전 시점에 캐시 유지보수(clean/invalidate)가 프레임당 비용으로 추가된다 — QA-04(5ms) 예산 산정에 포함할 것.
3. **잔류 데이터(VOS-08)**: LEND 순환에서 RECLAIM으로 돌아온 버퍼에는 이전 프레임이 남아 있다. 풀 반환 전 소거 또는 "다음 기록이 전체 덮어쓰기임을 보장"하는 프로토콜이 필요하다. DONATE와 달리 LEND/SHARE는 스펙이 소거를 강제하지 않는다(트랜잭션 디스크립터의 zero-memory 플래그는 relayer 구현 의존).
4. **성능 예산**: LEND 방식은 프레임당 hypercall 4회(LEND/RETRIEVE/RELINQUISH/RECLAIM) + Stage-2 갱신 + TLB 무효화가 고정 비용이다. 30fps 기준 실측으로 QA-04 잔여 예산을 확인해야 하며, 미달 시 SHARE 풀 + notification 조합으로 전환하는 것이 FF-A 내에서의 자연스러운 후퇴 경로다.
5. **격리 논증 관점의 이점**: 소유권 상태와 Stage-2 매핑이 모두 하이퍼바이저(relayer) 한 곳에서 강제되므로, "Host 및 비수신 도메인은 프레임에 접근 불가"라는 QA-01 논증이 FF-A 상태 기계 하나로 환원된다. 표준 ABI라서 격리 증빙(QA-07)의 시험 시나리오도 스펙의 상태 전이표를 그대로 재사용할 수 있다.

## 요약

- DMABUF는 "게스트 내부"의 버퍼 공유 추상화이고, FF-A 메모리 관리 ABI는 "도메인 간" 소유권 이전 추상화다. 둘을 잇는 접합 드라이버(sg_table ↔ 트랜잭션 디스크립터 변환) 2개를 게스트에 추가하면, pVM 간 zero-copy DMABUF 공유가 표준 ABI 위에서 성립한다.
- SHARE(상시 풀, 성능 우선)와 LEND(프레임 단위 배타 이전, 기밀성 우선)는 같은 인프라의 구성 차이이므로, DP-C1의 C1-1/C1-3 후보를 늦게 바인딩(late-binding)할 수 있는 공통 기반이 된다.
- 단, pKVM의 VM 간 relayer 구현 성숙도가 채택의 선행 관문이며, 미성숙 시 pKVM 고유 hypercall로 동일 의미론을 구성하는 대안 경로를 함께 설계해 두어야 한다.