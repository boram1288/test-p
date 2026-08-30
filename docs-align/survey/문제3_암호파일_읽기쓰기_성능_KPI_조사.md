# 문제 3 암호파일 읽기·쓰기 성능 KPI 조사

- 작성일: 2026-08-30
- 조사 범위: Baremetal과 VM 환경의 일반파일·암호파일 읽기/쓰기 성능
- 적용 대상: pVM에서 GP TEE Client API를 통해 암호파일을 저장·복원하는 구조

## 1. 결론

읽기·쓰기 속도는 문제 3의 연속형 KPI로 사용할 수 있다. 다만 단일 MB/s만 사용하면
캐시, 큐 깊이, 파일 크기, 쓰기 완료 기준 등의 차이로 결과가 왜곡될 수 있으므로 다음과
같이 정의하는 것이 적절하다.

1. Baremetal/VM과 일반파일/암호파일을 조합한 2×2 조건에서 동일 워크로드를 측정한다.
2. 절대 성능과 함께 Baremetal 대비 성능 보존율을 사용한다.
3. 읽기와 쓰기는 별도 KPI로 관리한다.
4. 순차 처리량, 랜덤 IOPS, 꼬리 지연, CPU 비용을 함께 관찰한다.
5. 보안·무결성·복구 성공 여부는 Gate로, 읽기·쓰기 성능은 연속형 KPI로 분리한다.

문제 3의 대표 연속형 KPI는 다음과 같이 제안한다.

> **암호파일 I/O 성능 보존율(%) = VM 암호파일 성능 / Baremetal 암호파일 성능 × 100**

읽기 성능 보존율과 쓰기 성능 보존율은 반드시 별도로 산출한다.

## 2. 문제 정의와 설계 고려사항

### 2.1 문제 정의

> ✓ pVM에서 대용량 암호파일을 처리할 경우 Secure OS 암·복호화 및 공유 메모리 전달과
> virtio-blk 저장 경로가 중첩되어, Baremetal 대비 읽기·쓰기 성능이 저하될 수 있음

이 문제 정의는 단순히 “VM이 느릴 수 있다”는 의미가 아니다. 암호화 비용과 가상화 I/O
비용이 결합될 때 각 비용을 독립적으로 측정한 결과보다 추가적인 성능 저하가 발생할 수
있다는 점까지 포함한다.

### 2.2 설계 고려사항

- **Gate 고려사항 — 보안·정합성:** 암호파일의 기밀성·무결성과 최신 버전 복구가 모든
  오류 및 재생성 조건에서 보장되어야 한다.
- **연속형 KPI 고려사항 — 성능:** pVM 암호파일의 읽기·쓰기 처리량을 Baremetal 암호화
  경로 대비 최대한 유지해야 한다.

Gate는 충족/미충족으로 판정하고, 성능은 연속적인 보존율과 지연으로 설계 대안을
비교한다. 성능 KPI가 높더라도 보안·정합성 Gate를 통과하지 못한 대안은 채택할 수 없다.

## 3. 2×2 비교 모델

| 환경 | 일반파일 | 암호파일 |
|---|---|---|
| Baremetal | **BM-P**: App → FS → UFS | **BM-E**: App → GP API/TEE → FS → UFS |
| VM | **VM-P**: pVM App → Guest FS → virtio-blk → UFS | **VM-E**: pVM App → GP API/TEE → Guest FS → virtio-blk → UFS |

네 조건은 다음 항목을 동일하게 유지해야 한다.

- 파일 크기, 데이터 내용, 접근 패턴, 블록 크기, 동시성 및 큐 깊이
- 암호 알고리즘, 키 크기, 청크 크기, 무결성 메타데이터 정책
- 파일시스템, 마운트 옵션, 저장장치 상태 및 여유 공간
- CPU 주파수 정책, 코어 수, 메모리 크기, 하드웨어 암호 가속
- 쓰기 완료의 의미: write 완료, fsync 완료, 최신 버전/RPMB commit 완료

프로젝트의 암호화가 GP API/TEE를 통한 애플리케이션 암호화라면 BM-E와 VM-E는 반드시
실제 암·복호화 API를 통과해야 한다. 미리 생성한 ciphertext 파일을 fio로 읽고 쓰는
시험은 저장장치 I/O만 측정하며 암·복호화 성능을 측정하지 못한다.

fscrypt, dm-crypt/LUKS, QEMU image encryption을 사용하는 경우에는 각 방식이 암호화를
수행하는 계층이 다르므로 별도 하위 시험으로 분리한다. 서로 다른 암호화 계층의 결과를
하나의 KPI로 합치지 않는다.

### 3.1 VM 환경의 일반파일·암호파일 Read/Write 흐름

virtio-blk frontend는 VM 내부, backend는 VM 외부의 저장장치 처리 영역에 위치한다고
가정한다. Read는 요청 전달과 데이터 반환 방향을 나누어 표현한다.

| 파일·동작 | 처리 순서 |
|---|---|
| 일반파일 Write | Workload → VFS → virtio-blk(frontend) → EL2 → virtio-blk(backend) → 저장장치 |
| 일반파일 Read 요청 | Workload → VFS → virtio-blk(frontend) → EL2 → virtio-blk(backend) → 저장장치 |
| 일반파일 Read 반환 | 저장장치 → virtio-blk(backend) → EL2 → virtio-blk(frontend) → VFS → Workload |
| 암호파일 Write | Workload(평문) → VFS → 암호화 → virtio-blk(frontend) → EL2 → virtio-blk(backend) → 저장장치(암호문) |
| 암호파일 Read 요청 | Workload → VFS → 암·복호화 모듈 → virtio-blk(frontend) → EL2 → virtio-blk(backend) → 저장장치 |
| 암호파일 Read 반환 | 저장장치(암호문) → virtio-blk(backend) → EL2 → virtio-blk(frontend) → 복호화 → VFS → Workload(평문) |

핵심 차이는 암호파일 경로에 암·복호화 단계가 추가된다는 점이다. Write에서는 평문을
암호화한 뒤 backend로 전달하고, Read에서는 backend가 반환한 암호문을 복호화한 뒤
Workload에 전달한다. 따라서 Read/Write KPI는 Workload 관점의 전체 구간을 측정해야
암·복호화와 EL2·virtio-blk 전환 비용을 모두 반영할 수 있다.

## 4. KPI 정의

워크로드별 읽기 또는 쓰기 성능을 다음과 같이 정의한다.

- B(BM-P): Baremetal 일반파일 성능
- B(BM-E): Baremetal 암호파일 성능
- B(VM-P): VM 일반파일 성능
- B(VM-E): VM 암호파일 성능

성능 B에는 워크로드에 따라 MiB/s 또는 IOPS를 사용한다.

### 4.1 1차 KPI

**암호파일 VM 성능 보존율**

R(virt, enc) = B(VM-E) / B(BM-E) × 100

- 읽기와 쓰기를 각각 산출한다.
- pVM을 도입했을 때 기존 Baremetal 암호화 경로의 성능을 얼마나 유지하는지 직접
  보여주므로 문제 3의 대표 KPI로 적합하다.

### 4.2 원인 분해용 KPI

| KPI | 산식 | 의미 |
|---|---|---|
| Baremetal 암호화 보존율 | B(BM-E) / B(BM-P) × 100 | Baremetal에서 암호화 자체의 비용 |
| VM 암호화 보존율 | B(VM-E) / B(VM-P) × 100 | VM 내부에서 암호화 자체의 비용 |
| 일반파일 VM 보존율 | B(VM-P) / B(BM-P) × 100 | 일반파일 경로의 가상화 비용 |
| 암호파일 VM 보존율 | B(VM-E) / B(BM-E) × 100 | 암호화된 상태에서의 가상화 비용 |
| 총 성능 보존율 | B(VM-E) / B(BM-P) × 100 | 최상의 기준 대비 최종 사용자 경로 성능 |

### 4.3 VM×암호화 상호작용 지표

I = {B(VM-E) × B(BM-P)} / {B(VM-P) × B(BM-E)}

- I = 1: 곱셈 척도에서 가상화와 암호화 비용 사이에 추가 상호작용이 없음
- I < 1: 두 경로가 결합되면서 별도의 추가 손실이 발생
- I > 1: 결합 경로에서 batching, cache 또는 가속 효과가 나타났을 가능성이 있음

I가 1에서 벗어났다고 바로 설계 결론을 내리기보다 CPU 포화, 메모리 복사, TEE 호출
횟수, virtio queue, 캐시 조건을 추가로 확인해야 한다.

### 4.4 지연 및 효율 KPI

처리량만으로는 작은 파일, 동기 쓰기, 복구 메타데이터 갱신의 품질을 설명하기 어렵다.
다음을 보조 KPI로 함께 관리한다.

- p50, p95, p99 및 필요 시 p99.9 요청 지연
- 지연 증가율 = 대상 조건 지연 / 기준 조건 지연
- Latency SLO를 만족하는 최대 처리량(Rate@SLO)
- CPU-seconds/GiB 또는 백만 I/O당 CPU-seconds
- 실행 간 변동계수와 I/O 오류율

## 5. 권장 워크로드

| 사용 시나리오 | 접근 패턴 | 블록 크기 예시 | 1차 지표 | 보조 지표 |
|---|---|---:|---|---|
| 모델·대형 자산 로딩 | 순차 읽기 | 128 KiB, 1 MiB | MiB/s | p99, CPU-seconds/GiB |
| 대형 암호파일 저장 | 순차 쓰기 | 128 KiB, 1 MiB | Durable MiB/s | commit p99, CPU-seconds/GiB |
| 설정·보안 상태 조회 | 랜덤 읽기 | 4 KiB | IOPS | p99/p99.9 |
| 메타데이터·작은 상태 갱신 | 랜덤 쓰기 | 4 KiB | Durable IOPS | fsync p99 |
| 운영 대표 부하 | 실제 R/W·크기·fsync 분포 | 실측값 | Rate@SLO | CPU 비용, 오류율 |

4 KiB와 64 KiB 등의 표준 anchor는 비교 가능성을 위해 사용할 수 있지만, 최종 KPI에는
실제 workload의 파일 크기와 접근 패턴을 반드시 포함한다. 큐 깊이는 QD1과 운영 최대
범위까지 단계적으로 측정한다.

- QD1: 단일 요청에 발생하는 암호화·가상화 지연 확인
- QD sweep: 병렬 처리 능력과 포화점 확인
- Total OIO = numjobs × iodepth
- 네 조건에서 thread 수와 실제 도달 queue depth를 동일하게 유지

## 6. 쓰기 완료 기준

쓰기 속도는 완료 시점에 따라 의미가 크게 달라진다.

| 구분 | 측정 종료 시점 | 용도 |
|---|---|---|
| ACK throughput | write 호출이 반환되는 시점 | 애플리케이션이 체감하는 비동기 입력 속도 |
| Durable throughput | FLUSH/FUA 또는 fsync와 최신 버전·root hash·RPMB commit이 끝난 시점 | 장애 후 복구 가능한 실제 저장 성능 |

문제 3은 재생성 및 최신 암호파일 복구를 다루므로 **Durable write**를 대표 쓰기 KPI로
사용하는 것이 타당하다. direct I/O만으로 전원 장애 시 영속성이 보장된다고 간주하지
않으며, 실제 설계의 fsync·flush·commit 절차를 시험에 포함한다.

## 7. 시험 방법 및 통제 조건

### 7.1 측정 도구

- 일반파일 또는 투명 암호화(fscrypt, dm-crypt) 경로: fio 사용 가능
- GP API/TEE를 통한 애플리케이션 암호화 경로: 실제 API를 호출하는 전용 benchmark
  harness 사용
- fio 사용 시 JSON과 latency histogram을 보존해 percentile과 신뢰구간을 재계산
- cryptsetup benchmark는 메모리 내 암호 primitive 성능을 측정하므로 저장장치 KPI의
  대체 수단으로 사용하지 않음

### 7.2 캐시 및 이미지 형식

- 저장장치 자체의 성능 비교는 direct=1을 1차 조건으로 사용
- QEMU cache mode는 동일하게 유지하고, 저장장치 비교에는 일반적으로 cache=none 사용
- raw와 qcow2, preallocated와 sparse image 결과를 혼합하지 않음
- buffered I/O는 cold와 warm 조건을 분리하고 guest와 host page cache를 모두 통제
- working set을 메모리보다 크게 하거나 실제 block I/O 발생 여부를 계측
- 0으로 채운 데이터 대신 비압축성 데이터를 사용해 압축·dedupe 최적화를 방지

### 7.3 시스템 조건

- Baremetal과 VM에 동등한 CPU·메모리 자원을 할당
- CPU affinity, governor, NUMA 배치, background load를 고정
- VM에 Baremetal과 동일한 AES 등 CPU 기능이 노출되는지 확인
- virtio controller, queue 수, IOThread, cache/AIO 설정을 기록
- 파일시스템, scheduler, mount 옵션, free-space, firmware, 온도 조건을 고정
- TEE shared-memory 크기, 암호화 청크 크기, API 호출 횟수와 복사 횟수를 기록

### 7.4 반복과 정상상태

- 장치를 사전 조건화한 뒤 정상상태에서 측정
- 네 조건의 실행 순서를 반복마다 무작위화하거나 Latin-square로 배치
- 동일 host/device/time block 안에서 paired run 수행
- 중앙값뿐 아니라 신뢰구간과 실행 간 변동을 보고
- 정상상태 미도달, thermal throttling, CPU steal, 외부 I/O 간섭이 발생한 실행은
  사전에 정한 무효 기준에 따라 처리

논문의 결과값을 그대로 합격 기준으로 사용하지 않는다. Pilot에서 paired ratio의
분산을 확인한 뒤 필요한 반복 횟수와 검출할 최소 실질 차이를 결정한다.

## 8. 목표값 설정 방법

절대 목표는 제품 요구사항에서 역산한다.

- 최소 읽기 처리량 = 최대 암호파일 크기 / 허용 로딩 시간
- 최소 durable 쓰기 처리량 = 최대 저장 상태 크기 / 허용 commit 시간
- 최대 p99 지연 = 사용자 또는 상위 서비스가 허용하는 응답 시간
- 최소 성능 보존율 = Baremetal 대비 허용 가능한 추가 처리 시간과 CPU/TCO에서 산정

초기에는 보존율 자체를 연속형 비교 지표로 사용하고, Pilot과 제품 SLO가 확보된 뒤
다음과 같이 판정 구간을 둘 수 있다.

- Green: 보존율의 단측 신뢰구간 하한이 최소 요구값 이상
- Red: 보존율의 신뢰구간 상한이 최소 요구값 미만
- Amber: 신뢰구간이 요구값과 겹침 — 반복 확대 또는 병목 분석 필요

보안 활성화, 데이터 무결성, 최신 버전 복구, I/O 오류 없음은 수치 성능으로 상쇄할 수
없는 별도 hard Gate로 유지한다.

## 9. 웹·논문·사례 조사 결과

### 9.1 표준 및 공식 문서

| 자료 | 확인 내용 | 본 설계에 주는 시사점 |
|---|---|---|
| [Android 16 CDD](https://source.android.com/docs/compatibility/16/android-16-cdd) | Android 호환성 요구사항은 정해진 파일 크기와 버퍼 크기로 순차·랜덤 읽기/쓰기 성능을 정량화한다. | 읽기·쓰기 속도가 공식 품질 KPI가 될 수 있다는 선례다. CDD 수치는 최소 호환성 기준이므로 본 시스템 목표로 그대로 사용하지 않는다. |
| [fio 공식 문서](https://fio.readthedocs.io/en/master/fio_doc.html) | direct I/O, iodepth, latency percentile, fsync·fdatasync·end_fsync, steady-state 설정을 제공한다. | 동일한 I/O 의미와 내구성 조건을 명시해야 결과를 비교할 수 있다. |
| [SNIA SSS PTS 2.0.2](https://www.snia.org/sites/default/files/2025-02/SNIA-SSS-PTS-2.0.2.pdf) | workload anchor, preconditioning, steady-state 판정 방법을 정의한다. | 4개 조건 모두 같은 사전 조건과 정상상태 기준을 적용한다. |
| [GlobalPlatform TEE Client API v1.0](https://globalplatform.org/wp-content/uploads/2010/07/TEE_Client_API_Specification-V1.0.pdf) | Shared Memory 구현은 zero-copy를 시도할 수 있지만 구현 조건에 따라 복사가 발생할 수 있다. | TEE 호출 수, 청크 크기, shared-memory 복사 횟수가 성능 병목인지 계측한다. |
| [Linux dm-crypt 문서](https://docs.kernel.org/admin-guide/device-mapper/dm-crypt.html) | workqueue, same_cpu_crypt, high_priority 등의 옵션이 I/O 처리 방식에 영향을 준다. | 암호화 설정을 시험 조건으로 고정하고 결과와 함께 기록한다. |
| [Android File-Based Encryption](https://source.android.com/docs/security/features/encryption/file-based) | 하드웨어 AES 가속과 inline encryption은 성능 및 전력 효율에 중요하다. | Baremetal과 VM에서 동일한 암호 가속 경로가 사용되는지 확인한다. |
| [QEMU virtio-blk/scsi 가이드](https://www.qemu.org/2021/01/19/virtio-blk-scsi-configuration/) | virtio-blk는 비교적 얇은 I/O stack으로 성능 중심 구성에 적합하다. | VM 시험의 virtual controller를 고정하고 운영 구성과 일치시킨다. |
| [QEMU IOThread 문서](https://www.qemu.org/docs/master/devel/multiple-iothreads.html) | IOThread는 main loop 경합을 줄여 지연과 jitter를 개선할 수 있다. | IOThread와 queue 구성을 숨은 변수로 두지 않는다. |
| [QEMU disk image 문서](https://www.qemu.org/docs/master/system/images) | image format과 image-level encryption은 I/O 경로와 기능이 다르다. | raw/qcow2와 guest/host 암호화 결과를 구분한다. |
| [OP-TEE Secure Storage](https://optee.readthedocs.io/en/3.13.0/architecture/secure_storage.html) | REE FS 기반 secure storage는 암호화와 여러 RPC를 거쳐 데이터를 저장한다. | 대형 파일 경로에서는 RPC 및 메타데이터 commit 비용을 별도로 확인한다. |

### 9.2 학술 연구 및 사례

| 연구·사례 | 관찰 결과 | 해석 및 한계 |
|---|---|---|
| [Daoud & Huen, Performance Study of Software-based Encrypting Data at Rest, 2022](https://www.easychair.org/publications/download/GHB6) | dm-crypt AES-XTS와 NVMe를 사용한 4 KiB random/QD64 시험에서 70/30 혼합 처리량은 33%, random write는 50% 감소했다. QD1 평균 지연도 증가했으며 CPU 사용량은 조건에 따라 크게 늘었다. | 암호화 영향은 read/write, queue depth, CPU 포화에 따라 다르므로 처리량과 지연·CPU를 함께 봐야 한다. 단일 서버 결과이므로 수치를 범용 임계값으로 사용하지 않는다. |
| [Bunker: A Privacy-Oriented Platform for Network Tracing, NSDI 2009](https://www.usenix.org/legacy/events/nsdi09/tech/full_papers/miklas/miklas_html/index.html) | 지속 무손실 쓰기 사례에서 BM 일반 925 Mbps, VM 일반 925 Mbps, BM 암호 817 Mbps, VM 암호 618 Mbps를 보였다. 이 값의 상호작용 계수는 약 0.756이다. | VM과 암호화가 결합될 때 추가 손실이 발생할 수 있다는 2×2 사례다. 구형 Xen·CPU와 입력 상한이 있는 workload이므로 목표값으로 사용하지 않는다. |
| [Rethinking Block Storage Encryption with Virtual Disks, HotStorage 2022](https://www.hotstorage.org/2022/camera-ready/hotstorage22-56/pdf/hotstorage22-56.pdf) | Ceph RBD와 fio를 사용해 4 KiB~4 MiB random I/O와 QD 변화를 반복 측정했다. 제안 방식은 비교 암호화 baseline 대비 읽기 차이를 작게 유지했고 쓰기는 I/O 크기에 따라 손실 폭이 달랐다. | I/O 크기와 queue depth별로 암호화 가상 디스크를 평가해야 한다. 논문의 기준은 plaintext가 아니라 암호화 baseline이므로 해석에 주의한다. |
| [UVBond, UCC 2018](https://www.ksl.ci.kyutech.ac.jp/papers/2018/inokuchi-ucc2018.pdf) | Xen VM에서 guest dm-crypt와 hypervisor 암호화를 비교했으며, AES-NI 사용 여부에 따라 손실 폭이 크게 달라졌다. | AES 가속 노출 여부를 BM/VM 조건에서 반드시 고정해야 한다. 구형 HDD/Xen 및 AES 모드의 한계로 절대 수치는 재사용하지 않는다. |
| [Cryptographic File Systems Performance, 2003](https://www.filesystems.org/docs/nc-perf/perf.pdf) | raw cipher 차이가 실제 filesystem workload에서는 I/O와 VFS에 가려졌으며 sparse allocation과 비동기 쓰기 때문에 결과가 역전되기도 했다. | 암호 primitive benchmark만으로 파일 KPI를 대신할 수 없고, cache·allocation·durability 의미를 일치시켜야 한다. |
| [Cloud Storage Cost Modeling for Cryptographic File Systems, 2017](https://repositorio.pucrs.br/dspace/bitstream/10923/23199/2/Cloud_Storage_Cost_Modeling_for_Cryptographic_File_Systems.pdf) | VM에서 데이터 크기가 메모리보다 작을 때 캐시로 처리량이 크게 증가했고 암호화 비용은 CPU·메모리·I/O에 따라 변했다. | working-set/RAM 비율과 CPU 비용을 KPI 시험 조건에 포함한다. |
| [TrustZone Performance, 2019](https://arxiv.org/pdf/1906.09799) | 특정 Raspberry Pi 3B 환경에서 REE↔TEE 전환과 secure storage 작업에 측정 가능한 지연이 발생했다. | 수치를 일반화하지 않고, 호출 횟수와 암호화 청크 크기를 줄이는 설계 근거로 사용한다. |
| [I/O Virtualization Bottlenecks, 2010](https://www.jeffshafer.com/publications/papers/shafer-wiov2010.pdf) | virtual controller, raw/sparse image, cache 및 동기 I/O 특성에 따라 VM I/O 차이가 크게 달라졌다. | “VM”이라는 조건만으로 비교할 수 없으며 virtio, image, cache, AIO 설정을 모두 명시해야 한다. |

## 10. 슬라이드용 최종 문안

### 문제 정의

> ✓ pVM에서 대용량 암호파일을 처리할 경우 Secure OS 암·복호화·공유 메모리 전달과
> virtio-blk 경로가 중첩되어, Baremetal 대비 읽기·쓰기 성능이 저하될 수 있음

### Gate 설계 고려사항

> ✓ 암호파일의 기밀성·무결성과 최신 버전 복구가 모든 오류 및 재생성 조건에서
> 보장되어야 함

### 연속형 KPI 설계 고려사항

> ✓ pVM 암호파일의 읽기·쓰기 처리량을 Baremetal 암호화 경로 대비 최대한 유지해야 함

### 대표 KPI

> **암호파일 읽기 성능 보존율(%) = VM 암호파일 읽기 속도 / Baremetal 암호파일 읽기
> 속도 × 100**

> **암호파일 쓰기 성능 보존율(%) = VM 암호파일 durable 쓰기 속도 / Baremetal
> 암호파일 durable 쓰기 속도 × 100**

두 KPI는 원인 분석용 2×2 측정값과 함께 제시한다. 슬라이드 공간이 제한되면 대표
KPI에는 보존율 두 개만 노출하고, 상세 시험표에 절대 MiB/s·IOPS·p99·CPU 비용을
배치한다.

## 11. 최종 제안

문제 3에서는 “읽기·쓰기 속도가 빠른가”보다 **“동일한 암호화 보안 수준과 내구성
조건에서 pVM이 Baremetal 성능을 얼마나 보존하는가”**를 평가해야 한다. 따라서 다음
구조가 가장 명확하다.

- Gate: 기밀성, 무결성, 최신 버전 복구, 오류 없는 I/O
- 1차 연속형 KPI: VM-E / BM-E 읽기 및 durable 쓰기 성능 보존율
- 진단 KPI: BM-E / BM-P, VM-P / BM-P, VM-E / VM-P, 상호작용 계수
- 품질 보조 KPI: p99 지연, Rate@SLO, CPU-seconds/GiB, 반복 변동성

이 구조는 보안 요구를 성능으로 상쇄하지 않으면서도, 설계 대안 간 품질 차이를
연속적인 수치로 비교할 수 있게 한다.
