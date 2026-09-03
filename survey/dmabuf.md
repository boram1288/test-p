# V920 플랫폼에서 DMA-BUF 할당과 SysMMU/S2MPU 연동, 프로세스/VM 간 공유 메커니즘 분석

## 목차

1. 개요
2. IOMMU / SysMMU(S1) / S2MPU(S2)란 무엇인가
3. dmabuf는 어떻게 생성되는가
4. dmabuf는 각 device의 SysMMU(S1)에 언제, 어떻게 사용되는가
5. dmabuf는 S2MPU(S2)에 언제, 어떻게 사용되는가
6. dmabuf를 프로세스 간에 어떻게 전달하는가
7. dmabuf를 VM 간에 어떻게 전달하는가
8. 결론 및 제언
9. References

## 1. 개요

### Executive Summary

V920 플랫폼에서 dmabuf 는 애플리케이션이 `/dev/dma_heap/system` 등을 통해 할당받는 단순한 메모리 버퍼 객체로 시작한다. 이 시점에는 어떤 디바이스(master IP)가 이 버퍼를 사용할지 정해지지 않은 상태이며, 특정 디바이스와의 연결은 `dma_buf_attach()` 호출 시점에 비로소 이루어진다. 이 attach 시점에 디바이스의 `struct device` 내 `dev->iommu` 정보를 통해 해당 디바이스에 붙어 있는 **SysMMU(S1 IOMMU)** 가 결정되고, IOVA→IPA 변환을 위한 페이지 테이블이 설정된다. 이후 실제 물리 메모리 접근이 이루어지기 전, **S2MPU(S2 IOMMU)** 가 IPA→PA 변환과 함께 하이퍼바이저 레벨의 최종 접근 권한 검사를 수행한다. 프로세스 간에는 dmabuf fd 를 exporting 프로세스가 생성하고 importing 프로세스가 자신의 디바이스로 다시 attach 하는 방식으로 공유되며, VM 간에는 커널 인스턴스가 다른 관계로 Unix domain socket 만으로는 fd 를 전달할 수 없어 virtio 등 하이퍼바이저 매개 메커니즘이 필요하다. 본 보고서는 이 다섯 가지 질문 — 생성, SysMMU(S1) 사용, S2MPU(S2) 사용, 프로세스 간 전달, VM 간 전달 — 을 중심으로 V920 환경에서의 dmabuf 동작 원리를 분석한다.

### 보고서 구성

1. **IOMMU / SysMMU(S1) / S2MPU(S2)란 무엇인가** — 이후 모든 장에서 사용되는 핵심 개념 정의
2. **dmabuf는 어떻게 생성되는가** — 사용자 공간에서의 할당 API 와 방법
3. **dmabuf는 각 device의 SysMMU(S1)에 언제, 어떻게 사용되는가** — attach/map_attachment 시점의 동작
4. **dmabuf는 S2MPU(S2)에 언제, 어떻게 사용되는가** — 하이퍼바이저 레벨의 권한 검사 메커니즘
5. **dmabuf를 프로세스 간에 어떻게 전달하는가** — 동일 커널 인스턴스 내 fd export/import
6. **dmabuf를 VM 간에 어떻게 전달하는가** — 커널 인스턴스 경계를 넘는 공유
7. **결론 및 제언** — 분석 요약 및 추가 조사 권고사항

---

## 2. IOMMU / SysMMU(S1) / S2MPU(S2)란 무엇인가

세 용어는 서로 다른 계층에 속하는 개념이며, 혼용하면 이후 내용을 이해하기 어렵다.

- **IOMMU**: 리눅스 커널이 제공하는 범용 프레임워크의 이름이다. IOMMU 프레임워크 자체에는 S1/S2 라는 단계 구분이 존재하지 않는다.
- **SysMMU**: Samsung 이 IOMMU 프레임워크를 구현한 IP 로, 각 master IP(GPU, NPU, DPU 등) 뒷단에 개별적으로 붙어 있다. Samsung 아키텍처에서는 이 SysMMU 를 **S1 단계**로 사용한다.
- **S2MPU**: Samsung 이 하이퍼바이저 보안 요구사항을 위해 추가한 **S2 단계** IP 로, 메모리 컨트롤러 앞단에 중앙 배치된다.

즉 "S1 iommu = SysMMU", "S2 iommu = S2MPU" 로 이해해도 무방하지만, S1/S2 구분은 IOMMU 프레임워크 자체의 개념이 아니라 Samsung 이 자체적으로 2단계로 나누어 사용하는 구현 방식이라는 점에 유의해야 한다.

### 2.1 연결 지점: `struct device`

각 master IP 를 나타내는 `struct device` (이하 `dev`) 는 `dev->iommu` 필드를 통해 자신에게 연결된 SysMMU 정보를 보유한다. 이 필드에는 IOMMU 프레임워크가 제공하는 `iommu_domain`, `iommu_device` 가 들어 있으며, 이 정보를 바탕으로 페이지 테이블 map/unmap 이 수행된다. `dev->iommu` 가 비어 있으면 IOMMU 프레임워크는 해당 디바이스에 대해 SysMMU ops 를 호출하지 못한다. 즉 "디바이스가 SysMMU 를 사용하는가"는 이 필드가 채워져 있는지에 달려 있다.

### 2.2 S1(SysMMU)과 S2(S2MPU) 비교

| 구분 | S1 IOMMU (SysMMU) | S2 IOMMU (S2MPU) |
| :--- | :--- | :--- |
| **주요 목적** | 주소 변환 및 편의성 (Translation) | 보안 및 하드웨어 격리 (Protection) |
| **변환 과정** | IOVA → IPA | IPA → PA |
| **관리 계층** | EL1 (Kernel / Guest OS) | EL2 (Hypervisor) |
| **설정 내용** | 페이지 테이블 (Page Table) | 메모리 보호 영역 (Region/Grant) |
| **작동 시점** | Master IP 바로 뒷단 (분산 배치) | 메모리 컨트롤러 앞단 (중앙 배치) |
| **실패 시 결과** | Page Fault (커널이 처리 가능) | S2MPU Fault (하이퍼바이저가 감지/차단) |

- **S1(SysMMU)** 은 물리적으로 흩어져 있는 메모리 페이지들을 각 master IP 입장에서 하나의 연속된 가상 주소 공간으로 보이게 하며, IP 별로 독립된 페이지 테이블을 가져 서로의 주소 공간을 침범하지 못하게 한다. 제어 주체는 Guest OS 커널(EL1)이다.
- **S2(S2MPU)** 는 S1 에서 변환된 IPA 가 실제로 해당 VM 이나 IP 가 접근해도 되는 물리 영역인지 최종 확인하는 계층이다. 하이퍼바이저(EL2)가 설정한 영역 외의 물리 메모리 접근을 차단하여, 특정 VM 이 손상되어도 다른 VM 이나 Hypervisor 영역을 침범하지 못하게 한다. 커널(EL1)은 S2 설정에 직접 개입할 수 없다.

이 두 계층의 구분은 4장(SysMMU 사용 시점)과 5장(S2MPU 사용 시점)을 이해하는 전제가 된다.

---

## 3. dmabuf는 어떻게 생성되는가

V920 플랫폼(Automotive-V920, KITT2)에서 애플리케이션이 DMA-BUF 를 할당하는 방법은 리눅스 커널의 표준 dma-buf 서브시스템을 기반으로 한다 [[1](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=000SXRC5S_SCH_0000)]. 아래 어느 경로로 생성하더라도, **이 생성 단계에서는 아직 어떤 master IP가 이 버퍼를 사용할지, 어떤 SysMMU가 개입할지 결정되지 않는다.** 디바이스와의 연결은 4장에서 설명하는 attach 단계에서 비로소 이루어진다.

### 3.1 DMA-Heap 인터페이스 (권장)

현대 리눅스 커널(5.18+)에서 표준으로 채택된 방식이다. 애플리케이션은 `/dev/dma_heap/system` 장치를 열고 `DMA_HEAP_IOCTL_ALLOC` ioctl 을 호출하여 버퍼를 할당받는다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)].

```c
int heap_fd = open("/dev/dma_heap/system", O_RDWR);
struct dma_heap_allocation_data alloc_data = {
    .len = buffer_size,
    .fd_flags = O_CLOEXEC | O_RDWR,
};
ioctl(heap_fd, DMA_HEAP_IOCTL_ALLOC, &alloc_data);
int dmabuf_fd = alloc_data.fd;
```

커널 내부에서는 `dma_heap_ioctl_allocate()` → `dma_heap_bufferfd_alloc()` → `dma_heap_buffer_alloc()` → `heap->ops->allocate()` 순으로 호출이 전파되어 실제 메모리 할당이 수행된다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)]. 이 호출 체인 어디에도 디바이스 정보는 전달되지 않으며, 반환되는 것은 물리 페이지가 할당된 dma_buf 에 대한 fd 뿐이다.

### 3.2 ION 인터페이스 (레거시)

V920 과 같은 임베디드 플랫폼에서는 기존 ION 프레임워크도 지원될 수 있다. ION 은 `dma_buf_fd()` 함수를 통해 할당된 dma_buf 에 대한 fd 를 생성한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)].

```c
struct ion_allocation_data alloc_data = {
    .len = buffer_size,
    .heap_id_mask = ION_HEAP_SYSTEM_MASK,
};
ioctl(ion_fd, ION_IOC_ALLOC, &alloc_data);
int dmabuf_fd = dma_buf_fd(ion_handle, O_CLOEXEC);
```

### 3.3 GPU 특화 할당 경로 (NVIDIA 기반)

NVIDIA 임베디드 GPU 를 포함하는 경우, NVMAP 드라이버를 통한 할당 경로가 사용될 수 있다. `NVMAP_IOC_CREATE` ioctl 이 dmabuf FD 핸들을 반환하며, 이후 `NVMAP_IOC_ALLOC` ioctl 이 실제 backing page 를 할당한다 [[4](https://doi.org/10.1109/RTSS55097.2022.00039)].

```c
struct nvmap_create_handle args = { .size = buffer_size };
ioctl(nvmap_fd, NVMAP_IOC_CREATE, &args);
int dmabuf_fd = args.fd;
```

fd 생성과 backing page 할당이 분리되어 있다는 점은, "생성 = 디바이스 결정"이 아니라는 것을 더욱 명확히 보여준다. 이 단계에서도 GPU 가상 주소 공간 매핑은 아직 이루어지지 않는다.

### 3.4 OpenCL External Memory 연동

V920 에서 GPU 연산을 수행하는 OpenCL 애플리케이션은 `cl_khr_external_memory_dma_buf` 확장을 통해 외부 dma-buf 를 import 할 수 있다 [[5](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964)].

```c
cl_mem cl_buf = clImportMemorySAMSUNG(context, CL_MEM_EXTERNAL_MEMORY_DMA_BUF,
                                       size, dmabuf_fd, 0);
```

`clImportMemorySAMSUNG()` 내부에서 실질적으로 디바이스 attach 가 수행되며, 이 호출이 곧 4장에서 설명할 attach 단계에 해당한다 [[6](https://confluence.samsungds.net/pages/viewpage.action?pageId=188092903)].

### 3.5 V4L2 통합 인터페이스

카메라/디스플레이 파이프라인에서는 V4L2 프레임워크가 dmabuf 와 통합되어 있다. VB2(Video Buffer 2)는 ion 및 dmabuf 와 통합되어 마스터 드라이버에 공통 인터페이스를 제공한다 [[7](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=00095L7EQ_SCH_0003)].

```c
struct v4l2_requestbuffers reqbufs = {
    .count = 4,
    .type = V4L2_BUF_TYPE_VIDEO_CAPTURE,
    .memory = V4L2_MEMORY_DMABUF,
};
ioctl(v4l2_fd, VIDIOC_REQBUFS, &reqbufs);
```

### 3.6 플랫폼별 고려사항 및 미확인 사항

내부 문서 검색 결과 V920/KITT2 플랫폼의 dmabuf allocation 관련 문서(`dmabuf.txt`, `dmabuf_per_process.txt`)가 존재함은 확인되었으나 실제 내용에는 접근하지 못했다 [[8](https://confluence.samsungds.net/pages/viewpage.action?pageId=2143308880),[13]]. 표준 리눅스 dma-buf API 를 기반으로 하되, 플랫폼별 드라이버(NVMAP, V4L2, OpenCL 확장)를 상황에 따라 선택적으로 사용하는 것이 권장된다.

---

## 4. dmabuf는 각 device의 SysMMU(S1)에 언제, 어떻게 사용되는가

### 4.1 생성 단계: 디바이스 미결정 (재확인)

3장에서 살펴본 대로, dmabuf 생성 시점에는 `struct device` 정보가 전혀 전달되지 않는다. 따라서 이 시점에는 어떤 SysMMU가 개입할지 결정할 수 있는 정보 자체가 없다.

### 4.2 attach 단계: SysMMU가 결정되는 실제 지점

디바이스가 dmabuf 를 사용하기 위해서는 `dma_buf_attach(dmabuf, dev)` 를 호출해야 한다. 이 호출 시점에 IOMMU 프레임워크는 인자로 전달된 `dev` 의 `dev->iommu` 필드를 조회하여, 그 디바이스에 등록되어 있는 SysMMU ops 를 호출한다. **"어느 master IP 에 붙어 있는 SysMMU 를 쓸지"는 dmabuf 생성 시점이 아니라, attach 시점에 어떤 `dev` 를 인자로 넘기느냐로 결정된다.** `dev->iommu` 가 비어 있는 디바이스로 attach 하면 SysMMU ops 자체가 수행되지 않는다.

| 단계 | 함수/IOCTL | 설명 |
|------|-----------|------|
| 1 | `dma_buf_get(fd)` | fd 를 통해 dma_buf 구조체 획득 |
| 2 | `dma_buf_attach(dmabuf, dev)` | `dev->iommu` 조회 → 해당 디바이스의 SysMMU(S1) ops 결정 |
| 3 | `dma_buf_map_attachment()` | SysMMU 페이지 테이블에 IOVA→IPA map 수행, scatterlist 획득 |
| 4 | `DMA_BUF_IOCTL_SYNC` | CPU/디바이스 간 접근 동기화 |

### 4.3 map_attachment 단계: 실제 페이지 테이블 프로그래밍

`dma_buf_map_attachment()` 호출은 dma_buf 의 scatterlist 테이블을 반환하며, 이는 디바이스가 DMA 연산을 수행하기 위해 필요한 물리 페이지 정보를 포함한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)]. 이 정보를 바탕으로 해당 디바이스의 SysMMU 페이지 테이블에 IOVA→IPA map/unmap 이 실제로 프로그래밍된다. GPU 의 경우 `NVGPU_AS_IOCTL_MAP_BUFFER_EX` ioctl 을 사용하여 페이지를 GPU 가상 주소 공간에 매핑한다 [[4](https://doi.org/10.1109/RTSS55097.2022.00039)].

### 4.4 코드 예시

exynosauto-modules 의 scaler 드라이버는 이 3단계(생성 → attach → map_attachment)를 명확히 보여준다.

```c
// exynosauto-modules/drivers/media/platform/exynos/scaler/scaler-core.c
// alloc_intermediate_buffer()
iframe->dma_buf[i] = dma_heap_buffer_alloc(iframe->dma_heap, size, 0, 0);
iframe->attachment[i] = dma_buf_attach(iframe->dma_buf[i], dev);
iframe->sgt[i] = dma_buf_map_attachment(iframe->attachment[i],
                                         DMA_BIDIRECTIONAL);
```

`dma_heap_buffer_alloc()` 은 dmabuf 를 생성만 할 뿐 디바이스와 무관하며, `dma_buf_attach(dmabuf, dev)` 호출에서 비로소 이 scaler 디바이스의 SysMMU 가 연동되고, `dma_buf_map_attachment()` 에서 실제 매핑이 완료된다. `dma_buf_xxx` 함수들은 커널 프레임워크 API 이며, 이 내부에서 Samsung 이 등록해 놓은 dmabuf/SysMMU ops 가 호출되는 구조다.

### 4.5 동기화 및 이종 디바이스 간 공유

CPU 와 디바이스 간 접근 동기화는 `DMA_BUF_IOCTL_SYNC` ioctl 로 수행하며, `DMA_BUF_SYNC_START`/`DMA_BUF_SYNC_END` 플래그로 접근 구간을 명시한다 [[9](https://confluence.samsungds.net/pages/viewpage.action?pageId=3364542927)].

```c
struct dma_buf_sync sync = { .flags = DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ };
ioctl(dmabuf_fd, DMA_BUF_IOCTL_SYNC, &sync);
void* base_addr = mmap(NULL, size, PROT_READ, MAP_SHARED, dmabuf_fd, 0);
// ... buffer access ...
munmap(base_addr, size);
sync.flags = DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ;
ioctl(dmabuf_fd, DMA_BUF_IOCTL_SYNC, &sync);
```

V920 은 GPU 와 NPU 를 모두 포함하는 이종 컴퓨팅 플랫폼으로, `dma_buf implicit fence` 를 이용한 context switching-less NPU/GPU interworking 이 가능하며, `cl_khr_memory_external` extension 을 이용하여 NPU 와 GPU 간 fence sync 를 공유할 수 있다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)]. 애플리케이션은 IFM(Input FeatureMap), OFM(Output FeatureMap), IM(Intermediate buffer)을 모두 포함하는 하나의 dma_buf 메모리 공간을 할당받고, GPU 와 NPU 가 각각 자신의 `dev` 로 attach 하여 번갈아 사용한다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)]. 이 방식은 call depth 를 줄이고 user mode/kernel mode 간 스위칭 횟수를 개선한다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)].

---

## 5. dmabuf는 S2MPU(S2)에 언제, 어떻게 사용되는가

4장에서 SysMMU(S1)가 IOVA→IPA 변환을 마치더라도, 이 IPA가 실제 물리 메모리(PA)에 접근하기 위해서는 S2MPU(S2)의 최종 검사를 통과해야 한다. S2MPU의 IPA→PA 매핑 설정은 기본적으로 **하이퍼바이저(EL2)가 독점적으로 제어**하지만, 하이퍼바이저가 임의로 설정을 만들어내는 것이 아니라 시스템 설계 단계의 정적 설정값, 또는 게스트 OS(EL1)의 런타임 요청에 의해 이루어진다. 이 절이 바로 "하이퍼바이저가 dmabuf 공유에 어떻게 개입하는가"에 대한 답이다.

S2MPU 설정이 이루어지는 시점은 부팅 단계와 런타임 단계로 나누어진다.

### 5.1 부팅 단계 (Static Configuration)

부팅 시에는 시스템 설계자가 정의한 정적 메모리 맵에 따라 하이퍼바이저가 초기 매핑을 수행한다.

- **결정 주체**: 시스템 설계자(Device Tree 등 정적 설정)
- **설정 시점**: 하이퍼바이저 부팅 및 VM 초기화 단계
- **과정**:
  1. 하이퍼바이저는 Device Tree(dts) 파일에 명시된 S2MPU 관련 설정을 참조한다.
  2. VM 초기화 과정에서 각 게스트 VM 에 할당될 메모리 범위와 이에 대응하는 IPA→PA 매핑 규칙을 읽어들여, S2MPU 페이지 테이블을 생성하고 프로그래밍한다.

즉 정상적인 부팅 흐름에서는 게스트 OS 나 디바이스 드라이버가 별도로 요청하지 않아도, 하이퍼바이저가 사전에 정의된 범위만큼 S2MPU 권한을 미리 설정해 둔다.

### 5.2 런타임 단계 (Dynamic Request)

시스템 동작 중에 새로운 메모리 영역을 공유하거나 권한을 변경해야 하는 경우, 게스트 OS 의 드라이버가 하이퍼바이저에 동적으로 요청한다.

- **요청 주체**: 게스트 OS 의 디바이스 드라이버(EL1)
- **설정 시점**: VM 실행 중, DMA 를 위한 공유 버퍼 생성 또는 메모리 권한 변경이 필요할 때
- **요청 및 처리 흐름**:
  1. **요청 발생**: 게스트 OS 의 드라이버(예: NPU 드라이버)가 특정 메모리 영역에 대한 S2MPU 권한 설정이 필요하다고 판단한다.
  2. **하이퍼바이저 호출(SMC)**: 게스트 OS 는 SMC(Secure Monitor Call) 또는 하이퍼바이저 콜을 통해 IPA 와 크기(size) 정보를 인자로 전달하며 권한 설정을 요청한다.
  3. **하이퍼바이저 처리(EL2)**: 하이퍼바이저는 SMC 트랩을 통해 요청을 수신하고, 내부 벤더 모듈로 포워딩한다. 요청된 IPA 를 실제 물리 주소(PA)로 변환한 뒤, 해당 VMID 에 대응하는 S2MPU 페이지 테이블(Permission Table)에 읽기/쓰기 권한을 설정한다.
  4. **결과 반영**: 설정이 완료되면 S2MPU 하드웨어가 이후의 모든 DMA 요청에 대해 이 테이블을 참조하여 통과 여부를 결정한다.

### 5.3 S2MPU 관점에서의 전체 데이터 흐름

4장과 5장의 내용을 결합하면, dmabuf 를 이용한 DMA 요청의 전체 흐름은 다음과 같다.

```
[Application]
    │  dmabuf 생성 (3장) — 디바이스 미결정
    ▼
[Device Driver]
    │  dma_buf_attach(dmabuf, dev) — dev->iommu 조회, SysMMU(S1) 결정 (4장)
    │  dma_buf_map_attachment() — IOVA→IPA 페이지 테이블 프로그래밍
    ▼
[SysMMU (S1, EL1 관리)]
    │  IOVA → IPA 변환
    ▼
[S2MPU (S2, EL2/하이퍼바이저 관리)]
    │  부팅 시 정적 설정 또는 런타임 SMC 요청으로 사전 프로그래밍된
    │  Permission Table 을 참조하여 IPA → PA 변환 + 접근 권한 검사 (5장)
    │  → 권한 없음: S2MPU Fault (하이퍼바이저가 감지/차단)
    ▼
[Hardware: GPU/NPU/Display/Camera] — 실제 물리 메모리 접근
```

### 5.4 미확인 사항

V920 플랫폼에서 S2MPU 권한 설정을 요청하는 실제 SMC 호출 규약(호출 번호, 인자 포맷)과, 어떤 드라이버가 어떤 시점에 런타임 요청을 발생시키는지에 대한 V920 특정 문서는 확인되지 않았다. 또한 부팅 시 Device Tree 에 정의되는 S2MPU 영역 설정의 V920 실제 값도 별도 확인이 필요하다.

---

## 6. dmabuf를 프로세스 간에 어떻게 전달하는가

동일 커널 인스턴스 내에서 서로 다른 프로세스가 하나의 dmabuf 를 공유하는 경우, export 측과 import 측이 각각 명확한 절차를 따른다.

### 6.1 Export 과정: dmabuf fd 생성 및 전달

프로세스 A 가 dmabuf 를 할당한 후 이를 공유하려면 먼저 fd 로 export 해야 한다. `dma_buf_fd()` 를 호출하면 dma-buf 객체에 대한 fd 가 생성되어 사용자 공간으로 반환된다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)]. 이 fd 는 Unix domain socket 등 IPC 메커니즘을 통해 프로세스 B 로 전달될 수 있다.

DRM PRIME 인터페이스를 사용하는 경우 `DRM_IOCTL_PRIME_HANDLE_TO_FD` ioctl 을 통해 DRM 버퍼 객체 핸들을 DMA-BUF fd 로 변환하여 export 한다 [[12](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808495)]. 이 ioctl 은 driver 가 사용자에게 제공한 handle 을 이용해 객체를 찾고, dmabuf 를 만든 후 fd 를 제공한다.

### 6.2 Import 과정: fd 수신과 자신의 디바이스로 attach

프로세스 B 는 전달받은 fd 로 다음 단계를 수행한다. **이때 4장에서 설명한 attach 메커니즘이 프로세스 B 의 관점에서 다시 한 번 수행된다.**

1. **`dma_buf_get(fd)`**: fd 를 통해 dma_buf 구조체 포인터를 획득한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)].
2. **`dma_buf_attach(dmabuf, dev)`**: 프로세스 B 가 사용하는 자신의 디바이스로 attach 하여, 그 디바이스에 붙은 SysMMU(S1) 매핑을 설정한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)].
3. **`dma_buf_map_attachment()`**: scatterlist 를 얻어 DMA 접근 가능한 물리 주소 정보를 확보한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)].

즉 동일한 dmabuf 라도 프로세스 A 의 디바이스와 프로세스 B 의 디바이스가 다르면, 각각 독립적인 SysMMU 매핑이 생성된다. dmabuf 자체는 물리 페이지 정보만 담고 있을 뿐이며, "어느 SysMMU 를 쓸지"는 attach 하는 쪽의 `dev` 에 의해 각자 결정된다.

OpenCL 환경에서는 `cl_khr_external_memory_dma_buf` extension 을 사용하여 dma-buf fd 를 OpenCL 메모리 객체로 import 할 수 있다 [[5](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964)]. `clImportMemorySAMSUNG(fd, offset=0)` 은 mmap 된 dma-buf fd 를 사용하여 `clCreateBuffer(fd)` 의 memcpy 를 제거하며, `clImportMemoryARM(fd) + clCreateSubBuffer()` 를 사용하면 dma-buf 중간 영역에도 접근할 수 있다 [[6](https://confluence.samsungds.net/pages/viewpage.action?pageId=188092903)].

### 6.3 동기화 메커니즘: Fence 및 Sync 연산

여러 프로세스가 동일 버퍼에 동시 접근할 경우 데이터 무결성이 훼손될 수 있으므로 명시적 동기화가 필수적이다. `DMA_BUF_IOCTL_SYNC` ioctl 로 CPU 와 디바이스 간 접근을 동기화하며, `DMA_BUF_SYNC_START`/`DMA_BUF_SYNC_END` 플래그로 접근 구역과 읽기/쓰기 모드를 지정한다 [[9](https://confluence.samsungds.net/pages/viewpage.action?pageId=3364542927)]. GPU-NPU 간 interworking 시에는 `dma_buf implicit fence` 를 이용한 context switching-less 동기화가 가능하다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)].

### 6.4 제약사항 및 주의사항

| 제약 항목 | 내용 |
|---------|------|
| **fd 전달 범위** | dmabuf fd 는 동일한 커널 인스턴스 내의 프로세스 간에만 전달 가능하며, VM 경계를 넘는 전달은 7장에서 설명하는 별도 메커니즘이 필요하다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)]. |
| **동기화 책임** | dma-buf 서브시스템은 메모리 공유만 제공하며, 동기화(fence, sync)는 사용자 공간 애플리케이션이 명시적으로 관리해야 한다 [[9](https://confluence.samsungds.net/pages/viewpage.action?pageId=3364542927)]. |
| **메모리 일관성** | 캐시 일관성이 없는 아키텍처에서는 `DMA_BUF_SYNC` 연산 전에 캐시 플러시/인밸리데이션이 필요하다 [[9](https://confluence.samsungds.net/pages/viewpage.action?pageId=3364542927)]. |
| **수명 관리** | fd 를 전달받은 프로세스는 사용 완료 후 반드시 `close(fd)` 를 호출해야 하며, 원본 프로세스가 fd 를 닫아도 import 측이 참조하는 한 메모리는 해제되지 않는다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)]. |
| **OpenCL tiling layout** | `cl_khr_external_memory_dma_buf` 및 `cl_khr_external_memory_opaque_fd` 의 경우 tiling layout 을 유추할 수 없어 추가 메타데이터 전달이 필요하다 [[5](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964)]. |

---

## 7. dmabuf를 VM 간에 어떻게 전달하는가

6장의 프로세스 간 공유는 Unix domain socket 을 통한 fd 전달을 전제로 하며, 이는 **동일한 커널 인스턴스** 안에서만 유효하다. VM(게스트 OS)은 서로 다른 커널 인스턴스이므로, 단순한 fd 전달로는 dmabuf 를 공유할 수 없고 하이퍼바이저가 매개하는 별도 메커니즘이 필요하다.

### 7.1 Virtio 기반 공유 메모리

Virtio 는 호스트-게스트 간 효율적인 통신을 위해 공유 메모리 상의 virtqueue 링 버퍼를 사용한다 [[10](https://doi.org/10.1109/TSC.2016.2594760)]. 게스트 드라이버는 scatter-gather 리스트를 avail-ring 에 기록하고 kick call 을 통해 호스트에 알린다. dmabuf fd 가 게스트-호스트 경계를 넘어 전달되기 위해서는 다음 단계가 추가로 필요하다.

1. **게스트 dmabuf 할당**: 게스트 OS 내에서 표준 dma-buf API 로 할당(3장 참고).
2. **fd 전달 메커니즘**: virtio-vdmabuf 를 통해 fd 를 호스트로 전달.
3. **호스트 dmabuf import**: 호스트 OS 에서 전달된 fd 를 import 하여 실제 하드웨어 접근(6장의 import 절차와 동일한 attach 과정을 호스트 측 디바이스에 대해 수행).
4. **주소 변환**: 게스트 물리 주소(GPA)를 호스트 물리 주소(HPA)로 변환.

Virtio 기반 공유 메모리 통신은 호스트-게스트 간 데이터 복사 비용을 줄이며, dma-buf 를 통한 제로카피 버퍼 공유가 가능하다 [[10](https://doi.org/10.1109/TSC.2016.2594760)].

### 7.2 S2MPU 를 통한 VM 간 권한 검사

VM 간 dmabuf 공유에서도 5장에서 설명한 S2MPU 는 동일하게 관여한다. 게스트 A 가 특정 물리 영역을 게스트 B 또는 호스트와 공유하려면, 하이퍼바이저가 해당 IPA 영역에 대해 두 VM(또는 호스트) 모두 접근 가능하도록 S2MPU Permission Table 을 갱신해야 한다. 이 갱신은 5.1절의 부팅 시 정적 설정 범위를 넘어서는 경우 5.2절의 런타임 SMC 요청 절차를 따른다. 즉 VM 간 공유는 "virtio 를 통한 fd/데이터 전달"과 "S2MPU 를 통한 물리 접근 권한 부여"라는 두 개의 독립적인 절차가 함께 이루어져야 완성된다.

### 7.3 제약사항 및 미확인 사항

하이퍼바이저 환경에서 게스트 VM 간 dmabuf 공유는 다음과 같은 제약을 가진다.

1. **물리 주소 변환**: 각 게스트는 독립적인 물리 주소 공간을 가지므로, GPA→HPA 변환에 하이퍼바이저의 중재가 필요하다.
2. **파일 디스크립터 전달**: Unix domain socket 을 통한 fd 전달은 동일 커널 인스턴스 내에서만 동작하므로, 게스트 간 fd 공유는 virtio-vdmabuf, virtio-serial 또는 virtio-vsock 메커니즘을 사용해야 한다.
3. **동기화 경계**: 게스트 간 fence 공유는 하이퍼바이저를 통한 명시적인 이벤트 주입(eventfd injection)이 필요하다.

**내부 문서 한계**: V920 특정 하이퍼바이저(KVM, Xen, 또는 삼성 커스텀)의 dmabuf 중재 메커니즘과 실제 virtio-vdmabuf 구현 세부사항에 대한 구체적인 문서는 확인되지 않았다. 관련 팀과의 추가 협의가 필요하다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423),[10](https://doi.org/10.1109/TSC.2016.2594760),[14]].

---

## 8. 결론 및 제언

### 종합 결론

V920 플랫폼(Automotive-V920, KITT2)에서 dmabuf 관련 동작은 다섯 가지 질문에 대한 답으로 요약된다.

1. **생성**: 애플리케이션은 `/dev/dma_heap/system` 등을 통해 dmabuf 를 할당받으며, 이 시점에는 디바이스가 결정되지 않는다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)].
2. **SysMMU(S1) 사용**: `dma_buf_attach(dmabuf, dev)` 호출 시 `dev->iommu` 를 통해 해당 디바이스의 SysMMU 가 결정되고, `dma_buf_map_attachment()` 에서 IOVA→IPA 페이지 테이블이 실제로 프로그래밍된다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)].
3. **S2MPU(S2) 사용**: SysMMU 가 변환한 IPA 는 S2MPU 의 검사를 거쳐야 실제 물리 메모리(PA)에 접근할 수 있다. S2MPU Permission Table 은 부팅 시 Device Tree 기반 정적 설정, 또는 런타임 중 게스트 드라이버의 SMC 요청으로 하이퍼바이저(EL2)가 프로그래밍한다.
4. **프로세스 간 전달**: exporting 프로세스가 `dma_buf_fd()` 또는 `DRM_IOCTL_PRIME_HANDLE_TO_FD` 로 fd 를 만들고, importing 프로세스는 자신의 디바이스로 다시 attach 하여 독립적인 SysMMU 매핑을 생성한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010),[12](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808495)].
5. **VM 간 전달**: 동일 커널 인스턴스 전제가 깨지므로 virtio-vdmabuf 등 하이퍼바이저 매개 메커니즘으로 fd/데이터를 전달하고, S2MPU Permission Table 갱신으로 물리 접근 권한을 별도로 부여해야 한다 [[10](https://doi.org/10.1109/TSC.2016.2594760)].

### 식별된 격차 (Gaps)

1. **V920 특정 하이퍼바이저 종류 및 S2MPU SMC 호출 규약 미확인**: 어떤 하이퍼바이저(KVM/Xen/커스텀)가 사용되는지, 런타임 S2MPU 권한 요청의 실제 SMC 호출 번호·인자 포맷은 V920 특정 문서에서 확인되지 않았다.
2. **V920 특정 ioctl 시퀀스 미확인**: 프로세스 간 fd export/import 를 위한 정확한 ioctl 시퀀스에 대한 V920 특정 문서가 발견되지 않았다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)].
3. **참고 문서 접근 제한**: 내부 문서에 `dmabuf.txt`, `dmabuf_per_process.txt`, `memory_diagnosis.txt` 파일이 언급되어 있으나 실제 내용은 확인되지 않았다 [[8](https://confluence.samsungds.net/pages/viewpage.action?pageId=2143308880)].
4. **virtio-vdmabuf 실제 구현 세부사항 미확인**: VM 간 dmabuf 전달에 사용되는 virtio-vdmabuf 의 V920 실제 구현과 GPA→HPA 변환 세부 절차는 추가 확인이 필요하다.

### 권고사항

1. **V920 플랫폼 dmabuf 가이드 문서화**: `dmabuf.txt`, `dmabuf_per_process.txt` 로 언급된 레퍼런스 파일의 실제 내용을 V920 플랫폼에 맞게 구체화하여 내부 Confluence 에 문서화할 것을 권고한다 [[8](https://confluence.samsungds.net/pages/viewpage.action?pageId=2143308880)].
2. **S2MPU 런타임 요청 절차 명확화**: 게스트 드라이버가 SMC 로 S2MPU 권한을 요청하는 실제 호출 규약과, 이를 처리하는 하이퍼바이저 내부 모듈의 동작을 V920 기준으로 문서화할 필요가 있다.
3. **프로세스 간 공유 시 동기화 메커니즘 활용**: `dma_buf implicit fence` 를 이용한 context switching-less NPU/GPU interworking 방식을 적극 활용하여 user mode/kernel mode 간 스위칭 횟수를 개선할 수 있다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)].
4. **OpenCL external memory extension 검토**: `cl_khr_external_memory_dma_buf` extension 을 활용하여 OpenCL 과 다른 API 간 버퍼 공유 시 memcpy 오버헤드를 제거하는 방안을 검토할 것을 권고한다 [[5](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964)].
5. **V920 특정 ioctl 시퀀스 검증**: 실제 V920 타겟 보드에서 `DMA_HEAP_IOCTL_ALLOC`, `DMA_BUF_IOCTL_SYNC`, `DRM_IOCTL_PRIME_HANDLE_TO_FD` 등 주요 ioctl 의 동작 시퀀스를 검증하고 문서화할 필요가 있다.
6. **HMM 과 dmabuf 의존성 평가**: HMM(Heterogeneous Memory Management)은 dmabuf 와 큰 의존성이 없는 것으로 확인되었으므로 [[15](https://confluence.samsungds.net/pages/viewpage.action?pageId=3448234410)], Device Memory 를 Page 로 관리하는 `migrate_to_ram()` 등의 API 와 dmabuf 의 공존 가능성을 추가로 평가할 것을 권고한다.

---

## 9. References

**[1]** [V920](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=000SXRC5S_SCH_0000) — glossary, updated: 2024-04
**[2]** [DMAHEAP, libion - 이기성](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423) — confl, updated: 2023-11
**[3]** [DMA-Buffer Sharing Framework](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010) — confl, updated: 2018-05
**[4]** [Enabling GPU Memory Oversubscription via Transparent Paging to an NVMe SSD](https://doi.org/10.1109/RTSS55097.2022.00039) — paper_ieee, updated: 2022-12
**[5]** [(2023/03) cl_khr_external_memory extension](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964) — confl, updated: 2023-03
**[6]** [Weekly Status 2022 (W39)](https://confluence.samsungds.net/pages/viewpage.action?pageId=188092903) — confl, updated: 2023-09
**[7]** [VB2](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=00095L7EQ_SCH_0003) — glossary, updated: 2026-07
**[8]** [\[TEMP\] AI Labelling](https://confluence.samsungds.net/pages/viewpage.action?pageId=2143308880) — confl, updated: 2025-01
**[9]** [11. 如何从 dmabuf中提取出 weight, nnc 정보](https://confluence.samsungds.net/pages/viewpage.action?pageId=3364542927) — confl, updated: 2026-03
**[10]** [HyperCo: Optimizing Network Performance in ARM-Based Mobile Virtualization](https://doi.org/10.1109/TSC.2016.2594760) — paper_ieee, updated: 2019-01
**[11]** [vOTF 를 이용한 GPU/NPU data 전송 환경에서 GPU/NPU Sync mechanism 제공](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624) — confl, updated: 2023-02
**[12]** [PRIME](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808495) — confl, updated: 2023-11
**[13]** [V920 플랫폼에서 application 이 dmabuf 를 allocation 하는 API 와 방법 - Worker Result w1](No URL) — research-worker, updated: 2026-12
**[14]** [V920 환경에서의 dmabuf 관련 커널 드라이버와 hypervisor 설정 및 요구사항 - Worker Result w4](No URL) — research-worker, updated: 2026-12
**[15]** [2026/04/13 (민재홍) GOST Workshop in SRCX (China)](https://confluence.samsungds.net/pages/viewpage.action?pageId=3448234410) — confl, updated: 2026-04
