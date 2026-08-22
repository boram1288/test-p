# pKVM PoC 과제 수정사항 및 Architecture Decision Point 분석

## 1. 분석 범위

이 문서는 `../poc-p`에서 공개 오픈소스 기반 코드에 추가된 프로젝트 전용 변경과
`../poc-p/work/src/tools`에 구현된 도구를 함께 분석한 결과다.

분석 대상은 다음과 같다.

- Linux v6.18 기반 `pkvm-linux` 프로젝트 전용 커밋
- QEMU v10.0.0 기반 장치 할당 확장
- kvmtool protected VM 실행 확장
- `work/src/tools`의 VM 관리, 장치 검증, DMA-BUF, 사용자 공간 통신 및 영상 파이프라인
- `docs/PLAN.md`와 Phase 07~10 설계·검증 문서

기존 공개 pKVM 패치 자체보다는 이 과제의 Reference Scenario를 성립시키기 위해 추가하거나
선택한 구조에 초점을 맞춘다.

## 2. 오픈소스 대비 추가된 구현

### 2.1 Linux/pKVM 커널 확장

`pkvm-linux`에는 공개 pKVM 패치 집합 위에 다음 프로젝트 전용 기능이 추가됐다.

#### Protected VM 간 DMA 공유 중재

- Camera pVM이 승인한 page를 AI pVM의 pVIOMMU domain에 매핑한다.
- 허용된 receiver와 SID인지 EL2에서 확인한다.
- 승인되지 않은 receiver의 DMA 접근을 차단한다.
- owner VM 종료 시 mapping과 page reference를 revoke한다.

#### Cross-pVM CPU-visible DMA-BUF lease

- `EXPORT`, `IMPORT`, `RETURN`, `REVOKE`, `LEASE_QUERY`, `EVENT_POLL`, `ID_GET` primitive를
  추가했다.
- Camera pVM의 4 KiB page를 Host stage-2에 매핑하지 않고 AI pVM으로 전달한다.
- AI pVM에는 동일 backing을 가리키는 새로운 local DMA-BUF FD를 생성한다.
- virtual IRQ를 사용해 receiver에 새 transfer를 알린다.
- PMD 크기로 매핑된 실제 Linux guest memory에서 단일 page만 이동할 수 있도록 stage-2 block을
  분할한다.

#### Protected peer metadata message queue

- frame 크기, FOURCC, dimension, plane layout 같은 bounded metadata를 pVM 사이에 전달한다.
- buffer lease와 독립적인 queue 및 lifecycle을 제공한다.
- endpoint policy, queue capacity, duplicate 및 stale message 검사를 EL2에서 수행한다.

#### OP-TEE/FF-A 공존 수정

- Secure Monitor가 없는 E-1 환경에서는 FF-A negotiation을 best-effort로 처리한다.
- OP-TEE가 share handle을 사용하지 않은 경우에도 Host-local FF-A tracking을 회수한다.
- 반복된 `FFA_MEM_SHARE` 과정에서 shared-page state와 handle pool이 누수되는 문제를 수정했다.

#### Linux 6.18 통합 호환성 수정

- Android pKVM 패치가 요구하는 `android_kabi.h`를 보완했다.
- `is_dma_buf_file()` linkage 충돌을 수정했다.
- token이 제거된 EL2 module registration API에 `pkvm-smc`를 맞췄다.
- 더 이상 존재하지 않는 EL2 event registration 호출을 제거했다.

이 확장의 핵심은 EL2가 pVM 간 buffer mapping, receiver authorization, notification, return 및
revoke를 직접 담당한다는 점이다.

### 2.2 QEMU 장치 모델 확장

QEMU v10.0.0에는 다음 프로젝트 전용 변경이 추가됐다.

- QEMU `edu` DMA 장치를 pKVM assignable platform device로 기술
- Camera와 AI 역할에 대응하는 두 개의 독립 장치 생성
- `pkvm,device-assignment` Device Tree descriptor 생성
- 장치 reset 및 pVM 종료 후 재할당 지원
- 두 장치에 독립 MMIO 영역과 virtual SID 부여

구현된 장치 할당 경로는 다음과 같다.

```text
QEMU edu PCI function
  -> pkvm,device-assignment platform descriptor
  -> vfio-platform
  -> VFIO_PKVM_IOMMU container
  -> KVM_DEV_TYPE_VFIO / KVM_DEV_VFIO_PVIOMMU
  -> EL2-managed PV IOMMU domain
  -> Camera 또는 AI pVM
```

Guest가 SMMU page table을 직접 관리하지 않고 EL2가 virtual SID와 pVIOMMU domain을 관리한다.

### 2.3 kvmtool 확장

kvmtool에는 일반 VM 실행 경로를 protected VM 실행기로 연결하는 runtime hook이 추가됐다.

- protected VM 실행 option
- `guest_memfd` 기반 guest memory 구성
- protected VM type 및 per-VM capability 설정
- pKVM guest 실행에 필요한 arm64 초기화 연결

변경량은 작지만 userspace VM framework와 실제 KVM protected VM 실행 경로를 연결하는 adapter다.

### 2.4 pVM 수명주기 관리 프레임워크

`work/src/tools/pvm-framework`에는 C 기반 VM 관리 계층이 구현됐다.

- `pvmd`: 요청 권한, 정책, 이미지 검증과 instance 상태를 관리하는 controller daemon
- `pvm_runner`: VM별 별도 프로세스에서 private KVM backend 실행
- `libpvm`: Application용 create/start/status/stop/delete/list API
- `pvmctl`: 운영 및 검증용 CLI
- role별 Camera/AI instance 관리
- Host 관리자 소유 SHA-256 allowlist 기반 이미지 검증
- 중복 생성, 잘못된 role/path, 이미지 변조 거부
- 한 VM runner 장애가 다른 VM과 daemon으로 전파되지 않는지 검증
- daemon 재시작 시 stale runner 정리
- stop/delete 후 memory, vCPU, FD 및 runner 회수

확정 구조는 `controller daemon + VM별 runner process + private KVM backend`다.

### 2.5 pVM 간 DMA-BUF 전달

`work/src/tools/pvm-buffer`에는 다음이 구현됐다.

- `/dev/pvm-dmabuf` guest kernel driver
- DMA-BUF allocate/export/import/return ioctl
- Camera 및 AI workload
- HVC를 통한 EL2 lease 생성과 event polling
- AI pVM에서 동일 backing을 참조하는 새 local FD 생성
- Camera의 return 대기와 teardown revoke
- Host 접근, 잘못된 receiver 및 stale token에 대한 negative test

Camera의 숫자 FD를 AI에 전달하는 구조가 아니다. Camera driver가 FD를 backing page로 resolve하고,
EL2 transfer object를 거쳐 AI driver가 자신의 FD table에 새로운 FD를 설치한다.

### 2.6 사용자 공간 통신 프로토콜

`work/src/tools/pvm-user-channel`은 신뢰 경계에 따라 통신 구조를 분리한다.

- Host에서 Camera로 전달하는 command: `AF_VSOCK`
- AI에서 Host로 전달하는 result: `AF_VSOCK`
- Camera에서 AI로 전달하는 frame backing: EL2 DMA-BUF lease
- Camera에서 AI로 전달하는 descriptor: 별도 EL2 message queue

프로토콜에는 다음 검증이 포함된다.

- magic, version, header length 및 payload length
- session ID, request ID 및 frame sequence
- role과 VSOCK peer CID 대조
- duplicate, replay 및 stale session 차단
- 최대 4 KiB message 상한
- format, plane, stride, offset 및 size overflow 검증
- descriptor와 buffer를 `transfer_id`로 결합
- descriptor-first와 buffer-first 순서 모두 처리
- 한쪽만 도착한 transfer의 timeout 및 자원 정리
- Host-facing result field와 detection 개수 제한

VSOCK은 Host가 실제 endpoint인 control/result 구간에만 사용한다. raw frame과 descriptor는
Host-facing protocol에 포함하지 않는다.

### 2.7 영상 분석 Reference Scenario

`work/src/tools/vision-pipeline`과 `pvm_vision.c`에는 실물 camera/GPU를 대체하는 결정적 simulator가
구현됐다.

- 공개 MP4 다운로드 및 SHA digest 검증
- 전체 동영상에서 30개 canonical frame 선택
- 32x32 BGR24, 4 KiB zero-padded frame fixture 생성
- OpenVINO 객체 탐지 결과를 detection oracle로 정규화
- Camera pVM의 frame replay
- AI pVM의 frame SHA-256 기반 oracle lookup
- 최대 16개 detection으로 제한된 결과 반환
- class, confidence 및 bounding box 재검증
- 변조 frame, 잘못된 layout, duplicate 및 replay 거부
- 정상 종료와 Camera/AI/Host 장애 주입 검증

이 구현은 실제 camera capture, GPU driver 또는 실제 pVM 내부 inference를 검증하지 않는다.
통신·격리·결과 상관관계를 재현 가능하고 결정적으로 검증하기 위한 대체 구조다.

## 3. 핵심 Architecture Decision Point

기존 D-1~D-11 중 단순 기술 선정이 아니라 후보 구조 간 품질속성 트레이드오프가 명확한 항목을
핵심 Decision Point로 재구성했다.

### DP-1. pVM 수명주기 관리 구조

| 후보 구조 | 장점 | 단점 |
|---|---|---|
| A. Application이 KVM 직접 제어 | 구조와 호출 경로가 단순하고 추가 IPC 지연이 작다. | Application이 KVM에 강하게 결합되고 권한 분리와 장애 격리가 어렵다. |
| B. 단일 daemon 내부에서 모든 VM 실행 | 정책과 상태를 중앙 관리하기 쉽고 프로세스 수가 적다. | 하나의 VM/backend 오류가 daemon과 다른 VM으로 전파될 수 있다. |
| C. controller daemon + VM별 runner | process boundary를 통한 장애 격리, 최소 권한 및 backend 교체성이 우수하다. | IPC, runner 감시와 stale process 정리 때문에 구현과 운영이 복잡하다. |

- 주요 품질속성: 격리성, 보안성, 변경용이성, 성능, 자원 효율
- 트레이드오프: **격리성·변경용이성 향상 대 단순성·자원 효율 저하**
- 채택안: **C. controller daemon + VM별 runner**
- 근거: Application에서 KVM 의존성을 제거하고 VM별 process boundary에서 장애를 격리한다.

### DP-2. pVM 이미지 신뢰성 검증 방식

| 후보 구조 | 장점 | 단점 |
|---|---|---|
| A. 검증 없이 image 실행 | 구현과 배포가 가장 단순하다. | image 변조나 잘못된 workload 실행을 방어할 수 없다. |
| B. Host 관리자 SHA-256 allowlist | 구현 가능성과 결정성, 재현성이 높다. | Host가 침해되면 신뢰가 붕괴하고 rollback/freshness를 보장하지 않는다. |
| C. secure boot + pvmfw 서명·측정 | 강한 trust chain과 attestation으로 확장할 수 있다. | firmware, key lifecycle과 verified boot 통합 비용이 크다. |

- 주요 품질속성: 보안성, 구현가능성, 운영성, 개발기간
- 트레이드오프: **신뢰 강도 향상 대 구현·키 관리 복잡도 증가**
- 채택안: **B. Host 관리자 SHA-256 allowlist**
- 제한: PoC는 Host 관리자와 allowlist manifest를 신뢰하며 rollback을 방어하지 않는다.

### DP-3. pVM 장치 할당 구조

| 후보 구조 | 장점 | 단점 |
|---|---|---|
| A. Host driver + virtio/RPC | 장치 호환성과 운영 편의가 높다. | Host가 데이터 경로에 남아 기밀성이 약해지고 복사가 증가한다. |
| B. `vfio-pci` 실장치 직접 할당 | 실제 장치 대표성과 native 성능 잠재력이 높다. | 현재 pKVM 지원 경로와 대상 하드웨어 성립 여부가 불확실하다. |
| C. `vfio-platform + pVIOMMU + EL2 PV IOMMU` | 배타적 소유권과 DMA 격리를 EL2에서 검증할 수 있다. | pKVM 전용 경로이므로 이식성·표준성이 낮고 구현이 복잡하다. |

- 주요 품질속성: 기밀성, 격리성, 성능, 호환성, 이식성
- 트레이드오프: **기밀성·DMA 격리 향상 대 호환성·이식성 저하**
- 채택안: **C. vfio-platform + pVIOMMU + EL2 PV IOMMU**
- PoC 적용: 실제 장치 대신 QEMU edu DMA 장치 두 개로 경로를 검증한다.

### DP-4. Camera pVM에서 AI pVM으로 frame을 전달하는 구조

| 후보 구조 | 장점 | 단점 |
|---|---|---|
| A. Host shared memory/relay | 구현과 디버깅이 쉽고 기존 IPC를 활용할 수 있다. | Host에 raw frame이 노출되고 복사 비용과 TCB가 증가한다. |
| B. `virtio-vsock` | 표준 socket API와 높은 개발 편의성을 제공한다. | Host backend가 packet을 중계하므로 strict Host-bypass를 만족하지 않는다. |
| C. FF-A VM-to-VM memory sharing | 표준 endpoint와 memory sharing model로 발전할 수 있다. | 현재 pKVM FF-A proxy가 VM-to-VM routing을 제공하지 않아 신규 구현 범위가 크다. |
| D. EL2 전용 DMA-BUF lease | Host 비노출, zero-copy와 EL2 receiver policy를 제공한다. | EL2 TCB와 검증 부담이 증가하고 전용 UAPI 때문에 유지보수성이 낮아진다. |

- 주요 품질속성: 기밀성, 성능, 표준성, 유지보수성, 검증가능성
- 트레이드오프: **기밀성·zero-copy 성능 향상 대 표준성·유지보수성 저하**
- 채택안: **D. EL2 전용 DMA-BUF lease**
- 장기 대안: pKVM이 VM-to-VM FF-A를 지원하면 C로 교체하는 방안을 검토할 수 있다.

### DP-5. Frame backing과 descriptor 전달 구조

| 후보 구조 | 장점 | 단점 |
|---|---|---|
| A. buffer payload에 descriptor 포함 | 하나의 채널만 관리하므로 결합이 단순하다. | data/control lifecycle이 결합되고 parser 오류의 영향 범위가 커진다. |
| B. Host-facing VSOCK으로 descriptor 전달 | 기존 transport와 protocol을 재사용할 수 있다. | Host가 descriptor를 관찰·변조할 수 있어 Host-bypass 경계가 약해진다. |
| C. DMA-BUF와 EL2 metadata queue 분리 | 독립 검증과 lifecycle, 최소 정보 노출 및 장애 격리가 가능하다. | transfer join, 순서 역전, timeout과 양쪽 자원 회수가 복잡하다. |

- 주요 품질속성: 보안성, 모듈성, 장애 격리, 단순성, 지연
- 트레이드오프: **보안성·모듈성 향상 대 상태 관리 복잡도·지연 증가**
- 채택안: **C. DMA-BUF와 EL2 metadata queue 분리**
- 결합 방식: `transfer_id`와 `frame_seq`를 이용해 userspace에서 결합한다.

### DP-6. PoC 검증 환경과 inference 구조

| 후보 구조 | 장점 | 단점 |
|---|---|---|
| A. 실물 USB camera + NVIDIA GPU + 실제 inference | 실제 환경 대표성, 성능과 driver 동작을 검증할 수 있다. | 장비 비용, driver/pKVM 지원, 일정과 재현성 리스크가 크다. |
| B. QEMU 장치 + runtime CPU inference | 일부 실제 inference 경로를 검증할 수 있다. | guest runtime/model 통합 부담이 크고 결과 결정성이 낮아질 수 있다. |
| C. QEMU 장치 + canonical frame/oracle replay | 재현성, 결정성, 자동화와 비용 측면이 우수하다. | 실제 장치·추론·성능 및 model/tensor 기밀성을 검증하지 못한다. |

- 주요 품질속성: 현실성, 대표성, 재현성, 시험가능성, 비용, 일정
- 트레이드오프: **재현성·시험가능성 향상 대 실제 환경 대표성 저하**
- 채택안: **C. QEMU 장치 + canonical frame/oracle replay**
- 제한: 실제 camera/GPU/inference가 검증됐다고 해석해서는 안 된다.

## 4. 보조 Decision Point

다음 항목도 설계 결정이지만 핵심 6개에 비해 아키텍처 구조 또는 품질속성 충돌의 영향이 작다.

| Decision Point | 후보 및 트레이드오프 | 채택안 |
|---|---|---|
| Linux 기준선 | 안정성·장기 유지보수성 대 최신 pKVM 기능 가용성·포팅 비용 | Linux v6.18 LTS |
| 첫 pVM 기능 검증 | selftest/direct ioctl의 원인 격리·단순성 대 범용 VMM의 운용 대표성 | KVM selftest와 직접 ioctl probe |
| 다중 pVM 초기 검증 | 최소 orchestrator의 낮은 의존성 대 production VMM의 기능 완전성 | selftest 기반 최소 orchestrator |
| OP-TEE 통합 환경 | 환경 분리의 결과 해석성 대 환경 수·검증 비용 | QEMU-only E-1과 OP-TEE E-2 분리 |
| Host-facing transport | AF_VSOCK의 표준성·편의성 대 Host 신뢰 최소화 | Host가 endpoint인 구간만 AF_VSOCK 사용 |

## 5. 전체 구조 요약

이 과제의 중심 아키텍처는 다음과 같이 요약할 수 있다.

> Host는 pVM 생성과 control/result 통신에는 관여하지만 민감한 frame 데이터 경로에서는 빠지고,
> EL2가 pVM 간 buffer 소유권, mapping, receiver policy, notification과 회수를 직접 중재한다.

```text
Host Application
  | AF_VSOCK command
  v
Camera pVM
  |-- EL2 DMA-BUF lease: frame backing ---------+
  +-- EL2 message queue: frame descriptor ------+--> AI pVM
                                                    |
                                                    | AF_VSOCK bounded result
                                                    v
                                              Host Application
```

따라서 이 과제에서 발표 우선순위가 높은 Decision Point는 다음 여섯 가지다.

1. VM 관리의 process boundary
2. pVM image trust chain 수준
3. protected device assignment 경로
4. cross-pVM frame transport
5. buffer와 metadata channel의 분리 여부
6. 실물 장치·실제 inference와 fixture 기반 검증 환경 사이의 선택

특히 DP-4는 기밀성과 zero-copy를 얻는 대신 EL2 TCB와 전용 구현 복잡도를 증가시키는 선택으로,
이 과제의 가장 핵심적인 Architecture Decision Point다.

## 6. 참고 경로

- `../poc-p/docs/PLAN.md`
- `../poc-p/docs/phase-07/userspace-vm-framework-design.md`
- `../poc-p/docs/phase-08/README.md`
- `../poc-p/docs/phase-09/el2-dmabuf-channel-design.md`
- `../poc-p/docs/phase-09-b/README.md`
- `../poc-p/docs/phase-10/README.md`
- `../poc-p/work/src/pkvm-linux`
- `../poc-p/work/src/qemu-phase08`
- `../poc-p/work/src/kvmtool`
- `../poc-p/work/src/tools/pvm-framework`
- `../poc-p/work/src/tools/pvm-buffer`
- `../poc-p/work/src/tools/pvm-user-channel`
- `../poc-p/work/src/tools/vision-pipeline`
