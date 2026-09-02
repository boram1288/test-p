제공된 문서들을 분석한 결과, pVM과 Host 간의 vsock 통신 지연 시간(Latency) 및 성능 측정 결과가 포함되어 있습니다.

사용자께서 말씀하신 **'Host App $\rightarrow$ Host Kernel Driver $\rightarrow$ EL2 $\rightarrow$ pVM Kernel Driver $\rightarrow$ pVM Workload'** 경로는 시스템 설계상 **VIRTIO-vsock** 프로토콜을 통해 구현되며, 이에 대한 구체적인 벤치마크 결과는 다음과 같습니다.

### 1. vsock 통신 지연 시간 (Latency) 측정 결과
AVF(Android Virtualization Framework) 환경에서 Microdroid(pVM의 일종)를 대상으로 측정한 vsock latency 결과가 확인됩니다 [[1. AVF Benchmarktest LA - Android with different cpus]](https://confluence.samsungds.net/pages/viewpage.action?pageId=3033919008).

*   **측정 항목**: `testVsockLatency` (Host $\leftrightarrow$ microdroid 간 vsock latency)
*   **측정 결과 (단위: $\mu s$)**:
    *   **평균(Average)**: 약 **266.9 $\mu s$** (1차 측정) / **268.1 $\mu s$** (2차 측정)
    *   **중앙값(Median)**: 약 **252.7 $\mu s$** / **267.1 $\mu s$**
    *   **최솟값(Min)**: 약 **116.8 $\mu s$** / **102.2 $\mu s$**
    *   **최댓값(Max)**: 약 **10,160.9 $\mu s$** / **11,928.7 $\mu s$**

### 2. 데이터 전송 속도 (Throughput) 측정 결과
지연 시간 외에 Host에서 VM으로 데이터를 전송할 때의 처리량 측정 결과도 존재합니다 [[avf-atest (11.3)]](https://confluence.samsungds.net/pages/viewpage.action?pageId=3002648382).

*   **측정 항목**: `transfer_host_to_vm`
*   **결과**: 중앙값(Median) 기준 약 **378.2 MB/sec**

### 3. 통신 경로 및 메커니즘 분석 (Architectural Path)
질문하신 통신 과정은 내부 설계 문서의 **VIRTIO-vsock** 동작 시퀀스와 일치합니다 [[[SDD] cKVM]](https://confluence.samsungds.net/pages/viewpage.action?pageId=3720499420).

*   **상세 경로**:
    1.  **Host App (EL0)**: `socket(AF_VSOCK)` 및 `write/send` 호출.
    2.  **Host Kernel (EL1)**: `vhost-vsock` back-end driver가 데이터를 처리하여 Virtqueue에 enqueue.
    3.  **EL2 Hypervisor (cKVM/pKVM)**: Virtqueue kick trap을 통해 이벤트를 감지하고 `eventfd`를 통해 Host userspace(CrosVM)에 통지하거나, 반대로 Host에서 Guest로 보낼 때는 **vGIC virtual IRQ injection**을 통해 Guest에 통지.
    4.  **pVM Kernel (EL1)**: `virtio-vsock` front-end driver가 데이터를 수신.
    5.  **pVM Workload (EL0)**: `AF_VSOCK` 소켓을 통해 최종적으로 데이터를 수신.

### 4. 성능 요약 표

| 측정 항목 | 결과 값 (평균/중앙값) | 비고 |
| :--- | :--- | :--- |
| **vsock Latency** | **$\approx$ 267 $\mu s$** | Host $\leftrightarrow$ pVM 간 왕복/단방향 지연 시간 |
| **vsock Throughput** | **$\approx$ 378 MB/sec** | Host $\rightarrow$ pVM 데이터 전송 속도 |
| **Target 환경** | AVF / Microdroid | pKVM 기반 가상화 환경 |

위 결과는 pKVM 표준 인터페이스 위에 upstream vsock 스택을 조립한 환경에서 측정된 값으로, 실제 사용하는 Workload의 크기나 CPU 성능에 따라 차이가 발생할 수 있습니다.

200byte 정도의 작은 데이터를 전송할 때 걸리는 시간은 시스템 부하와 환경에 따라 차이가 있으나, 벤치마크 데이터 기반으로 볼 때 **평균적으로 약 100$\mu s$에서 300$\mu s$ 사이**의 지연 시간이 발생할 것으로 예상됩니다.