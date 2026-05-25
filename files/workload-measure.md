# 워크로드 측정 도구 추천

ARM TrustZone의 단일 격리(Secure/Non-secure) 한계를 넘어, pKVM(Protected KVM) 스타일의 Stage-2 Page Table 기반 다중 격리 도메인을 구축하는 과제는 최근 안드로이드(AVF) 및 임베디드 오토모티브 분야에서 가장 핫한 아키텍처 트렌드입니다.

제시해주신 품질 속성 시나리오(QS-001, QS-002)를 검증하기 위해, 학계(ACM 등)와 산업계(Google AVF, Linaro 등)에서 사실상 표준(De-facto Standard)으로 사용하며 신뢰성이 검증된 오픈소스 워크로드를 추천해 드립니다.

---

## 1. QS-001 (CPU/메모리 집약 워크로드) 추천 오픈소스

가상화 환경에서 CPU 연산은 대부분 하드웨어 가속(EL1 직접 실행)을 받으므로 오버헤드가 적지만, 메모리(Stage-2 Page Table 및 TLB Miss, Page Fault Handling) 처리는 하이퍼바이저(EL2) 개입을 유발하여 성능 차이를 만듭니다. 이를 정밀하게 측정할 수 있는 도구들입니다.

### 1.1 sysbench (강력 추천)

- **개요**: 가상화 성능 평가에서 가장 널리 쓰이는 가벼우면서도 강력한 도구입니다. CPU 연산 및 메모리 할당/접근 속도를 직관적으로 측정합니다.
- **적용 방법**:
  - CPU: 소수(Prime number) 구하기 연산을 통해 순수 CPU 스케줄링 및 연산 성능 측정

    ```bash
    sysbench cpu --cpu-max-prime=20000 run
    ```

  - Memory: 순차적/무작위 메모리 읽기/쓰기를 통해 Stage-2 Page Table 트랜스레이션 오버헤드 측정

    ```bash
    sysbench memory --memory-block-size=1M --memory-total-size=10G run
    ```

### 1.2 CoreMark (임베디드 필수)

- **개요**: EEMBC에서 개발한 임베디드 표준 벤치마크입니다. 리눅스 가상화 플랫폼이 차량용이나 IoT 장비 등 임베디드 환경을 타겟팅한다면 신뢰성을 확보하기 위해 필수적입니다.
- **적용 방법**: 파이프라인 제어, 행렬 연산, 상태 머신 등 실제 임베디드 코어의 성능을 측정하며, 컴파일 후 가볍게 실행 가능하여 pVM 내부에서 구동하기 매우 편리합니다.

### 1.3 STREAM

- **개요**: 지속적인 메모리 대역폭(Bandwidth)을 측정하는 학계 표준 벤치마크입니다. ACM SAC 2024 논문 등 가상화 논문에서 메모리 오버헤드를 증명할 때 단골로 등장합니다.
- **적용 방법**: Copy, Scale, Add, Triad 4가지 연산을 통해 격리 도메인 전환 시 발생하는 메모리 버스 및 캐시 오버헤드를 측정합니다.

---

## 2. QS-002 (I/O 집약 워크로드) 추천 오픈소스

pVM(Protected VM) 환경에서 I/O는 대개 VirtIO를 통해 Host로 위임(Forwarding)되거나 SWIOTLB(Bounce Buffer)를 거치게 되므로, 트래핑(Trap-and-Emulate) 및 메모리 복사 오버헤드가 가장 크게 발생하는 구간입니다.

### 2.1 fio (Flexible I/O Tester - 블록 I/O 추천)

- **개요**: 리눅스 저장장치 및 VirtIO-Block 성능 검증의 표준 툴입니다.
- **적용 방법**: pVM 내부에 할당된 가상 디스크(VirtIO-blk)에 무작위(Random) 및 순차(Sequential) 읽기/쓰기 부하를 주어, I/O 요청이 Stage-2를 거쳐 호스트로 전달될 때의 IOPS 및 레이턴시를 측정합니다.
- **추천 스크립트 예시 (Random Read/Write)**:

  ```bash
  fio --name=randrw --ioengine=libaio --iodepth=16 --rw=randrw \
      --bs=4k --direct=1 --size=1G --numjobs=4 --runtime=60 --time_based
  ```

### 2.2 iperf3 (네트워크 I/O 추천)

- **개요**: 네트워크 대역폭 및 VirtIO-net 오버헤드를 측정하는 가장 대중적인 툴입니다.
- **적용 방법**: Host(또는 외부 서브넷)에 `iperf3 -s`를 띄우고, pVM 내부에서 `iperf3 -c [IP]`를 실행합니다. VirtIO 네트워크 드라이버가 패킷을 처리할 때 하이퍼바이저 엑싯(Hypervisor Exit)이 얼마나 발생하는지, 대역폭 저하가 목표치(10% 이내)에 들어오는지 측정하기에 가장 적합합니다.

---

## 3. 아키텍트 관점의 현실적인 측정 팁 (Senior 팁)

### 3.1 SWIOTLB (Bounce Buffer) 크기 최적화 점검

pVM 구조에서는 보안상 Host가 Guest의 메모리를 마음대로 읽을 수 없기 때문에, I/O 공유 메모리 영역인 SWIOTLB를 사용하게 됩니다. fio나 iperf3 측정 시 이 버퍼 크기가 작으면 I/O 병목이 발생하여 오버헤드가 10%를 훌쩍 넘길 수 있습니다.

벤치마크 수행 전 커널 파라미터(`swiotlb=...`) 설정을 Native와 pVM에서 최적화한 후 비교해야 공정한 측정이 됩니다.

### 3.2 Hypervisor Exit 카운터 모니터링

단순히 '시간'만 측정하기보다, 벤치마크 도중 호스트 커널에서 `kvm_exit` 이벤트를 `perf` 툴 등으로 함께 모니터링하세요. I/O 오버헤드의 근본 원인이 VirtIO 알림(Notification)으로 인한 EL2 엑싯 횟수 때문인지 아키텍처적으로 증명할 수 있습니다.

---

## 4. 추천 요약 테이블

| 품질 속성 | 측정 대상 | 추천 워크로드 (우선순위 순) | 핵심 측정 지표 |
|---|---|---|---|
| QS-001 | CPU / 메모리 | sysbench, CoreMark, STREAM | Execution Time (sec), Memory Bandwidth (MB/s) |
| QS-002 | I/O (블록/네트워크) | fio (저장장치), iperf3 (네트워크) | IOPS, Latency (ms), Throughput (Gbps) |

---

이 도구들은 Google이 AVF(Android Virtualization Framework)를 개발하고 성능을 메인라인에 보고할 때도 핵심적으로 사용한 툴셋이므로, 과제 평가 위원회나 고객사(OEM) 제출용 근거 자료로 활용하기에 가장 안전하고 확실한 선택입니다.
