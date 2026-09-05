# 문제 1. DMA-BUF 버퍼 운용 정책 기반 후보 구조

상태: **평가 중**. 구조적 품질 평가일: 2026-09-05. 별점은 최대 3개이며 실측 전 잠정 평가다.

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
- backing 재사용은 해당 content 회차의 DMA 완료와 사용 lease/reference 종료 후에만 허용한다.
- backing 해제는 DMA 종료, mapping 정리와 allocation을 유지하는 reference 종료 후에만 허용한다.
- 후보 B의 session 동안 유지하는 객체 reference와 attachment는 매 회차의 반환 조건에 넣지 않는다.
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

- frame별 객체를 식별해 국소 오류 buffer를 격리하기 쉽다. 장치 reset이나 endpoint crash의 영향까지 frame 하나로 제한되는 것은 아니다.
- allocation 크기 변화에 유연하다. 해상도, format과 modifier 변경에는 장치별 재설정·호환성 조건도 충족해야 한다.
- outstanding frame과 격리 buffer를 모두 회수하면 payload backing 점유를 줄일 수 있다.
- 국소 오류는 해당 frame의 수명으로 정리할 수 있으나 회수 전까지 자원 상한에 포함한다.

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

여기서 session reference는 allocation을 살려두기 위한 참조이고, content 사용 lease는
현재 frame의 읽기·쓰기를 끝내기 위한 계약이다. 전자는 유지한 채 후자만 종료해야 slot을
반복 사용할 수 있다. 지속 mapping과 회차별 실제 접근권 강제의 양립 여부는 8절에서 별도로 평가한다.

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
8. 해당 content의 consumer DMA가 완료되고 모든 사용 lease/reference가 종료되면 slot을 `FREE`로 반환한다. Session reference와 attachment는 유지한다.
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

보유시간에는 `READY_FOR_AI` 대기, AI 실행과 반환 처리까지 포함한다. 이 식은 최대
보유시간과 입력 burst가 제한된 경우의 초기 산정 모델이며, 실제 상한은 동시 점유 상태로
검증해야 한다. 평균 AI latency만으로 N을 정해서는 안 된다. AI 정지가 무한히 길어지거나
지속 처리율이 입력률보다 낮으면 유한한 N으로 30fps 입력과 loss 0%를 계속 보장할 수 없다.

### 5.9 정상 종료

1. 신규 QBUF와 frame publication을 중지한다.
2. Camera streaming을 중지하고 진행 중 DMA를 quiesce한다.
3. `READY_FOR_AI`와 `AI_ACTIVE` slot을 drain한다.
4. 반환된 slot을 다시 QBUF하지 않는다.
5. 양쪽 장치의 DMA mapping을 해제한 뒤 device attachment를 detach한다.
6. pVM CPU 접근용 Stage-2 mapping을 제거한다.
7. local DMA-BUF와 session reference를 정리한다.
8. pool registry와 backing allocation을 일괄 해제한다.

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

- 정상 frame 경로에서 backing allocation, 최초 import와 DMA 주소 연결의 반복 준비를 줄인다. 회차별 권한 갱신까지 생략할 수 있는지는 별도 검증이 필요하다.
- 메모리 사용량과 최대 in-flight frame 수가 명확하다.
- latency와 jitter를 예측하기 쉽다.
- queue 자체가 backpressure 경계를 제공한다.
- 지속적인 고정 format stream에 적합하다.

단점:

- 사용하지 않는 slot도 session 동안 보호 메모리를 점유한다.
- 협의한 format, modifier 또는 크기 범위를 벗어나면 pool 재협상·재구성이 필요하다.
- 느린 AI가 여러 slot을 잡으면 pool 전체가 고갈될 수 있다.
- 반복 slot의 ABA와 queue 정합성 검증이 필요하다. A의 반복 등록·부분 실패 rollback과 다른 복잡성이다.
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
| backing과 DMA 주소 연결 | frame마다 설정·정리 | pool 설정과 종료 시 중심. 회차별 접근권 갱신은 별도 |
| 정상 경로 identity | buffer UUID | pool/slot/content sequence |
| 메모리 사용량 | outstanding·byte 상한 안에서 탄력적 | N개 slot을 session 동안 유지 |
| steady-state latency | 반복 준비 비용으로 불리할 것으로 예상 | 준비 비용을 분산해 유리할 것으로 예상. 권한 전환 비용 확인 필요 |
| format 변경 | 버퍼는 frame별 대응 가능. 장치 재설정 제약은 별도 | 협의 범위 밖이면 pool 재구성 필요 |
| backpressure | 별도 outstanding quota 필요 | FREE slot 수로 명시 |
| 국소 frame 오류 | 해당 buffer 격리, 회수 전까지 outstanding 용량 감소 | slot 격리, 사용 가능한 pool 용량 감소 |
| stale message 위험 | stale handle | slot ABA 위험 |
| 정상 종료 | frame별 drain/delete | stream drain 후 pool 일괄 삭제 |
| 적합 workload | 희소·가변 frame | 지속·고정 format streaming |

## 8. 품질속성의 구조적 평가 — 최대 별 3개

**지속적인 고정 format stream에서는 B가 반복 준비 비용과 실행 중 자원 확보 실패를
줄이는 데 유리하다. A는 짧거나 희소한 작업의 시작 비용, 유휴 backing 점유와 버퍼 규격
변경에 유리하다. 보안 강제와 endpoint 장애 복구는 할당 정책만으로 우열을 확정할 수 없다.**

### 8.1 평가 기준과 공통 조건

[후보 구조 품질 평가 규칙](../후보_구조_품질_평가_규칙.md)에 따라 필수 조건과 별점을
분리한다. 요구 추적은 [QA·Measure 정의](../품질속성_QA_Measure_ISO25010.md)의 QA-01~08과
M-xx ID를 사용한다. 자료마다 문제 번호가 달라 pVM 간 데이터 전달이라는 주제로 대응한다.
이 평가는 **구조적 추론**이며 성능 실측, 승인된 KPI 구간 또는 채택 결론이 아니다.

| 잠정 별점 | 이번 구조 평가에서의 의미 |
|---|---|
| 잠정 ★★★ | 해당 시나리오의 주요 비용·실패 원인을 구조에서 제거하거나, 요구 변화를 직접 수용한다. |
| 잠정 ★★☆ | 명시된 관리 책임으로 대응하지만 추가 계약이 필요하거나, 상반된 효과로 우열을 가르기 어렵다. |
| 잠정 ★☆☆ | 해당 시나리오에서 반복 준비나 session 재구성과 같은 부담을 피하기 어렵다. 부적합 판정이나 gate 실패를 뜻하지 않는다. |

정량 KPI 값과 확정 별점 구간은 모두 **TBD**다. 두 후보에 같은 기준을 적용하고,
가중 평균·합계·종합 별점은 만들지 않는다. 보안·정확성처럼 현재 지표가 pass/fail뿐인
항목은 별점 대신 필수 조건으로 평가한다.

비교 조건은 다음과 같이 고정한다.

- 같은 Camera→AI 두 pVM, protected control plane, HW, allocator 종류와 보안 요구를 사용한다.
- 정상 지속 부하는 M-01b/M-01c의 **1080p RGB24, 30fps, 10분 이상**을 적용한다. Warm-up과 배경 부하도 같게 한다.
- 같은 payload byte 예산과 최대 동시 frame 수를 적용한다. 고정 크기 비교에서는 A의 `max_outstanding_frames = B의 N`으로 둔다.
- 준비 중·격리 중·회수 대기 buffer도 byte와 outstanding 상한에 포함한다. A에만 무제한 추가 allocation을 허용하지 않는다.
- 같은 접근권 정책, fence·cache·zeroize 조건과 장치 reset 범위를 적용한다. B만 보안 처리를 생략해 얻은 성능은 비교 근거로 사용하지 않는다.
- 시작·희소 입력·규격 변경·장애 시나리오는 정상 지속 부하와 분리해 양쪽에 동일하게 적용한다. Session을 유지한 유휴 상태와 session 종료도 구분한다.

### 8.2 필수 조건 평가

여기서 `확인 필요`는 문서에 의도와 책임이 있지만 실제 집행·시험 근거가 없다는 뜻이다.
아래 조건을 통과할 수 있다는 전제로만 8.3절의 잠정 별점을 해석한다.

| 필수 조건 | 요구·판정 기준 | A | B | 구조 검토 결과와 남은 확인 |
|---|---|---|---|---|
| 정상 지속 처리 | QA-01 / M-01c: 30fps 이상, 유실률 0% | 확인 필요 | 확인 필요 | B는 반복 준비 비용을 줄인다. 두 후보 모두 AI 처리율·최대 보유시간·입력 제어 조건이 필요하며, capture 전 drop도 입력 손실로 별도 기록해야 한다. |
| 정상 payload zero-copy | QA-02 / M-02d: 0회, 0 byte/frame | 확인 필요 | 확인 필요 | 두 후보 모두 동일 backing을 공유하도록 설계됐다. 실제 data path의 복사 유무를 계측한다. |
| Host 기밀성 | QA-03 / M-03b: Host CPU·DMA 접근 성공 0회 | 확인 필요 | 확인 필요 | 동일한 보호 control plane을 사용하므로 할당 정책 자체에는 가점을 주지 않는다. 생성·정상 사용·회수 전 구간의 실제 권한을 확인한다. |
| 접근권 강제 | QA-04 / M-04b: 비인가 pVM·mode·generation 접근 성공 0건 | 확인 필요 | 확인 필요 | A도 AI가 읽는 동안 Camera의 쓰기 권한을 실제 회수하는 단계가 명시되지 않았다. B는 지속 mapping과 회차별 권한 제한을 어떻게 양립시키는지 추가 설명이 필요하다. |
| 상태 정확성 | QA-05 / M-05b: 잘못된 전이·중복 반환·stale generation 수용 0건 | 확인 필요 | 확인 필요 | A의 부분 등록 rollback과 B의 slot ABA·queue 정합성을 각각 검증한다. Session reference와 content 사용 lease를 구분한다. |
| 안전한 장애 회수 | QA-06·07 / M-06b·M-07a: DMA 안전 조건 유지, 회수율 100% | 확인 필요 | 확인 필요 | 두 후보 모두 DMA 정지와 generation 회수를 요구한다. 회수 제한시간·허용 중단시간은 TBD이며, 강제종료·timeout 시험이 필요하다. |
| 메모리 상한 | QA-02·06 / 공통 bounded 운용 조건: 할당 byte가 승인 상한 이하 | 확인 필요 | 확인 필요 | B는 N개 slot으로 표현한다. A도 frame 수와 byte 상한을 함께 강제하면 bounded다. 실제 예산은 TBD다. |
| 신규 pVM 쌍 통합 | QA-08 / M-08a: Framework core 변경 0 LoC | 확인 필요 | 확인 필요 | 공통 registry·adapter 구조가 같으므로 버퍼 운용 정책만으로 충족을 단정하지 않는다. Core와 adapter 경계를 고정한 뒤 확인한다. |
| 플랫폼 실현 가능성 | 보호 backing 공유, DMA 집행, crash 후 권한 회수 | 확인 필요 | 확인 필요 | 두 pVM 및 장치가 사용하는 실제 Stage-2·DMA 보호 기능을 확인한다. 별점에는 포함하지 않는다. |

필수 조건이 실제로 실패한 후보는 채택 대상에서 제외하며 그 후보의 잠정 별점도 선택
근거로 사용하지 않는다. 보안 실패를 성능 별점으로 상쇄할 수 없다.

### 8.3 별점 비교와 구조적 원인

각 행은 하나의 시나리오·지표를 평가한다. QA-03·04·05는 8.2절에서 평가했으며,
pass/fail 결과를 임의로 1~3점으로 바꾸지 않는다. 아래 수치의 근거 수준은 모두 구조적
추론이고, 실제 값은 8.5절의 공통 방법으로 측정한다.

| 품질속성 / 평가 지표·시나리오 | 후보 A | 후보 B | 구조적 원인 → 품질 영향 / 평가 조건 |
|---|---|---|---|
| QA-01 전달 지연 p99 — 정상 지속 처리, M-01b | 잠정 ★☆☆ | 잠정 ★★★ | A-11은 Camera 완료 뒤 AI proxy·attachment를 준비한다. B-12는 이를 session 시작으로 옮기므로 전달 구간의 준비·실패 경로를 줄인다. 회차별 접근권 강제 비용은 두 후보에 포함한다. |
| QA-01 최초 frame 준비 시간 — 짧은 session | 잠정 ★★★ | 잠정 ★☆☆ | A는 HW 시작에 필요한 최소 F개를 준비하면 시작할 수 있다. B는 5.6절대로 N개 전체를 등록·import한 뒤 시작하므로 F < N일 때 초기 비용이 크다. F = N이면 이 우열을 적용하지 않는다. |
| QA-02 평균 payload backing 점유 — session 유지 중 희소 입력, M-02a | 잠정 ★★★ | 잠정 ★☆☆ | A는 완료된 frame backing을 반환한다. B는 FREE slot도 계속 점유한다. 항상 N개가 사용 중이면 차이가 줄며, A의 allocator가 예약한 메모리가 시스템에 즉시 반환된다는 뜻은 아니다. |
| QA-02 frame당 버퍼 관리 CPU 시간 — 정상 지속 처리 | 잠정 ★☆☆ | 잠정 ★★★ | A-02·06·07·11·05의 할당·등록·매핑·import·해제가 반복된다. B는 이를 초기 N개 준비에 분산한다. Fence, queue, 권한·cache 처리와 필요한 zeroize 비용은 B에도 남는다. |
| QA-06 기한 준수율 — 정상 운용 중 backing allocator 압박, M-06b | 잠정 ★☆☆ | 잠정 ★★★ | A는 새 frame마다 backing 확보 성공이 필요하다. B는 pool 준비가 끝난 뒤 이미 확보한 backing을 사용한다. B도 fence·제어 객체의 추가 할당, lazy map이나 backing 이동이 남으면 이점이 줄어든다. |
| QA-06 최장 중단시간 — AI 지연·timeout·endpoint 장애, M-06b | 잠정 ★★☆ | 잠정 ★★☆ | A는 outstanding 상한, B는 FREE slot 소진에서 멈춘다. A의 격리 buffer도 예산을 소비한다. 공통 AI reset이나 endpoint 장애는 양쪽의 여러 frame에 영향을 줄 수 있어 A의 frame별 identity만으로 가점을 주지 않는다. |
| QA-07 안전한 회수 완료 시간 — endpoint 장애, M-07a 보조 | 잠정 ★★☆ | 잠정 ★★☆ | A-09는 진행 단계가 다른 동적 객체와 orphan을 회수한다. B-11은 유한 slot table을 대조하기 쉽지만 pool generation 폐기와 지속 mapping 정리 범위가 커질 수 있다. 회수할 객체 수와 reset 범위 없이 우열을 정하지 않는다. |
| QA-08 규격 변경 후 재개 시간 — 기존 pool의 협의 범위를 벗어남 | 잠정 ★★★ | 잠정 ★☆☆ | A는 다음 allocation에 새 크기·배치를 적용할 수 있다. B는 기존 slot drain과 pool 재협상·재구성이 필요하다. 장치 자체의 재설정 시간은 양쪽에 공통으로 포함하고, 기존 slot 범위 안의 변경에는 이 우열을 적용하지 않는다. |
| QA-08 신규 대상 통합 리드타임 — 동일한 adapter 경계, M-08b | 잠정 ★★☆ | 잠정 ★★☆ | A에는 반복 생성·부분 실패 계약, B에는 pool·slot·회차 수명의 계약이 있다. 두 후보 모두 공통 control plane과 local adapter를 사용하므로 모듈 개수나 V4L2 유사성만으로 유지보수 우열을 정하지 않는다. |

같은 `잠정 ★★☆`는 성능 수치가 같다는 뜻이 아니다. **현재 결정축과 문서 근거만으로
일방적인 이점을 인정하기 어렵다**는 평가다. 신규 pVM 쌍 추가는 별도 adapter 시나리오로
확인하며, 현재 범위 밖인 N:M·fan-out 확장성을 별점 차이로 사용하지 않는다.

### 8.4 구조적으로 중요한 네 가지 판정

**첫째, B의 성능 이점은 준비 작업의 재사용에서 나온다.** Payload는 두 후보 모두
zero-copy이므로 B가 payload 복사를 더 적게 한다는 설명은 맞지 않는다. P개 frame을
처리하고 slot 수가 N인 session의 단순 작업량 모델은 다음과 같다.

```text
A의 버퍼 관리 작업량 ≈ P × (객체 준비 + 회차 처리 + 객체 정리)
B의 버퍼 관리 작업량 ≈ N × (객체 준비 + 객체 정리) + P × 회차 처리
```

이 모델은 호출·작업량의 분해이며 latency 산식이 아니다. 작업은 겹쳐 실행될 수 있고,
각 작업의 p99를 더해 종단 p99를 구할 수 없다. 특히 A의 Camera capture 이전 allocation은
M-01b 전달 구간 밖이므로 최초 준비·frame admission 지연과 따로 측정한다. 장기간 운용해
P가 N보다 훨씬 커질수록 B의 초기 준비 비용을 frame당 분산하기 쉽다.

**둘째, A의 메모리 이점은 유휴 상태에서 backing을 놓아주는 데 있다.** 고정 frame 크기를
S, 아직 반환할 수 없는 frame 수를 K(t)라고 하면 payload 점유는 대략 `A = K(t) × S`,
`B = N × S`다. K에는 준비·DMA·원격 사용·격리·회수 대기 상태를 모두 포함한다. 실제
계산은 정렬과 plane 크기, metadata, allocator 예약량, pin된 page·IOVA를 별도 집계한다.
A도 K의 상한이 있으므로 AI 정체를 추가 allocation으로 무한히 흡수하지 못한다.

**셋째, 저장 수명과 권한 유효 기간은 별도 결정이다.** 상위
[pVM 간 전달 위협](../품질위협_문제1_pVM간_데이터전달.md)의 10절은 승인된 세대와
처리 기간에 필요한 접근 모드만 허용하도록 요구한다. A의 매 frame unmap도 AI 읽기 중
Camera 쓰기를 자동 차단하지 않는다. B의 pool/slot/content token 검증도 이미 존재하는
CPU·DMA mapping을 통한 접근까지 막지는 못한다.

B가 N개 slot을 양쪽에 session 내내 유효한 접근권으로 열어 둔다면 필요한 회차만
허용한다는 요구와 충돌한다. 승인된 상태에 따라 실제 접근권을 차단·복원하는 집행 수단을
제시해야 하며, 이 과정에 page-table·DMA 권한 갱신 비용이 발생하면 성능 모델에 포함한다.
이는 pool allocation을 재사용할 수 없다는 뜻은 아니지만 **모든 mapping·권한 비용을
session 시작과 종료로만 옮겼다는 주장은 그대로 유지할 수 없다.**

Fence는 작업 완료를, cache sync는 데이터 가시성을 다루며 접근권 집행을 대신하지 않는다.
또한 DMA-BUF의 attach만으로 backing이 영구 고정되는 것은 아니므로 B의 persistent
mapping 조건도 대상 exporter/importer에서 확인해야 한다. [Linux DMA-BUF의 수명·mapping·동기화 계약](https://docs.kernel.org/driver-api/dma-buf.html)

**넷째, 개별 객체 격리와 장치 장애 격리는 다르다.** A는 잘못된 frame을 별도 객체로
정리하기 쉽고 B도 해당 slot을 격리할 수 있다. 그러나 공통 AI HW를 reset해야 하면
두 후보 모두 관련 in-flight 작업이 중단될 수 있다. B의 N개 등록부는 회수 대상을 열거하기
쉽지만 실제 DMA 종료 증거를 대신하지 못한다. A의 allocator도 회수되지 않은 page를
새 작업에 넘겨서는 안 된다. 장치 정지·완료 확인이 먼저라는 원칙은 V4L2 streaming
종료에도 적용된다. [videobuf2 stop_streaming 계약](https://docs.kernel.org/driver-api/media/v4l2-videobuf2.html)

### 8.5 측정값과 별점 확정에 필요한 검증

모든 행의 실측값·확정 별점 구간은 **TBD**다. 다음 방법을 양쪽에 동일하게 적용하며,
정상 상태·시작·규격 변경·장애의 결과를 한 평균으로 합치지 않는다.

| 평가 지표 | 계산·단위 / 유리한 방향 | 동일 시험과 별점 재검토 조건 |
|---|---|---|
| 전달 지연 M-01b | `t(AI 접근 가능) - t(Camera write fence 완료)`의 p99·최댓값, ms / 작을수록 유리 | 접근 가능은 token 수신뿐 아니라 local proxy·필요 권한이 준비된 시점이다. B에 회차별 권한 갱신을 포함한 뒤 재측정한다. |
| 최초 frame 준비 시간 | `t(최초 capture 제출 가능) - t(session 시작 요청)`의 p99, ms / 작을수록 유리 | HW 최소 준비 수 F, N, 초기 가용 memory를 고정한다. F=N이거나 A가 같은 수를 사전 준비하면 A의 높은 별점을 재검토한다. |
| 평균·최대 memory M-02a | payload 할당 byte의 시간가중 평균·최댓값, MB / 작을수록 유리 | 같은 입력과 유휴 비율을 사용한다. 별도로 allocator 예약량·pin된 byte·IOVA 점유를 기록해 실제 시스템 회수와 구분한다. |
| frame당 버퍼 관리 CPU 시간 | registry·allocator·mapping·proxy·queue·fence 처리 CPU 시간 합 / 완료 frame 수, μs/frame / 작을수록 유리 | 준비·종료 비용을 포함한 session 평균과 반복 구간을 나눈다. Protected control plane의 처리 시간도 포함한다. |
| 기한 준수·중단 M-06b | `D_frame 내 완료 수 / 입력 frame 수`, % / 클수록 유리; 최장 중단시간, ms / 작을수록 유리 | 메모리 압박과 AI timeout을 별도로 주입한다. 입력 throttle·capture 전 drop·격리 slot 수를 함께 기록한다. D_frame과 장애 지속시간 상한은 TBD다. |
| 안전한 회수 완료 시간 | `t(실제 회수 완료) - t(오류 확정)`, ms / 작을수록 유리 | 양쪽 모두 다음 frame에 안전하게 재사용·재할당 가능한 상태를 회수로 본다. A의 backing free, B의 slot FREE 또는 pool 삭제 후 backing free를 이에 대응시킨다. 단순 token 삭제는 성공이 아니다. 회수 후 재설정·첫 정상 frame까지의 서비스 재개 시간은 별도로 기록한다. |
| 규격 변경 후 재개 | 변경 요청부터 새 규격 첫 정상 frame 완료까지, ms / 작을수록 유리 | 같은 규격 전환과 HW 재설정 조건을 적용한다. 기존 pool 안에서 수용되는 변경과 pool 교체가 필요한 변경을 나눈다. |
| 신규 대상 통합 M-08a·b | core 추가·삭제 LoC, 통합시험까지 인일 / 작을수록 유리 | 같은 신규 대상, core/adapter 범위와 완료 조건을 적용한다. Core 0 LoC는 gate이고 인일의 별점 구간은 TBD다. |

보안·정확성 확인에는 Host·비인가 pVM의 CPU/DMA 접근, 잘못된 mode/generation,
순서 역전·중복 반환·이전 content의 지연된 release와 pVM 재시작을 주입한다. 양쪽의
같은 불변조건을 검사하고, 신뢰 경계 밖의 로그만으로 통과를 판정하지 않는다.

### 8.6 평가 결과와 조건부 권고

- **현재 고정 format 지속 streaming에서는 B를 우선 검증한다.** 반복 준비 비용과 실행 중 backing 확보 실패를 줄이는 구조적 근거가 있다. 회차별 접근권 집행과 그 비용을 먼저 명확히 해야 한다.
- **희소 입력·짧은 session·기존 pool 범위를 벗어나는 규격 변화에서는 A를 우선 검증한다.** 유휴 backing과 pool 일괄 준비·교체 부담을 줄일 수 있다. Per-frame 준비 비용과 공통 HW 재설정은 남는다.
- **Endpoint crash 복구, 기밀성, 접근권 강제에는 A/B의 이름만으로 우열을 주지 않는다.** 실제 권한 회수·DMA 정지 범위와 회수 계약이 선택 가능성을 결정한다.

평가 상태는 `평가 중`을 유지한다. 현재 결과는 다음 검증의 우선순위를 정하는 근거이며,
필수 조건 통과나 최종 구조 채택을 의미하지 않는다.

## 9. 1차 권고와 검증 가설

1080p 30fps처럼 format과 producer/consumer가 안정적인 지속 streaming workload라면
후보 B인 `REQBUFS-Style Shared Buffer Pool`을 우선 평가한다.

아직 성능 실측이 없으므로 채택 결론이 아니라 다음 검증 가설로 둔다.

> 사전 import와 backing·DMA 주소 연결 재사용으로 반복 준비 비용을 줄이면 지속 처리에
> 유리하다. 회차별 접근권 강제 비용을 포함해 30fps·frame loss 0%를 검증해야 한다.

후보 A는 다음 조건에서 우선 평가한다.

- frame 발생이 희소하거나 session이 짧아 pool 전체 준비 비용을 분산하기 어렵다.
- frame 크기, format 또는 modifier가 기존 pool의 협의 범위를 벗어나 자주 바뀐다.
- 고정 pool의 유휴 메모리 비용이 허용되지 않는다.
- 오류가 장치 reset 없이 frame 단위로 정리될 수 있고, 동적 객체별 회수가 운용 요구에 맞는다.
- 측정 결과 per-frame allocation/import/mapping 비용이 허용 범위 안이다.

consumer 수가 동적이라는 사실만으로 후보 A를 선택하지 않는다. 후보 B도 session
재등록이나 pool 재구성으로 consumer 변경을 지원할 수 있다.

## 10. 후속 상세 설계 항목

1. 두 후보의 생성, 공유, release, 삭제 sequence diagram
2. 후보 A의 frame 상태 머신과 후보 B의 pool/slot 상태 머신
3. protected token과 fence translation protocol
4. Camera/AI/broker crash injection별 회수 규칙
5. pool slot 수와 outstanding frame 상한 산정
6. 1080p 30fps latency, jitter, memory와 frame loss 측정
7. Stage-2와 SMMU/IOMMU 보호 기능의 platform 실현 가능성 검증
8. Session reference와 content 사용 lease, allocation 수명과 접근권 유효 기간의 분리
9. 8.5절의 공통 측정과 필수 조건 확인 후 잠정 별점 재평가
