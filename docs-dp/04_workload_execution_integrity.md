# DP-04. Workload 실행과 무결성 검증 구조

## 1. 상태

도출

## 2. 결정 목적

Workload 검증 주체를 정한다.
검증 시점을 정한다.
검증 결과와 실제 실행 image를 결합한다.

## 3. 문제 상황

Workload image는 Host storage에 있다.
Host는 image를 변경할 수 있다.
Host가 검증도 담당하면 검증을 우회할 수 있다.
검증 후 적재 전에 image가 바뀔 수도 있다.
신규 Workload는 공통 형식으로 탑재해야 한다.

## 4. 결정 질문

Host Manager가 image digest를 검증할 것인가?
아니면 protected loader가 서명된 package를 최종 검증할 것인가?

## 5. 후보 구조

### 후보 A. Host 사전 검증 구조

Host Manager가 SHA-256 digest를 계산한다.
관리자 allowlist와 digest를 비교한다.
일치한 image만 pVM에 적재한다.

### 후보 B. Protected Loader 최종 검증 구조

최소 loader를 protected boot chain에 포함한다.
Loader가 signed manifest를 검증한다.
Loader가 payload를 검증한 뒤 실행한다.

## 6. 후보별 동작 구조

### 후보 A

```text
Host storage
  -> Host Manager: SHA-256 계산
  -> Host allowlist 대조
  -> pVM memory 적재
  -> Workload 실행
```

- 실행 위치: 검증기를 Host userspace에 둔다.
- 제어 흐름: Manager가 검증과 실행 허가를 함께 수행한다.
- 데이터 흐름: image byte가 Host에서 pVM으로 이동한다.
- 신뢰 주체: Host 관리자와 allowlist를 신뢰한다.
- 비신뢰 주체: 일반 Host process를 비신뢰로 둔다.
- 자원 소유권: Manager가 image FD와 VM FD를 소유한다.

### 후보 B

```text
Host storage
  -> signed package 전달
  -> protected Loader
       -> manifest signature 검증
       -> payload digest 검증
       -> Workload 실행
```

- 실행 위치: 최종 검증기를 pVM 내부에 둔다.
- 제어 흐름: Loader만 payload 실행을 승인한다.
- 데이터 흐름: package는 Host를 지나지만 검증 전에는 실행하지 않는다.
- 신뢰 주체: loader, public key와 protected boot chain을 신뢰한다.
- 비신뢰 주체: Host storage와 Host loader를 비신뢰로 둔다.
- 자원 소유권: pVM이 검증된 payload memory를 소유한다.

## 7. 품질속성 비교

### 7.1 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.

| 품질속성 | KPI | 별 1개 | 별 2개 | 별 3개 |
|---|---|---|---|---|
| 보안성 | 변조 corpus 탐지율 | 99% 미만 | 99% 이상 99.999% 미만 | 99.999% 이상 |
| 성능 | 검증으로 추가되는 start p99 | 500ms 초과 | 100ms 초과 500ms 이하 | 100ms 이하 |
| 확장성 | 신규 Workload 추가 시 core 변경량 | 100 LoC 초과 | 1~100 LoC | 0 LoC |
| 변경 용이성 | signing algorithm 교체 시 수정 module 수 | 4개 이상 | 2~3개 | 1개 이하 |
| 자원 효율 | 검증 중 peak 추가 memory | payload의 100% 초과 | payload의 25% 초과 100% 이하 | payload의 25% 이하 |

fs-verity는 read-only file을 Merkle tree로 검증한다.
IMA는 signature appraisal에 fs-verity digest를 사용할 수 있다.
변조 corpus와 signature 검증 KPI의 근거다.
[Linux fs-verity](https://docs.kernel.org/filesystems/fsverity.html)

pKVM은 pVM page를 Host stage-2에서 제거한다.
보호된 실행 경계 안의 최종 검증이 필요한 근거다.
[Linux pKVM](https://cdn.kernel.org/doc/html/latest/virt/kvm/arm/pkvm.html)

### 7.2 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | ★ | Host 침해 시 검증과 적재를 함께 우회할 수 있다. | ★★★ | 최종 실행 경계 안에서 payload를 다시 검증한다. |
| 성능 | ★★★ | Host에서 digest 한 번만 계산한다. | ★★ | signature와 payload 검증이 boot path에 추가된다. |
| 확장성 | ★★ | allowlist 운영이 Workload 수에 비례한다. | ★★★ | 공통 manifest schema로 package를 추가할 수 있다. |
| 변경 용이성 | ★★★ | 검증기가 Host module 하나에 모인다. | ★★ | loader와 package tool의 호환성을 함께 바꿔야 한다. |
| 자원 효율 | ★★★ | pVM에 별도 검증 runtime이 없다. | ★★ | loader, key와 manifest parser가 pVM에 추가된다. |

## 8. 핵심 트레이드오프

후보 A는 boot path를 단순하게 만든다.
대신 Host 침해를 신뢰 모델에서 제외할 수 없다.

후보 B는 검증과 실행 사이의 경계를 줄인다.
대신 protected loader와 key lifecycle이 추가된다.

## 9. 검증 기준

- payload bit를 한 개씩 변조한 corpus를 만든다.
- manifest, signature와 payload 변조를 각각 시험한다.
- rollback package를 별도로 시험한다.
- 검증 실패 후 실행된 instruction 수를 확인한다.
- 검증 추가 start latency를 1,000회 측정한다.
- peak memory를 측정한다.
- 신규 Workload package를 추가한다.
- core diff LoC를 측정한다.

## 10. 검토 결과

검토 전이다.

## 11. 최종 결정

