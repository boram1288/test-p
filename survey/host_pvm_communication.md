# Host Application·pVM Workload 및 Host·pVM Kernel Driver 통신 조사

- 조사일: 2026-08-31
- 상태: 공개 규격과 구현을 기준으로 한 설계 조사, 대상 platform 확인 전
- 대상: 로봇용 Custom SoC의 Linux-native pKVM Framework
- 관련 모듈: M-01 Framework API / Request Gateway, M-07 Secure Inter-domain Channel,
  M-08 HW IP Mediation Layer, M-09 DMA/S2MPU Isolation Controller

## 1. 조사 목적과 범위

이 문서는 다음 두 통신을 구분해 실제 구현 방법을 정리한다.

1. Host Application과 pVM 안의 Workload 사이의 request, response와 event 통신
2. Host Linux kernel driver와 pVM Linux kernel driver 사이의 control/data 통신

대상 시스템은 Android 제품이 아니라 Yocto/Ubuntu 계열 Embedded Linux다.
Android AVF와 Microdroid는 pKVM에서 실제 사용되는 공개 구현 선례로만 다룬다.
Android `VirtualMachine`, Binder RPC 또는 `VirtualizationService`를 제품 의존성으로
제안하지 않는다.

다음 조건은 [시스템 개요](../docs/01_시스템_개요.md)와
[설계 범위 모듈](../docs/02_설계_범위_모듈.md)을 따른다.

- Host Application뿐 아니라 Host kernel도 비신뢰다.
- pVM private memory는 Host가 읽거나 쓸 수 없어야 한다.
- pVM이 명시적으로 Host와 공유한 page만 Host transport/backend가 접근한다.
- 권한의 최종 허가와 실제 Stage-2, S2MPU/IOMMU 상태는 보호 경계에서 확인한다.
- EL2에는 일반 RPC parser나 bulk data path를 넣지 않고 작은 TCB를 유지한다.
- guest OS 제품과 VMM은 아직 고정하지 않는다.

공식 문서와 원본 코드를 우선 확인했다. 이 문서에서 "가능"은 공개 interface가
있다는 뜻이며, 현재 Custom SoC port가 그대로 지원한다는 뜻은 아니다.

## 2. 결론

### 2.1 한눈에 보는 답

| 구분 | 우선 방법 | 실제 경로 | 적합한 자료 | 핵심 제약 |
| --- | --- | --- | --- | --- |
| Host Application ↔ pVM Workload | `AF_VSOCK` `SOCK_STREAM` 위의 versioned RPC | Host socket ↔ `vhost-vsock`/VMM ↔ shared virtqueue ↔ guest `virtio-vsock` ↔ Workload socket | 명령, 상태, 작은 AI 결과, 저·중용량 stream | Host가 payload를 보고 바꾸고 버리거나 지연할 수 있음 |
| Host kernel driver ↔ pVM kernel driver, 빠른 PoC | 양쪽 kernel의 `AF_VSOCK` socket | `sock_create_kern()`/`kernel_sendmsg()` ↔ 기존 virtio-vsock transport | 저빈도 control/event | kernel 내부 API 호환성, blocking/복구 처리, stream copy |
| Host kernel driver ↔ pVM kernel driver, 제품 data path | 표준 또는 전용 virtio front-end + Host vhost/backend | guest virtio driver ↔ Host-shared virtqueue/buffer + kick/IRQ ↔ Host backend/native driver | job queue, 다중 outstanding 요청, device/data plane | 양쪽 driver와 VMM 연결부를 구현하고 악성 descriptor를 방어해야 함 |
| pVM이 물리 HW를 직접 사용 | VFIO/device assignment + pVM native driver | Host native driver unbind ↔ VFIO/IOMMU/EL2 ownership 전환 ↔ guest native driver | Camera/AI 고대역폭, Host 비노출이 필요한 HW data path | 이 경우 정상 data path에는 Host driver↔guest driver 통신이 없음 |

따라서 이 Framework의 기본안은 다음과 같다.

- Host Application의 pipeline 관리 요청은 M-01 관리 API로 받는다.
- 실행 중 Workload RPC와 작은 추론 결과는 `AF_VSOCK`으로 전달한다.
- 원본 frame, model과 중간 결과는 Host-facing vsock에 넣지 않는다.
- kernel 간 단순 control PoC는 kernel vsock으로 시작할 수 있다.
- 성능·backpressure·DMA 의미가 필요한 driver data path는 virtio split device로
  만든다.
- Camera/AI HW를 pVM에 직접 할당한다면 Host native driver와 pVM native driver가
  서로 HW context를 주고받지 않는다. 신뢰 중재자가 기존 owner를 회수·소거한 뒤
  새 owner에게 MMIO, DMA와 IRQ를 부여한다.

### 2.2 통신층과 보안층은 다르다

`vsock`, virtqueue, shared ring은 byte와 descriptor를 운반한다. 다음을 자동으로
제공하지 않는다.

- Host가 보낸 요청의 보안상 정당성
- CID가 가리키는 VM의 측정 identity와 실행 generation
- 악성 Host에 대한 payload 기밀성·무결성·freshness
- Host가 VM을 schedule하고 channel을 서비스한다는 가용성
- HW owner 변경, DMA 차단, reset과 zeroize 완료의 증거

Host가 통신의 최종 평문 endpoint라면, 그 Host가 침해된 상황에서도 같은 평문을
숨기는 것은 불가능하다. 이 경우 해법은 암호화 channel이라는 표현이 아니라
**Host에 내보낼 자료 자체를 최소화**하는 것이다. 이 시스템에서는 판단 결과만
Host에 반환하고 원본 frame과 model은 보호 경계 안에 둬야 한다.

### 2.3 공개 baseline에서 찾지 못한 것

이번 조사에서는 다음을 바로 제공하는 범용 공개 interface를 찾지 못했다.

- pVM private page 또는 DMA-BUF를 private 상태 그대로 Host Application에 mapping하는
  Linux/AVF API
- 임의의 Host kernel driver와 pVM kernel driver를 자동으로 연결하는 pKVM 전용
  message bus
- `MEM_SHARE`만으로 queue, notification, lifetime과 reset까지 완성하는 API
- mainline pKVM에서 완료된 protected IOMMU device assignment
- 악성 Host에 대한 기밀성·무결성·가용성을 제공하는 vsock mode

따라서 application channel에는 별도 RPC contract가 필요하고, 새 device data
plane에는 양쪽 virtio/backend 구현이 필요하다. protected device assignment는
실제 vendor port의 기능을 확인한 뒤에만 사용할 수 있다.

## 3. 계층 구조

### 3.1 Application ↔ Workload

```text
Host EL0                                      pVM EL0
+--------------------+                       +--------------------+
| Host Application   |<---- framed RPC ---->| Protected Workload |
+---------+----------+                       +----------+---------+
          | AF_VSOCK                                     | AF_VSOCK
----------+---------------- Host/pVM boundary ------------+---------
          |                                               |
Host EL1  |  AF_VSOCK core + vhost-vsock       guest EL1 | virtio-vsock
          +---- shared virtqueue/bounce window -----------+
                         ^              ^
                         | VMM configures CID, vring, kick/call
                         +---------------------------------------
```

Host Application이 보는 interface는 socket이다. `vhost-vsock`은 Host Application
API가 아니라 그 socket을 guest의 virtqueue에 연결하는 Host kernel backend다.
[Linux `vsock(7)`][S4]은 주소를 32-bit CID와 32-bit port의 쌍으로 정의하고 Host의
well-known CID를 2로 정의한다. [crosvm 문서][S5]도 guest CID를 VMM 실행 시 할당하고
Host CID 2와 guest 사이에 통신하는 구성을 제시한다.

### 3.2 Kernel driver ↔ Kernel driver

```text
Host EL1                                             pVM EL1
+----------------------+                         +----------------------+
| Host native driver   |                         | guest virtio driver  |
+----------+-----------+                         +-----------+----------+
           | request/completion                              |
+----------v-----------+  descriptors + shared buffers  +----v---------+
| custom vhost/backend |<=============================>| virtqueue     |
+----------+-----------+  kick/eventfd       vIRQ      +--------------+
           ^
           | /dev/vhost-* ioctl, vring/IOTLB, kick/call 설정
     +-----+-----+
     | VMM EL0   |
     +-----------+
```

virtio는 guest의 driver와 가상 device 구현 사이의 규약이다. [Linux virtio
문서][S6]에 따르면 양쪽은 shared memory의 virtqueue로 descriptor와 buffer를
교환하고, guest가 넣은 buffer를 device가 처리한 뒤 used 상태와 interrupt로
완료를 알린다. Host kernel에 backend를 둘 때는 vhost가 이 device 측 data path를
담는다. Linux vhost core 자체도 자신을 "Host kernel의 generic virtio server"로
설명하며, `vhost-vsock`은 `/dev/vhost-vsock`과 두 virtqueue를 구현한다.[S11][S12]

VMM은 빠지지 않는다. Host kernel backend를 쓰더라도 VMM이 VM과 virtual device를
만들고, vring 주소, IOTLB, guest CID와 kick/call eventfd를 vhost에 설정한다.

## 4. Host Application과 pVM Workload 통신

### 4.1 Baseline: raw `AF_VSOCK` + 명시적 RPC framing

가장 작은 Linux-native 구현은 pVM Workload가 well-known port에 server socket을
열고, Host의 M-01/M-07 component가 해당 VM CID로 연결하는 방식이다.

일반 Linux/crosvm vsock은 어느 쪽이 listen할지도 protocol이 정할 수 있고, 연결된
stream은 full duplex다.[S4][S5] 여기서는 lifecycle owner가 Host Framework이고
guest service의 준비 시점을 명확히 하기 위해 `guest listen → Host connect`를
기본 topology로 선택한다.

```text
1. M-02가 pVM을 생성하고 generation g와 guest CID를 연결해 기록
2. pVM Workload가 AF_VSOCK/SOCK_STREAM port P에 bind/listen
3. Workload가 별도 lifecycle 경로로 READY(g, protocol_version)을 알림
4. M-01이 Host caller를 확인하고 CID:g:P로 connect
5. 양단이 version/capability와 최대 message 크기를 협상
6. request_id + generation + sequence가 있는 request/response 교환
7. stop/crash 시 socket을 닫고 generation g의 모든 in-flight 요청 폐기
```

개념적인 userspace 호출은 다음과 같다.

```c
int fd = socket(AF_VSOCK, SOCK_STREAM, 0);

struct sockaddr_vm peer = {
    .svm_family = AF_VSOCK,
    .svm_cid = guest_cid,   /* guest에서는 VMADDR_CID_HOST(2) 사용 가능 */
    .svm_port = service_port,
};

connect(fd, (struct sockaddr *)&peer, sizeof(peer));
```

`SOCK_STREAM`에는 message 경계가 없다. 한 번의 `send()`와 한 번의 `recv()`가
대응한다고 가정하면 안 된다. 최소 header는 다음 정보를 가져야 한다.

| field | 목적 |
| --- | --- |
| `magic`, `protocol_major/minor` | 잘못된 endpoint와 호환되지 않는 peer 거부 |
| `message_type`, `flags` | request, response, event와 오류 구분 |
| `header_len`, `payload_len` | 부분 read와 framing 처리, 크기 상한 강제 |
| `request_id` | 비동기 response와 timeout 연결 |
| `vm_generation`, `pipeline_epoch` | 재시작 전의 stale message 거부 |
| `sequence` | 중복, 역전과 replay 탐지 |
| `status` | transport 오류와 workload 오류 분리 |
| 선택적 `auth_tag` | 보호된 key endpoint가 있을 때 message 인증 |

guest CID는 routing identifier일 뿐 영속 identity가 아니다. Android
`VirtualizationService`도 VM이 종료된 뒤 CID를 재사용할 수 있다고 설명한다.[S18]
따라서 CID만으로 Workload나 실행 세대를 인증하지 않는다.

### 4.2 Host 연결 권한과 readiness

Linux-native 환경에는 Android의 "VM을 만든 app만 연결" 정책이 자동으로 없다.
다음 배치가 관리하기 쉽다.

```text
Host App --local UDS/API--> M-01/M-07 --AF_VSOCK--> pVM Workload
```

M-01/M-07이 local Unix socket의 peer credential과 policy를 확인하고, 자신이 관리하는
`VM identity + generation + CID + port`에만 연결한다. 이후 다음 중 하나를 택한다.

- 연결된 vsock FD를 허가된 Host Application에 Unix `SCM_RIGHTS`로 넘긴다.
- M-01/M-07이 bounded message proxy로 남아 schema와 rate를 제한한다.

첫 방법은 copy와 proxy state가 적다. 두 번째 방법은 API를 한 곳에서 versioning하고
감사하기 쉽지만 Host relay가 data path에 남는다. 둘 다 Host 침해에 대한 보안
경계는 아니며, 정상 운용에서 잘못된 app의 연결을 줄이는 정책이다.

guest server가 listen하기 전에 Host가 연결하면 race가 생긴다. AOSP AVF도 payload가
server socket을 만든 뒤 ready callback을 알리고 app이 연결하도록 권한다.[S8]
이 원칙은 Android API 없이도 lifecycle event로 그대로 적용할 수 있다.

### 4.3 RPC 선택

| 방식 | Linux-native 적용성 | 장점 | 제약과 판정 |
| --- | --- | --- | --- |
| 자체 binary framing + Protobuf/FlatBuffers/CBOR 등 schema | 높음 | 작고 OS 독립적, 크기와 version을 명확히 제한 가능 | framing, timeout와 호환성 규칙을 직접 정의해야 함. **기본안** |
| Android Binder RPC over vsock | 낮음 | AIDL interface와 Android 공개 구현 선례 | Binder RPC와 AVF library 의존. 본 시스템에는 직접 사용하지 않음 |
| TCP/IP over `virtio-net` | 보통 | 기존 network RPC와 도구 재사용 | TAP, IP, routing, firewall가 추가되고 Host 의존/노출은 줄지 않음 |
| `virtio-console`/serial | 낮음 | bootstrap과 debug가 단순 | service multiplexing, authorization, reconnect가 약함. 운영 RPC에 비권장 |
| `virtio-fs`/`virtio-blk` 파일 교환 | 목적 한정 | 큰 정적 input/output와 persistence에 맞음 | request/event channel이 아니며 Host 변조·rollback을 별도로 막아야 함 |

AOSP AVF는 raw vsock과 Binder RPC 두 방식을 모두 공개한다. Binder RPC도 실제
transport는 vsock이고 file descriptor를 전달할 수 없다.[S8] 이 제약은 Linux-native
설계에서도 중요하다. Host의 FD 숫자, kernel pointer와 `dma_buf` 객체는 pVM의 다른
kernel instance에서 의미가 없으므로 wire protocol에는 opaque resource ID만 넣는다.

### 4.4 보안 성질

#### 제공되는 것

- network 설정 없이 Host와 guest 사이의 양방향 ordered byte stream
- CID와 port에 의한 routing과 service multiplexing
- socket의 일반적인 blocking/nonblocking I/O와 disconnect 통지
- 기존 virtio-vsock guest driver와 vhost backend 재사용

#### 제공되지 않는 것

- CID의 measured identity 또는 cryptographic authentication
- Host로부터의 기밀성: queue와 data buffer는 Host와 명시적으로 공유된다.
- 악성 Host에 대한 message 무결성, replay 방지와 availability
- application message 경계와 schema validation
- FD, DMA-BUF 또는 guest private page의 직접 전달

이 "제공되지 않음" 판정은 virtio-vsock 규격이 socket transport와 flow control만
정의하고, pKVM 구현이 queue/data buffer를 Host-shared memory에 둔다는 공개 구조에서
내린 설계상 추론이다.[S3][S7] 별도 cryptographic handshake를 구현하면 message
보호를 추가할 수 있지만 그것은 vsock 자체의 성질이 아니다.

[AOSP AVF architecture][S3]는 pVM의 virtqueue와 data buffer를 고정 shared window에
두고 private buffer와 필요에 따라 bounce copy한다고 설명한다. [pKVM hypercall
문서][S2]의 `MEM_SHARE`는 지정 granule을 KVM Host에 read/write/execute 권한으로
공유한다. 따라서 shared page에는 Host가 보아도 되는 자료, 암호문 또는 엄격히
검증할 transport state만 둔다.

Host를 통과하는 중간 component만 믿지 않되 양 endpoint의 key는 보호할 수 있는
별도 구조라면 attestation 기반 key agreement와 AEAD를 RPC에 붙일 수 있다. 그러나
최종 endpoint인 Host Application과 Host kernel까지 침해된 threat에서는 그 key와
복호화된 결과도 Host가 읽을 수 있다. 이 경우 AEAD가 해결책이라고 주장하지 않는다.

pVM이 보안상 중요한 명령을 받아야 한다면 다음 중 보호 가능한 authority가 발급한
capability 또는 signature를 pVM 안에서 검증해야 한다.

- TEE/Secure OS
- 별도 protected service pVM
- remote management authority
- EL2가 검증한 작은 capability interface

Host가 제공한 `allow=true`, CID, PID, UID 또는 generation 문자열만 최종 허가 근거로
사용하지 않는다. Host가 packet을 drop하거나 VM을 schedule하지 않는 DoS는 pKVM이
막을 수 없으므로 timeout 뒤 안전한 중단과 자원 회수로 대응한다.[S9]

### 4.5 큰 자료를 보낼 때

vsock은 bulk byte도 전달할 수 있지만 pVM private buffer와 Host shared bounce
window 사이의 copy와 socket stack 비용이 따른다. 자료가 의도적으로 Host에
공개되는 경우 다음 기준을 사용한다.

| 요구 | 선택 |
| --- | --- |
| 명령, 상태, bounded AI 판단 결과 | vsock RPC 하나로 충분 |
| 드물게 전달하는 중간 크기 file/blob | chunked vsock, 전체 길이와 digest 검증 |
| 지속적인 고대역폭 Host-facing stream | 전용 virtio device의 descriptor queue 검토 |
| Host에 노출하면 안 되는 Camera frame/model | Host-facing channel로 보내지 않음 |
| pVM 간 frame 전달 | 이 문서의 Host↔pVM channel과 별도 설계; Host relay를 직접 채택하지 않음 |

OASIS Virtio 1.4의 일반 "shared memory region"은 continuous shared cache 같은
용도이며, device control이나 streaming data에 사용하지 말라고 규정한다.[S7]
따라서 고대역폭 custom device도 임의 영구 shared region에 stream을 쓰기보다
virtqueue descriptor가 가리키는 수명 제한 buffer를 사용한다.

## 5. Host kernel driver와 pVM kernel driver 통신

### 5.1 먼저 결정할 질문

"driver끼리 통신"의 목적에 따라 구조가 달라진다.

| 목적 | 권장 구조 |
| --- | --- |
| 낮은 빈도의 설정, 상태, fault event | 가능하면 양쪽 daemon + userspace vsock; direct kernel 경로가 꼭 필요하면 kernel vsock |
| device command, 여러 outstanding job, backpressure와 completion | 표준 또는 전용 virtio device |
| Host driver가 HW를 계속 소유하고 guest 요청을 대신 실행 | mediated/split virtio device + backend |
| pVM이 HW와 DMA buffer를 Host 비노출로 직접 사용 | protected device assignment; Host native driver는 data path에서 제거 |
| 권한 grant/revoke와 Stage-2/S2MPU commit | EL2/pKVM vendor enforcement interface; 일반 message transport와 분리 |

### 5.2 선택 A: userspace relay

```text
Host driver <-ioctl/netlink-> Host daemon <-vsock-> guest daemon <-ioctl-> guest driver
```

control 빈도가 낮다면 이 방식이 가장 작은 kernel 변경으로 시작할 수 있다. protocol
parser, retry와 version negotiation을 userspace에 둘 수 있고 kernel crash 범위를
줄인다. 추가 context switch와 copy가 허용되는지 측정해야 한다. Host daemon과 Host
driver는 모두 같은 비신뢰 경계이므로 daemon을 넣는 것이 보안 authority를 만든다는
뜻은 아니다.

### 5.3 선택 B: kernel `AF_VSOCK`

양쪽 kernel은 Linux socket API로 `AF_VSOCK` endpoint를 만들 수 있다. Linux kernel
networking API는 `sock_create_kern()`, `kernel_sendmsg()`, `kernel_recvmsg()`,
`kernel_accept()`를 제공한다.[S10] 이를 `AF_VSOCK`과 조합하면 기존 vhost-vsock과
virtio-vsock을 그대로 사용해 kernel module 사이에서 byte message를 교환할 수 있다.

이 방식은 **기술적으로 가능한 빠른 PoC**이지 pKVM 전용 stable driver ABI는 아니다.

- kernel socket 호출은 interrupt handler가 아니라 kthread/workqueue의 sleep 가능한
  context에서 수행한다.
- 모든 I/O는 partial send/receive, `EINTR`, disconnect와 timeout을 처리한다.
- module unload와 pVM reset 전에 receiver thread를 깨우고 socket을 닫는 순서를 둔다.
- Linux 내부 kernel API는 stable UAPI가 아니다. target kernel별 build/compatibility
  시험이 필요하다.
- socket stack과 bounce copy가 있고 device feature negotiation이나 scatter-gather
  completion 의미가 약하므로 고빈도 HW job queue의 최종안으로 삼지 않는다.
- byte가 Host kernel endpoint에 도달하므로 pVM secret을 숨길 수 없다.

기존 vsock transport를 재사용해 control path를 빨리 검증해야 하는 경우에는 유용하다.
성능이나 device semantics가 부족하다는 측정 결과가 나온 뒤 virtio 전용 device로
옮기는 단계적 접근이 가능하다.

### 5.4 선택 C: virtio split device

제품 수준의 driver data path에는 이 방식이 가장 자연스럽다.

#### 역할

| 구성요소 | 책임 |
| --- | --- |
| pVM virtio front-end driver | feature 협상, queue와 buffer 준비, request 제출, completion 검증, guest userspace API 제공 |
| Host backend/vhost module | descriptor 안전 검증, Host native driver로 job 전달, completion 기록, rate/backpressure 관리 |
| Host native driver | 현재 Host가 소유한 HW의 실제 요청 실행과 오류 처리 |
| VMM | virtual device 생성, MMIO/PCI transport, memslot/IOTLB, vring과 kick/call 연결 |
| pKVM/EL2 | pVM private/shared page 상태와 허용 MMIO trap을 강제 |
| M-09/S2MPU 또는 IOMMU | physical device DMA가 허가된 실제 page만 접근하도록 강제 |

Host backend는 두 곳 중 하나에 둘 수 있다.

1. **VMM/userspace backend**: AOSP crosvm의 일반 virtio device 배치다. 구현과
   sandboxing은 쉽지만 엄밀히는 Host kernel driver↔guest kernel driver 직접 구조가
   아니다.
2. **Host kernel vhost backend**: VMM이 `/dev/vhost-*`를 설정한 뒤 kernel backend가
   virtqueue data path를 처리한다. 질문의 kernel↔kernel 구조에 해당하며 context
   switch를 줄일 수 있지만 새 Host kernel attack surface와 구현 부담이 생긴다.

공개 vhost core는 새 제품 protocol을 등록해 주는 범용 userspace 설정만 제공하는
것이 아니다. 표준 backend가 없는 device라면 Host vhost module과 VMM 연결 코드를
새로 만들고 target kernel revision에 맞춰 함께 유지해야 한다.

기존 표준 virtio device type이 요구를 만족하면 그대로 사용한다. Camera/AI 전용
job semantics가 표준 device와 맞지 않을 때만 새 device protocol과 guest/backend를
만든다. `virtio-rpmsg`는 kernel message bus 선례지만 remote processor/AMP용이며
KVM pVM용 Host backend를 자동으로 제공하지 않는다.[S15]

#### 요청 흐름

```text
1. VMM이 device ID, config space, queue와 virtual IRQ를 pVM에 노출
2. guest driver가 feature/version, queue 수, 최대 SG와 최대 request 크기를 협상
3. guest가 Host-shared DMA window에서 descriptor와 transport buffer를 준비
4. guest가 request descriptor를 available ring에 넣고 device를 kick
5. VMM 또는 vhost가 notification을 받아 Host backend를 실행
6. backend가 모든 address/length/direction/opcode를 검증한 뒤 native driver에 전달
7. 완료 후 status/used length를 기록하고 guest virtual IRQ를 발생
8. guest가 used entry와 response를 다시 검증한 뒤 private state에 반영
```

MMIO는 주로 초기화, config와 doorbell에 사용한다. AOSP는 MMIO trap 왕복이 비싸므로
실제 자료 이동은 대부분 memory virtqueue를 사용한다고 설명한다.[S3] pVM에서는
private memory를 backend가 읽을 수 없으므로 virtqueue와 Host 접근 buffer를 명시적인
shared window에 둔다. private payload가 필요하면 guest DMA layer의 `swiotlb` 같은
bounce 경로로 shared buffer와 복사한다.[S3][S16]

#### 최소 wire contract

| 항목 | 필요한 규칙 |
| --- | --- |
| version/features | major 불일치 fail, minor feature bit 협상, unknown bit 거부 |
| queue | command/completion 또는 bidirectional queue, depth와 credit 상한 |
| request | fixed-width type, opcode, flags, request ID, generation, SG count, total length |
| buffer | guest physical raw pointer를 다른 문맥에 보존하지 않음, descriptor 범위와 방향 검증 |
| ordering | out-of-order completion 허용 여부, fence와 memory barrier 정의 |
| cancellation | timeout 뒤 cancel, late completion과 duplicate completion 처리 |
| reset | queue reset, pVM crash, backend crash 때 generation 증가와 in-flight 폐기 |
| error | transport, protocol, authorization, HW와 timeout 오류를 분리 |
| resource limit | queue depth, bytes, pinned/shared page, IRQ rate와 CPU budget 제한 |

Host와 guest가 모두 상대를 악성으로 취급해야 한다. guest driver는 Host가 쓴 used
index, used length, status와 payload를 검증한다. Host backend도 guest가 만든
descriptor chain, loop, overlap, integer overflow, 방향, opcode와 rate를 검증한다.
virtual IRQ나 `revoke_ready` message는 완료 힌트이지 보호 권한 변경의 증거가 아니다.

### 5.5 선택 D: protected device assignment

Camera/AI HW의 MMIO, IRQ와 DMA를 pVM에 직접 할당할 수 있으면 지속적인
Host-driver↔guest-driver RPC를 없앨 수 있다.

```text
HOST_OWNED
  → Host 신규 제출 차단
  → drain/강제 중단
  → Host native driver unbind
  → IRQ 차단 + reset + 잔류 자료 zeroize
  → 기존 MMIO/DMA mapping revoke, owner=NONE 확인
  → VFIO/IOMMU/Stage-2를 pVM generation에 bind
  → pVM native driver bind
  → PVM_OWNED
```

[Android 16 device assignment 문서][S13]는 `vfio-platform`을 사용하며 Host native
driver에서 device를 unbind하고 VFIO driver에 bind한다고 설명한다. 이 경우 pVM
native driver가 HW를 직접 사용하므로 정상 data path에 Host native driver가 없다.
[Linux VFIO 문서][S14]도 direct assignment를 VM이 bare-metal driver로 device를 직접
사용하는 구조로 설명한다.

다만 공개 mainline pKVM 최신 문서는 IOMMU를 이용한 DMA isolation을 아직
`Unimplemented`로 표시한다.[S1] 반면 Android vendor 계열은 pKVM vendor module,
IOMMU와 device assignment 문서를 제공한다.[S3][S13] 따라서 Custom SoC에 포팅된
tree가 다음을 실제 지원하는지 먼저 확인해야 한다.

- platform device의 secure assignment와 강제 revoke
- 모든 DMA master의 SMMU/S2MPU stream 분리
- MMIO와 IRQ routing의 owner 전환
- reset 뒤에도 우회할 수 없는 IOMMU programming interface
- device-local SRAM/cache/firmware state의 zeroize
- fault/timeout 때 guest 협조 없이 owner를 `NONE`으로 만드는 경로

Host driver의 `drain 완료` 보고만 신뢰하면 안 된다. Host와 pVM driver는
`prepare_revoke`와 `ready` 같은 협조 신호만 보내고, M-08/M-09의 protected
enforcement가 실제 MMIO, DMA, IRQ, reset과 generation 전환을 확인해야 한다.

### 5.6 HVC, MMIO trap, FF-A와 shared memory의 위치

| 수단 | 할 수 있는 일 | 이 질문의 판정 |
| --- | --- | --- |
| pKVM `MEM_SHARE`/`MEM_UNSHARE` | guest page를 Host와 공유하거나 Host 접근 회수 | memory primitive일 뿐 queue, message와 notification은 별도 필요 |
| MMIO guard + trap-and-emulate | guest가 선언한 MMIO range 접근을 Host VMM이 emulation | config/doorbell에는 가능, 매 byte data path에는 비효율적 |
| custom guest HVC | guest EL1에서 EL2의 작은 operation 호출 | 권한 commit/조회 후보. Host kernel driver RPC가 아니며 새 ABI와 EL2 TCB 필요 |
| pKVM vendor module call | Host EL1 module과 EL2 vendor module 연결 | IOMMU/S2MPU enforcement 후보. guest driver와의 일반 channel이 아님 |
| FF-A | Normal/Secure world message와 memory share/lend | Host↔pVM Linux driver의 turnkey IPC가 아님. TEE/SP endpoint 연동에 사용 |
| permanent shared ring + doorbell | 낮은 latency의 custom queue | 가능하지만 사실상 virtio 일부를 재구현함. 최소 권한, reset, cache 규칙 부담 |
| `virtio-rpmsg` | virtio 기반 kernel message channel | remoteproc용 선례. pKVM Host backend와 보호 규약은 새로 필요 |

`MEM_SHARE`와 custom HVC를 곧 "Host driver와 guest driver가 직접 통신한다"고 표현하면
안 된다. 전자는 Host-visible page를 만드는 primitive이고, 후자는 guest→EL2
호출이다. 일반 data/control transport는 virtio/vsock과 분리하고, EL2 호출은 최종
권한 집행처럼 작고 bounded된 operation으로 제한한다. AOSP pKVM module 문서도 EL2
코드는 non-preemptible이므로 짧아야 한다고 명시한다.[S17]

## 6. pVM memory와 buffer 계약

### 6.1 공개 구현에서 확인되는 상태

[mainline pKVM 문서][S1]는 protected guest가 `CONFIG_ARM_PKVM_GUEST`를 사용해
자신의 특정 IPA 영역을 Host와 공유할 수 있다고 설명한다. private page를 Host가
접근하면 fault가 발생한다. `MEM_SHARE`/`MEM_UNSHARE`의 상대는 KVM Host이며 다른
pVM ID를 받지 않는다.[S2]

따라서 Host↔pVM 통신 buffer는 다음처럼 나눈다.

```text
pVM private page                       Host-shared transport page
+---------------------------+          +---------------------------+
| model, frame, key, state  | --copy-->| 허용된 request/result 또는|
| 검증 전에는 갱신 안 함   |<--copy---| 암호문, descriptor, index |
+---------------------------+          +---------------------------+
       Host 접근 불가                    Host read/write 가능
```

### 6.2 필수 규칙

1. shared page에는 private allocator의 이웃 object가 섞이지 않도록 전용 pool을 쓴다.
2. page granule보다 작은 message 때문에 같은 page의 unrelated secret이 노출되지
   않도록 한다.
3. Host가 쓴 자료는 private state로 복사하기 전에 길이, 형식, identity, generation,
   sequence와 cryptographic tag를 필요한 수준까지 검증한다.
4. request 완료 전 buffer를 재사용하거나 `UNSHARE`하지 않는다.
5. DMA 또는 backend reference가 모두 끝났음을 확인한 뒤 cache sync, zeroize와
   unshare/reclaim을 수행한다.
6. raw HPA, Host VA, guest kernel pointer, FD 번호와 kernel object pointer를 protocol
   identifier로 쓰지 않는다.
7. interrupt, used-ring 변경과 Host completion은 data visibility를 위한 memory
   barrier와 별도로 authorization completion을 의미하지 않는다.

## 7. 선택지 비교

### 7.1 Host Application ↔ Workload

| 기준 | vsock RPC | `virtio-net` RPC | custom virtio data device | shared file/block |
| --- | --- | --- | --- | --- |
| 첫 PoC | 쉬움 | 보통 | 어려움 | 보통 |
| Linux-native API | socket | socket | 전용 library/device node | file API |
| 별도 guest driver | 기존 virtio-vsock | 기존 virtio-net | 필요 | 기존 fs/blk driver |
| message/RPC 적합성 | 높음 | 높음 | protocol에 따라 높음 | 낮음 |
| 고대역폭 지속 stream | 보통, copy 측정 필요 | 보통, network stack | 높게 설계 가능 | batch/file에 적합 |
| Host payload 가시성 | 있음 | 있음 | shared buffer는 있음 | 있음/암호화에 따름 |
| Host DoS 가능 | 있음 | 있음 | 있음 | 있음 |
| 본 Framework 판정 | **control/result 기본안** | 기존 network RPC가 꼭 필요할 때 | Host-facing bulk 요구가 확인된 뒤 | package/storage 용도만 |

### 7.2 Host kernel driver ↔ pVM kernel driver

| 기준 | daemon relay | kernel vsock | virtio + userspace backend | virtio + vhost backend | direct assignment |
| --- | --- | --- | --- | --- | --- |
| kernel 변경 | 가장 적음 | 양쪽 module | guest driver | 양쪽 driver/backend | guest native + assignment |
| 구현 난이도 | 낮음 | 낮음~보통 | 보통~어려움 | 어려움 | platform 의존, 매우 어려움 |
| latency/copy | 가장 많음 | socket/bounce | virtqueue/bounce | virtqueue/bounce | 가장 적을 수 있음 |
| 여러 outstanding job | 별도 RPC 설계 | 별도 RPC 설계 | 자연스러움 | 자연스러움 | HW 능력에 따름 |
| Host가 HW data를 봄 | mediation에 따름 | message는 봄 | backend가 봄 | backend가 봄 | 올바른 IOMMU 구성 시 보지 않음 |
| fault 격리 | userspace process | kernel 양쪽 | backend sandbox 가능 | Host kernel 영향 | HW/guest와 enforcement 품질에 따름 |
| 권장 용도 | 저빈도 control | control PoC | 일반 virtual device | 고성능 kernel backend | protected HW data path |

## 8. Framework 적용안

### 8.1 M-01: 관리 plane

Host Application은 M-01의 안정된 local API만 사용한다. `create/start/stop`, package,
pipeline과 policy request를 Workload RPC port와 섞지 않는다. M-01은 다음 mapping을
관리한다.

```text
framework_handle
  → verified_workload_identity
  → vm_generation
  → current_cid
  → allowed_service_ports/protocol_versions
```

CID는 VM이 재시작될 때 다시 bind하며 public authorization token으로 노출하지 않는다.

### 8.2 M-07: Host-facing runtime channel

- Workload가 listen하고 Framework가 ready 뒤 연결한다.
- command, health, bounded inference result만 허용한다.
- frame, model, intermediate tensor와 key material message type은 정의하지 않는다.
- request마다 generation, pipeline epoch, request ID, timeout와 payload 상한을 둔다.
- disconnect 뒤 자동으로 이전 session을 이어 쓰지 않고 새 handshake를 수행한다.

### 8.3 M-08/M-09: device plane

두 배치 후보를 분리해 시험한다.

1. **split virtual device**: Host가 HW를 소유하고 virtio backend가 pVM request를
   mediation한다. Host가 frame을 보면 안 되는 요구와 충돌하는지 먼저 판정한다.
2. **whole-device assignment lease**: pVM 소유 동안 guest native driver가 직접 HW를
   사용한다. Host driver는 unbind되고 M-09가 MMIO/DMA/IRQ를 강제한다.

HW 전환 control message는 proposal과 progress event다. 최종 grant/revoke 결과는
EL2/S2MPU/IOMMU의 actual state와 reset/zeroize gate가 성공했을 때만 확정한다.

### 8.4 최종 권장 topology

```text
Management plane
Host App --UDS/API--> M-01/M-02/M-03 --VMM/KVM ioctl--> pVM lifecycle

Runtime Host-facing plane
Host App <--connected FD or bounded proxy--> M-07 <--AF_VSOCK--> pVM Workload
                         판단 결과/명령만, frame/model 금지

Driver control PoC
Host driver <--kernel AF_VSOCK--> pVM driver
              또는 양쪽 daemon relay

Protected HW data plane
Host native driver --unbind--> owner NONE --EL2+SMMU commit--> pVM native driver
                          정상 처리 중 driver-to-driver payload 없음
```

## 9. 최소 PoC와 검증 계획

### 9.1 단계 0: target capability 확인

- Host/guest kernel version과 pKVM source revision 고정
- `CONFIG_ARM_PKVM_GUEST`, `CONFIG_VSOCKETS`, `CONFIG_VIRTIO_VSOCKETS`,
  `CONFIG_VHOST_VSOCK`과 `/dev/vhost-vsock` 확인
- VMM의 protected VM, CID, virtio transport와 shared `swiotlb` 구성 확인
- custom virtio/vhost 확장 point와 VMM sandbox 정책 확인
- pKVM vendor IOMMU module, VFIO platform device assignment와 강제 revoke 확인
- Camera/AI HW별 MMIO, IRQ, DMA master, reset과 zeroize 목록 작성

### 9.2 단계 1: Application ↔ Workload

1. ping/echo가 아니라 실제 `start_job`, `cancel`, `get_status`, `result` schema를 만든다.
2. partial read/write, 큰 길이, unknown version과 malformed message를 주입한다.
3. payload ready 전 연결, 정상 종료, crash와 빠른 restart를 시험한다.
4. 이전 CID/generation request와 duplicate/late response가 거부되는지 확인한다.
5. Host가 message를 바꾸고 replay, delay, drop할 때 pVM이 fail-safe인지 확인한다.
6. private canary page가 Host에서 fault하고 shared page의 허용 자료만 보이는지 확인한다.
7. p50/p95/p99 latency, throughput, CPU, context switch와 copy byte 수를 측정한다.

### 9.3 단계 2: Driver control

1. daemon relay와 kernel vsock으로 같은 protocol을 구현해 latency와 변경량을 비교한다.
2. kernel worker 종료, socket disconnect, module unload와 pVM reset 순서를 시험한다.
3. interrupt context에서 blocking I/O가 없음을 lockdep과 fault injection으로 확인한다.
4. 최대 message/rate, timeout, stale generation과 backpressure를 시험한다.

### 9.4 단계 3: virtio split device

1. queue 1개와 순차 request만 지원하는 최소 front-end/backend를 만든다.
2. shared transport pool과 private buffer가 물리 page 수준에서 분리되는지 확인한다.
3. invalid descriptor chain, out-of-range GPA, overlap, 방향 위반, overflow, duplicate
   completion과 IRQ storm을 주입한다.
4. queue reset과 backend/pVM crash 뒤 shared page와 in-flight request를 모두 회수한다.
5. multi-queue와 zero-copy 최적화는 안전한 단일 queue 기준이 성립한 뒤 추가한다.

### 9.5 단계 4: device assignment

1. Host driver unbind부터 guest bind까지 owner가 없는 deny 구간을 trace한다.
2. 전환 전후 Host CPU MMIO, pVM CPU MMIO와 각 DMA master의 negative access를 시험한다.
3. 진행 중 DMA, guest 무응답, Host 거짓 `drain done`, reset 실패를 주입한다.
4. fault 뒤 owner `NONE`, IRQ 차단, mapping 회수와 민감 SRAM/cache zeroize를 확인한다.
5. pVM 소유 중 Host가 frame buffer와 HW context를 읽지 못함을 검증한다.

## 10. 현재 확정할 수 없는 부분

공개 자료만으로 다음을 확정할 수 없다.

- Custom SoC pKVM port가 mainline과 Android vendor tree 중 어느 기능 집합에 가까운가
- VMM이 crosvm인지, virtio-mmio와 virtio-pci 중 무엇을 쓰는가
- guest OS와 kernel version, `SOCK_SEQPACKET` feature 지원 여부
- protected shared window와 `swiotlb` 크기, 실제 copy 수와 처리량
- Camera/AI HW가 안전한 reset, context save/restore와 강제 revoke를 지원하는가
- S2MPU/IOMMU가 모든 DMA master를 VM generation별로 분리하는가
- pVM attestation 결과를 누가 검증하고 authorization capability를 누가 발급하는가
- Host-facing 결과의 최대 크기, driver control 빈도와 latency budget

특히 mainline pKVM의 "DMA isolation unimplemented"와 Android vendor device assignment를
혼합해 이미 지원되는 기능처럼 서술하면 안 된다. 실제 port의 source/config와
negative DMA test를 통과하기 전까지 protected device assignment는 조건부 후보로 둔다.

## 11. 자주 생기는 오해

| 오해 | 실제 의미 |
| --- | --- |
| `vhost-vsock`이 Host Application API다 | Application API는 `AF_VSOCK`; vhost-vsock은 Host kernel backend다. |
| vsock이 pVM private memory를 보호한 채 payload를 Host에 보낸다 | 전송 buffer는 Host-shared다. private 원본은 bounce copy되고 전송 payload는 Host가 본다. |
| CID가 pVM identity다 | CID는 수명 제한 routing ID다. verified identity/generation과 별도로 bind해야 한다. |
| vsock으로 FD나 DMA-BUF를 넘길 수 있다 | FD/object는 kernel instance-local이다. byte serialization 또는 별도 resource protocol이 필요하다. |
| `MEM_SHARE`만 호출하면 통신 channel이 완성된다 | shared page만 생긴다. queue, ownership, notification, validation과 reset protocol이 필요하다. |
| guest HVC는 Host driver RPC다 | HVC는 guest→EL2 호출이다. Host driver와의 transport가 아니다. |
| vhost-user는 Host kernel driver 방식이다 | vhost-user는 device backend를 Host userspace process로 분리하는 protocol이다. |
| direct assignment도 두 native driver가 계속 대화한다 | Host driver를 떼고 guest driver가 HW를 직접 소유한다. 전환은 별도 authority가 중재한다. |
| 암호화하면 악성 Host 문제를 모두 해결한다 | Host가 최종 평문 endpoint이면 해결할 수 없다. Host-visible 자료를 최소화해야 한다. |

## 12. 공식 자료와 원본 코드

- [S1] [Linux kernel: Protected KVM (pKVM)](https://www.kernel.org/doc/html/latest/virt/kvm/arm/pkvm.html)
- [S2] [Linux kernel: KVM/arm64-specific hypercalls](https://www.kernel.org/doc/html/latest/virt/kvm/arm/hypercalls.html)
- [S3] [AOSP: AVF architecture](https://source.android.com/docs/core/virtualization/architecture)
- [S4] [Linux man-pages: `vsock(7)`](https://www.man7.org/linux/man-pages/man7/vsock.7.html)
- [S5] [crosvm: Vsock device](https://crosvm.dev/book/devices/vsock.html)
- [S6] [Linux kernel: Virtio on Linux](https://docs.kernel.org/driver-api/virtio/virtio.html)
- [S7] [OASIS: Virtual I/O Device (VIRTIO) 1.4](https://docs.oasis-open.org/virtio/virtio/v1.4/virtio-v1.4.pdf)
- [S8] [AOSP source: Android Virtualization Framework API](https://android.googlesource.com/platform/packages/modules/Virtualization/+/HEAD/libs/framework-virtualization/README.md)
- [S9] [AOSP: AVF security](https://source.android.com/docs/core/virtualization/security)
- [S10] [Linux kernel: Networking kernel API](https://docs.kernel.org/networking/kapi.html)
- [S11] [Linux source: generic vhost core](https://github.com/torvalds/linux/blob/master/drivers/vhost/vhost.c)
- [S12] [Linux source: vhost-vsock backend](https://github.com/torvalds/linux/blob/master/drivers/vhost/vsock.c)
- [S13] [AOSP Android 16 source: device assignment](https://android.googlesource.com/platform/packages/modules/Virtualization/+/refs/heads/android16-release/docs/device_assignment.md)
- [S14] [Linux kernel: VFIO](https://docs.kernel.org/driver-api/vfio.html)
- [S15] [Linux kernel: Remote Processor Messaging](https://docs.kernel.org/staging/rpmsg.html)
- [S16] [Linux kernel: DMA and `swiotlb`](https://docs.kernel.org/core-api/swiotlb.html)
- [S17] [AOSP: Implement a pKVM vendor module](https://source.android.com/docs/core/virtualization/pkvm-modules)
- [S18] [AOSP: VirtualizationService](https://source.android.com/docs/core/virtualization/virtualization-service)

[S1]: https://www.kernel.org/doc/html/latest/virt/kvm/arm/pkvm.html
[S2]: https://www.kernel.org/doc/html/latest/virt/kvm/arm/hypercalls.html
[S3]: https://source.android.com/docs/core/virtualization/architecture
[S4]: https://www.man7.org/linux/man-pages/man7/vsock.7.html
[S5]: https://crosvm.dev/book/devices/vsock.html
[S6]: https://docs.kernel.org/driver-api/virtio/virtio.html
[S7]: https://docs.oasis-open.org/virtio/virtio/v1.4/virtio-v1.4.pdf
[S8]: https://android.googlesource.com/platform/packages/modules/Virtualization/+/HEAD/libs/framework-virtualization/README.md
[S9]: https://source.android.com/docs/core/virtualization/security
[S10]: https://docs.kernel.org/networking/kapi.html
[S11]: https://github.com/torvalds/linux/blob/master/drivers/vhost/vhost.c
[S12]: https://github.com/torvalds/linux/blob/master/drivers/vhost/vsock.c
[S13]: https://android.googlesource.com/platform/packages/modules/Virtualization/+/refs/heads/android16-release/docs/device_assignment.md
[S14]: https://docs.kernel.org/driver-api/vfio.html
[S15]: https://docs.kernel.org/staging/rpmsg.html
[S16]: https://docs.kernel.org/core-api/swiotlb.html
[S17]: https://source.android.com/docs/core/virtualization/pkvm-modules
[S18]: https://source.android.com/docs/core/virtualization/virtualization-service
