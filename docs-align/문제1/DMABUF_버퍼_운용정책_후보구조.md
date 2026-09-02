# 문제 1. DMA-BUF 버퍼 운용 정책 기반 후보 구조

## 1. 결정 질문

기존의 `Pair-Direct 대 Protected Broker`는 exporter와 control plane의 배치 방식에
관한 결정이다. 이번 후보를 가르는 1차 결정축은 다음과 같다.

> Camera pVM과 AI pVM 사이에서 보호 frame buffer를 frame마다 동적으로 생성하고
> 폐기할 것인가, stream session 동안 사전 할당한 bounded pool의 slot을 순환시킬
> 것인가?

후보는 정확히 두 개다.

| 후보 | 버퍼 운용 정책 | 주 스타일 |
|---|---|---|
| A. Per-Frame Dynamic DMA-BUF | frame마다 allocation, export, import, release와 delete 수행 | Pipe-and-Filter, Dynamic Resource Allocation |
| B. REQBUFS-Style Shared Buffer Pool | session 시작 시 N개 slot을 등록하고 queue로 반복 사용 | Resource Pool, Producer-Consumer, Queue-Based Pipeline |

`Pair-Direct 대 Protected Broker`는 두 후보 모두에 적용할 수 있는 2차 결정축으로
내린다. 두 후보를 공정하게 비교하기 위해 동일한 protected control plane을 사용한다고
가정한다.

## 2. 용어 보정

DRM PRIME과 DMA-BUF 자체가 frame별 buffer 생성을 요구하지는 않는다. PRIME은 GEM
handle과 DMA-BUF fd 사이의 export/import 및 cross-device buffer sharing을 제공한다.

또한 `VIDIOC_REQBUFS`는 `V4L2_MEMORY_MMAP`에서는 device buffer를 할당하지만,
`V4L2_MEMORY_DMABUF`에서는 application이 별도로 할당한 DMA-BUF를 사용하는 streaming
mode와 내부 queue를 설정한다. 따라서 후보 B는 Linux ioctl을 그대로 복제하는 것이
아니라 `REQBUFS`, `QBUF`, `DQBUF`, `STREAMOFF`의 pool과 queue 수명 의미를 적용한다.

- [DRM PRIME 공식 문서](https://docs.kernel.org/gpu/drm-mm.html)
- [V4L2 REQBUFS 공식 문서](https://docs.kernel.org/userspace-api/media/v4l/vidioc-reqbufs.html)
- [V4L2 QBUF/DQBUF 공식 문서](https://docs.kernel.org/userspace-api/media/v4l/vidioc-qbuf.html)

DMA-BUF fd, GEM handle과 DRM framebuffer ID는 각 kernel 또는 DRM file에 local하다.
두 pVM 사이에는 fd 정숫값이나 framebuffer ID가 아니라 protected identity와 image
metadata를 전달해야 한다. 멀티플레인 frame은 하나 이상의 DMA-BUF로 구성될 수 있다.

## 3. 공통 전제와 불변조건

```text
Camera pVM local DMA-BUF ─┐
                           ├─> 동일한 보호 backing page
AI pVM local DMA-BUF ─────┘

Camera HW ──DMA write──> 보호 backing page ──DMA read──> AI HW
```

- 정상 frame payload `memcpy`는 0회다.
- Host와 등록되지 않은 제3 pVM은 frame payload를 mapping하거나 읽지 못한다.
- Camera와 AI pVM은 서로 다른 kernel이므로 각각 local DMA-BUF proxy를 가진다.
- image metadata는 format, modifier, width, height와 plane별 offset, stride, size를 포함한다.
- producer fence가 완료되기 전에 AI job을 제출하지 않는다.
- consumer DMA 완료와 모든 reference 해제 전에 backing을 재사용하거나 해제하지 않는다.
- fence 완료와 reference 해제는 서로 다른 사건이다.
- endpoint crash 후 해당 endpoint generation의 handle, reference와 mapping을 회수한다.
- stale identity와 이미 signal된 fence를 새 frame에 재사용하지 않는다.
- pVM CPU 접근용 Stage-2 mapping과 장치 DMA용 SMMU/IOMMU mapping을 구분한다.
- 장치 DMA를 quiesce하거나 reset한 것을 확인하기 전에 mapping을 제거하거나 page를
  해제하지 않는다.

### 3.1 공통 컴포넌트

| ID와 이름 | 위치 | 책임 |
|---|---|---|
| C-01 Camera Frame Producer | Camera pVM | capture 시작, frame sequence와 producer fence 생성 |
| C-02 Camera DMA-BUF Adapter | Camera pVM | 보호 page를 Camera local DMA-BUF로 표현 |
| C-03 Protected Buffer Registry | EL2 또는 보호 service | identity, generation과 cross-pVM reference 관리 |
| C-04 Protected Mapping Adapter | EL2와 SMMU/IOMMU 제어 경로 | pVM Stage-2 및 장치 DMA mapping 관리 |
| C-05 Fence Relay | 보호 control plane | Camera와 AI kernel 사이 fence translation |
| C-06 Endpoint Health Monitor | EL2 또는 보호 service | Camera/AI generation과 crash 감지 |
| C-07 AI DMA-BUF Proxy Importer | AI pVM | protected identity를 AI local DMA-BUF와 attachment로 변환 |
| C-08 AI Frame Consumer | AI pVM | fence 대기, AI job 제출과 consumer fence 생성 |

## 4. 후보 A — Per-Frame Dynamic DMA-BUF

### 4.1 구조적 핵심

Camera workload가 capture할 frame마다 새로운 backing allocation과 buffer identity를
만든다. AI workload는 frame마다 protected handle을 redeem하고 local DMA-BUF와 device
attachment를 생성한다. AI 처리가 끝나면 양쪽 local 객체, cross-pVM reference, mapping과
backing allocation을 frame 단위로 정리한다.

```text
Frame N
  생성 -> 등록 -> Camera DMA -> 공유 -> AI import
       -> AI DMA -> release -> unmap -> 삭제

Frame N+1
  별도의 backing allocation과 buffer identity 사용
```

### 4.2 Camera workload 모듈

| ID와 이름 | 책임 |
|---|---|
| A-01 Frame Admission Controller | 최대 outstanding frame을 제한하고 capture 허용 여부 결정 |
| A-02 Per-Frame Buffer Allocator/Exporter | frame마다 backing과 Camera local DMA-BUF 생성 |
| A-03 Camera Capture Submitter | Camera HW attachment와 capture DMA 제출 |
| A-04 Frame Publisher | image metadata, protected handle과 producer fence 게시 |
| A-05 Frame Reclaimer | AI release 후 handle, local DMA-BUF와 backing 정리 |

### 4.3 보호 control plane 모듈

| ID와 이름 | 책임 |
|---|---|
| A-06 Per-Frame Handle Registry | frame handle, generation, endpoint와 reference 기록 |
| A-07 Per-Frame Mapping Manager | frame 등록/import 시 mapping하고 마지막 reference 후 unmap |
| A-08 Fence Translator | frame별 producer/consumer fence 전달 |
| A-09 Orphan Buffer Reaper | endpoint crash와 timeout buffer 격리 및 회수 |

### 4.4 AI workload 모듈

| ID와 이름 | 책임 |
|---|---|
| A-10 Frame Token Receiver | frame descriptor와 protected handle 검증 |
| A-11 On-Demand Proxy Importer | frame마다 AI local DMA-BUF와 device attachment 생성 |
| A-12 Fence-Gated AI Scheduler | producer fence 완료 후 AI HW job 제출 |
| A-13 Frame Release Adapter | consumer fence와 release 전송 후 local handle 정리 |

### 4.5 Frame identity

```text
DynamicFrameToken
  producer_endpoint_generation
  buffer_uuid
  buffer_generation
  frame_sequence
  format, modifier, width, height
  plane_count
  plane[].offset, stride, size
  producer_fence
```

fd나 GEM handle은 local identity이므로 token에 넣지 않는다. `buffer_uuid`와 generation을
cross-pVM identity로 사용한다.

### 4.6 정상 동작

1. A-01 Frame Admission Controller가 outstanding 한도를 확인한다.
2. A-02 Per-Frame Buffer Allocator/Exporter가 backing page와 local DMA-BUF를 생성한다.
3. A-06 Per-Frame Handle Registry가 buffer와 endpoint generation을 등록한다.
4. A-07 Per-Frame Mapping Manager가 Camera 장치용 DMA mapping을 설정한다.
5. A-03 Camera Capture Submitter가 Camera HW capture를 제출한다.
6. Camera DMA 완료 후 A-04 Frame Publisher가 handle, metadata와 producer fence를 게시한다.
7. A-11 On-Demand Proxy Importer가 AI local DMA-BUF와 attachment를 만든다.
8. A-12 Fence-Gated AI Scheduler가 producer fence 완료 후 AI HW job을 제출한다.
9. AI 완료 후 A-13 Frame Release Adapter가 consumer fence와 release를 전송한다.
10. 모든 reference와 DMA 완료를 확인한 뒤 Stage-2 및 SMMU/IOMMU mapping을 제거한다.
11. local DMA-BUF와 backing page를 해제한다.

### 4.7 수명 모델

```text
Allocation lifetime
  backing 할당
    -----------------------------------> 최종 unmap/free

Frame-content lifetime
             Camera write 완료
                    -------------------> AI read 완료
```

두 수명은 비슷하게 움직이지만 동일하지 않다. AI read가 끝나도 남은 local handle,
attachment, fence와 DMA 작업이 있으면 backing을 해제할 수 없다.

### 4.8 Backpressure

- `max_outstanding_frames`로 allocation을 제한한다.
- 한도 도달 시 새 backing을 할당하기 전에 capture를 차단한다.
- capture 대기, sensor throttle 또는 capture 시작 전 frame drop 중 하나를 정책으로 정한다.
- Camera DMA가 이미 시작된 buffer를 AI 지연 때문에 덮어쓰지 않는다.
- allocation 실패와 frame publication 실패를 구분한다.

### 4.9 종료와 장애 처리

| 사건 | 처리 |
|---|---|
| 정상 종료 | 신규 admission 중지, outstanding frame drain, frame별 mapping과 backing 정리 |
| stale handle | endpoint generation, buffer UUID와 buffer generation 불일치 거부 |
| Camera crash | Camera generation 폐기, 신규 redeem 차단, Camera DMA 정지 후 격리·회수 |
| AI crash | AI DMA 정지 후 해당 generation reference 강제 해제, AI mapping 제거 |
| producer fence timeout | AI job을 제출하지 않고 해당 frame 격리 |
| consumer fence timeout | AI device reset 결과가 확인될 때까지 backing 재사용과 free 금지 |
| 부분 등록 실패 | handle, reference, device mapping과 Stage-2 mapping을 역순 rollback |

### 4.10 장단점

장점:

- frame별 fault containment가 명확하다.
- 해상도, format, modifier와 allocation 크기 변화에 유연하다.
- 사용하지 않을 때 보호 메모리를 점유하지 않는다.
- 문제가 생긴 frame 하나만 격리하거나 폐기하기 쉽다.

단점:

- 매 frame allocation, register, mapping, import, attachment와 delete가 발생한다.
- allocator fragmentation과 latency jitter가 커질 수 있다.
- 지속 streaming에서 control path가 병목이 될 수 있다.
- crash와 timeout에 따른 orphan buffer 수가 많아질 수 있다.

## 5. 후보 B — REQBUFS-Style Shared Buffer Pool

### 5.1 구조적 핵심

stream 시작 시 N개의 protected backing buffer를 준비한다. 각 slot은 session 동안 local
DMA-BUF, mapping과 device attachment를 유지한다. frame마다 새로 생성하는 것은 backing
allocation이 아니라 slot의 content generation과 producer/consumer fence다.

```text
Pool 생성: Slot 0 ... Slot N-1 allocation, mapping, import

반복:
FREE -> CAMERA_QUEUED -> CAMERA_ACTIVE -> READY_FOR_AI
     -> AI_ACTIVE -> RETURNING -> FREE
```

V4L2 capture 관점에서는 빈 slot을 `QBUF`하고 capture 완료된 slot을 `DQBUF`한 후 AI에
넘기는 의미다. `QBUF`된 DMA-BUF는 `DQBUF`, `STREAMOFF` 또는 device close까지 driver가
사용하는 buffer로 취급한다.

### 5.2 Camera workload 모듈

| ID와 이름 | 책임 |
|---|---|
| B-01 Pool Session Manager | format, slot 수와 session 경계 협상 |
| B-02 Pool Provisioner/Exporter | N개 backing과 Camera local DMA-BUF 사전 생성 |
| B-03 Camera Free Queue Manager | FREE slot을 Camera capture queue에 QBUF |
| B-04 Camera Capture Completion Adapter | 완료 slot을 DQBUF하고 content sequence 부여 |
| B-05 Ready Slot Publisher | slot token과 producer fence를 AI에 전달 |
| B-06 Returned Slot Requeuer | AI가 반환한 slot을 FREE 또는 QBUF로 이동 |

### 5.3 보호 control plane 모듈

| ID와 이름 | 책임 |
|---|---|
| B-07 Pool Registry | pool generation, slot table, endpoint와 format 관리 |
| B-08 Slot State Manager | slot 상태 전이와 queue invariant 검증 |
| B-09 Persistent Mapping Manager | pool 설정 시 mapping하고 종료 시 일괄 해제 |
| B-10 Fence/Event Relay | slot 회전별 producer/consumer fence 전달 |
| B-11 Pool Recovery Manager | 오류 slot 격리, endpoint crash와 pool 재구성 처리 |

### 5.4 AI workload 모듈

| ID와 이름 | 책임 |
|---|---|
| B-12 AI Pool Session Client | pool의 모든 slot을 session 시작 시 한 번 import |
| B-13 AI Ready Queue Manager | READY_FOR_AI slot 수신과 identity/순서 검증 |
| B-14 Fence-Gated AI Scheduler | 해당 content sequence의 fence 완료 후 AI job 제출 |
| B-15 AI Slot Return Manager | consumer fence와 함께 slot 반환 |
| B-16 AI Pool Detacher | stream 종료 시 attachment와 local DMA-BUF 일괄 정리 |

### 5.5 Slot identity

```text
PoolSlotToken
  pool_id
  pool_generation
  slot_index
  slot_generation
  content_sequence
  producer_endpoint_generation
  consumer_endpoint_generation
  producer_fence
```

- `pool_generation`: pool 재생성 또는 session 재시작을 구분한다.
- `slot_generation`: slot backing 교체나 재할당을 구분한다.
- `content_sequence`: 동일 slot에 새 frame이 채워진 회차를 구분한다.

`slot_index`만 전달하면 이전 회차의 지연된 release가 현재 frame을 반환시키는 ABA
문제가 발생한다.

### 5.6 정상 동작

Pool 설정:

1. B-01 Pool Session Manager가 format, modifier와 N을 결정한다.
2. B-02 Pool Provisioner/Exporter가 N개 buffer를 생성한다.
3. B-07 Pool Registry가 pool과 slot table을 등록한다.
4. B-09 Persistent Mapping Manager가 각 slot을 두 pVM과 Camera/AI 장치에 mapping한다.
5. B-12 AI Pool Session Client가 모든 slot을 local DMA-BUF로 한 번씩 import한다.
6. 모든 slot을 `FREE` 상태로 전환한다.

Frame 반복:

1. B-03 Camera Free Queue Manager가 FREE slot을 capture queue에 넣는다.
2. Camera HW가 slot에 DMA write한다.
3. capture 완료 후 slot을 DQBUF하고 `content_sequence`를 증가시킨다.
4. 새 producer fence와 함께 slot을 `READY_FOR_AI`로 게시한다.
5. AI가 pool, slot, content와 endpoint generation을 검증한다.
6. producer fence 완료 후 B-14 Fence-Gated AI Scheduler가 AI HW job을 제출한다.
7. AI 완료 후 B-15 AI Slot Return Manager가 consumer fence를 전송한다.
8. consumer fence와 모든 reference가 완료되면 slot을 `FREE`로 반환한다.
9. Camera workload가 같은 slot을 다시 QBUF한다.

### 5.7 수명 모델

```text
Pool allocation lifetime
  pool 생성
    ------------------------------------------------> pool 삭제

Frame N content lifetime
          Camera write 완료 ---------> AI read 완료

Frame N+1 content lifetime
                                  Camera write 완료 ---------> AI read 완료
```

같은 allocation 안에서 여러 frame content lifetime이 반복된다.

### 5.8 Backpressure

FREE slot이 0개라면 Camera는 어떤 slot도 덮어쓰면 안 된다.

- Camera capture를 block한다.
- sensor 또는 upstream capture를 throttle한다.
- capture 시작 전에 신규 frame을 drop한다.
- loss 0%가 필수라면 AI의 검증 가능한 최대 slot 보유시간을 수용하도록 N을 산정한다.

초기 slot 수 산정식은 다음과 같다.

```text
N >= Camera HW in-flight 수
     + ceil(frame rate * AI 최대 slot 보유시간)
     + jitter/recovery 여유 slot
```

평균 AI latency가 아니라 최대 보유시간을 기준으로 해야 한다.

### 5.9 정상 종료

1. 신규 QBUF와 frame publication을 중지한다.
2. Camera streaming을 중지하고 진행 중 DMA를 quiesce한다.
3. `READY_FOR_AI`와 `AI_ACTIVE` slot을 drain한다.
4. 반환된 slot을 다시 QBUF하지 않는다.
5. 양쪽 device attachment와 local DMA-BUF를 제거한다.
6. Stage-2와 SMMU/IOMMU mapping을 제거한다.
7. pool registry와 backing allocation을 일괄 해제한다.

`REQBUFS(0)`에 해당하는 논리적 삭제는 remote reference와 DMA가 남은 상태에서 실행하면
안 된다. 실제 V4L2도 mapped/exported buffer 처리 가능 여부가
`V4L2_BUF_CAP_SUPPORTS_ORPHANED_BUFS` capability에 따라 달라진다.

### 5.10 장애 처리

| 사건 | 처리 |
|---|---|
| stale slot | pool generation, slot generation과 content sequence 불일치 거부 |
| Camera crash | pool generation 폐기, 신규 READY 차단, Camera DMA 정지 후 영향 slot 격리 |
| AI crash | AI DMA 정지 후 AI_ACTIVE slot 격리, 나머지 slot의 계속 사용 여부 결정 |
| producer fence timeout | 해당 slot을 `ERROR_QUARANTINED`로 이동 |
| consumer fence timeout | AI reset 완료까지 slot 재사용 금지 |
| slot 장애 | 최소 watermark 이상이면 N-1개로 운용, 미만이면 pool 재구성 |
| queue 불일치 | pool freeze 후 registry와 양쪽 local queue 재동기화 |
| session 재시작 | pool과 endpoint generation을 증가시켜 이전 메시지 거부 |

### 5.11 장단점

장점:

- 정상 frame 경로에서 allocation, import와 mapping이 발생하지 않는다.
- 메모리 사용량과 최대 in-flight frame 수가 명확하다.
- latency와 jitter를 예측하기 쉽다.
- queue 자체가 backpressure 경계를 제공한다.
- 지속적인 고정 format stream에 적합하다.

단점:

- 사용하지 않는 slot도 session 동안 보호 메모리를 점유한다.
- format, modifier 또는 최대 크기 변경 시 pool 재생성이 필요하다.
- 느린 AI가 여러 slot을 잡으면 pool 전체가 고갈될 수 있다.
- stale slot과 queue state corruption 처리가 동적 모델보다 복잡하다.
- 오류 slot 격리가 누적되면 처리량이 급격히 감소한다.

## 6. Fence, cache와 zeroize 불변조건

Claude와 교차 검토한 결과를 Linux fence 의미에 맞게 다음과 같이 정리한다.

- 같은 ordered timeline이면 fence context는 session 동안 재사용할 수 있다.
- 각 frame 또는 slot 회전에는 새로운 fence instance와 단조 증가 seqno가 필요하다.
- 이미 signal된 fence나 seqno를 새 content에 재사용하지 않는다.
- endpoint identity가 바뀌면 새 fence context를 발급한다.
- cache maintenance는 coherency 문제이며 각 회전의 장치 접근 순서에 맞게 수행한다.
- zeroize는 confidentiality 문제이며 cache maintenance와 별도로 판단한다.
- trust domain 변경, endpoint 재할당, pool 재배정 또는 전체 overwrite가 보장되지 않을
  때 zeroize한다.
- 동일 producer가 유효 영역 전체를 덮어쓰는 것이 검증되면 매 frame zeroize는 생략할
  수 있다.

## 7. 후보 비교

| 비교 항목 | 후보 A: 프레임별 동적 | 후보 B: REQBUFS형 Pool |
|---|---|---|
| allocation lifetime | frame 중심 | stream session 중심 |
| content lifetime | allocation당 일반적으로 1회 | slot당 여러 회차 반복 |
| Camera local DMA-BUF 생성 | frame마다 | pool 설정 시 N개 |
| AI import와 attachment | frame마다 | pool 설정 시 N개 |
| Stage-2/SMMU mapping | frame마다 | pool 설정과 종료 시 |
| 정상 경로 identity | buffer UUID | pool/slot/content sequence |
| 메모리 사용량 | 탄력적 | 고정·bounded |
| steady-state latency | 상대적으로 높고 편차 큼 | 낮고 예측 가능 |
| format 변경 | frame별 대응 가능 | pool 재구성 필요 |
| backpressure | 별도 outstanding quota 필요 | FREE slot 수로 명시 |
| frame 장애 영향 | 해당 buffer로 격리 | slot 격리, pool 용량 감소 |
| stale message 위험 | stale handle | slot ABA 위험 |
| 정상 종료 | frame별 drain/delete | stream drain 후 pool 일괄 삭제 |
| 적합 workload | 희소·가변 frame | 지속·고정 format streaming |

## 8. 1차 권고와 검증 가설

1080p 30fps처럼 format과 producer/consumer가 안정적인 지속 streaming workload라면
후보 B인 `REQBUFS-Style Shared Buffer Pool`을 우선 평가한다.

아직 성능 실측이 없으므로 채택 결론이 아니라 다음 검증 가설로 둔다.

> 사전 import와 지속 mapping으로 정상 frame 경로의 allocation 및 mapping jitter를
> 제거하면 30fps와 frame loss 0% 조건에 유리하다.

후보 A는 다음 조건에서 우선 평가한다.

- frame 발생이 희소하거나 burst 형태다.
- frame 크기, format 또는 modifier가 자주 바뀐다.
- 고정 pool의 유휴 메모리 비용이 허용되지 않는다.
- 오류 영향 범위를 frame 하나로 제한하는 것이 latency보다 중요하다.
- 측정 결과 per-frame allocation/import/mapping 비용이 허용 범위 안이다.

consumer 수가 동적이라는 사실만으로 후보 A를 선택하지 않는다. 후보 B도 session
재등록이나 pool 재구성으로 consumer 변경을 지원할 수 있다.

## 9. 후속 상세 설계 항목

1. 두 후보의 생성, 공유, release, 삭제 sequence diagram
2. 후보 A의 frame 상태 머신과 후보 B의 pool/slot 상태 머신
3. protected token과 fence translation protocol
4. Camera/AI/broker crash injection별 회수 규칙
5. pool slot 수와 outstanding frame 상한 산정
6. 1080p 30fps latency, jitter, memory와 frame loss 측정
7. Stage-2와 SMMU/IOMMU 보호 기능의 platform 실현 가능성 검증
