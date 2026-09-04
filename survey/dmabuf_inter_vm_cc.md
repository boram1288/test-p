# DMA-BUF 프로세스·VM 간 공유 C&C View

## 1. 범위와 결론

- 대상은 Red Bend/HARMAN 계열 Type-1 또는 XGEN 계열 하이퍼바이저의 일반 Linux VM 두 개다. pVM은 전제하지 않는다.
  - `Type-1 hypervisor`: Host OS를 거치지 않고 HW 바로 위에서 여러 VM을 실행하는 하이퍼바이저다.
- VM A의 Process A가 만든 DMA-BUF를 Process B가 받은 뒤, VM B의 장치가 같은 DRAM backing page에 DMA 접근하는 zero-copy 경로를 다룬다.
  - `DMA-BUF`: Linux에서 여러 프로세스와 장치가 같은 버퍼를 공유하도록 만든 커널 기능이다.
  - **용어 설명:** DRAM backing page는 쉽게 말해 DMA-BUF의 실제 데이터가 저장되어 있는 DRAM 메모리 영역이다.
  - `zero-copy`: frame payload를 새 버퍼로 복사하지 않고 같은 메모리 영역을 공유하는 방식이다.
- 그림의 HW 경로는 ARM virtualization과 양 VM이 접근 가능한 동일 SoC DRAM을 가정한다.
  - `ARM virtualization`: ARM CPU가 VM별 주소 변환과 실행 격리를 제공하는 기능이다.
  - `SoC`: CPU, DMA 장치와 메모리 연결부 등을 하나의 칩에 통합한 시스템이다.
- 같은 VM에서는 `SCM_RIGHTS`가 같은 커널의 open-file 참조를 복제한다.
  - `SCM_RIGHTS`: Unix domain socket으로 같은 커널의 열린 파일 참조를 다른 프로세스에 전달하는 기능이다.
- 다른 VM에는 FD, `struct dma_buf`, `dma_resv`, `dma_fence` 포인터가 전달되지 않는다. VM 경계에서는 page grant와 opaque buffer ID를 전달하고, VM B가 별도의 local DMA-BUF를 만든다.
  - `FD`: 프로세스가 열린 커널 객체를 가리킬 때 사용하는 정수 번호다.
  - `page grant`: 한 VM의 메모리 페이지를 다른 VM이 정해진 권한으로 접근하도록 허용하는 하이퍼바이저 기능이다.
  - `opaque buffer ID`: 내부 주소를 노출하지 않고 VM Share Service만 해석하는 버퍼 식별자다.
  - `struct dma_buf`: 실제 버퍼 메모리와 공유 동작을 관리하는 커널 객체다.
  - `dma_resv`: 한 DMA-BUF의 fence들을 모아 접근 순서를 관리하는 커널 객체다.
  - `dma_fence`: GPU/NPU 같은 비동기 작업의 완료를 알리는 커널 객체다.

## 2. C&C 구성요소

### 2.1 HW 컴포넌트 — 7개

이 C&C에서 HW는 아래 7개의 논리 컴포넌트로만 표현한다. 하나의 S1/S2 박스 안에서도 각 VM과 장치는 서로 다른 변환표를 사용한다.

1. **CPU S1-MMU (VA → IPA)** — 제어: Guest OS kernel
   - **용어 설명:** 프로세스가 쓰는 VA(가상 주소)를 VM이 물리 주소처럼 보는 IPA로 바꾸는 CPU 변환 단계다.
2. **CPU S2-MMU (IPA → PA)** — 제어: Hypervisor
   - **용어 설명:** VM의 IPA를 실제 DRAM의 PA(물리 주소)로 바꾸고 VM 간 CPU 접근을 분리하는 단계다.
3. **DMA S1-MMU (IOVA → IPA)** — 런타임 제어: 장치를 소유한 Guest OS kernel
   - **용어 설명:** DMA 장치가 쓰는 IOVA(장치 가상 주소)를 해당 VM의 IPA로 바꾸는 장치 변환 단계다.
4. **DMA S2-MMU (IPA → PA)** — 제어: Hypervisor/BSP
   - **용어 설명:** DMA 요청의 IPA를 실제 DRAM의 PA로 바꾸고 다른 VM 메모리 접근을 차단하는 단계다.
   - `BSP`: 대상 SoC에 맞춰 Hypervisor와 HW를 연결하는 플랫폼 지원 SW다.
   - **구현 경계:** 이 이름은 논리 역할이며 실제 SoC의 HW 이름은 다를 수 있다.
5. **Producer DMA HW** — 제어: Producer Driver
   - **용어 설명:** Camera/ISP/GPU처럼 frame을 DRAM pages에 쓰는 장치다.
6. **Consumer DMA HW** — 제어: Consumer Driver
   - **용어 설명:** NPU/GPU/Display처럼 공유 frame을 읽고 처리하는 장치다.
7. **DRAM pages**
   - **용어 설명:** DMA-BUF의 실제 frame 데이터가 저장되는 물리 메모리 조각이다.

주소 변환 경로는 다음 두 개로 분리한다.

- CPU 경로: App → CPU S1-MMU → CPU S2-MMU → DRAM pages
- DMA 경로: Producer/Consumer DMA HW → DMA S1-MMU → DMA S2-MMU → DRAM pages

그림의 초록색 화살표는 DMA transaction의 read/write 요청 방향이다. read 데이터와 write 완료 응답은 같은 connector를 반대 방향으로 돌아온다. Producer와 Consumer는 서로 다른 변환표와 서로 다른 시점에 이 경로를 사용한다. 알림 전달과 cache coherency를 구현하는 보조 HW는 이 7개 박스의 범위 밖이다.

- `DMA transaction`: DMA HW와 DRAM 사이에서 오가는 메모리 read/write 요청과 응답이다.
- `cache coherency`: CPU와 DMA HW가 같은 메모리의 최신 데이터를 보도록 유지하는 성질이다.

### 2.2 런타임 SW 컴포넌트

| 컴포넌트 | 위치 | 책임 |
|---|---|---|
| Producer App | VM A / Process A | 버퍼 할당, producer 장치에 FD queue |
| Share Service | VM A / Process B | `SCM_RIGHTS`로 FD 수신, 공유 요청과 메타데이터 관리 |
| Buffer Allocator/Exporter | VM A kernel | DMA Heap 또는 장치 allocator로 backing page와 local DMA-BUF 생성 |
| DMA-BUF Core A | VM A kernel | local `dma_buf`, attachment, reservation과 fence 수명 관리 |
| Producer Driver | VM A kernel | local DMA-BUF importer, DMA S1-MMU map과 Producer DMA HW submit |
| VM-Share FE A | VM A kernel | local DMA-BUF importer, page pin/register, buffer ID 생성 |
| Inter-VM Bridge | VM 경계 | ID, `READY`, `DONE`, 오류와 수명 메시지 전달 |
| Memory Grant/Mapper | Hypervisor | 같은 backing page의 CPU S2-MMU/DMA S2-MMU 권한 설정과 회수 |
| DMA Permission Manager | Hypervisor/BSP | Consumer DMA HW의 DMA S2-MMU 접근 허용과 차단 |
| Notification Router | Hypervisor/BSP | VM 간 상태 변경 알림 전달 |
| VM-Share FE B / Proxy Exporter | VM B kernel | grant를 받아 VM B의 새 local DMA-BUF 생성 |
| DMA-BUF Core B | VM B kernel | VM B의 attachment, reservation과 local fence 관리 |
| Consumer Driver | VM B kernel | proxy DMA-BUF importer, DMA S1-MMU map과 Consumer DMA HW submit |
| Consumer App | VM B user | local FD로 처리 job 요청 |

`VM-Share FE A`는 DMA-BUF **importer**이고, `VM-Share FE B`는 grant의 수신자이면서 VM B local DMA-BUF의 **exporter**다. Consumer Driver는 그 proxy DMA-BUF의 **importer**다.

DMA Heap을 쓰는 그림에서는 Buffer Allocator가 exporter이고 Producer Driver가 importer다. 장치 드라이버가 직접 버퍼를 할당하는 제품에서는 exporter 역할만 그 드라이버로 이동한다.

### 2.3 설정 시점 SW 컴포넌트

다음 모듈은 필요하지만 frame별 fast path에는 넣지 않았다.

| 컴포넌트 | 책임 |
|---|---|
| Hypervisor Configuration | VM memory, CPU S2-MMU/DMA S2-MMU, shared channel과 peer 관계 정의 |
| Device Assignment/BSP | 각 DMA HW 요청을 해당 VM의 DMA S1-MMU/DMA S2-MMU 변환표와 연결 |
| Grant Policy/ACL | source/target VM identity와 R/W/DMA 권한 제한 |
| Lifecycle/Diagnostics | VM reset 시 회수, fault, timeout과 stale ID 추적 |

### 2.4 C&C 다이어그램

[PlantUML C&C 원본](./dmabuf_inter_vm_cc.puml)은 제품 API 이름을 추정하지 않고 두 개의 단순한 view로 나눈다.

#### 제어·핸들 경로

![DMA-BUF 프로세스·VM 간 공유 C&C](./images/dmabuf_inter_vm_cc.svg)

#### HW 주소 경로 — 7개 컴포넌트

![DMA-BUF HW 주소 경로 C&C](./images/dmabuf_inter_vm_hw.svg)

### 2.5 Connector와 전달 데이터

| Connector | 전달 내용 |
|---|---|
| DMA Heap/subsystem ioctl | allocation 요청과 local DMA-BUF FD |
| Unix socket + `SCM_RIGHTS` | 같은 VM 커널의 open-file 참조 |
| Driver ioctl | local FD와 device job |
| `dma_buf_attach()` + `dma_buf_map_attachment()` | local attachment와 DMA S1-MMU mapping |
| VM-share ioctl | local FD, frame metadata, 접근 권한 |
| Hypercall/vendor grant API | CPU S2-MMU map/revoke와 DMA S2-MMU allow/revoke |
| Inter-VM channel | buffer ID, generation, `READY`/`DONE`/`ERROR` |
| Shared page mapping | frame payload가 있는 동일 DRAM pages |
| Doorbell/cross-interrupt/vIRQ | 상태 변경 알림 |
| CPU memory access | VA → CPU S1-MMU → IPA → CPU S2-MMU → PA |
| DMA transaction | IOVA → DMA S1-MMU → IPA → DMA S2-MMU → PA |

FD, `struct dma_buf`, SG table, IOVA/GPA/HPA, grant handle, fence는 컴포넌트가 아니라 local object 또는 전달 데이터다.

## 3. 동작 순서

1. Process A가 DMA-BUF를 할당하고 Producer Driver에 queue한다.
2. Process A가 Unix socket의 `SCM_RIGHTS`로 Process B에 같은 file object의 참조를 전달한다.
3. FE A가 backing page를 pin/register하고 Hypervisor에 VM B의 page grant와 CPU/DMA 권한을 요청한다.
4. Hypervisor가 CPU S2-MMU mapping과 DMA S2-MMU permission을 완료한다.
5. Producer DMA HW 완료와 4단계 완료를 모두 확인한 뒤 FE A가 `buffer ID + metadata + READY(sequence)`를 보낸다.
6. FE B가 grant된 page를 감싼 새 local DMA-BUF를 만들고, Consumer Driver가 DMA S1-MMU를 map하여 DMA를 실행한다.
7. Consumer DMA HW와 local 사용이 끝나면 FE B가 `DONE(sequence)`를 보낸다. 이후에만 mapping을 revoke하고 VM A가 버퍼를 재사용한다.

이 순서는 같은 physical page를 양 VM에 map할 수 있을 때만 zero-copy다. Hypervisor가 동적 grant를 지원하지 않으면 미리 공유한 pool을 allocator로 쓰거나 staging copy 경로가 필요하다.

## 4. 동기화와 수명 계약

- Source의 `dma_fence *` 또는 sync-file FD를 VM B로 보내지 않는다. FE A가 producer 완료를 기다린 뒤 `READY(sequence)`를 보내고, FE B가 이를 local completion/fence로 바꾼다.
- 임의의 DMA-BUF가 항상 grant 가능한 것은 아니다. page pin과 revoke가 보장되는 heap/exporter 또는 처음부터 공유된 pool을 사용한다.
- VM channel에는 raw SG table, IOVA/GPA/HPA를 싣지 않는다. Hypervisor가 검증하는 opaque buffer ID만 노출한다.
- VM A는 같은 buffer generation의 `DONE(sequence)` 전에 overwrite, free 또는 revoke하지 않는다.
- revoke 순서는 새 job 차단 → Consumer DMA HW 정지 → local detach와 DMA S1-MMU unmap → DMA S2-MMU/CPU S2-MMU revoke → source unpin이다.
- `DMA_BUF_IOCTL_SYNC`는 CPU `mmap()` 접근의 cache coherency 구간 표시다. device-device 배타 동기화를 대신하지 않는다.
- metadata에는 최소한 size, plane offset, stride, format/modifier, R/W 권한, buffer generation과 sequence가 필요하다.
- VM reset, timeout, 중복 ID, stale generation과 부분 실패를 정리하는 recovery 책임은 양 FE와 Bridge에 있어야 한다.

## 5. 제품별 매핑

제품 자료의 다음 명칭은 별도 C&C 박스가 아니라 앞서 정의한 DMA S1-MMU 또는 DMA S2-MMU의 실제 구현 후보다.

- `SMMU`: DMA 장치의 주소를 변환하고 접근 권한을 검사하는 ARM의 System MMU다.
- `S2MPU`: 일부 SoC에서 DMA의 물리 메모리 접근 권한을 검사하는 보호 HW다.

따라서 DMA S2-MMU는 제품에 따라 nested SMMU의 stage 2, S2MPU 또는 동등한 보호 HW로 구현될 수 있다.

| 일반 C&C 요소 | Red Bend/HARMAN에서 확인된 대응 | XGEN |
|---|---|---|
| Type-1 hypervisor | HARMAN 공개 페이지에서 확인 | 제품 문서 확인 필요 |
| CPU S1-MMU | Guest Linux/ARM의 표준 변환 단계 | Guest 제어 방식 확인 필요 |
| CPU S2-MMU | HARMAN 공개 페이지의 second-stage MMU | API/구성 확인 필요 |
| DMA S1-MMU | HARMAN 공개 페이지에서 SMMU 사용은 확인되나 단계별 API는 미확인 | Guest map 방식 확인 필요 |
| DMA S2-MMU | SMMU 기반 격리와 DMA memory grant는 확인되나 실제 HW 구성은 미확인 | 격리 HW와 권한 API 확인 필요 |
| Producer/Consumer DMA HW | 플랫폼별 pass-through 또는 공유 장치 | 장치 배정 방식 확인 필요 |
| DRAM pages | 2021 매뉴얼 공개 사본의 page-aligned R/W/DMA memory grant | grant/map/revoke 확인 필요 |
| Inter-VM Bridge | 공개 페이지의 bridge component | peer channel 확인 필요 |
| Inter-VM resource link | 2021 매뉴얼 공개 사본의 vLink | 이름과 ABI 확인 필요 |
| Event | 같은 사본의 XIRQ/cross-interrupt | doorbell/vIRQ 확인 필요 |
| Shared control memory | 같은 사본의 PMEM; PDEV는 hypervisor 전용 metadata | shared-memory 영역 확인 필요 |

현재 HARMAN 공개 페이지는 CPU S2-MMU에 해당하는 second-stage MMU, DMA S1/S2-MMU의 구현 후보인 SMMU와 bridge 기반 inter-VM channel을 확인해 준다. 다만 이 페이지는 SMMU 내부의 S1/S2 분리나 Linux DMA-BUF 전용 bridge, proxy exporter의 존재까지 보장하지 않는다. vLink/XIRQ/PMEM/PDEV와 동적 memory grant 명칭은 제3자 사이트에 공개된 2021 HARMAN 매뉴얼 사본에서 확인했으므로, 현재 납품 버전의 API/ABI와 대조해야 한다.

2026-09-04 기준 `XGEN hypervisor`라는 정확한 제품명에 해당하는 공개 기술 사양은 찾지 못했다. Xen으로 간주하지 않았으며, 다음 계약을 공급사 문서로 확인해야 한다.

- 고정 shared pool 또는 동적 page grant 지원 여부와 scatter-gather 제약
- peer-to-peer channel인지 service VM/backend 경유인지
- grant의 R/W 및 DMA 권한, revoke 완료 보장
- notification primitive와 ordering 보장
- guest frontend/backend 또는 proxy DMA-BUF driver 제공 여부
- fence/ownership 전달 규약과 VM crash 시 회수 절차

## 6. `survey/dmabuf.md` 적용 시 보정점

[기존 조사](./dmabuf.md)는 allocation, 동일 커널의 FD 공유, VM 경계에 별도 중재가 필요하다는 출발점으로 사용했다. 공식 Linux 문서와 hypervisor 자료를 대조하면 다음처럼 보정해야 한다.

- `dma_buf_attach()`는 attachment를 만든다. device address mapping은 `dma_buf_map_attachment()`와 exporter의 `map_dma_buf()` 경로에서 수행된다.
- `DMA_BUF_IOCTL_SYNC`는 CPU 접근 cache coherency만 제공하며 다른 process/device의 동시 접근을 막지 않는다.
- vsock/serial은 bytes나 opaque handle을 운반할 수 있지만 다른 kernel에 file object를 복제하지 않는다.
- VirtIO 1.4에서 임의 Linux DMA-BUF를 VM 간 전달하는 범용 표준 protocol은 확인되지 않았다. `virtio-vdmabuf`를 존재가 보장된 표준 모듈로 모델링하지 않는다.
- S2MPU와 특정 SMC/eventfd 호출은 제품별 구현이다. 일반 C&C에는 CPU S1/S2-MMU, DMA S1/S2-MMU, vendor grant와 event 계약을 둔다.

## 7. 근거

### 로컬 조사

- [`survey/dmabuf.md`](./dmabuf.md): DMA-BUF allocation, attach/map, 동일 커널 공유와 VM 경계 쟁점. 위 6절의 보정을 적용했다.
- `survey/` 전체에서 Red Bend, vLink, XIRQ 또는 XGEN의 직접 기술 자료는 발견되지 않았다. pVM 전용 설계는 이번 C&C의 구성 근거로 사용하지 않았다.

### 웹 자료

- [Linux DMA-BUF 공식 문서](https://docs.kernel.org/driver-api/dma-buf.html): exporter/importer, FD, attachment/map, fence와 CPU sync semantics.
- [Linux DMA Heap 공식 문서](https://docs.kernel.org/userspace-api/dma-buf-heaps.html): userspace allocation API.
- [Linux unix(7)](https://man7.org/linux/man-pages/man7/unix.7.html): `SCM_RIGHTS`가 open-file 참조를 전달하는 semantics.
- [Arm Memory Management](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/LearnTheArchitecture-MemoryManagement-101811_0100_00_en.pdf): CPU S1의 VA→IPA와 S2의 IPA→PA 변환.
- [Arm SMMU Architecture Specification](https://documentation-service.arm.com/static/66c5c097882fec713ef4a8ff): DMA S1/S2 변환과 장치별 context.
- [HARMAN Device Virtualization](https://car.harman.com/solutions/device-virtualization): Type-1, Stage-2 MMU, SMMU, bridge 기반 inter-VM communication.
- [TI VirtualLogix VLX 교육자료](https://software-dl.ti.com/trainingTTO/trainingTTO_public_sw/dm643x1day/DM643x1day%20COLOR.pdf): 역사적 VLX의 shared memory와 cross-interrupt 구조.
- [2021 HARMAN/Red Bend 매뉴얼 공개 사본](https://www.scribd.com/document/752680019/Hypervisor-Overview-Application-Note-Hypervisor-Description-ALL-REV-0-00): memory grant, vLink, XIRQ, PMEM/PDEV. 현재 공식 배포본이 아닌 제3자 호스팅 사본이다.
- [OASIS VirtIO 1.4](https://docs.oasis-open.org/virtio/virtio/v1.4/virtio-v1.4.pdf): 표준 장치·object 정의를 확인하는 데 사용했다.

## 8. 확인 경계

이 문서는 구현의 논리적 C&C와 필수 계약을 식별한 것이다. 실제 설계 확정에는 Red Bend/HARMAN 또는 XGEN BSP에서 다음 이름과 동작을 확인해야 한다: CPU/DMA S1·S2의 실제 HW 매핑, grant/map/revoke API, DMA permission API, event primitive, page/SG 제한, cache policy, proxy exporter 제공 여부, VM reset cleanup.
