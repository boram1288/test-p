# DP-06. HW 장치 할당과 DMA 격리 구조

## 1. 상태

평가 중

## 2. 결정 목적

Camera와 AI 장치의 소유권 구조를 정한다.
DMA 격리 집행 위치를 정한다.
장치 전환과 회수 절차를 정한다.

## 3. 문제 상황

- 선행 DP: DP-03 pVM 생명주기, DP-04 Workload identity/measurement
- 연관 DP: DP-05 pVM 간 보안 데이터 채널
- 요구 해석: R-2의 동시 사용은 FR-04에 따라 물리적 병렬 접근이 아니라 한 시점 한 owner를 유지하는 고속 시분할로 해석한다.
- 범위: upstream pKVM의 DMA/IOMMU 격리는 미구현 상태다. pVIOMMU/EL2 DMA gate는 project-custom PoC 확장과 목표 제품 기능을 구분한다.

Camera와 AI 장치는 DMA를 수행한다.
잘못된 DMA는 다른 pVM memory를 읽을 수 있다.
Host가 장치를 계속 소유하면 frame에 접근할 수 있다.
직접 할당은 장치 공유율을 낮출 수 있다.
장치 reset이 불완전하면 이전 데이터가 남을 수 있다.

## 4. 결정 질문

Host가 scheduling을 담당하고 EL2가 DMA 권한을 집행할 것인가?
아니면 EL2가 장치를 pVM에 배타적으로 직접 할당할 것인가?

## 5. 후보 구조

### 후보 A. Host Scheduling과 EL2 DMA Gate 구조

Host driver가 scheduling과 power management를 담당한다.
pVM은 virtio 또는 RPC로 작업을 요청한다.
EL2가 capability, owner, device ID와 SID를 확인한다.
S2MPU mapping, protected 사용 구간과 revoke는 EL2 gate를 통해서만 바꾼다.
Host는 protected 사용 구간에 S2MPU/MMIO로 우회할 수 없다.

### 후보 B. EL2 집행 직접 할당 구조

장치를 pVM에 배타적으로 할당한다.
EL2가 pVIOMMU domain과 SID를 관리한다.
전환 시 revoke, reset과 reassign을 수행한다.

## 6. 후보별 동작 구조

### 후보 A

```text
pVM request
  -> Host virtual device
  -> Host scheduler/driver
  -> EL2 capability + owner gate
  -> S2MPU protected domain
  -> Camera 또는 AI HW
```

- 실행 위치: driver/scheduler는 Host kernel에, 권한 집행은 EL2/S2MPU에 둔다.
- 제어 흐름: Host가 순서를 요청하고 EL2가 manifest capability와 현재 owner를 대조한다.
- 데이터 흐름: protected 구간의 DMA는 owner pVM domain으로만 제한한다.
- 신뢰 경계: EL2, S2MPU와 reset/sanitize를 신뢰한다. Host driver는 비신뢰다.
- 자원 소유권: Host는 scheduling state를, EL2는 배타적 HW/DMA owner 원장을 가진다.
- 자원 회수: EL2가 revoke와 quiesce를 확인한 뒤 reset/sanitize하고 다음 owner를 승인한다.

### 후보 B

```text
Host assignment request
  -> VFIO boundary
  -> EL2 pVIOMMU policy
  -> pVM DMA domain
  -> Camera 또는 AI HW
```

- 실행 위치: 정책 집행을 EL2에 둔다.
- 제어 흐름: Host는 할당을 요청한다.
- 데이터 흐름: 장치 DMA는 소유 pVM domain으로 제한된다.
- 신뢰 경계: EL2, S2MPU/pVIOMMU와 장치 reset을 신뢰한다.
- 자원 소유권: 한 시점에 하나의 pVM만 장치를 소유한다.
- 자원 회수: EL2 revoke 후 reset하고 Host에 반환한다.

## 7. 품질속성 비교

### 7.1 필수 gate

| Gate | 합격 기준 | 후보 A | 후보 B |
|---|---|---|---|
| SEC-02 권한 전환 | 권한 중첩 0, reset 뒤 잔류 data 노출 0건 | EL2 gate 확인 필요 | break-before-make 확인 필요 |
| SEC-03 DMA 격리 | 비할당 domain DMA 성공 0건 | Host MMIO/S2MPU 우회 차단 필요 | pVIOMMU/SID binding 확인 필요 |
| 실현 가능성 | target SoC와 baseline에서 gate API/reset 확인 | project-custom 범위 확인 필요 | project-custom 범위 확인 필요 |

두 후보 모두 gate를 통과하려면 EL2가 capability 대조, SID/device binding, revoke, quiesce, reset/sanitize와 실패 시 재할당 거부를 집행해야 한다.
Buffer lease state의 정본은 DP-05의 owner-state 표다.
DP-06은 `TRANSFER_PENDING`과 `RETURNING`에서 DMA owner가 없도록 break-before-make를 집행한다.

### 7.2 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.
PERF-04가 전환 지연 p99 10ms를 정의한다.
SEC-02/03의 0건 조건은 별점이 아니라 위 필수 gate다.

| 품질속성 | KPI | 별 1개 | 별 2개 | 별 3개 |
|---|---|---|---|---|
| 보안성 | 10^6회 전환 중 권한 중첩/비인가 DMA 성공 건수 | 2건 이상 | 1건 | 0건 |
| 성능 | 장치 소유권 전환 지연 p99 | 10ms 초과 | 5ms 초과 10ms 이하 | 5ms 이하 |
| 확장성 | 신규 장치 class 추가 시 mediation core 변경량 | 100 LoC 초과 | 1~100 LoC | 0 LoC |
| 변경 용이성 | SoC S2MPU/pVIOMMU 교체 시 수정 module 수 | 4개 이상 | 2~3개 | 1개 이하 |
| 자원 효율 | 장치 유휴 시간 비율 | 20% 초과 | 5% 초과 20% 이하 | 5% 이하 |

IOMMUFD는 I/O address space와 device 연결을 userspace에 제공한다.
DMA domain 연결과 회수 KPI의 근거다.
[Linux IOMMUFD](https://docs.kernel.org/userspace-api/iommufd.html)

pKVM은 Host stage-2와 pVM stage-2를 분리한다.
upstream 문서에서 DMA/IOMMU 격리는 아직 미구현 상태이므로 project-custom gate를 별도로 검증해야 한다.
[Linux pKVM](https://cdn.kernel.org/doc/html/latest/virt/kvm/arm/pkvm.html)

30fps의 frame 주기는 33.3ms다.
전환 목표 10ms는 frame 주기의 약 30%다.

### 7.3 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | ★★★ | Host는 scheduling만 요청하고 EL2가 DMA owner와 mapping을 집행한다. | ★★★ | EL2가 pVM별 DMA domain과 배타 owner를 집행한다. |
| 성능 | ★★ | RPC와 Host scheduling 비용이 있다. | ★★★ | 할당 후에는 장치가 pVM에 직접 연결된다. |
| 확장성 | ★★★ | 기존 Linux driver model을 재사용한다. | ★★ | 장치별 reset과 assignment descriptor가 필요하다. |
| 변경 용이성 | ★★★ | SoC 차이를 Host driver가 흡수한다. | ★★ | EL2 S2MPU/pVIOMMU adapter와 platform 기술이 바뀔 수 있다. |
| 자원 효율 | ★★★ | Host가 여러 client 요청을 연속 scheduling한다. | ★ | 배타 할당 중 다른 client가 장치를 쓰지 못한다. |

## 8. 핵심 트레이드오프

후보 A는 기존 driver scheduling/power 자산을 재사용한다.
대신 Host 요청과 EL2 gate의 계약이 늘고, Host의 직접 MMIO 우회를 차단해야 한다.

후보 B는 Host의 장치 접근을 줄인다.
대신 reset, revoke와 platform별 EL2 통합이 필요하다.

## 9. 검증 기준

- Host와 두 pVM에서 동시 장치 접근을 시도한다.
- 허용 domain 밖 DMA를 반복 주입한다.
- DMA 차단 주소와 SID를 기록한다.
- 권한 회수와 부여 시점을 trace한다.
- domain 중첩 시간을 계산한다.
- 전환 지연 p50, p95와 p99를 측정한다.
- 장치 reset 후 이전 frame marker를 검색한다.
- pVM 종료 후 장치를 다른 pVM에 재할당한다.
- 30fps에서 frame drop 비율을 측정한다.
- Host가 S2MPU/MMIO를 직접 바꾸거나 device/SID/capability를 위조하는 공격을 주입한다.
- 10^6회 전환 동안 `revoke -> quiesce -> reset/sanitize -> assign` 순서와 중첩 0건을 검증한다.
- HW wedge, reset 실패와 이전 owner 무응답 때 다음 owner 부여가 fail-closed인지 확인한다.
- DP-05 owner-state 표의 CPU mapping/DMA owner 조합을 전 상태/전이에서 확인한다.
- upstream baseline과 project-custom pVIOMMU/EL2 변경 범위를 분리 기록한다.

## 10. 검토 결과

사용자 요청에 따라 Claude와 교차 검토했다.
R-2의 동시 사용을 FR-04의 배타적 고속 시분할 의미로 정렬했다.
후보 A의 scheduling은 Host에 두되 DMA 권한 집행은 EL2/S2MPU gate로 이동했다.
target SoC reset/sanitize와 project-custom pVIOMMU 실현 가능성 확인이 남아 있다.

## 11. 최종 결정
