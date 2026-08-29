# pkVM 환경에서 pVM 간 DMA-BUF 전달

조사일: 2026-07-12

## 결론

현재 Android AVF/pKVM의 표준 구성에서는 pVM A의 DMA-BUF를 pVM B에 DMA-BUF 그대로 전달할 수 없다. 실용적인 기본 해법은 vsock을 host relay로 사용해 버퍼 내용을 복사하는 것이다. 진짜 zero-copy 공유가 필요하면 pKVM과 guest kernel 양쪽에 새로운 공유 메모리 장치와 프로토콜을 구현해야 한다.

## DMA-BUF FD를 직접 전달할 수 없는 이유

DMA-BUF FD는 단순한 정수 식별자가 아니라 해당 Linux 커널 안의 `struct file`에서 `dma_buf` 객체로 이어지는 핸들이다.

- pVM A와 pVM B는 서로 다른 커널 인스턴스다.
- A의 FD 번호를 B에 숫자로 보내도 B의 FD 테이블에서는 아무 의미가 없다.
- 일반적인 FD 전달인 `SCM_RIGHTS`는 같은 커널의 AF_UNIX 소켓에서 커널 객체 참조를 복제하는 기능이다.
- AF_VSOCK은 바이트 스트림이며 DMA-BUF나 `SCM_RIGHTS` 객체 전달을 제공하지 않는다.
- DMA-BUF에 연결된 implicit fence인 `dma_resv`와 `dma_fence` 역시 다른 VM 커널로 자동 전달되지 않는다.

따라서 FD 자체를 전달하는 것이 아니라 두 VM의 드라이버가 각각 로컬 DMA-BUF FD를 만들고, 그 아래에서 같은 물리 페이지나 가상 리소스를 공유하는 별도 장치 프로토콜이 필요하다.

## pVM 간 vsock 통신

AF_VSOCK 주소 체계 자체는 CID로 VM을 식별하므로 API 형식만 보면 다른 guest CID를 지정할 수 있다. 하지만 현재 AVF에서 사용하는 `vhost-vsock` 구성은 사실상 host와 guest 사이의 통신을 제공한다.

Linux `vhost-vsock` backend는 guest TX 패킷을 처리할 때 목적지 CID가 host CID인지 검사하고, 그렇지 않으면 패킷을 버린다. 반대로 host에서는 목적지 CID로 해당 guest를 찾아 전송한다.

```text
pVM A ──vsock──> Android host ──vsock──> pVM B   가능
pVM A ─────────vsock───────────> pVM B           표준 AVF에서는 불가
```

Android 공식 아키텍처 문서도 AVF의 `vhost-vsock`을 host와의 통신 용도로 설명한다.

## 현재 구현 가능한 권장 방식

표준 AVF를 유지해야 한다면 host relay 방식이 가장 현실적이다.

```text
pVM A
  1. producer fence 대기
  2. DMA-BUF CPU mapping
  3. payload를 chunk 단위로 읽음
  4. vsock으로 metadata와 payload 전송
             │
             ▼
Android host relay
  5. A 연결에서 읽어 B의 CID와 port 연결로 전달
             │
             ▼
pVM B
  6. 로컬 dma-heap에서 DMA-BUF 할당
  7. payload 복사
  8. local fence 또는 완료 이벤트 생성
```

프로토콜에는 적어도 다음 정보가 필요하다.

- buffer ID와 generation
- 전체 크기
- pixel format 또는 데이터 형식
- plane별 offset, stride, size
- modifier 또는 tile layout
- producer 완료 상태
- sequence number
- payload checksum 또는 AEAD tag
- consume 완료 ACK

host가 pVM 내부 데이터를 볼 수 없어야 한다면 A와 B 사이에 end-to-end 암호화를 적용해야 한다. pVM의 DICE 또는 attestation 결과를 사용해 키를 합의하고, host relay는 암호문만 전달하도록 구성할 수 있다. 다만 host는 통신을 차단하거나 지연시키는 DoS를 여전히 수행할 수 있다.

이 방법에는 다음 특성이 있다.

- AVF와 pKVM 변경이 거의 필요 없다.
- DMA-BUF 공유가 아니라 데이터 복사다.
- A에서 virtqueue, host, virtqueue, B로 여러 번 복사된다.
- 고해상도 영상처럼 대역폭이 큰 경우 비용이 크다.

## zero-copy가 반드시 필요한 경우

표준 기능만으로는 불가능하며 다음과 같은 플랫폼 확장이 필요하다.

### 1. 전용 virtio shared-buffer 장치

가장 정석적인 설계다.

- pVM A의 guest driver가 버퍼를 `resource_id`로 export한다.
- EL2/pKVM이 해당 페이지를 B에도 명시적으로 매핑한다.
- pVM B의 guest driver가 `resource_id`를 import한다.
- B 커널 안에서 별도의 로컬 DMA-BUF FD를 생성한다.
- 실제 backing page만 A와 B가 공유한다.

```text
A의 fd ──> A dma-buf driver ─┐
                             ├─ shared physical pages
B의 fd <── B dma-buf driver ─┘
                ▲
       resource ID/control protocol
```

필수 구현 범위는 다음과 같다.

- pKVM의 guest-to-guest page share, map, unmap
- VM별 권한 및 승인 검사
- host가 페이지를 매핑하지 못하게 하는 stage-2 관리
- SMMU/IOMMU DMA 권한
- scatter-gather table 변환
- cache coherency와 cache maintenance
- 버퍼 수명 및 강제 회수
- VM 종료 시 revoke와 page wipe
- producer/consumer fence 전달
- 악성 guest의 잘못된 크기, offset, lifetime 방어

Android 문서에 나오는 현재 일반적인 memory-sharing 경로는 guest가 페이지를 host에 공유하는 형태다. 보안 모델상 소유자가 명시적으로 공유한 다른 pVM만 접근하게 하는 것은 허용 가능한 개념이지만, 이를 위한 범용 pVM-to-pVM DMA-BUF UAPI가 AVF에 제공되지는 않는다.

### 2. 동시 공유 대신 ownership transfer

A와 B가 동시에 접근할 필요가 없다면 더 안전한 설계다.

1. A가 버퍼 사용을 완료한다.
2. 모든 DMA와 fence 완료를 확인한다.
3. A의 CPU 및 DMA 매핑을 제거한다.
4. cache를 정리한다.
5. pKVM이 페이지 소유권을 A에서 B로 전환한다.
6. B가 로컬 DMA-BUF로 import한다.

동시 공유보다 격리와 동기화가 단순하지만, 이 방식 역시 pKVM과 양쪽 guest driver에 전용 기능을 추가해야 한다.

### 3. virtio-gpu/cross-domain 계열 활용

일반 VM 환경에서는 virtio-gpu resource ID, resource UUID, blob 또는 cross-domain 프로토콜을 이용해 host와 guest 사이에서 DMA-BUF와 유사한 공유를 구현할 수 있다.

하지만 이를 pVM A와 pVM B 사이에 적용하려면 다음 조건이 필요하다.

- 두 pVM에 virtio-gpu 또는 전용 proxy 장치 제공
- resource backing을 두 pVM에 안전하게 매핑
- protected memory와 IOMMU 지원
- host가 backing 내용을 읽지 못하도록 보장

따라서 현재 AVF에서 바로 사용할 수 있는 해결책은 아니며, 전용 shared-buffer virtio 장치를 설계할 때 참고할 수 있는 모델에 가깝다.

## 선택 기준

| 요구사항 | 현실적인 방법 |
|---|---|
| 적은 데이터, 구현 우선 | host-relayed vsock 복사 |
| host가 plaintext를 보면 안 됨 | host relay와 pVM 간 E2E 암호화 |
| 고대역폭이지만 일부 복사 허용 | chunked vsock relay와 로컬 DMA-BUF 재할당 |
| 진짜 동시 zero-copy | custom virtio shared-buffer와 pKVM guest-to-guest 공유 |
| 동시 접근 불필요 | pKVM 기반 ownership transfer |
| FD 숫자 또는 `SCM_RIGHTS`를 vsock으로 전달 | 불가능 |

현행 pkVM/AVF를 수정하지 않는 조건이라면 DMA-BUF 자체는 전달할 수 없고 host를 경유해 내용을 복사해야 한다. zero-copy가 제품 요구사항이라면 통신 API만의 문제가 아니라 pKVM 메모리 소유권, guest DMA-BUF 드라이버, IOMMU와 fence를 함께 설계하는 플랫폼 기능이 된다.

## 외부 참고 자료

- [Android AVF Architecture - memory ownership, virtio, DMA protection](https://source.android.com/docs/core/virtualization/architecture)
- [Android AVF Security - pVM memory isolation](https://source.android.com/docs/core/virtualization/security)
- [Linux DMA-BUF documentation](https://docs.kernel.org/driver-api/dma-buf.html)
- [Linux vsock(7)](https://man7.org/linux/man-pages/man7/vsock.7.html)
- [Linux unix(7) - SCM_RIGHTS](https://man7.org/linux/man-pages/man7/unix.7.html)
- [Linux vhost-vsock implementation](https://github.com/torvalds/linux/blob/master/drivers/vhost/vsock.c)

이 조사는 저장소 안의 기존 문서를 참고하지 않고 외부 공식 자료와 upstream 구현을 기준으로 수행했다.
