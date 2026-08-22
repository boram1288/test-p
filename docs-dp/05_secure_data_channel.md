# DP-05. pVM 간 보안 데이터 채널 구조

## 1. 상태

도출

## 2. 결정 목적

Camera pVM과 AI pVM의 frame 전달 경로를 정한다.
Host가 frame을 볼 수 있는 범위를 정한다.
buffer와 metadata의 소유권 전환 방식을 정한다.

## 3. 문제 상황

Camera frame은 크고 전송 빈도가 높다.
복사 기반 전달은 CPU와 memory bandwidth를 사용한다.
Host relay는 raw frame을 Host에 노출한다.
서로 다른 pVM은 FD table을 공유하지 않는다.
buffer 반환 실패는 stale mapping을 남길 수 있다.

## 4. 결정 질문

Host가 frame을 relay할 것인가?
아니면 EL2가 shared backing의 lease를 중재할 것인가?

## 5. 후보 구조

### 후보 A. Host Relay 채널

Camera가 Host transport로 frame을 보낸다.
Host가 frame을 AI pVM으로 전달한다.
Host가 buffer와 metadata를 함께 관리한다.

### 후보 B. EL2 중재 Shared Buffer 채널

Camera가 protected buffer를 export한다.
EL2가 receiver와 lease를 검증한다.
AI는 같은 backing을 새 local FD로 import한다.
Metadata는 별도 bounded message로 전달한다.

## 6. 후보별 동작 구조

### 후보 A

```text
Camera pVM
  -> guest transport
  -> Host backend
  -> Host buffer
  -> guest transport
  -> AI pVM
```

- 실행 위치: relay와 routing을 Host에 둔다.
- 제어 흐름: Host가 session과 frame sequence를 관리한다.
- 데이터 흐름: raw frame이 Host address space를 지난다.
- 신뢰 경계: Host backend가 frame 기밀성 경계에 포함된다.
- 자원 소유권: Host가 relay buffer를 소유한다.
- 자원 회수: Host가 양쪽 연결과 buffer를 정리한다.

### 후보 B

```text
Camera pVM
  -> local DMA-BUF
  -> HVC
  -> EL2 lease manager
       -> shared backing mapping
       -> bounded metadata queue
  -> AI local DMA-BUF FD
```

- 실행 위치: policy와 mapping을 EL2에 둔다.
- 제어 흐름: EL2가 endpoint와 transfer ID를 확인한다.
- 데이터 흐름: frame backing은 Host에 relay하지 않는다.
- 신뢰 경계: EL2와 guest driver가 frame 경계에 포함된다.
- 자원 소유권: lease 상태에 따라 Camera와 AI가 소유한다.
- 자원 회수: return 또는 revoke가 mapping을 제거한다.

## 7. 품질속성 비교

### 7.1 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.

| 품질속성 | KPI | 별 1개 | 별 2개 | 별 3개 |
|---|---|---|---|---|
| 보안성 | Host에서 관찰 가능한 raw frame byte 비율 | 1% 초과 | 0% 초과 1% 이하 | 0% |
| 성능 | frame 전달 지연 p99 | 5ms 초과 | 2.5ms 초과 5ms 이하 | 2.5ms 이하 |
| 확장성 | 신규 receiver role 추가 시 channel core 변경량 | 100 LoC 초과 | 1~100 LoC | 0 LoC |
| 변경 용이성 | transport 교체 시 수정 module 수 | 4개 이상 | 2~3개 | 1개 이하 |
| 자원 효율 | frame당 CPU memcpy 횟수 | 2회 이상 | 1회 | 0회 |

Linux DMA-BUF는 exporter와 importer가 같은 backing을 공유하게 한다.
Userspace에는 local FD를 제공한다.
별도 FD와 zero-copy KPI의 근거다.
[Linux DMA-BUF](https://docs.kernel.org/driver-api/dma-buf.html)

DMA-BUF의 CPU access에는 cache synchronization이 필요하다.
동시 device access는 별도 fence가 필요하다.
전달 지연에 fence와 cache 비용을 포함한 근거다.
[Linux DMA-BUF synchronization](https://kernel.org/doc/html/next/driver-api/dma-buf.html)

Virtio는 guest와 hypervisor가 shared virtqueue로 통신한다.
Host backend 경유 여부를 신뢰 경계에 포함한 근거다.
[Linux Virtio](https://docs.kernel.org/driver-api/virtio/virtio.html)

30fps의 frame 주기는 33.3ms다.
채널 목표 5ms는 frame 주기의 약 15%다.

### 7.2 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | ★ | Host backend가 raw frame을 처리한다. | ★★★ | Host relay 없이 receiver mapping을 만든다. |
| 성능 | ★ | 두 전송 구간과 relay copy가 필요하다. | ★★★ | 같은 backing을 import할 수 있다. |
| 확장성 | ★★★ | 일반 transport routing을 재사용할 수 있다. | ★★ | endpoint policy와 queue 한계를 관리해야 한다. |
| 변경 용이성 | ★★★ | 표준 socket adapter로 교체할 수 있다. | ★ | EL2, guest driver와 UAPI가 함께 바뀐다. |
| 자원 효율 | ★ | Host relay buffer와 copy가 추가된다. | ★★★ | frame backing을 복사하지 않는다. |

## 8. 핵심 트레이드오프

후보 A는 표준 transport와 Host 도구를 재사용한다.
대신 Host가 frame 기밀성 경계에 들어온다.

후보 B는 Host relay와 frame copy를 제거한다.
대신 EL2 TCB와 전용 UAPI가 증가한다.

## 9. 검증 기준

- 1080p 30fps 입력으로 10분간 실행한다.
- frame 전달 지연 p50, p95와 p99를 측정한다.
- `memcpy` 계열 호출을 frame별로 추적한다.
- Host mapping에서 frame marker를 검색한다.
- 잘못된 receiver ID를 주입한다.
- stale transfer ID와 duplicate metadata를 주입한다.
- Camera 종료 후 AI mapping의 revoke 시간을 측정한다.
- buffer와 metadata의 순서 역전을 시험한다.

## 10. 검토 결과

검토 전이다.

## 11. 최종 결정

