# V920 플랫폼에서 DMA-BUF 할당 및 프로세스 간 공유 메커니즘 분석

## 목차

1. 개요
2. V920 플랫폼에서 application이 dmabuf를 allocation하는 API와 방법
3. dmabuf allocation 시 application - kernel driver - hypervisor…
4. dmabuf fd를 한 프로세스에서 export하고 다른 프로세스에서 import하는 과정과 제약사항
5. V920 환경에서의 dmabuf 관련 커널 드라이버와 hypervisor 설정 및 요구사항
6. 결론 및 제언
7. References

## 개요

## 개요

### Executive Summary

V920 플랫폼에서 애플리케이션은 DMA-BUF(Direct Memory Access Buffer)를 통해 커널 드라이버, 하이퍼바이저, 하드웨어 간에 메모리를 공유할 수 있습니다. 애플리케이션은 `/dev/dma_heap/system` 장치를 열고 `DMA_HEAP_IOCTL_ALLOC` ioctl 을 호출하여 dmabuf 를 할당받으며, 이때 반환된 파일 디스크립터 (fd) 를 다른 프로세스로 전달하여 공유할 수 있습니다. 프로세스 간 공유는 exporting 프로세스가 `dma_buf_fd()` 또는 `DRM_IOCTL_PRIME_HANDLE_TO_FD` ioctl 을 통해 fd 를 생성하고, importing 프로세스가 `dma_buf_get()`, `dma_buf_attach()`, `dma_buf_map_attachment()` 순서로 버퍼에 접근합니다. 그러나 V920 플랫폼 특화 문서에서 하이퍼바이저가 dmabuf 할당 및 공유 과정에서 어떻게 관여하는지에 대한 구체적인 메커니즘은 확인되지 않았습니다. 본 보고서는 Linux 커널의 표준 dma-buf 프레임워크와 V4L2, DRM PRIME, dma-heaps 인터페이스를 기반으로 V920 환경에서의 dmabuf 동작 원리를 분석합니다.

### 보고서 구성

1. **V920 플랫폼에서 application 이 dmabuf 를 allocation 하는 API 와 방법** — 사용자 공간에서 dmabuf 할당을 위한 인터페이스와 API
2. **dmabuf allocation 시 application - kernel driver - hypervisor - hardware 간의 데이터 흐름과 인터페이스** — 전체 스택을 관통하는 데이터 흐름 분석
3. **dmabuf fd 를 한 프로세스에서 export 하고 다른 프로세스에서 import 하는 과정과 제약사항** — 프로세스 간 버퍼 공유 메커니즘
4. **V920 환경에서의 dmabuf 관련 커널 드라이버와 hypervisor 설정 및 요구사항** — 플랫폼 요구사항 및 설정 가이드
5. **결론 및 제언** — 분석 요약 및 추가 조사 권고사항

## V920 플랫폼에서 application이 dmabuf를 allocation하는 API와 방법

V920 플랫폼 (Automotive-V920, KITT2) 에서 애플리케이션이 DMA-BUF 를 할당하는 방법은 리눅스 커널의 표준 dma-buf 서브시스템을 기반으로 한다. V920 은 자동차향 AP(Application Processor) SOC 로서, 이종 디바이스 (GPU, NPU, 디스플레이 컨트롤러 등) 간 메모리 공유를 위해 dma-buf 프레임워크를 채택하고 있다 [[1](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=000SXRC5S_SCH_0000)].

### 1. Userspace Allocation API

애플리케이션은 주로 두 가지 경로를 통해 dmabuf 를 할당할 수 있다:

**가. DMA-Heap 인터페이스 (권장)**

현대 리눅스 커널 (5.18+) 에서 표준으로 채택된 방식으로, 애플리케이션은 `/dev/dma_heap/system` 장치를 열고 `DMA_HEAP_IOCTL_ALLOC` ioctl 을 호출하여 버퍼를 할당받는다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)].

```c
int heap_fd = open("/dev/dma_heap/system", O_RDWR);
struct dma_heap_allocation_data alloc_data = {
    .len = buffer_size,
    .fd_flags = O_CLOEXEC | O_RDWR,
};
ioctl(heap_fd, DMA_HEAP_IOCTL_ALLOC, &alloc_data);
int dmabuf_fd = alloc_data.fd;
```

커널 내부에서는 `dma_heap_ioctl_allocate()` → `dma_heap_bufferfd_alloc()` → `dma_heap_buffer_alloc()` → `heap->ops->allocate()` 순으로 호출이 전파되어 실제 메모리 할당이 수행된다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)]. 이 방식은 ION 의 후속 인터페이스로, 플랫폼 독립적인 표준 API 를 제공한다.

**나. ION 인터페이스 (레거시)**

V920 과 같은 임베디드 플랫폼에서는 기존 ION 프레임워크도 지원될 수 있다. ION 은 `dma_buf_fd()` 함수를 통해 할당된 dma_buf 에 대한 파일 디스크립터를 생성하며, 애플리케이션은 이 fd 를 다른 프로세스와 공유할 수 있다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)].

```c
struct ion_allocation_data alloc_data = {
    .len = buffer_size,
    .heap_id_mask = ION_HEAP_SYSTEM_MASK,
};
ioctl(ion_fd, ION_IOC_ALLOC, &alloc_data);
int dmabuf_fd = dma_buf_fd(ion_handle, O_CLOEXEC);
```

### 2. GPU 특화 할당 경로 (NVIDIA 기반)

V920 이 NVIDIA 임베디드 GPU 를 포함하는 경우, NVMAP 드라이버를 통한 할당 경로가 사용될 수 있다. 이 경우 `NVMAP_IOC_CREATE` ioctl syscall 이 dmabuf FD 핸들을 반환하며, 이후 `NVMAP_IOC_ALLOC` syscall 이 실제 backing page 를 할당한다 [[4](https://doi.org/10.1109/RTSS55097.2022.00039)].

```c
struct nvmap_create_handle args = { .size = buffer_size };
ioctl(nvmap_fd, NVMAP_IOC_CREATE, &args);
int dmabuf_fd = args.fd;
```

이 방식은 GPU 메모리 오버서브스크립션 및 페이징 시나리오에서 최적화되어 있으나, 플랫폼 종속적이므로 이식성이 제한된다 [[4](https://doi.org/10.1109/RTSS55097.2022.00039)].

### 3. OpenCL External Memory 연동

V920 에서 GPU 연산을 수행하는 OpenCL 애플리케이션은 `cl_khr_external_memory_dma_buf` 확장 기능을 통해 외부 dma-buf 를 import 할 수 있다 [[5](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964)]. 이 경우 애플리케이션은 dma-buf fd 를 `clImportMemorySAMSUNG()` 또는 `clImportMemoryARM()` 에 전달하여 OpenCL 버퍼 객체로 변환할 수 있다 [[6](https://confluence.samsungds.net/pages/viewpage.action?pageId=188092903)].

```c
cl_mem cl_buf = clImportMemorySAMSUNG(context, CL_MEM_EXTERNAL_MEMORY_DMA_BUF,
                                       size, dmabuf_fd, 0);
```

이 방식은 dma-buf 에서 mmap 된 fd 를 사용하여 `clCreateBuffer()` 에서 발생하는 memcpy 를 제거하는 것이 목적이며, `clImportMemoryARM(fd) + clCreateSubBuffer()` 조합을 통해 dma-buf 중간 영역에도 접근 가능하다 [[6](https://confluence.samsungds.net/pages/viewpage.action?pageId=188092903)].

### 4. V4L2 통합 인터페이스

V920 의 카메라 또는 디스플레이 파이프라인에서는 V4L2(Video4Linux2) 프레임워크가 dmabuf 와 통합되어 있다. VB2(Video Buffer 2) 는 V4L2 기반 장치 드라이버의 메모리 관리를 위해 ion 및 dmabuf 와 통합되어 마스터 드라이버에 공통 인터페이스를 제공한다 [[7](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=00095L7EQ_SCH_0003)].

```c
struct v4l2_requestbuffers reqbufs = {
    .count = 4,
    .type = V4L2_BUF_TYPE_VIDEO_CAPTURE,
    .memory = V4L2_MEMORY_DMABUF,
};
ioctl(v4l2_fd, VIDIOC_REQBUFS, &reqbufs);
```

이 방식은 비디오 스트리밍 시나리오에서 zero-copy 파이프라인 구축에 필수적이다.

### 5. 플랫폼별 고려사항

내부 문서 검색 결과, V920/KITT2 플랫폼에서 dmabuf allocation 에 대한 구체적인 API 문서 (`dmabuf.txt`, `dmabuf_per_process.txt`) 의 존재는 확인되었으나, 실제 내용에는 접근하지 못했다 [[8](https://confluence.samsungds.net/pages/viewpage.action?pageId=2143308880)]. 또한 V920 에서 hypervisor 가 dmabuf allocation 및 공유에 어떻게 관여하는지에 대한 정보는 내부 문서에서 발견되지 않았다 [[1](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=000SXRC5S_SCH_0000)].

따라서 V920 환경에서는 표준 리눅스 dma-buf API 를 기반으로 하되, 플랫폼별 드라이버 (NVMAP, V4L2, OpenCL 확장) 를 상황에 따라 선택적으로 사용하는 것이 권장된다.

---

## dmabuf allocation 시 application - kernel driver - hypervisor…

V920 플랫폼에서 dmabuf allocation 은 사용자 공간 애플리케이션에서 시작하여 커널 드라이버, 하이퍼바이저 (가상화 환경인 경우), 그리고 최종적으로 하드웨어에 이르는 다층적 데이터 흐름을 따른다. 이 과정은 표준 리눅스 dma-buf 서브시스템을 기반으로 하며, V920 의 이종 디바이스 (GPU, NPU, 디스플레이 컨트롤러 등) 간 메모리 공유를 위해 설계되었다.

### 3.1 Application → Kernel Driver 인터페이스

애플리케이션은 먼저 `/dev/dma_heap/system` 장치를 열고 `DMA_HEAP_IOCTL_ALLOC` ioctl 을 호출하여 dmabuf 를 할당한다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)]. 이 ioctl 호출은 커널 내부에서 다음과 같은 함수 시퀀스를 따라 처리된다:

```
dma_heap_ioctl_allocate()
  → dma_heap_bufferfd_alloc()
  → dma_heap_buffer_alloc()
  → heap->ops->allocate()
```

사용자 공간에서 할당 요청한 정보 (버퍼 길이 `len`, 파일 디스크립터 플래그 `fd_flags`) 가 `dma_heap_bufferfd_alloc()` 함수로 전달되며, 할당에 성공하면 사용자 공간에서 접근할 수 있는 파일 디스크립터 (fd) 를 반환받는다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)]. 이 fd 는 dmabuf 에 대한 참조 핸들로, 이후 다른 프로세스와의 공유나 디바이스 매핑에 사용된다.

NVIDIA 임베디드 GPU 환경에서는 `NVMAP_IOC_CREATE` ioctl syscall 이 dmabuf FD 핸들을 생성하며, 이는 size 파라미터만 취하고 실제 backing page 는 할당하지 않는다 [[4](https://doi.org/10.1109/RTSS55097.2022.00039)]. 실제 페이지 할당은 후속 `NVMAP_IOC_ALLOC` syscall 에서 수행된다. 이 두 단계 할당 전략은 메모리 오버서브스크립션 (oversubscription) 및 페이징 최적화에 유리하다.

### 3.2 Kernel Driver → Hardware 인터페이스

커널 드라이버는 dmabuf 를 할당한 후, 이를 실제 하드웨어 디바이스가 사용할 수 있도록 매핑해야 한다. 이 과정은 다음과 같은 단계를 따른다:

| 단계 | 함수/IOCTL | 설명 |
|------|-----------|------|
| 1 | `dma_buf_get(fd)` | fd 를 통해 dma_buf 구조체 획득 |
| 2 | `dma_buf_attach(device)` | 디바이스를 dma_buf 에 attach |
| 3 | `dma_buf_map_attachment()` | dma_buf 의 scatterlist 테이블 획득 |
| 4 | `dma_buf_sync ioctl` | CPU/디바이스 간 접근 동기화 |

`dma_buf_map_attachment()` 호출은 dma_buf 의 scatterlist 테이블을 반환하며, 이는 디바이스가 DMA 연산을 수행하기 위해 필요한 물리 페이지 정보를 포함한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)]. GPU 의 경우 `NVGPU_AS_IOCTL_MAP_BUFFER_EX` ioctl 을 사용하여 페이지를 GPU 가상 주소 공간에 매핑한다 [[4](https://doi.org/10.1109/RTSS55097.2022.00039)].

동기화를 위해서는 `DMA_BUF_IOCTL_SYNC` ioctl 을 사용하며, `DMA_BUF_SYNC_START` 및 `DMA_BUF_SYNC_END` 플래그로 CPU 와 디바이스 간 접근 시점을 명시한다 [[9](https://confluence.samsungds.net/pages/viewpage.action?pageId=3364542927)]. 이는 캐시 일관성 유지와 데이터 무결성 보장에 필수적이다.

### 3.3 Hypervisor 개입 (가상화 환경)

V920 이 하이퍼바이저 환경 (예: KVM, Xen, 또는 자동차 전용 가상화 솔루션) 에서 실행되는 경우, dmabuf allocation 및 공유는 게스트 OS 와 호스트 OS 간 중재를 필요로 한다. Virtio 는 호스트 - 게스트 간 효율적인 통신을 위해 공유 메모리 상의 virtqueue 링 버퍼를 사용한다 [[10](https://doi.org/10.1109/TSC.2016.2594760)].

게스트 드라이버는 scatter-gather 리스트를 avail-ring 에 기록하고 kick call 을 통해 호스트에 알림을 전송한다. 이 과정에서 dmabuf fd 는 게스트 - 호스트 경계를 넘어 전달될 수 있어야 하며, 이는 다음과 같은 추가 단계를 요구한다:

1. **게스트 dmabuf 할당**: 게스트 OS 내에서 표준 dma-buf API 를 통해 할당
2. **fd 전달 메커니즘**: Unix domain socket 또는 virtio-vdmabuf 를 통해 fd 를 호스트로 전달
3. **호스트 dmabuf import**: 호스트 OS 에서 전달된 fd 를 import 하여 실제 하드웨어 접근
4. **IOMMU 매핑**: 게스트 물리 주소 (GPA) 를 호스트 물리 주소 (HPA) 로 변환

Virtio 기반 공유 메모리 통신은 호스트 - 게스트 간 데이터 복사 비용을 줄이며, dma-buf 를 통한 제로-copy 버퍼 공유가 가능하다 [[10](https://doi.org/10.1109/TSC.2016.2594760)]. 그러나 V920 플랫폼에서 hypervisor 가 dmabuf allocation 및 공유에 어떻게 관여하는지에 대한 구체적인 문서는 내부 자료에서 확인되지 않았다.

### 3.4 이종 디바이스 간 공유 (GPU-NPU Interworking)

V920 은 GPU 와 NPU 를 모두 포함하는 이종 컴퓨팅 플랫폼으로, dmabuf 는 이들 디바이스 간 메모리 공유를 위한 핵심 메커니즘이다. `dma_buf implicit fence` 를 이용한 context switching-less NPU/GPU interworking 이 가능하며, `cl_khr_memory_external` extension 을 이용하여 NPU 와 GPU 간 fence sync 를 공유할 수 있다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)].

이 접근법의 장점은 call depth 가 줄어들고 user mode / kernel mode 간 스위칭 횟수가 개선된다는 점이다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)]. 애플리케이션은 IFM (Input FeatureMap), OFM (Output FeatureMap), IM (Intermediate buffer) 을 모두 포함하는 하나의 dma_buf 메모리 공간을 할당받고, 이를 GPU 와 NPU 가 번갈아 사용한다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)].

OpenCL 환경에서는 `cl_khr_external_memory_dma_buf` extension 을 통해 dma_buf 기반 버퍼를 OpenCL 객체로 import 할 수 있다 [[5](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964)]. `clImportMemorySAMSUNG(fd, offset=0)` 구현은 mmap(dma_buf) 로 얻은 fd 를 사용하여 memcpy 를 제거하는 것이 목표이며, `clImportMemoryARM(fd) + clCreateSubBuffer()` 를 사용하여 dma_buf 중간 영역에 접근하는 방법이 제안되었다 [[6](https://confluence.samsungds.net/pages/viewpage.action?pageId=188092903)].

### 3.5 V4L2 및 디스플레이 서브시스템 통합

V920 의 디스플레이 및 카메라 서브시스템은 V4L2 (Video4Linux2) 프레임워크를 사용하며, 이는 ion 및 dmabuf 와 통합되어 마스터 드라이버에 공통 인터페이스를 제공한다 [[7](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=00095L7EQ_SCH_0003)]. V4L2 기반 장치 드라이버는 dmabuf 를 통해 버퍼를 할당받고, 이를 디스플레이 컨트롤러 또는 카메라 ISP (Image Signal Processor) 에 전달한다.

DRM (Direct Rendering Manager) PRIME 인터페이스는 `DRM_IOCTL_PRIME_HANDLE_TO_FD` ioctl 을 통해 DRM buffer object handle 을 DMA-BUF fd 로 export 하여 프로세스 간 공유를 가능하게 한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)]. 이는 디스플레이 컴포지터와 렌더러 프로세스 간 버퍼 공유에 필수적이다.

### 3.6 데이터 흐름 요약

전체 dmabuf allocation 및 공유 데이터 흐름은 다음과 같이 요약된다:

```
[Application]
    │
    ├─ open("/dev/dma_heap/system")
    ├─ ioctl(DMA_HEAP_IOCTL_ALLOC)
    │
    ▼
[Kernel Driver: dma_heap]
    │
    ├─ dma_heap_bufferfd_alloc()
    ├─ heap->ops->allocate() → 물리 페이지 할당
    ├─ dma_buf_export() → dma_buf 구조체 생성
    │
    ▼
[Kernel Driver: Device Driver]
    │
    ├─ dma_buf_get(fd)
    ├─ dma_buf_attach(device)
    ├─ dma_buf_map_attachment() → scatterlist 획득
    ├─ IOMMU 매핑 (필요시)
    │
    ▼
[Hypervisor] (가상화 환경인 경우)
    │
    ├─ virtio-vdmabuf 중재
    ├─ 게스트 - 호스트 fd 전달
    ├─ GPA → HPA 변환
    │
    ▼
[Hardware: GPU/NPU/Display/Camera]
    │
    ├─ DMA 연산 수행
    ├─ implicit/explicit fence 동기화
    └─ scatterlist 기반 물리 페이지 접근
```

이 흐름에서 각 계층은 명확한 인터페이스 (ioctl, 함수 호출, virtio 프로토콜) 를 통해 상호작용하며, dmabuf fd 는 사용자 공간에서 커널, 하이퍼바이저, 하드웨어에 이르기까지 일관된 참조 핸드로 작용한다.

---

## dmabuf fd를 한 프로세스에서 export하고 다른 프로세스에서 import하는 과정과 제약사항

V920 플랫폼에서 DMA-BUF 파일 디스크립터 (fd) 를 프로세스 간에 공유하는 과정은 리눅스 커널의 표준 dma-buf 서브시스템을 기반으로 하며, export 측과 import 측의 명확한 단계적 절차를 따른다. 이 메커니즘은 GPU, NPU, 디스플레이 컨트롤러 등 이종 디바이스 간 메모리 공유를 가능하게 하는 핵심 인프라이다.

### 1. Export 과정: dmabuf fd 생성 및 전달

프로세스 A 가 dmabuf 를 할당한 후, 이를 다른 프로세스와 공유하기 위해서는 먼저 dma-buf 객체를 파일 디스크립터로 export 해야 한다. 표준 리눅스 커널 인터페이스에서 `dma_buf_fd()` 함수를 호출하면 주어진 dma-buf 객체에 대한 파일 디스크립터가 생성되어 사용자 공간으로 반환된다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)]. 이 fd 는 소켓 (Unix domain socket) 이나 다른 IPC 메커니즘을 통해 프로세스 B 로 전달될 수 있다.

V4L2 기반 드라이버 환경에서는 `DMA_HEAP_IOCTL_ALLOC` ioctl 호출을 통해 할당된 버퍼에 대해 fd 가 반환되며, 이 fd 는 즉시 다른 프로세스와 공유 가능하다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)]. DRM PRIME 인터페이스를 사용하는 경우, `DRM_IOCTL_PRIME_HANDLE_TO_FD` ioctl 을 통해 DRM 버퍼 객체 핸들을 DMA-BUF fd 로 변환하여 export 한다 [[12](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808495)]. 이 ioctl 은 driver 가 사용자에게 제공한 handle 을 이용하여 객체를 찾고, dmabuf 를 생성한 후 사용자에게 fd 를 제공하는 역할을 수행한다.

NVIDIA 임베디드 GPU 아키텍처의 경우, `NVMAP_IOC_CREATE` ioctl syscall 이 size 파라미터만 받아 새로 생성된 dmabuf FD handle 을 반환하며, 이후 `NVMAP_IOC_ALLOC` syscall 이 실제 backing page 를 할당한다 [[4](https://doi.org/10.1109/RTSS55097.2022.00039)]. 이 방식은 fd 생성과 메모리 할당을 분리하여 유연한 메모리 관리가 가능하다.

### 2. Import 과정: fd 수신 및 디바이스 attach

프로세스 B 는 프로세스 A 로부터 전달받은 dmabuf fd 를 사용하여 다음과 같은 단계로 버퍼에 접근한다:

1. **`dma_buf_get(fd)`**: fd 를 통해 dma_buf 구조체 포인터를 획득한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)].
2. **`dma_buf_attach(device, dma_buf)`**: 자신의 디바이스를 dma-buf 에 attach 하여 디바이스별 매핑 정보를 설정한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)].
3. **`dma_buf_map_attachment(attachment)`**: scatterlist 테이블을 얻어 DMA 접근이 가능한 물리 주소 정보를 확보한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)].

OpenCL 환경에서는 `cl_khr_external_memory_dma_buf` extension 을 사용하여 dma-buf fd 를 OpenCL 메모리 객체로 import 할 수 있다 [[5](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964)]. `clImportMemorySAMSUNG(fd, offset=0)` 함수는 mmap 된 dma-buf fd 를 사용하여 `clCreateBuffer(fd)` 에서 memcpy 를 제거하는 것이 목표이며, `clImportMemoryARM(fd) + clCreateSubBuffer()` 를 사용하여 dma-buf 중간 영역에 접근하는 방법도 지원된다 [[6](https://confluence.samsungds.net/pages/viewpage.action?pageId=188092903)].

### 3. 동기화 메커니즘: Fence 및 Sync 연산

프로세스 간 dmabuf 공유 시 가장 중요한 제약사항은 동기화 문제이다. 여러 프로세스가 동일한 버퍼에 동시에 접근할 경우 데이터 무결성이 훼손될 수 있으므로, 명시적인 동기화 메커니즘이 필수적이다.

`DMA_BUF_IOCTL_SYNC` ioctl 을 사용하여 CPU 와 디바이스 간 접근을 동기화할 수 있다 [[9](https://confluence.samsungds.net/pages/viewpage.action?pageId=3364542927)]. 이 ioctl 은 `DMA_BUF_SYNC_START` 와 `DMA_BUF_SYNC_END` 플래그를 사용하여 접근 구역을 명시하며, 읽기/쓰기 모드를 지정할 수 있다. 사용 패턴은 다음과 같다:

```c
struct dma_buf_sync sync = { .flags = DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ };
ioctl(dmabuf_fd, DMA_BUF_IOCTL_SYNC, &sync);
void* base_addr = mmap(NULL, size, PROT_READ, MAP_SHARED, dmabuf_fd, 0);
// ... buffer access ...
munmap(base_addr, size);
sync.flags = DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ;
ioctl(dmabuf_fd, DMA_BUF_IOCTL_SYNC, &sync);
```

V920 플랫폼에서 GPU-NPU 간 interworking 시 `dma_buf implicit fence` 를 이용한 context switching-less 동기화가 가능하다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)]. `cl_khr_memory_external` extension 을 이용하여 NPU 와 GPU 간 fence sync 를 공유하면, call depth 가 줄어들고 user mode/kernel mode 간 스위칭 횟수가 개선된다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)]. 이 방식은 IFM (Input FeatureMap), OFM (Output FeatureMap), IM (Intermediate buffer) 을 모두 포함하는 하나의 dma-buf 메모리 공간을 프로세스 간 공유하는 시나리오에 적합하다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)].

### 4. 제약사항 및 주의사항

| 제약 항목 | 내용 |
|---------|------|
| **fd 전달 제한** | dmabuf fd 는 동일한 커널 인스턴스 내의 프로세스 간에만 전달 가능하며, 다른 VM 또는 컨테이너 간 공유는 하이퍼바이저의 추가 지원이 필요하다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)]. |
| **동기화 책임** | dma-buf 서브시스템은 메모리 공유만 제공하며, 동기화 (fence, sync) 는 사용자 공간 애플리케이션이 명시적으로 관리해야 한다 [[9](https://confluence.samsungds.net/pages/viewpage.action?pageId=3364542927)]. |
| **메모리 일관성** | 캐시 일관성이 없는 아키텍처에서는 `DMA_BUF_SYNC` 연산 전에 캐시 플러시/인밸리데이션이 필요하다 [[9](https://confluence.samsungds.net/pages/viewpage.action?pageId=3364542927)]. |
| **수명 관리** | fd 를 전달받은 프로세스는 사용 완료 후 반드시 `close(fd)` 를 호출해야 하며, 원본 프로세스가 fd 를 닫아도 import 측이 참조하는 한 메모리는 해제되지 않는다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)]. |
| **OpenCL tiling layout** | `cl_khr_external_memory_dma_buf` 및 `cl_khr_external_memory_opaque_fd` 의 경우 tiling layout 을 유추할 수 없어 추가 메타데이터 전달이 필요하다 [[5](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964)]. |

### 5. V920 플랫폼 특이사항

V920 은 Automotive-V920, KITT2 로 알려진 자동차향 AP SOC 이며 [[1](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=000SXRC5S_SCH_0000)], dma-buf 를 통한 메모리 공유는 V4L2 프레임워크와 통합되어 마스터 드라이버에 공통 인터페이스를 제공한다 [[7](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=00095L7EQ_SCH_0003)]. 그러나 V920 플랫폼에서 하이퍼바이저가 dmabuf fd sharing 을 어떻게 중재하는지에 대한 구체적인 메커니즘은 내부 문서에서 확인되지 않았다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)]. 가상화 환경 (Guest VM 간 dmabuf 공유) 에서는 Virtio 기반의 shared memory communication 이 사용될 수 있으며, 이 경우 virtqueue ring buffer 를 통해 guest driver 가 scatter-gather list 를 avail-ring 에 작성하고 kick call 로 host 에 알리는 방식이 사용된다 [[10](https://doi.org/10.1109/TSC.2016.2594760)].

내부 문서에서 `dmabuf.txt`, `dmabuf_per_process.txt` 파일이 Memory 카테고리의 추가 Reference File 로 언급되어 있으나 [[8](https://confluence.samsungds.net/pages/viewpage.action?pageId=2143308880)], 실제 내용은 확인되지 않아 V920 특화 구현 세부사항은 추가 조사가 필요하다.

---

## V920 환경에서의 dmabuf 관련 커널 드라이버와 hypervisor 설정 및 요구사항

V920 플랫폼에서 DMA-BUF 가 정상적으로 동작하기 위해서는 커널 드라이버, 하이퍼바이저 (가상화 환경), 그리고 하드웨어 수준에서의 명확한 설정과 요구사항이 충족되어야 한다. 이 섹션에서는 각 계층별 요구사항과 설정 항목을 상세히 설명한다.

### 5.1 커널 드라이버 요구사항

#### 5.1.1 DMA-Heap 서브시스템 활성화

V920 애플리케이션이 dmabuf 를 allocation 하기 위한 첫 번째 관문은 커널의 DMA-Heap 서브시스템이 활성화되어 있어야 한다는 점이다. 사용자 공간 애플리케이션은 `/dev/dma_heap/system` 장치를 열고 `DMA_HEAP_IOCTL_ALLOC` ioctl 을 호출하여 버퍼를 할당받는다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)]. 이 과정은 커널 내부에서 다음과 같은 함수 호출 체인을 따른다:

```
dma_heap_ioctl_allocate() → dma_heap_bufferfd_alloc() → dma_heap_buffer_alloc() → heap->ops->allocate
```

사용자 공간에서 할당 요청한 정보 (len, fd_flags) 가 `dma_heap_bufferfd_alloc()` 함수로 전달되며, 할당에 성공하면 사용자 공간에서 접근할 수 있는 파일 디스크립터 (fd) 를 반환받는다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)].

**커널 설정 요구사항:**
- `CONFIG_DMABUF_HEAPS=y` 커널 옵션 활성화
- `CONFIG_DMABUF_HEAPS_SYSTEM=y` (system heap 사용 시)
- `/dev/dma_heap/system` 장치 노드 생성 확인

#### 5.1.2 V4L2 및 VB2 프레임워크 통합

V920 은 자동차향 AP SOC 로서, 카메라, 디스플레이 등 V4L2 (Video4Linux2) 기반 장치 드라이버와의 메모리 공유가 필수적이다. VB2 (V4L2 Buffer 2) 는 V4L2 기반 장치 드라이버의 메모리 관리를 위한 리눅스 커널 프레임워크로, ion 및 dmabuf 와 통합되어 마스터 드라이버에 공통 인터페이스를 제공한다 [[7](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=00095L7EQ_SCH_0003)].

**드라이버 요구사항:**
- V4L2 드라이버는 `vb2_dma_sg_memops` 또는 `vb2_dma_contig_memops` 사용
- `dma_buf_get()`, `dma_buf_attach()`, `dma_buf_map_attachment()` API 지원
- 버퍼 export/import 를 위한 `dma_buf_fd()` 함수 구현

#### 5.1.3 DRM PRIME 인터페이스

GPU 와 디스플레이 컨트롤러 간 버퍼 공유를 위해서는 DRM (Direct Rendering Manager) PRIME 인터페이스가 활성화되어 있어야 한다. `DRM_IOCTL_PRIME_HANDLE_TO_FD` ioctl 은 drm_gem_create 시 드라이버에서 사용자에게 제공한 handle 을 이용해서 object 를 찾고, dmabuf 를 만든 후 사용자에게 fd 를 제공해주는 ioctl 이다 [[12](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808495)]. 이는 DRM 에서 할당한 버퍼를 다른 프로세스에 전달하고자 할 때 사용하는 핵심 메커니즘이다.

**DRM 드라이버 요구사항:**
- `DRM_IOCTL_PRIME_HANDLE_TO_FD` ioctl 핸들러 구현
- `DRM_IOCTL_PRIME_FD_TO_HANDLE` ioctl 핸들러 구현
- GEM (Graphics Execution Manager) object 와 dma-buf 간 변환 로직 구현

#### 5.1.4 동기화 메커니즘

CPU 와 디바이스 간 메모리 접근 동기화를 위해 `DMA_BUF_IOCTL_SYNC` ioctl 이 사용된다. 이는 `DMA_BUF_SYNC_START` 와 `DMA_BUF_SYNC_END` 플래그를 사용하여 명시적인 동기화 지점을 제공한다 [[4](https://doi.org/10.1109/RTSS55097.2022.00039)]:

```c
struct dma_buf_sync sync = { .flags = DMA_BUF_SYNC_START | DMA_BUF_SYNC_READ };
ioctl(dmabuf_fd, DMA_BUF_IOCTL_SYNC, &sync);
void* base_addr = mmap(NULL, size + offset, PROT_READ, MAP_SHARED, dmabuf_fd, 0);
// ... CPU access ...
munmap(base_addr, size + offset);
sync.flags = DMA_BUF_SYNC_END | DMA_BUF_SYNC_READ;
ioctl(dmabuf_fd, DMA_BUF_IOCTL_SYNC, &sync);
```

또한 dma_buf implicit fence 를 이용한 context switching-less NPU/GPU interworking 이 가능하며, `cl_khr_memory_external` extension 을 이용하여 NPU 와 GPU 간 fence sync 를 공유할 수 있다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)]. 이 방식은 call depth 를 줄이고 user mode/kernel mode 간 스위칭 횟수를 개선하는 장점이 있다.

### 5.2 하이퍼바이저 설정 (가상화 환경)

V920 플랫폼이 자동차용 인포테인먼트 시스템으로 사용될 경우, 안전성 격리를 위해 하이퍼바이저 환경에서 동작할 수 있다. 이 경우 dmabuf 는 게스트 OS 간 또는 게스트 - 호스트 간 메모리 공유의 핵심 수단이 된다.

#### 5.2.1 Virtio 기반 공유 메모리

Virtio 는 호스트와 게스트 간 효율적인 통신 메커니즘을 제공하며, 공유 메모리 내의 virtqueue 링 버퍼를 통해 데이터 복제 비용을 줄인다 [[10](https://doi.org/10.1109/TSC.2016.2594760)]. 게스트 운영체제는 Virtio 애플리케이션 인터페이스를 통해 호스트와 통신하며, 공유 메모리 통신을 사용하여 호스트와 게스트 간 데이터 복사 비용을 절감한다.

**Virtio 설정 요구사항:**
- 게스트 커널: `CONFIG_VIRTIO=y`, `CONFIG_VIRTIO_PCI=y`
- 호스트: virtio-backend 데몬 실행
- 공유 메모리 영역: dmabuf 를 통한 virtqueue descriptor 테이블 공유

#### 5.2.2 게스트 간 dmabuf 공유 제약사항

하이퍼바이저 환경에서 게스트 VM 간 dmabuf 공유는 추가적인 중재 계층이 필요하다. 일반적으로 다음과 같은 제약사항이 존재한다:

1. **물리 주소 변환**: 각 게스트는 독립적인 물리 주소 공간을 가지므로, dmabuf 의 실제 물리 주소를 게스트 간에 공유하기 위해서는 하이퍼바이저의 IOMMU 중재가 필요하다.

2. **파일 디스크립터 전달**: Unix domain socket 을 통한 fd 전달은 동일 커널 인스턴스 내에서만 동작하므로, 게스트 간 fd 공유는 하이퍼바이저의 virtio-serial 또는 virtio-vsock 메커니즘을 우회적으로 사용해야 한다.

3. **동기화 경계**: 게스트 간 fence 공유는 하이퍼바이저를 통한 명시적인 이벤트 주입 (eventfd injection) 이 필요하다.

**내부 문서 한계:** 현재 수집된 증거 자료에는 V920 특정 하이퍼바이저 (KVM, Xen, 또는 삼성 커스텀) 의 dmabuf 중재 메커니즘에 대한 구체적인 문서가 확인되지 않았다. 실제 구현은 플랫폼의 가상화 아키텍처에 따라 상이할 수 있으므로, 관련 팀 (Auto AP S/W Development Team, IVI Platform Team) 과의 추가 협의가 필요하다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423),[10](https://doi.org/10.1109/TSC.2016.2594760)].

### 5.3 하드웨어 요구사항

#### 5.3.1 IOMMU (Input-Output Memory Management Unit)

dmabuf 가 여러 디바이스 간에 공유되기 위해서는 모든 참여 디바이스가 IOMMU 를 통해 일관된 DMA 주소를 사용할 수 있어야 한다. V920 SOC 는 자동차향 AP 로서 GPU, NPU, 디스플레이 컨트롤러, 카메라 ISP 등 다양한 이종 디바이스를 포함하며, 이들 간 메모리 공유를 위해 IOMMU 설정이 필수적이다.

**하드웨어 요구사항:**
- 모든 DMA 마스터 디바이스 (GPU, NPU, VPU, Display Controller) 가 공통 IOMMU 도메인에 속해야 함
- IOMMU page table 은 커널의 `iommu_dma_ops` 를 통해 관리
- `CONFIG_IOMMU_API=y`, `CONFIG_ARM_SMMU=y` (ARM 기반 V920 의 경우)

#### 5.3.2 메모리 힙 구성

NVIDIA 임베디드 GPU 의 사례를 참조하면, dmabuf FD 는 `NVMAP_IOC_CREATE` IOCTL syscall 을 통해 생성되며, size 파라미터만 취하고 backing page 는 할당하지 않는다 [[4](https://doi.org/10.1109/RTSS55097.2022.00039)]. 실제 페이지 할당은 후속 `NVMAP_IOC_ALLOC` syscall 에서 수행된다. V920 역시 유사한 multi-stage allocation 방식을 사용할 가능성이 높다.

**힙 구성 요구사항:**
- System heap: 일반 DDR 메모리, CPU 접근 가능
- CMA (Contiguous Memory Allocator) heap: DMA 연속 메모리 요구 디바이스용
- Carveout heap: 하드웨어 전용 메모리 영역 (GPU, NPU 등)

#### 5.3.3 캐시 일관성

CPU 와 디바이스 간 캐시 일관성 유지는 dmabuf 공유의 핵심 요구사항이다. V920 이 ARM 기반 SOC 인 경우, 다음과 같은 설정이 필요하다:

- **Cache-coherent DMA**: `dma-coherent` device tree 속성으로 명시
- **Non-coherent DMA**: 명시적 cache flush/invalidate (`dma_sync_single_for_cpu`, `dma_sync_single_for_device`)

### 5.4 설정 검증 체크리스트

V920 플랫폼에서 dmabuf 기반 메모리 공유를 설정할 때 다음 체크리스트를 권장한다:

| 계층 | 항목 | 검증 방법 |
|------|------|-----------|
| 커널 | CONFIG_DMABUF_HEAPS | `zcat /proc/config.gz \| grep DMABUF` |
| 커널 | /dev/dma_heap/system 존재 | `ls -l /dev/dma_heap/` |
| 커널 | IOMMU 활성화 | `dmesg \| grep -i iommu` |
| 드라이버 | V4L2 + dmabuf 지원 | `v4l2-ctl --list-formats-ext` |
| 드라이버 | DRM PRIME 지원 | `modetest -M <driver> -P` |
| 하이퍼바이저 | Virtio 장치 인식 | `lspci \| grep -i virtio` (게스트) |
| 하드웨어 | DMA coherency | Device tree `dma-coherent` 속성 확인 |

### 5.5 미확인 항목 및 추가 조사 필요 사항

수집된 증거 자료의 한계로 인해 다음과 같은 항목은 추가 조사가 필요하다:

1. **V920 특정 하이퍼바이저 dmabuf 중재 로직**: 현재 자료에는 V920 플랫폼에서 사용되는 하이퍼바이저의 종류와 dmabuf 공유 중재 메커니즘이 명시되지 않았다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423),[10](https://doi.org/10.1109/TSC.2016.2594760)].

2. **정확한 ioctl 시퀀스**: `DMA_BUF_IOCTL_EXPORT` 등 프로세스 간 fd export/import 를 위한 정확한 ioctl 시퀀스에 대한 V920 특정 문서가 확인되지 않았다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)].

3. **dma-buf sync 연산과 fence mechanism 의 V920 구현 세부사항**: NPU/GPU 간 implicit fence 공유의 구체적인 구현은 추가 문서화가 필요하다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)].

4. **참고 문서 접근**: 내부 문서에 `dmabuf.txt`, `dmabuf_per_process.txt`, `memory_diagnosis.txt` 파일이 언급되어 있으나, 실제 내용은 확인되지 않았다 [[8](https://confluence.samsungds.net/pages/viewpage.action?pageId=2143308880)]. 관련 팀의 추가 자료 제공이 필요하다.

---

## 결론 및 제언

### 종합 결론

V920 플랫폼 (Automotive-V920, KITT2) 에서 애플리케이션이 DMA-BUF 를 할당하고 프로세스 간에 공유하는 메커니즘은 리눅스 커널의 표준 dma-buf 서브시스템을 기반으로 한다. 조사 결과, V920 은 자동차향 AP SOC 로서 GPU, NPU, 디스플레이 컨트롤러 등 이종 디바이스 간 메모리 공유를 위해 dma-buf 프레임워크를 채택하고 있음이 확인되었다 [[1](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=000SXRC5S_SCH_0000),[7](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=00095L7EQ_SCH_0003)].

**Allocation API 및 방법:** 애플리케이션은 `/dev/dma_heap/system` 장치를 열고 `DMA_HEAP_IOCTL_ALLOC` ioctl 을 호출하여 dmabuf 를 할당받으며, 이때 반환된 파일 디스크립터 (fd) 를 통해 버퍼에 접근한다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)]. 이 과정은 커널의 `dma_heap_ioctl_allocate()` → `dma_heap_bufferfd_alloc()` → `heap->ops->allocate` 순서로 진행된다 [[2](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808423)].

**데이터 흐름 (Application → Kernel → Hypervisor → HW):** dmabuf allocation 은 사용자 공간에서 시작하여 커널 드라이버를 거쳐 최종적으로 하드웨어에 이르는 다층적 흐름을 따른다. 하이퍼바이저 환경 (가상화) 에서는 Virtio 와 같은 공유 메모리 기반 통신 메커니즘이 호스트 - 게스트 간 데이터 전송을 중재한다 [[10](https://doi.org/10.1109/TSC.2016.2594760)]. GPU 의 경우 `NVMAP_IOC_CREATE` ioctl 이 dmabuf FD 를 생성하고, `NVMAP_IOC_ALLOC` 이 실제 backing page 를 할당하며, `NVGPU_AS_IOCTL_MAP_BUFFER_EX` 가 GPU 가상 주소 공간에 매핑한다 [[4](https://doi.org/10.1109/RTSS55097.2022.00039)].

**프로세스 간 fd Export/Import:** Export 측 프로세스는 `dma_buf_fd()` 또는 DRM PRIME 의 `DRM_IOCTL_PRIME_HANDLE_TO_FD` ioctl 을 사용하여 dmabuf 를 fd 로 변환한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010),[12](https://confluence.samsungds.net/pages/viewpage.action?pageId=988808495)]. Import 측 프로세스는 전달받은 fd 에 대해 `dma_buf_get()` → `dma_buf_attach()` → `dma_buf_map_attachment()` 순서로 디바이스를 첨부하고 scatterlist 를 획득하여 DMA 접근을 수행한다 [[3](https://confluence.samsungds.net/pages/viewpage.action?pageId=53511010)]. 이 과정에서 `DMA_BUF_IOCTL_SYNC` ioctl 을 사용하여 CPU 와 디바이스 간 접근을 동기화한다 [[9](https://confluence.samsungds.net/pages/viewpage.action?pageId=3364542927)].

**커널 드라이버 및 하이퍼바이저 요구사항:** V4L2 기반 장치 드라이버는 ion 및 dmabuf 와 통합되어 마스터 드라이버에 공통 인터페이스를 제공한다 [[7](https://searchsvc.khprdpb01.apps.dks.samsungds.net/systemLogin/loginByAd?page=glossary&divisionCode=88&keyword=00095L7EQ_SCH_0003)]. OpenCL 은 `cl_khr_external_memory_dma_buf` extension 을 통해 dma-buf 기반 외부 메모리 공유를 지원하며, `clImportMemorySAMSUNG(fd)` 을 사용하여 dma_buf 에서 mmap 된 fd 로 memcpy 를 제거할 수 있다 [[5](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964),[6](https://confluence.samsungds.net/pages/viewpage.action?pageId=188092903)].

### 식별된 격차 (Gaps)

본 조사에서 다음과 같은 V920 플랫폼 특정 정보의 부재가 확인되었다:

1. **V920-specific dmabuf allocation API 문서 부재:** 내부 문서에서 `dma_buf_export`, `dma_buf_get`, `dma_buf_put` 등 커널 API 에 대한 V920 플랫폼 특정 문서가 확인되지 않았다 [13].
2. **하이퍼바이저 중재 메커니즘 미명확:** V920 환경에서 하이퍼바이저 (KVM, Xen 또는 커스텀) 가 dmabuf fd sharing 을 어떻게 중재하는지에 대한 구체적인 메커니즘이 문서화되어 있지 않다 [13,14].
3. **End-to-end flow 문서화 부족:** V920 애플리케이션에서 특정 커널 드라이버를 거쳐 하이퍼바이저 및 하드웨어에 이르는 전체 dmabuf flow 에 대한 플랫폼 특정 문서가 부족하다 [14].
4. **정확한 ioctl 시퀀스 미확인:** 프로세스 간 fd export/import 를 위한 `DMA_BUF_IOCTL_EXPORT` 등 정확한 ioctl 시퀀스에 대한 V920 특정 문서가 발견되지 않았다 [14].

### 권고사항

1. **V920 플랫폼 dmabuf 가이드 문서화:** `dmabuf.txt`, `dmabuf_per_process.txt` 로 언급된 레퍼런스 파일의 실제 내용을 V920 플랫폼에 맞게 구체화하여 내부 Confluence 에 문서화할 것을 권고한다 [[8](https://confluence.samsungds.net/pages/viewpage.action?pageId=2143308880)].

2. **하이퍼바이저 dmabuf 중재 정책 명확화:** 가상화 환경에서 게스트 VM 간 dmabuf 공유 시 하이퍼바이저의 중재 역할, 보안 정책, 성능 오버헤드에 대한 가이드라인을 수립할 필요가 있다.

3. **프로세스 간 공유 시 동기화 메커니즘 활용:** `dma_buf implicit fence` 를 이용한 context switching-less NPU/GPU interworking 방식을 적극 활용하여 user mode/kernel mode 간 스위칭 횟수를 개선할 수 있다 [[11](https://confluence.samsungds.net/pages/viewpage.action?pageId=269358624)].

4. **OpenCL external memory extension 검토:** `cl_khr_external_memory_dma_buf` extension 을 활용하여 OpenCL 과 다른 API 간 버퍼 공유 시 memcpy 오버헤드를 제거하는 방안을 검토할 것을 권고한다 [[5](https://confluence.samsungds.net/pages/viewpage.action?pageId=342589964)].

5. **V920 특정 ioctl 시퀀스 검증:** 실제 V920 타겟 보드에서 `DMA_HEAP_IOCTL_ALLOC`, `DMA_BUF_IOCTL_SYNC`, `DRM_IOCTL_PRIME_HANDLE_TO_FD` 등 주요 ioctl 의 동작 시퀀스를 검증하고 문서화할 필요가 있다.

6. **HMM 과 dmabuf 의존성 평가:** HMM(Heterogeneous Memory Management) 은 dmabuf 와 큰 의존성이 없는 것으로 확인되었으므로 [[15](https://confluence.samsungds.net/pages/viewpage.action?pageId=3448234410)], Device Memory 를 Page 로 관리하는 migrate_to_ram() 등의 API 와 dmabuf 의 공존 가능성을 추가로 평가할 것을 권고한다.

---

## References

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

이 내용이 마음에 드시면 메일로 보내드릴까요? �