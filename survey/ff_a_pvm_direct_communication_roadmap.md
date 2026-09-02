# Arm FF-A와 pVM 간 직접 통신·향후 기능 조사

- 조사일: 2026-09-02
- 상태: 공개 규격·공식 문서·원본 코드 기준 기술 조사
- 대상: 로봇용 Custom SoC의 Linux-native pKVM Framework
- 관련 모듈: M-02 pVM Lifecycle Manager, M-03 Multi-pVM Orchestrator,
  M-04 Fault/Recovery Manager, M-05 Workload Loader / Verifier,
  M-06 Protected Policy Authority, M-07 Secure Inter-domain Channel,
  M-08 HW IP Mediation Layer, M-09 DMA/S2MPU Isolation Controller
- 기준: `FF-A 규격의 가능 범위`, `Linux/TF-A 구현`, `upstream pKVM`,
  `Android downstream pKVM·AVF`를 서로 구분한다.

## 1. 조사 질문과 결론

이 문서는 다음 질문에 답한다.

1. Arm FF-A는 어떤 기술이고 현재 어느 수준까지 공개됐는가?
2. 앞으로 추가되는 FF-A 기능은 무엇인가?
3. FF-A 규격으로 pVM 간 직접 통신과 메모리 공유가 가능한가?
4. 현재 pKVM/AVF에서 가능한가?
5. 가능하지 않다면 공개적으로 추가 계획이나 일정이 있는가?

대상 제품은 Android가 아니라 Linux-native pKVM Framework다. AVF/AOSP는 공개
capability와 구현 선례를 확인하는 자료이지 제품 runtime/API 의존성이 아니다.
적용 판단은 현재 요구사항인 Camera pVM→AI pVM 두 domain에 한정하며 임의 N-domain
message bus의 설계는 범위 밖이다.

### 1.1 한눈에 보는 답

| 질문 | 판정 | 근거 수준 |
| --- | --- | --- |
| 현재 최신 FF-A 문서 | **v1.3 ALP5, 2026-07-14** | Arm 공개 문서 |
| 현재 최신 정식 Release | **v1.2 REL0, 2024-08-05** | Arm 공개 문서 |
| FF-A 규격상 VM↔VM direct message | **가능** | v1.3의 direct-message 전달 규칙 |
| FF-A 규격상 VM↔VM indirect message·notification | **가능** | v1.3의 명시적 VM-to-VM 흐름 |
| FF-A 규격상 VM↔VM donate/lend/share | **가능** | DEN0140의 역할 조합 표 |
| upstream Linux `arm_ffa` | **v1.2 sender 중심 구현** | Linux mainline 원본 코드 |
| upstream Linux pKVM의 FF-A | **Host↔Secure World 보호 proxy** | Linux mainline 원본 코드 |
| Android downstream pKVM guest FF-A | **pVM→Secure Partition 방향 일부 지원** | ACK 원본 코드 |
| 현재 AVF guest pVM↔guest pVM 직접 통신 | **불가** | AOSP Security·API 문서 |
| pKVM의 pVM↔pVM 직접 통신 공개 일정 | **확인하지 못함** | AOSP·ACK·upstream 공개 자료 조사 |

핵심 결론은 다음 두 문장이다.

> **FF-A 규격에는 VM 간 통신과 메모리 거래를 구성할 표준 모델이 이미 있다.**

> **그러나 2026-09-02 현재 공개된 pKVM/AVF 구현에는 guest pVM 사이를 연결하는
> FF-A relayer·receiver 경로가 없고, 이를 추가하겠다는 확정 일정도 공개 자료에서
> 확인하지 못했다.**

여기서 “직접”은 Host Linux 사용자 영역을 자료 경로로 거치지 않는다는 뜻으로
사용한다. FF-A도 Hypervisor라는 신뢰 중재자가 endpoint ID, scheduling과 Stage-2
mapping을 관리한다. 물리적으로 중재자 없이 peer가 서로 접근한다는 뜻은 아니다.
또한 `pVM`은 Android/pKVM의 protected VM 용어이지 FF-A 규격 용어가 아니다.
FF-A가 정의하는 `VM↔VM` 모델에 pVM을 적용하려면 pKVM의 별도 구현과 보안 policy가
필요하다.

### 1.2 공개 계획에 대한 정확한 답

“계획이 없다”고 단정할 근거는 없다. 내부 Android/OEM/SoC vendor 계획은 공개되지
않을 수 있다. 확인 가능한 범위에서 정확한 표현은 다음과 같다.

- 공개된 Arm 문서는 FF-A 규격 자체를 v1.3으로 확장하고 있다. 특히
  `Inter-partition setup protocol`에는 향후 protocol version 협상과 callee의
  memory map/unmap을 요청하는 메시지를 추가한다는 공개 방향이 있다.[S22] 다만
  이는 ALP4에도 있던 비규범적 `Issue` note이며 target version·날짜·encoding은 없다.
- Android downstream은 pVM이 FF-A를 이용해 Secure World의 SP와 통신하는 범위를
  넓히고 있다.
- Linux·TF-A도 FF-A v1.2와 일부 v1.3 기능을 계속 구현하고 있다.
- 그러나 이 표준 방향은 Android/pKVM 구현 약속이 아니다. **guest pVM↔guest pVM
  routing, target Android release, 공개 API와 완료 일정**을 약속한 AOSP 문서나
  accepted upstream patch series는 찾지 못했다.

따라서 이 기능을 제품 일정의 전제로 두면 안 된다. 대상 SoC vendor가 별도 기능을
제공한다는 증거가 나오기 전까지는 “미지원 capability”로 관리해야 한다.

## 2. 조사 방법과 증거 등급

공식 규격, 공식 프로젝트 문서와 원본 코드를 우선 확인했다. 기존 저장소의
`old/docs/99_ffa.md`와 `old/docs/99_pvm_dmabuf_transfer.md`는 질문과 가설을 찾는
용도로만 사용하고 결론의 근거로 사용하지 않았다.

| 등급 | 의미 | 이 문서의 예 |
| --- | --- | --- |
| Published specification | 표준이 기능과 동작을 정의 | FF-A v1.3 VM-to-VM 흐름 |
| Released implementation | 공식 release나 mainline에 코드가 존재 | Linux `arm_ffa` v1.2 |
| Android downstream | ACK에는 있으나 upstream Linux와 다름 | guest FF-A handler |
| Posted/FROMLIST | 검토 중이며 merge를 보장하지 않음 | 일부 pKVM FF-A 보완 patch |
| Experimental/ALP | 변경 가능한 preview | FF-A v1.3 ALP5, SP live activation |
| No public evidence | 공개 약속·일정을 찾지 못함 | pVM↔pVM pKVM roadmap |

“규격에 있다”는 “현재 제품에서 된다”와 다르고, “patch가 게시됐다”는 “release에
포함된다”와 다르다. 이 문서의 로드맵 판정은 이 차이를 유지한다.

## 3. FF-A의 기술적 위치

### 3.1 SMC와 FF-A는 비교 대상 계층이 다르다

`SMC`는 CPU가 Secure Monitor로 예외를 발생시키는 instruction/conduit다. FF-A는
SMCCC 위에서 endpoint, message, scheduling, notification과 memory transaction의
의미를 표준화한 ABI와 실행 모델이다. 구현은 상황에 따라 SMC, HVC, SVC와 ERET
conduit를 사용한다.

```text
Application protocol / device protocol
                |
FF-A partition message, notification, memory transaction
                |
FF-A ABI: discovery, direct/indirect message, scheduling, lifecycle
                |
SMCCC conduit: SMC / HVC / SVC / ERET
                |
Exception level, Stage-2 MMU, interrupt controller, SMMU/IOMMU
```

따라서 FF-A를 “새로운 SMC 대체 transport”라고 설명하면 부정확하다. FF-A direct
message도 임의 byte stream이 아니라 request를 받은 endpoint에 CPU cycle을
넘기고 response를 기다리는 동기 procedure-call 모델이다.

### 3.2 FF-A가 표준화하는 기능

- endpoint ID, UUID, partition property와 discovery
- register 기반 synchronous direct request/response
- endpoint TX/RX buffer 기반 asynchronous indirect message
- global/per-vCPU notification과 virtual interrupt 연계
- `FFA_RUN`, `FFA_YIELD`, `FFA_MSG_WAIT` 등을 통한 scheduling·execution state
- memory `DONATE`, `LEND`, `SHARE`, `RETRIEVE`, `RELINQUISH`, `RECLAIM`
- partition boot, stop, abort와 lifecycle
- Hypervisor와 SPM/SPMC 사이의 routing과 역할 분담

이 기능은 “보낼 수 있는 ABI”뿐 아니라 sender/receiver/relayer의 권한 검사와
상태 전이를 정의한다. 실제 isolation은 Hypervisor·SPM의 Stage-2/S-Stage-2와
platform DMA isolation 구현이 강제해야 한다.

## 4. 버전과 향후 기능

### 4.1 버전 흐름

| 버전 | 공개 시점·품질 | 주요 변화 | 제품 판단 |
| --- | --- | --- | --- |
| v1.0 REL | 2020-07-24 | 초기 partition discovery, direct message, memory management, scheduling | 오래된 공통 기반 |
| v1.1 REL0 | 2022-11-30 | notification, indirect messaging 확대, VM/SP runtime·interrupt·power guidance | 현재 생태계의 중요한 baseline |
| v1.2 REL0 | 2024-08-05 | `DIRECT_REQ2/RESP2`, extended registers, `FFA_CONSOLE_LOG`, register discovery, 여러 UUID, periodic wake, memory supplement 분리 | 최신 정식 Release |
| v1.3 ALP2 | 2025-07-09, Alpha | 최대 384 notification, `*2` notification ABI, `FFA_ABORT`, partition lifecycle/LFA, ACPI FF-A device 등 | preview |
| v1.3 ALP3 | 2025-10-17, Alpha | version 재협상·query, direct message x8-x17, 64-bit cycle-management 지원 표시 | preview |
| v1.3 ALP4 | 2026-02-12, Alpha | `FFA_VERSION` framework message의 64-bit direct encoding, 시작·중지 상태의 `FFA_RUN`, LFA 호환성 guidance 등 | preview |
| v1.3 ALP5 | 2026-07-14, Alpha | Inter-partition setup message discovery, ACPI FF-A guidance의 BETA 승격과 호환성·forwarding 명확화 | 최신 공개 preview |

[Arm FF-A v1.3 ALP4↔ALP5 공식 diff][S22]는 ALP5의 release information과 전체
변경 표시를 제공한다. [ALP3↔ALP4 diff][S1]와 [v1.3 ALP2 전체 규격][S2]은 이전
revision의 상세 change log를 교차 확인하는 데 사용했다.

가장 중요한 버전 해석은 다음과 같다.

- 최신 번호는 v1.3이지만 문서 품질은 `ALP`, 즉 변경 가능한 Alpha다.
- 안정적인 조달·상호운용 baseline은 여전히 v1.2 REL0로 보는 편이 안전하다.
- 새 v1.3 기능 목록은 implementation roadmap이나 Android release 약속이 아니다.
- pVM↔pVM 기능은 v1.3에서 새로 생긴 것이 아니다. 기존 FF-A architecture가 이미
  VM endpoint와 Hypervisor relayer 모델을 포함한다.

### 4.2 v1.3에서 추가되는 기능의 의미

#### 더 많은 event와 확장 ABI

v1.3 ALP2는 notification을 64개에서 최대 384개로 늘리고
`FFA_NOTIFICATION_BIND2`, `UNBIND2`, `SET2`, `GET2`와 일부 bitmap 조회 기능을
추가했다. endpoint·vCPU·service가 늘어나는 platform에는 유용하지만 Linux
mainline driver는 현재 최대 64개를 전제로 한다.

#### lifecycle와 live firmware activation

`FFA_ABORT`, partition의 전체 lifecycle guidance, image UUID, SP live activation
guidance가 추가됐다. ALP4는 현재 image와 target image가 호환되지 않을 때의 처리
guidance도 보강했다. 이는 **Secure Partition update**에 관한 기능이며 guest
pVM-to-pVM channel roadmap은 아니다.

Trusted Firmware-A 2.15에는 FVP를 중심으로 live activation 구현이 들어가지만
별도 build option으로 켜는 실험적 기능이다. production SoC에 자동으로 제공된다고
볼 수 없다.[S12][S13][S19]

#### 더 넓은 register와 64-bit 실행 관리

ALP3는 direct request/response가 x8-x17을 사용하도록 확장하고 version 재협상과
64-bit CPU-cycle-management FID 표시를 추가했다. ALP4는 `FFA_VERSION` framework
message의 64-bit direct encoding과 시작·중지 상태의 `FFA_RUN`을 추가했다. 큰
payload transport라기보다 ABI expressiveness와 version interoperation 개선이다.

#### OS integration

ACPI FF-A device와 OS driver integration guidance, Guarded memory/BTI manifest
property, inter-partition setup protocol, Non-secure resource information ABI가
추가됐다. server/ACPI platform과 lifecycle 자동화에는 중요하지만 pKVM이 Normal
World VM 사이의 routing을 구현하게 만들지는 않는다.

ALP2에서 도입된 `Inter-partition setup protocol`은 현재 partition 쌍 사이의
notification 등록·해제 메시지를 `DIRECT_REQ2/RESP2`로 교환한다. ALP5는 이 protocol
message를 discovery하는 방법을 추가했다. 규격 §18.7의 비규범적 `Issue` note는 향후
revision에 protocol version 협상과 caller가 callee에 memory map/unmap을 요청하는
메시지를 추가한다고 명시한다.[S22] 이 note는 ALP4에도 있었고 target version·날짜,
message encoding과 보안 semantics는 정하지 않았다. 따라서 **Arm 표준 계층의 공개
future signal**이지만 Android pVM peer routing이나 release commitment는 아니다.

별도 memory supplement ALP5는 일부 page만 회수할 수 있는 optional
`FFA_MEM_RECLAIM2`를 추가했다. 큰 영역의 회수 지연을 줄이는 lifecycle 개선이며,
trust boundary와 EMAD `Cookie` 의미도 명확히 했다.[S23] FF-A memory management가
v1.2부터 base 문서에서 DEN0140으로 분리됐다는 점과 함께 읽어야 한다.

### 4.3 공개 최신 규격과 구현의 차이

| 계층 | 공개 확인 상태 | v1.3과의 차이 |
| --- | --- | --- |
| Arm base specification | v1.3 ALP5 | 규격 자체가 Alpha |
| Arm memory supplement | v1.3 ALP5 | `FFA_MEM_RECLAIM2` 추가, 규격 자체가 Alpha |
| Linux `arm_ffa` master | `FFA_VERSION_1_2`, notification 64 | v1.3 expanded notification 등 미구현 |
| Linux upstream pKVM FF-A proxy | Host client 한 개, Host↔SPMD 보호 | guest virtual FF-A instance 없음 |
| Android downstream pKVM | guest→Secure World proxy 일부 존재 | 같은 Normal World VM receiver/routing 없음 |
| AVF framework API | app/Host↔pVM channel | guest pVM↔guest pVM 연결 금지 |

규격 버전만 보고 platform capability를 추정하면 안 된다. boot 시
`FFA_VERSION`·`FFA_FEATURES`, Hypervisor capability와 양쪽 endpoint driver를
각각 확인해야 한다.

## 5. FF-A 규격상 pVM 간 통신

### 5.1 규격에는 이미 VM↔VM 모델이 있다

안정판 FF-A v1.2 REL0의 core direct-message 규칙은 partition manager가 관리하는
Receiver가 VM이면 Hypervisor가 Non-secure virtual FF-A instance에서 ERET conduit로
request와 response를 전달하도록 정의한다.[S24] v1.3 ALP도 이 모델을 유지한다.[S2]
이는 같은 Hypervisor가 관리하는 두 VM을 포함하는 일반 모델이다.

부록은 더 명시적으로 다음 흐름을 제시한다. 해당 부록의 diagram format은
`Provisional`이지만 VM-to-VM notification·indirect message의 존재와 core ABI
요건은 별도로 정의돼 있다.

- VM1이 VM0에 `FFA_NOTIFICATION_SET`; Hypervisor가 virtual notification-pending
  interrupt를 VM0에 inject; VM0가 `FFA_NOTIFICATION_GET`
- VM1이 `FFA_MSG_SEND2`; Hypervisor가 VM1 TX buffer의 message를 VM0 RX buffer로
  복사하고 notification으로 VM0를 깨움

[FF-A Memory Management Protocol v1.2 REL0][S3]의 표 1.7과 1.8은 더 직접적이다.
최신 ALP5의 memory 변경점은 별도로 4.2절과 [S23]에 정리했다.

| Sender | Receiver | Relayer | 거래 |
| --- | --- | --- | --- |
| VM | VM | Hypervisor | donate/lend/share |
| VM (borrower) | VM (lender) | Hypervisor | relinquish |

따라서 “FF-A는 Secure World 전용이라서 VM-to-VM은 규격상 불가능하다”는 설명은
틀리다. 반대로 “규격에 있으므로 현재 pKVM에서 된다”는 설명도 틀리다.

문헌 검색 때 대소문자도 구분해야 한다. Hafnium 자료의 `PVM`은 보통
`Primary VM`을 뜻하며 Android의 lowercase `pVM`, 즉 `protected VM`과 다르다.
Hafnium의 Primary VM→Secondary VM direct-message 구현을 Android protected
VM↔protected VM 지원 근거로 사용할 수 없다.[S21]

### 5.2 direct, indirect, notification, memory의 차이

| 기능 | 전달 자료 | 실행 의미 | Camera→AI 적용 |
| --- | --- | --- | --- |
| Direct message | register의 작은 request/response | receiver를 동기 호출, caller는 response 대기 | setup·작은 control·handle 전달 |
| Indirect message | sender TX→receiver RX copy | notification 후 receiver가 비동기 처리 | metadata/event, bulk frame에는 작음 |
| Notification | bitmap bit와 vIRQ | event 알림, payload 없음 | ring index·buffer-ready 알림 |
| `MEM_SHARE` | page 접근을 sender와 receiver가 함께 보유 | 장기 shared pool | 성능 우선 고정 pool |
| `MEM_LEND` | sender 접근을 제거하고 borrower에 임시 부여 | 배타적 handoff 후 반환 | 기밀성 우선 frame handoff |
| `MEM_DONATE` | ownership 자체 이전 | 반환을 전제하지 않음 | 순환 frame에는 부적합 |

DMA-BUF file descriptor는 한 Linux kernel instance에만 의미가 있다. FF-A가 fd를
VM 사이로 보내 주는 것은 아니다. 실제 구현은 producer DMA-BUF의 page/SG 목록을
FF-A memory descriptor로 바꾸고, receiver VM에서 받은 IPA page를 새 DMA-BUF로
감싸야 한다. cache ownership, DMA mapping, fence와 device reset은 FF-A message
하나로 해결되지 않는다.

## 6. 현재 Linux와 pKVM 구현

### 6.1 Linux mainline `arm_ffa` driver

[Linux mainline `drivers/firmware/arm_ffa/driver.c`][S4]와 해당 Kconfig[S11]는 현재
다음을 보여 준다.

- driver version은 `FFA_VERSION_1_2`
- 최대 notification 수는 64
- partition discovery, direct request/response와 `REQ2/RESP2`
- indirect send, notification API
- memory `share`, `lend`, `reclaim`

그러나 `struct ffa_mem_ops`에는 `memory_reclaim`, `memory_share`, `memory_lend`만
있고 `FFA_MEM_RETRIEVE_REQ` 문자열과 borrower operation이 없다. Linux가 SP에
memory를 주는 기존 sender 사용례에는 충분하지만, 다른 VM이 준 memory를 guest
Linux가 retrieve하고 relinquish하는 pVM receiver에는 부족하다.

### 6.2 upstream Linux pKVM

[upstream pKVM `ffa.c`][S5]의 파일 설명과 코드는 다음 구조다. pKVM의 일반 보호
모델은 upstream 문서[S14]와 교차 확인했다.

```text
Host Linux FF-A client
        |
        | SMC trap/filter + Host Stage-2 ownership check
        v
pKVM EL2 FF-A proxy
        |
        | forward
        v
SPMD at EL3 -> SPMC / Secure Partition
```

목적은 악성 Host가 pVM 또는 Hypervisor memory를 FF-A로 Secure World에 노출하지
못하게 하는 것이다. 코드 주석도 host buffer 하나만 사용하는 `one client` 구조를
명시한다. guest마다 virtual endpoint를 만들고 다른 guest vCPU로 message를
전달하는 VM router가 아니다.

### 6.3 Android downstream pKVM

Android Common Kernel에는 upstream보다 앞선 guest FF-A support가 있다.
[Android 17 ACK 공개 `ffa.c`][S6]에서 guest handler는 다음 호출 일부를
처리한다.

- `FFA_VERSION`, `FFA_FEATURES`, `FFA_ID_GET`, partition discovery
- guest RX/TX map/unmap
- guest memory share/lend/reclaim
- direct request와 FF-A 1.1 notification 논리 interface 7종: bitmap create/destroy,
  bind/unbind, set/get, info-get. Info-get은 32/64-bit FID를 모두 처리한다.

또한 pVM별 FF-A handle과 `FFA_ID_GET`, Secure World 결과를 받는
`FFA_PARTITION_INFO_GET`, VM creation/destruction을 SP에 알리는 lifecycle message,
종료 시 transfer reclaim 경로가 있다. 이는 peer 지원에 재사용할 수 있는 기반이지만,
현재 실제 경로는 다음과 같이 Secure World를 향한다.

- direct request는 source endpoint 위조를 검사한 뒤 SMC로 SPMD에 전달한다.
- memory share/lend도 receiver 한 개와 guest sender를 검증한 뒤 Secure World의
  physical FF-A instance로 전달한다.
- guest가 borrower로 호출하는 `FFA_MEM_RETRIEVE_REQ`·`FFA_MEM_RELINQUISH`, indirect
  `FFA_MSG_SEND2`와 guest receiver-side delivery는 지원 목록에 없다. 다만 EL2의
  Host reclaim descriptor 복원 경로는 내부적으로 `FFA_MEM_RETRIEVE_REQ`를
  사용하므로 “코드 어디에도 retrieve가 없다”는 뜻은 아니다.
- destination guest를 찾아 해당 pVM vCPU에 ERET로 전달하는 Normal World router가
  없다.

즉 공개 downstream 기능은 **pVM→Secure Partition/TrustZone** 경로를 활성화한
것이지 **pVM A→pVM B** 경로를 구현한 것이 아니다. 2026년 ACK backport commit도
upstream에는 guest FF-A support가 없어서 conflict를 조정했다고 명시한다.[S7]
Android 16의 pKVM enable 경로 주석도 이 capability를 FF-A를 통한 Secure 측 IPC
channel로 설명한다.[S18]

### 6.4 AVF의 현재 policy와 API

[AOSP AVF Security 문서][S8]는 guest pVM이 다른 guest pVM과 직접 상호작용하거나
vsock 연결을 만들 수 없고, Host pVM의 `VirtualizationService`만 pVM과의 channel을
만들 수 있다고 명시한다. 생성한 channel을 다른 주체에 넘길 수는 있지만 그
구조도 Host가 setup을 중재한다.

[AVF framework API README][S9]도 VM은 자신을 시작한 app의 연결을 받을 수 있지만
다른 VM 또는 Host Android의 다른 process로 연결을 시작할 수 없다고 명시한다.
Binder RPC도 underlying vsock을 사용하고 file descriptor를 보낼 수 없다.

AOSP의 별도 `VirtualizationService` 설명[S10]에는 “pVMs 간 주 interface가
vsock”이라는
모호한 문장이 있으나, Security 문서와 실제 app-facing API의 명시적 제한이 더
구체적이다. 이 문장을 guest-to-guest 직접 vsock 지원의 증거로 사용하면 안 된다.

## 7. 왜 현재 pVM↔pVM FF-A가 동작하지 않는가

규격을 현재 pKVM에 단순히 enable하는 것으로는 충분하지 않다. Android downstream에
이미 있는 부분과 pVM peer를 위해 새로 필요한 부분을 구분해야 한다.

| 재사용 가능한 downstream 기반 | 현재 한계 |
| --- | --- |
| EL2가 각 pVM에 제공하는 FF-A handle과 virtual endpoint context | Secure World proxy용이며 peer-visible registry·route가 아님 |
| guest RX/TX buffer와 sender-side share/lend/reclaim | pVM borrower retrieve/relinquish가 없음 |
| direct request와 notification proxy | request·event가 Secure World를 향함 |
| VM availability message와 teardown/reclaim | SP notification·sender transfer 정리이며 peer 양쪽 lifecycle protocol이 아님 |

FF-A memory protocol에서 Hypervisor의 역할은 endpoint owner가 아니라 **Relayer**다.
따라서 “EL2 endpoint를 하나 더 만든다”보다, EL2가 VM별 virtual FF-A context와
peer identity를 연결하고 Relayer로서 policy·mapping·delivery를 집행한다고 표현하는
것이 정확하다. 최소한 다음 결정적 기능이 추가돼야 한다.

| 계층 | 추가로 필요한 결정적 기능 | 보안·복구 요구 |
| --- | --- | --- |
| pKVM EL2 | 같은 Normal World pVM의 peer registry·endpoint routing | ID spoofing 방지, VM generation·epoch·capability에 binding |
| M-06 + pKVM EL2 | M-06의 policy/capability 판정과 EL2 same-world routing 집행 | 허용된 producer/consumer만 연결, EL2에 일반 policy parser 금지 |
| pKVM EL2 | direct request/response의 receiver vCPU delivery와 call chain | waiting/blocked/preempted state와 timeout |
| pKVM EL2 | `SEND2` RX/TX ownership과 peer notification/vIRQ | malicious peer의 flood·stale event 제한 |
| pKVM EL2 | VM→VM share/lend/retrieve/relinquish/reclaim | 양쪽 Stage-2 mapping과 단일 handle 상태 기계 |
| guest Linux | borrower `RETRIEVE_REQ`·`RELINQUISH` | fragment, permission과 address 검증 |
| guest Linux | SG page↔DMA-BUF bridge | cache, DMA direction, fence, importer lifetime |
| DMA isolation | platform DMA isolation mapping 전환 | Host와 비수신 device의 DMA 차단 |
| lifecycle | stop/crash/force-kill cleanup | orphan handle 회수, unmap, reset, zeroize |

가장 중요한 공백은 sender API가 아니라 **receiver와 relayer**다. producer가
`FFA_MEM_LEND`를 호출할 수 있어도 Hypervisor가 target pVM을 receiver로 인정하고
mapping을 만들며, receiver Linux가 retrieve하지 못하면 거래가 완성되지 않는다.

## 8. 공개 로드맵 판정

### 8.1 공개적으로 진행 중인 인접 작업

다음은 실제 공개 개발 방향이지만 pVM↔pVM 지원 약속과 동일하지 않다.

- FF-A Inter-partition setup protocol의 discovery와 향후 protocol version·callee
  memory map/unmap request 계획
- FF-A v1.3의 expanded notification, 64-bit ABI, lifecycle와 SP live activation
- Linux `arm_ffa` v1.2 기능의 유지·확장
- TF-A/Hafnium의 SPMC·SP 기능과 live activation
- Android downstream의 guest pVM→Secure Partition FF-A proxy
- pKVM의 protected memory, IOMMU/DMA isolation과 teardown 강화

확인 가능한 최신 상세 [TF-A 공개 roadmap(2025-11)][S17]도 SP live activation,
Hafnium feature discovery, Rust SPMC·FF-A SPMD와 secure interrupt를 다루지만
pVM↔pVM Normal World routing은 항목에 없다. 이는 TF-A/SPM의 범위상 자연스러운
결과이며, Android pKVM 내부 계획 부재의 증거로 확대 해석하지 않는다.

2026-08-30에 게시된 upstream KVM v7 `Support FF-A direct messaging interfaces`
patch series도 제목만으로 pVM peer 기능처럼 읽으면 안 된다. 명시된 use case는
pKVM을 켠 Host의 TPM CRB over FF-A이고 변경 대상도 **host handler→SP/EL3** direct
request다. guest-to-guest route가 아니다.[S20]

여기서는 표준과 제품 roadmap을 분리해야 한다.

| 계층 | 공개 future signal | 판정 |
| --- | --- | --- |
| Arm FF-A 표준 | setup protocol의 비규범적 Issue note에 version 협상·callee map/unmap message를 향후 추가 | 방향은 있으나 version·일정·encoding 미정[S22] |
| Linux/Android pKVM 구현 | pVM peer registry·routing·borrower API의 accepted series | 확인하지 못함 |
| AVF 제품/API | guest-to-guest authorization/API와 target release | 확인하지 못함 |

인접 작업은 향후 pVM peer channel의 일부 기반이 될 수 있다는 **추론**은 가능하다.
그러나 Arm의 향후 protocol message가 receiver VM routing을 자동 제공하지 않고,
public pKVM·AVF 계획도 없으므로 이를 Android pVM-to-pVM release roadmap으로
해석할 수 없다.

### 8.2 찾지 못한 공개 증거

2026-09-02 기준 다음 항목은 공식 AOSP 문서, ACK 공개 code/tag, upstream Linux
mainline과 공개 FF-A/TF-A 자료에서 찾지 못했다.

- Android/pKVM의 “guest pVM-to-guest pVM direct communication” feature commitment
- target Android version 또는 ACK release
- guest-to-guest FF-A relayer의 accepted upstream patch series
- AVF application API와 authorization model
- pVM receiver용 Linux `MEM_RETRIEVE_REQ`/DMA-BUF API
- 성능·failure semantics·security requirement와 compatibility test

이 부재는 “Google이나 vendor 내부에 계획이 없다”는 증거가 아니다. 공개적으로
제품 일정을 세울 근거가 없다는 뜻이다.

### 8.3 채택 판단

| 판단 | 현재 판정 |
| --- | --- |
| 장기 architecture 후보로 FF-A semantics 사용 | 조건부 적합 |
| 공개 upstream만으로 즉시 구현 | 부적합 |
| Android downstream을 가져오면 pVM↔pVM 해결 | 부적합 |
| vendor가 VM relayer·borrower를 제공하면 적용 | PoC 후 가능 |
| 향후 Android release가 해결한다고 일정에 반영 | 근거 부족 |

## 9. Camera pVM→AI pVM 적용 판단

### 9.1 목표 구조

대상 시스템이 원하는 장기 data path는 개념적으로 다음과 같다.

```text
Camera pVM (owner/lender)        pKVM EL2 (relayer)       AI pVM (borrower)
        | FFA_MEM_LEND ---------------->| lender mapping 제거     |
        |<--------- handle -------------|                         |
        | control(handle)               |                         |
        |------------------------------>| route + notify          |
        |                               |------------------------>|
        |                               |<-- RETRIEVE_REQ --------|
        |                               | map receiver IPA         |
        |                               |------------------------>|
        |                               |<-- RELINQUISH -----------|
        | FFA_MEM_RECLAIM ------------->| owner mapping 복구       |
        |<---------- success -----------|                         |
```

Host Linux는 scheduling과 가용성을 방해할 수 있지만 frame의 CPU/Stage-2 mapping과
DMA mapping을 얻지 않는 것이 목표다. 이 보장은 FF-A 함수 이름이 아니라 실제
pKVM/S2MPU 구현과 negative test로 증명해야 한다.

### 9.2 이 프로젝트에서의 결론

- FF-A memory lifecycle은 M-07 channel과 M-09 isolation의 장기 contract 후보로
  좋다. vendor 독자 ABI보다 상태·역할·오류를 설명하기 쉽다.
- 현재 공개 stack에는 필요한 pVM↔pVM 구현이 없으므로 baseline으로 선택할 수 없다.
- 일반 pKVM core 개발·porting은 현재 범위 밖이다. 먼저 platform owner/vendor가
  동일 기능을 제공하는지 확인하고, 없다면 feasibility를 통과한 최소 EL2 interface나
  extension만 별도 architecture decision으로 다룬다. 배치와 ABI는 공개 pKVM
  hypercall·vendor module의 보안 경계도 함께 검토한다.[S15][S16]
- Host relay + end-to-end 기밀성·무결성·freshness/anti-replay와 endpoint identity·
  generation binding은 지금 만들 수 있지만 zero-copy가 아니고 Host DoS·삭제·지연을
  막지 못한다. Host 비관여·zero-copy data path의 대체물은 아니다.
- Secure Partition broker는 현재 guest FF-A 방향을 활용할 수 있으나 pVM-to-pVM
  direct가 아니다. 이는 TrustZone SP이며 저장소의 protected service pVM과 다르다.
  작은 Secure World memory와 TCB를 고려하면 control/authority에는 쓸 수 있지만
  bulk frame broker는 부적합하고 copy·scheduling 비용이 생길 수 있다.

`MEM_SHARE`의 장기 shared pool은 `MEM_LEND`와 보안상 동등한 fallback이 아니다.
성능 실험 후보로 사용하더라도 mapping을 pipeline epoch에 묶고 page·permission과
노출 시간을 최소화하며, revoke·zeroize·stale-frame 차단을 입증해야 한다. Camera와
AI HW lease도 memory 거래와 별개다. M-08은 이전 owner를 revoke한 뒤 request를
drain하고 reset/zeroize와 S2MPU 갱신을 완료한 후에만 새 owner에게 HW를 부여해야
한다.

### 9.3 vendor capability gate

SoC vendor에는 기능 이름이 아니라 다음 evidence를 요청해야 한다.

1. 두 protected VM endpoint 사이 direct/indirect message와 notification 지원 여부
2. VM→VM `MEM_SHARE` 또는 `MEM_LEND`의 sender·receiver ABI와 version
3. receiver의 retrieve/relinquish와 sender reclaim 지원 여부
4. Host CPU Stage-2와 Host device DMA mapping이 동시에 제거됨을 보이는 trace
5. Camera/NPU device assignment와 S2MPU mapping 전환 방식
6. receiver crash, sender crash, Host kill과 EL2 reset의 강제 회수 절차
7. buffer reuse 전 zeroize·cache maintenance·fence ordering
8. endpoint ID를 verified Workload identity(image/manifest/version/freshness), pVM
   generation, pipeline epoch와 policy version/capability에 binding하는 방식
9. supported kernel/firmware versions, ABI stability와 update policy
10. source, conformance test 또는 최소한 재현 가능한 security test 결과

이 질문에 답이 없으면 “FF-A compatible”이라는 marketing 문구만으로 기능을
채택하면 안 된다.

### 9.4 권장 PoC 순서

1. target board에서 Host·각 pVM·SPMC의 `FFA_VERSION`과 `FFA_FEATURES`를 dump한다.
2. pVM A가 pVM B endpoint를 discovery할 수 있는지 negative/positive test한다.
   허가된 Camera↔AI만 성공하고 제3 pVM과 이전 generation/epoch는 실패해야 한다.
3. 작은 direct message와 notification을 보내고 실제 receiver vCPU delivery를
   trace한다.
4. 한 page를 lend/retrieve/relinquish/reclaim하고 각 단계의 Stage-2 mapping을
   확인한다.
5. Host CPU read/write와 Host/제3 device DMA가 모두 실패하는지 공격 test한다.
6. receiver를 각 상태에서 강제 종료해 orphan handle, stale mapping과 data remanence를
   확인한다.
7. DMA-BUF bridge를 붙이고 buffer generation/handle/trace binding과 cache/fence
   correctness를 검증한다.
8. 마지막에 frame pool 크기, fps, latency, TLB invalidation과 S2MPU update 비용을
   측정해 `SHARE pool`과 frame별 `LEND`를 비교한다.

3단계가 실패하면 messaging조차 vendor 기능이 없는 것이고, 4단계가 실패하면
pVM-to-pVM data path의 선행 조건이 없다. DMA-BUF driver를 먼저 만드는 순서는
효율적이지 않다.

## 10. Claude 독립 검증

사용자 요청에 따라 2026-09-02에 옆 패널의 Claude agent
`claude_arch_review`에게 잠정 보고서와 1차 자료를 전달해 독립 검증을 요청했다.
검증 질문은 다음에 집중했다.

- FF-A 규격상 가능 범위와 pKVM 구현 범위를 혼동했는가?
- Android guest FF-A→Secure Partition 기능을 pVM↔pVM으로 잘못 해석했는가?
- v1.3 ALP 기능을 production roadmap처럼 과장했는가?
- 공개 계획을 찾지 못한 것을 내부 계획 부재로 단정했는가?

Claude는 핵심 방향인 “규격은 VM↔VM을 표현하지만 현재 공개 pKVM/AVF에는 pVM peer
경로와 확정 제품 일정이 없다”는 결론을 유지했다. 동시에 다음 정정을 요구했다.

| 검증 지적 | 독립 재확인 | 보고서 반영 |
| --- | --- | --- |
| 최신 문서는 ALP4가 아니라 **v1.3 ALP5, 2026-07-14** | Arm base·memory 공식 ALP4↔ALP5 diff[S22][S23] | 표·요약·추적 기준 수정 |
| §18.7에 향후 version 협상과 callee map/unmap request 방향이 있음 | Arm base의 비규범적 issue note[S22] | target version·일정 없는 표준 signal과 Android 제품 계획을 분리 |
| Android guest notification은 “일부”가 아니라 FF-A 1.1 interface 7종 | ACK exact source의 guest switch[S6] | 구현 범위 표현 수정 |
| EL2의 Host reclaim descriptor 복원은 `MEM_RETRIEVE_REQ`를 사용함 | ACK reclaim helper·guest allowlist[S6] | guest borrower API 부재로 범위를 한정 |
| pVM handle·ID, availability와 teardown 기반은 이미 있음 | ACK lifecycle·cleanup 경로[S6] | 재사용 기반과 peer 공백을 별도 표로 분리 |

Claude 의견 자체는 기술 근거로 사용하지 않았다. 각 지적은 위 공식 Arm 문서와 ACK
원본 코드로 다시 확인한 뒤 반영했다. 수정 완료본을 같은 Claude agent에 다시 보내
5개 핵심 정정의 반영 여부를 확인했고 **최종 판정 `FINAL PASS`**를 받았다. 남는
불확실성은 비공개 Android/OEM 계획과 target SoC vendor capability다.

## 11. 최종 판정과 추적 항목

### 11.1 최종 판정

- **규격 적합성:** FF-A는 pVM 간 control, event와 memory lifecycle을 표현할 수 있다.
- **현재 구현성:** 공개 upstream pKVM·AVF만으로는 pVM↔pVM 직접 통신이 안 된다.
- **Arm 표준 future signal:** setup protocol의 향후 version 협상·map/unmap message
  방향이 `Issue` note에 있지만 target version·일정·encoding은 없고, ALP 과정에서
  변경·삭제될 수 있다.
- **제품 로드맵:** Android/pKVM의 pVM peer 기능, release와 공개 API 일정은
  확인하지 못했다.
- **프로젝트 적용:** vendor capability가 확인될 때까지 장기 후보로만 유지한다.
- **현재 대안:** Host relay+E2E protection, control용 Secure Partition broker, 또는
  feasibility와 별도 승인을 통과한 최소 EL2 extension 중 요구사항에 맞춰 선택한다.

### 11.2 재조사 trigger

다음 사건이 발생하면 이 문서를 갱신한다.

- FF-A v1.3 `REL`, ALP6 또는 새 v1.4 ALP 공개
- Linux `arm_ffa`에 borrower retrieve/relinquish API merge
- upstream pKVM에 guest FF-A virtual instance merge
- ACK/AOSP에 guest-to-guest routing 또는 AVF API 공개
- target SoC vendor가 VM relayer와 protected DMA-BUF capability 제공
- TF-A/Hafnium에서 관련 conformance test와 production support 공개

## 12. 공식 자료

[S1]: https://developer.arm.com/-/cdn-downloads/permalink/Architectures/Armv9/DEN0077A_Firmware_Framework_Arm_A-profile_1.3_ALP3_ALP4_Diff.pdf
[S2]: https://documentation-service.arm.com/static/6876738e9f5181111629b363
[S3]: https://developer.arm.com/documentation/den0140/d
[S4]: https://raw.githubusercontent.com/torvalds/linux/master/drivers/firmware/arm_ffa/driver.c
[S5]: https://raw.githubusercontent.com/torvalds/linux/master/arch/arm64/kvm/hyp/nvhe/ffa.c
[S6]: https://android.googlesource.com/kernel/common/+/bb4c8fa976f662066ab110812acb9a82ed3faf1c/arch/arm64/kvm/hyp/nvhe/ffa.c
[S7]: https://android.googlesource.com/kernel/common/+/c23c055311e1b36c7daac89cdab2bc1de02c517d
[S8]: https://source.android.com/docs/core/virtualization/security
[S9]: https://android.googlesource.com/platform/packages/modules/Virtualization/+/HEAD/libs/framework-virtualization/README.md
[S10]: https://source.android.com/docs/core/virtualization/architecture
[S11]: https://github.com/torvalds/linux/blob/master/drivers/firmware/arm_ffa/Kconfig
[S12]: https://trustedfirmware-a.readthedocs.io/en/v2.15.0/components/secure-partition-manager.html
[S13]: https://trustedfirmware-a.readthedocs.io/en/latest/change-log.html
[S14]: https://docs.kernel.org/virt/kvm/arm/pkvm.html
[S15]: https://docs.kernel.org/virt/kvm/arm/hypercalls.html
[S16]: https://source.android.com/docs/core/virtualization/pkvm-modules
[S17]: https://lists.trustedfirmware.org/archives/list/tsc@lists.trustedfirmware.org/message/BRX7YC4DAXKYUKS24QN3LWTLYDK3F7PN/attachment/4/202511_TSC_TF-A_Presentation_Public_v3.0.pdf
[S18]: https://android.googlesource.com/kernel/common/+/refs/heads/android16-6.12/arch/arm64/kvm/pkvm.c
[S19]: https://trustedfirmware-a.readthedocs.io/en/latest/getting_started/build-options.html
[S20]: https://lore.kernel.org/all/20260830-host-direct-messages-v7-0-45f6e6db72c2@google.com/
[S21]: https://android.googlesource.com/platform/external/hafnium/+/676ab03c6a3d78f10ddc0f8b96c02475da24392f/docs/change-log.md
[S22]: https://developer.arm.com/-/cdn-downloads/permalink/Architectures/Armv9/DEN0077A_Firmware_Framework_Arm_A-profile_1.3_ALP4_ALP5_Diff.pdf
[S23]: https://developer.arm.com/-/cdn-downloads/permalink/Architectures/Armv9/DEN0140_FF-A_Memory_Management_Protocol_1.3_ALP4_ALP5_Diff.pdf
[S24]: https://developer.arm.com/documentation/den0077/j
