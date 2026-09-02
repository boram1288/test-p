# 문제 1. DMA-BUF 기반 pVM 간 프레임 전달 필수 모듈

## 1. 목적과 범위

이 문서는 Camera pVM이 생성한 프레임을 AI pVM에 전달하는 경로에 직접 필요한
모듈만 정의한다. pVM 생성, Workload 검증, 전체 pipeline orchestration과
Camera/AI HW IP의 사용 주체 중재는 다루지 않는다.

두 후보는 Linux DMA-BUF의 export/import, reference count, fence와 cache 동기화
방식을 pVM 경계에 맞게 응용한다. 프레임 payload를 다른 물리 페이지로 복사하지
않으며 Host는 보호 프레임 페이지를 매핑할 수 없어야 한다.

## 2. 전달 모델

Camera pVM과 AI pVM의 페이지 테이블에는 동일한 물리 프레임 페이지를 가리키는
매핑을 생성한다. 복제되는 것은 페이지 데이터가 아니라 페이지 테이블 엔트리다.

```text
Camera pVM Page Table ─┐
                       ├─> 동일한 보호 물리 Frame Page
AI pVM Page Table ─────┘
```

이 구조에서는 프레임 페이지를 Camera pVM에서 AI pVM으로 이전하지 않는다.
따라서 별도의 배타적 페이지 소유권은 정의하지 않고 다음 항목을 관리한다.

- 각 pVM 내부 DMA-BUF 객체의 reference count
- 두 pVM이 공유하는 backing page의 전체 수명
- pVM별 DMA-BUF attachment와 mapping
- Camera write와 AI read 사이의 fence
- buffer handle의 generation과 오류 정리

두 pVM의 매핑을 계속 유지하고 fence로 접근 순서만 동기화하므로, 프레임마다
Stage-2와 DMA 접근권을 회수·부여하는 버퍼 상태 머신은 사용하지 않는다.

## 3. DMA-BUF 적용 원칙

Camera pVM과 AI pVM은 서로 다른 Linux kernel instance이므로 Camera pVM의
DMA-BUF fd와 `struct dma_buf`를 AI pVM이 그대로 사용할 수 없다. 각 pVM은 로컬
DMA-BUF 객체를 가지며, 보호된 buffer handle을 통해 동일한 backing page에 연결한다.

```text
Camera의 DMA-BUF fd / struct dma_buf
                ↓ export
보호 buffer handle + metadata + fence
                ↓ bridge
AI의 proxy DMA-BUF fd / struct dma_buf
```

적용 범위는 다음과 같다.

- 전달 API는 Linux DMA-BUF API와 동작 모델을 응용한다.
- Camera pVM은 DMA-BUF exporter, AI pVM은 proxy importer로 동작한다.
- 각 pVM 내부 객체의 정상 수명은 DMA-BUF reference count로 관리한다.
- fence와 cache 동기화 순서는 DMA-BUF 규칙을 응용한다.
- pVM 경계를 넘을 수 없는 fd, `struct dma_buf`, `dma_resv`와 reference count는
  Cross-pVM DMA-BUF Bridge가 handle과 protocol로 연결한다.
- pVM 비정상 종료처럼 정상 `dma_buf_put()`이 실행되지 않는 경우에는 buffer
  generation을 폐기하고 해당 pVM의 원격 참조와 매핑을 강제로 정리한다.

## 4. 공통 필수 모듈

| 위치 | 모듈 | 핵심 책임 |
|---|---|---|
| Camera pVM | Camera Frame Producer | Camera HW에 프레임 생성을 요청하고 DMA 완료 fence를 발행한다. |
| Camera pVM | Camera DMA-BUF Exporter | backing page를 로컬 DMA-BUF로 만들고 export 가능한 보호 handle 등록을 요청한다. |
| 보호 경계 | Cross-pVM DMA-BUF Bridge | buffer handle, metadata, 원격 참조, fence와 generation을 pVM 사이에서 중계한다. |
| 보호 경계 | Shared Page Mapping Adapter | 동일한 보호 물리 페이지를 Camera/AI pVM에 연결하고 Host 매핑을 차단한다. |
| AI pVM | AI DMA-BUF Proxy Importer | 보호 handle을 검증해 AI kernel의 로컬 proxy DMA-BUF와 device attachment를 만든다. |
| AI pVM | AI Frame Consumer | 전달된 DMA-BUF를 AI HW 처리에 사용하고 완료 fence와 참조 해제를 수행한다. |

구조도에는 위 6개 모듈을 최소 단위로 표시한다.

```text
Camera Frame Producer
        ↓
Camera DMA-BUF Exporter
        ↓
Cross-pVM DMA-BUF Bridge
        ↓
Shared Page Mapping Adapter
        ↓
AI DMA-BUF Proxy Importer
        ↓
AI Frame Consumer
```

### 4.1 Cross-pVM DMA-BUF Bridge 내부 책임

다음 책임은 같은 buffer handle과 generation을 공유하고 함께 변경되므로 별도 상위
모듈로 나누지 않고 Cross-pVM DMA-BUF Bridge의 하위 컴포넌트로 둔다.

| 하위 컴포넌트 | 책임 |
|---|---|
| Buffer Handle Registry | backing page를 Host가 위조할 수 없는 handle과 generation에 연결한다. |
| Cross-pVM Reference Manager | Camera와 AI의 원격 참조를 종합해 backing page를 해제할 시점을 결정한다. |
| Fence Relay | Camera write 완료 fence와 AI read 완료 fence를 상대 pVM의 로컬 동기화 객체에 반영한다. |
| Generation/Error Cleanup | 오래된 handle을 거부하고 pVM 비정상 종료 시 원격 참조와 잔존 mapping을 정리한다. |

## 5. 후보별 모듈

### 5.1 후보 1: 동적 개별 DMA-BUF

후보 1은 프레임 수요가 발생할 때 개별 backing page와 DMA-BUF를 생성한다.

추가 모듈은 `Dynamic Frame Buffer Allocator`다.

```text
Camera Frame Producer
  -> Dynamic Frame Buffer Allocator
  -> Camera DMA-BUF Exporter
  -> Cross-pVM DMA-BUF Bridge
  -> Shared Page Mapping Adapter
  -> AI DMA-BUF Proxy Importer
  -> AI Frame Consumer
```

`Dynamic Frame Buffer Allocator`는 다음을 담당한다.

- 프레임 요구 크기에 맞는 backing page 동적 할당
- Camera DMA-BUF Exporter에 backing page 제공
- Camera와 AI의 참조가 모두 끝난 뒤 backing page 해제
- 할당 실패와 부분 생성 실패 시 자원 정리

### 5.2 후보 2: 사전 할당 DMA-BUF pool

후보 2는 정해진 수의 backing buffer를 미리 생성하고 pool slot으로 반복 사용한다.

추가 모듈은 `Preallocated DMA-BUF Pool Manager`다.

```text
Camera Frame Producer
  -> Preallocated DMA-BUF Pool Manager
  -> Camera DMA-BUF Exporter
  -> Cross-pVM DMA-BUF Bridge
  -> Shared Page Mapping Adapter
  -> AI DMA-BUF Proxy Importer
  -> AI Frame Consumer
```

`Preallocated DMA-BUF Pool Manager`는 다음을 담당한다.

- 고정된 수와 크기의 backing buffer 사전 할당
- 사용 가능한 pool slot 선택
- Camera write fence와 AI read fence 완료 확인 후 slot 재사용
- pool 고갈 시 대기, frame drop 또는 backpressure 결과 반환
- 종료 시 pool의 DMA-BUF와 backing page 일괄 해제

## 6. 후보 간 결정 차이

두 후보 모두 페이지 소유권을 이전하지 않고 동일 물리 페이지를 양쪽 pVM에 매핑한다.
따라서 결정 질문은 다음과 같다.

> 개별 DMA-BUF를 프레임 수요에 따라 동적으로 생성·매핑할 것인가,
> 사전 할당된 DMA-BUF pool의 slot을 반복해서 사용할 것인가?

| 비교 항목 | 후보 1: 동적 개별 DMA-BUF | 후보 2: 사전 할당 DMA-BUF pool |
|---|---|---|
| backing buffer 생성 | 프레임 수요 시 생성 | pipeline 시작 전에 생성 |
| mapping | buffer마다 동적 생성·해제 | pool 초기화 시 생성 후 재사용 |
| 정상 수명 | 원격 참조가 모두 끝나면 해제 | 원격 참조와 fence 완료 후 slot 반환 |
| 메모리 사용 | 실제 수요에 따라 변동 | 최대 pool 크기를 상시 예약 |
| 반복 경로 비용 | 할당·등록·mapping 비용 발생 | slot 선택과 fence 동기화 중심 |
| 자원 부족 | 동적 할당 실패 | pool slot 고갈 |

## 7. 기존 논리 모듈과의 관계

| 이 문서의 컴포넌트 | 기존 논리 모듈 |
|---|---|
| Camera DMA-BUF Exporter / AI DMA-BUF Proxy Importer | M-07 Secure Inter-domain Channel의 guest adapter |
| Cross-pVM DMA-BUF Bridge | M-07 Secure Inter-domain Channel의 pVM 간 bridge |
| Shared Page Mapping Adapter | M-09 DMA/S2MPU Isolation Controller의 memory mapping 부분 |
| Dynamic Allocator / Pool Manager | M-07 내부의 후보별 buffer allocation 전략 |

M-09는 프레임별 CPU/DMA 권한 전환을 담당하지 않는다. 이 문제에서는 공유 페이지의
초기 Stage-2 mapping, Host 비매핑 보장, 잘못된 handle의 mapping 차단과 종료 시
잔존 mapping 제거만 담당한다.

## 8. 제외 모듈과 책임

프레임 생성·전달 경로를 구체화하는 현재 범위에서는 다음 모듈을 제외한다.

- M-01 Framework API / Request Gateway
- M-02 pVM Lifecycle Manager
- M-03 Multi-pVM Orchestrator
- M-04 Fault/Recovery Manager
- M-05 Workload Loader / Verifier
- M-06 Protected Policy Authority
- M-08 HW IP Mediation Layer
- M-10 Secure OS Adapter
- M-11 Secure Persistent Storage
- M-12 Runtime Resource / QoS Authority
- 별도의 페이지 소유권 관리자
- 프레임별 접근권 전환 상태 머신

모듈을 제외한다는 것은 관련 시스템 기능을 제거한다는 의미가 아니다. 이 문서와 후보
구조 다이어그램의 비교 범위에서 제외하고, 상위 pipeline 또는 다른 Decision Point의
공통 전제로 둔다는 의미다.
