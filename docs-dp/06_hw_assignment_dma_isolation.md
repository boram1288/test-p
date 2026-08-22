# DP-06. HW 장치 할당과 DMA 격리 구조

## 1. 상태

도출

## 2. 결정 목적

Camera와 AI 장치의 소유권 구조를 정한다.
DMA 격리 집행 위치를 정한다.
장치 전환과 회수 절차를 정한다.

## 3. 문제 상황

Camera와 AI 장치는 DMA를 수행한다.
잘못된 DMA는 다른 pVM memory를 읽을 수 있다.
Host가 장치를 계속 소유하면 frame에 접근할 수 있다.
직접 할당은 장치 공유율을 낮출 수 있다.
장치 reset이 불완전하면 이전 데이터가 남을 수 있다.

## 4. 결정 질문

Host driver가 장치를 소유하고 요청을 중재할 것인가?
아니면 EL2가 장치를 pVM에 배타적으로 직접 할당할 것인가?

## 5. 후보 구조

### 후보 A. Host Driver 중재 구조

Host driver가 장치를 계속 소유한다.
pVM은 virtio 또는 RPC로 작업을 요청한다.
Host가 DMA buffer와 scheduling을 관리한다.

### 후보 B. EL2 집행 직접 할당 구조

장치를 pVM에 배타적으로 할당한다.
EL2가 pVIOMMU domain과 SID를 관리한다.
전환 시 revoke, reset과 reassign을 수행한다.

## 6. 후보별 동작 구조

### 후보 A

```text
pVM request
  -> Host virtual device
  -> Host driver
  -> Host IOMMU domain
  -> Camera 또는 AI HW
```

- 실행 위치: driver와 scheduler를 Host kernel에 둔다.
- 제어 흐름: Host가 모든 요청 순서를 정한다.
- 데이터 흐름: Host가 DMA descriptor와 buffer를 관리한다.
- 신뢰 경계: Host driver가 frame 보호 경계에 포함된다.
- 자원 소유권: Host가 장치를 계속 소유한다.
- 자원 회수: Host driver가 queue와 buffer를 정리한다.

### 후보 B

```text
Host assignment request
  -> VFIO boundary
  -> EL2 pVIOMMU policy
  -> pVM IOMMU domain
  -> Camera 또는 AI HW
```

- 실행 위치: 정책 집행을 EL2에 둔다.
- 제어 흐름: Host는 할당을 요청한다.
- 데이터 흐름: 장치 DMA는 소유 pVM domain으로 제한된다.
- 신뢰 경계: EL2, SMMU와 장치 reset을 신뢰한다.
- 자원 소유권: 한 시점에 하나의 pVM만 장치를 소유한다.
- 자원 회수: EL2 revoke 후 reset하고 Host에 반환한다.

## 7. 품질속성 비교

### 7.1 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.

| 품질속성 | KPI | 별 1개 | 별 2개 | 별 3개 |
|---|---|---|---|---|
| 보안성 | 권한 전환 중 DMA domain 중첩 시간 p99 | 1ms 초과 | 0ns 초과 1ms 이하 | 0ns |
| 성능 | 장치 소유권 전환 지연 p99 | 10ms 초과 | 5ms 초과 10ms 이하 | 5ms 이하 |
| 확장성 | 신규 장치 class 추가 시 mediation core 변경량 | 100 LoC 초과 | 1~100 LoC | 0 LoC |
| 변경 용이성 | SoC IOMMU 교체 시 수정 module 수 | 4개 이상 | 2~3개 | 1개 이하 |
| 자원 효율 | 장치 유휴 시간 비율 | 20% 초과 | 5% 초과 20% 이하 | 5% 이하 |

IOMMUFD는 I/O address space와 device 연결을 userspace에 제공한다.
DMA domain 연결과 회수 KPI의 근거다.
[Linux IOMMUFD](https://docs.kernel.org/userspace-api/iommufd.html)

pKVM은 Host stage-2와 pVM stage-2를 분리한다.
DMA 보호도 CPU mapping과 별도로 검증해야 한다.
[Linux pKVM](https://cdn.kernel.org/doc/html/latest/virt/kvm/arm/pkvm.html)

30fps의 frame 주기는 33.3ms다.
전환 목표 10ms는 frame 주기의 약 30%다.

### 7.2 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | ★ | Host driver가 DMA buffer와 descriptor를 볼 수 있다. | ★★★ | EL2가 pVM별 DMA domain을 집행한다. |
| 성능 | ★★ | RPC와 Host scheduling 비용이 있다. | ★★★ | 할당 후에는 장치가 pVM에 직접 연결된다. |
| 확장성 | ★★★ | 기존 Linux driver model을 재사용한다. | ★★ | 장치별 reset과 assignment descriptor가 필요하다. |
| 변경 용이성 | ★★★ | SoC 차이를 Host driver가 흡수한다. | ★★ | EL2 IOMMU adapter와 platform 기술이 바뀔 수 있다. |
| 자원 효율 | ★★★ | Host가 여러 client 요청을 연속 scheduling한다. | ★ | 배타 할당 중 다른 client가 장치를 쓰지 못한다. |

## 8. 핵심 트레이드오프

후보 A는 장치 공유율과 driver 호환성을 높인다.
대신 Host가 DMA 데이터 경로에 남는다.

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

## 10. 검토 결과

검토 전이다.

## 11. 최종 결정

