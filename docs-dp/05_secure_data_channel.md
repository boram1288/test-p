# DP-05. pVM 간 보안 데이터 채널 구조

## 1. 상태

평가 중

## 2. 결정 목적

Camera pVM과 AI pVM의 frame 전달 경로를 정한다.
Host가 frame을 볼 수 있는 범위를 정한다.
buffer와 metadata의 소유권 전환 방식을 정한다.

## 3. 문제 상황

- 선행 DP: DP-03 pVM 생명주기, DP-04 Workload identity/measurement
- 연관 DP: DP-06 HW 할당과 DMA 격리
- 범위: encrypted Host relay는 baseline 비교안이다. EL2 DMA-BUF lease와 metadata queue는 project-custom PoC 확장이므로 제품 baseline 제공 기능과 구분한다.

Camera frame은 크고 전송 빈도가 높다.
복사 기반 전달은 CPU와 memory bandwidth를 사용한다.
plaintext Host relay는 raw frame을 Host에 노출한다.
서로 다른 pVM은 FD table을 공유하지 않는다.
buffer 반환 실패는 stale mapping을 남길 수 있다.

## 4. 결정 질문

Host가 종단간 암호화된 frame을 opaque하게 relay할 것인가?
아니면 EL2가 shared backing의 lease를 중재할 것인가?

## 5. 후보 구조

### 후보 A. 종단간 암호화 Host Relay 채널

Camera가 measurement-bound AI identity와 인증된 session key를 수립한다.
Camera가 frame과 metadata를 AEAD로 암호화한다.
Host는 ciphertext만 AI pVM으로 relay한다.
AI는 tag, session ID와 sequence를 검증한 뒤 복호화한다.

### 후보 B. EL2 중재 Shared Buffer 채널

Camera가 protected buffer를 export한다.
EL2가 receiver와 lease를 검증한다.
AI는 같은 backing을 새 local FD로 import한다.
Metadata는 별도 bounded message로 전달한다.

## 6. 후보별 동작 구조

### 후보 A

```text
Camera pVM
  -> AEAD ciphertext + authenticated metadata
  -> Host relay buffer
  -> guest transport
  -> AI pVM
```

- 실행 위치: relay와 routing을 Host에 둔다.
- 제어 흐름: endpoint가 session과 frame sequence를 검증하고 Host는 opaque routing만 수행한다.
- 데이터 흐름: Host address space에는 ciphertext와 제한된 routing metadata만 지난다.
- 신뢰 경계: Camera/AI identity, session key와 AEAD 구현을 신뢰한다. Host backend는 비신뢰다.
- 자원 소유권: endpoint가 plaintext buffer를 소유하고 Host는 ciphertext relay buffer만 소유한다.
- 자원 회수: Host가 연결/ciphertext buffer를 정리하고 endpoint가 session key와 replay state를 폐기한다.

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
- 자원 소유권: `CAMERA_WRITE -> TRANSFER_PENDING -> AI_READ -> RETURNING -> CAMERA_WRITE` 상태를 따른다. crash/timeout은 `REVOKED`로 종료한다. AI mapping은 read-only다.
- 자원 회수: return 또는 revoke가 mapping을 제거한다.
- metadata는 `transfer_id`, `frame_seq`, buffer size와 receiver identity에 인증 결합한다.

DP-05를 buffer lease state의 정본으로 사용한다.
DP-06은 각 상태에서 허용된 DMA owner/mapping을 집행한다.

| Lease state | CPU mapping | DP-06 DMA owner/mapping | 전환 조건 |
|---|---|---|---|
| `CAMERA_WRITE` | Camera RW | Camera HW만 RW | 신규 frame 작성 |
| `TRANSFER_PENDING` | 신규 CPU access 금지 | owner 없음 | Camera fence 완료, Camera DMA revoke |
| `AI_READ` | AI read-only | AI HW만 read | receiver/transfer 검증, break-before-make 완료 |
| `RETURNING` | 신규 CPU access 금지 | owner 없음 | AI fence/quiesce, AI DMA revoke |
| `REVOKED` | mapping 없음 | owner 없음 | crash, timeout 또는 검증 실패 |

## 7. 품질속성 비교

### 7.1 필수 gate

| Gate | 합격 기준 | 후보 A | 후보 B |
|---|---|---|---|
| SEC-01 Host 침해 기밀성 | Host에서 raw frame 노출 0건 | 인증된 key 수립 시 통과 가능 | EL2 mapping 격리 확인 필요 |
| PERF-02 zero-copy | 데이터 경로 `memcpy` 0회 | 암복호화와 relay 때문에 실패, 비교 기준선 | PoC 확인 필요 |
| 수명주기 완결성 | crash/timeout 뒤 stale mapping과 key 0건 | session key 폐기 확인 필요 | revoke 원자성 확인 필요 |

후보 A는 SEC-01을 만족할 수 있지만 PERF-02 필수 gate를 구조적으로 만족하지 못한다.
따라서 선택 후보가 아니라 EL2 확장 없이 가능한 보안 비교 기준선으로 사용한다.

### 7.2 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.
PERF-02가 frame 전달 p99 5ms와 `memcpy` 0회를 정의한다.
후보 B의 별점은 hypercall, TLB invalidation, cache/fence 비용을 포함한 실측 전 가설이다.

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

### 7.3 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | — | SEC-01은 만족 가능하지만 PERF-02 gate 실패로 비교 기준선이다. | ★★★ | Host relay 없이 receiver mapping을 만든다. |
| 성능 | — | frame 전체 암복호화와 relay 비용이 발생한다. | ★★★ | 같은 backing을 import한다. 실측 전 잠정치다. |
| 확장성 | — | 일반 transport routing을 재사용한다. | ★★ | endpoint policy와 queue 한계를 관리해야 한다. |
| 변경 용이성 | — | 표준 socket/crypto adapter를 재사용한다. | ★ | EL2, guest driver와 UAPI가 함께 바뀐다. |
| 자원 효율 | — | ciphertext buffer와 crypto CPU/전력이 추가된다. | ★★★ | frame backing을 복사하지 않는다. |

## 8. 핵심 트레이드오프

후보 A는 표준 transport를 재사용하면서 Host에는 ciphertext만 노출한다.
대신 zero-copy gate를 포기하고 crypto CPU/전력과 relay 지연을 지불한다.

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
- 후보 A의 key 교환에서 Host 위장, ciphertext 변조, replay와 sequence 역전을 시험한다.
- 후보 A의 frame당 crypto CPU 사용률, 전력과 추가 buffer 수를 측정한다.
- 후보 B에서 Camera/AI CPU mapping, device DMA mapping과 cache/fence 순서를 추적한다.
- 위 owner-state 표를 기준으로 DP-06 DMA owner/mapping이 모든 전환에서 일치하는지 검증한다.
- baseline pKVM과 project-custom EL2 lease/UAPI 변경 범위를 분리 기록한다.

## 10. 검토 결과

사용자 요청에 따라 Claude와 교차 검토했다.
Host relay는 종단간 암호화 기준선으로 바꿨지만 PERF-02 zero-copy gate 실패를 명시했다.
EL2 lease의 owner state, read-only receiver mapping과 DP-06 DMA owner 정합 gate를 추가했다.
project-custom EL2 기능과 성능 PoC 확인이 남아 있다.

## 11. 최종 결정
