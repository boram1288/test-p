# DP-04. Workload 실행과 무결성 검증 구조

## 1. 상태

평가 중

## 2. 결정 목적

Workload 검증 주체를 정한다.
검증 시점을 정한다.
검증 결과와 실제 실행 image를 결합한다.

## 3. 문제 상황

- 선행 DP: DP-03 pVM 생명주기 관리 구조
- 연관 DP: DP-07 TrustZone 연동, DP-08 저장 데이터와 키 보호
- 범위: 현재 PoC의 Host SHA-256 allowlist는 관찰 근거다. upstream pKVM의 pVM firmware/초기 측정 지원과 project-custom protected loader는 별도 실현 가능성 gate로 구분한다.

Workload image는 Host storage에 있다.
Host는 image를 변경할 수 있다.
Host가 검증도 담당하면 검증을 우회할 수 있다.
검증 후 적재 전에 image가 바뀔 수도 있다.
신규 Workload는 공통 형식으로 탑재해야 한다.

## 4. 결정 질문

Host가 성능용 사전 필터를 수행하고 non-Host 신뢰 앵커가 실제 launch measurement를 승인할 것인가?
아니면 protected loader가 서명된 package를 최종 검증할 것인가?

## 5. 후보 구조

### 후보 A. Host 사전 필터와 Trusted Measurement 승인 구조

Host Manager가 fs-verity와 signed manifest로 잘못된 package를 먼저 거른다.
이 검사는 성능 최적화이며 보안 경계가 아니다.
EL2가 실제 launch byte의 measurement를 생성한다.
TEE 또는 동등한 non-Host 신뢰 앵커가 signed manifest의 digest/version과 measurement를 대조한다.
승인 token은 instance와 measurement에 결합한다.

### 후보 B. Protected Loader 최종 검증 구조

최소 loader를 protected boot chain에 포함한다.
Loader가 signed manifest를 검증한다.
Loader가 payload를 검증한 뒤 실행한다.
Loader가 protected version state를 대조해 rollback package를 거부한다.

## 6. 후보별 동작 구조

### 후보 A

```text
Host storage
  -> Host Manager: fs-verity + signed manifest 사전 필터
  -> pVM memory 적재
  -> EL2: 실제 launch measurement 생성
  -> non-Host trust anchor: digest/version 대조와 승인
  -> Workload 실행
```

- 실행 위치: 사전 필터는 Host에, 최종 measurement 승인은 EL2/TEE 신뢰 경계에 둔다.
- 제어 흐름: Host는 적재를 요청하지만 승인 token 없이는 실행할 수 없다.
- 데이터 흐름: image byte가 Host에서 pVM으로 이동한다.
- 신뢰 주체: measurement 생성 경로, trust anchor, public key와 anti-rollback state를 신뢰한다.
- 비신뢰 주체: Host Manager, Host storage와 사전 필터 결과를 비신뢰로 둔다.
- 자원 소유권: Manager가 image FD를 소유하고 pVM이 승인된 실행 memory를 소유한다.

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

### 7.1 필수 gate

| Gate | 합격 기준 | 후보 A | 후보 B |
|---|---|---|---|
| SEC-04 Workload 무결성 | 미검증 image 실행 0건, 변조 탐지율 100% | measurement 승인 경로 확인 필요 | protected loader boot chain 확인 필요 |
| TOCTOU 차단 | 검증/측정된 byte와 최초 실행 byte가 동일함 | EL2 measurement 결합 필요 | loader가 검증한 memory에서 직접 실행 |
| Anti-rollback | manifest/image version 단조성 위반 실행 0건 | trust anchor counter 필요 | protected counter 연동 필요 |

Host-only digest/allowlist 검증은 AT-2 Host kernel 공격자에게 우회된다.
따라서 보안 후보가 아니라 PoC 비교 기준선으로만 사용한다.
launch measurement gate가 실패하면 DP-07의 measured caller identity와 DP-08의 measured key release도 함께 성립하지 않는다.

### 7.2 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.
SEC-04의 탐지율 100%는 별점이 아니라 위 필수 gate다.
start latency 임계값은 PERF-07 전체 cold start p95 2초의 세부 예산이 승인되기 전까지 PoC 작업값이다.

| 품질속성 | KPI | 별 1개 | 별 2개 | 별 3개 |
|---|---|---|---|---|
| 보안성 | 신뢰 경계 안의 가변 길이 package parser 수 | 2개 이상 | 1개 | 0개 |
| 성능 | 검증으로 추가되는 start p99 | 500ms 초과 | 100ms 초과 500ms 이하 | 100ms 이하 |
| 확장성 | 신규 Workload 추가 시 core 변경량 | 100 LoC 초과 | 1~100 LoC | 0 LoC |
| 변경 용이성 | 검증 정책 변경 시 protection domain 간 interface 수정 수 | 4개 이상 | 2~3개 | 1개 이하 |
| 자원 효율 | 검증 중 peak 추가 memory | payload의 100% 초과 | payload의 25% 초과 100% 이하 | payload의 25% 이하 |

fs-verity는 read-only file을 Merkle tree로 검증한다.
IMA는 signature appraisal에 fs-verity digest를 사용할 수 있다.
변조 corpus와 signature 검증 KPI의 근거다.
[Linux fs-verity](https://docs.kernel.org/filesystems/fsverity.html)

pKVM은 pVM page를 Host stage-2에서 제거한다.
보호된 실행 경계 안의 최종 검증이 필요한 근거다.
[Linux pKVM](https://cdn.kernel.org/doc/html/latest/virt/kvm/arm/pkvm.html)

upstream pKVM 문서는 pVM firmware를 아직 미구현 항목으로 표시한다.
후보 A의 launch measurement와 후보 B의 protected loader는 baseline 제공 여부를 별도로 확인해야 한다.
[Linux pKVM status](https://www.kernel.org/doc/html/latest/virt/kvm/arm/pkvm.html)

### 7.3 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | ★★★ | trust anchor는 고정 형식 measurement/token만 대조하고 package parser는 Host에 남긴다. | ★★ | protected loader 안에 manifest와 package parser가 포함된다. |
| 성능 | ★★★ | Host 사전 필터와 고정 형식 measurement 대조로 protected 처리량을 줄인다. | ★★ | signature와 payload 검증이 boot path에 추가된다. |
| 확장성 | ★★★ | 공통 signed manifest로 Workload를 추가한다. | ★★★ | 공통 manifest schema로 package를 추가할 수 있다. |
| 변경 용이성 | ★★ | Host, EL2/TEE와 package tool 사이의 interface를 함께 바꾼다. | ★★★ | protected loader 내부 정책 interface 하나에 변경을 가둘 수 있다. |
| 자원 효율 | ★★★ | 고정 크기 measurement/token state만 추가하고 payload를 복제하지 않는다. | ★★★ | loader/parser memory는 payload의 25% 이하로 제한하고 payload를 복제하지 않는다. |

## 8. 핵심 트레이드오프

후보 A는 Host 사전 필터로 잘못된 package를 일찍 거르고 protected parser를 줄인다.
대신 여러 protection domain에 걸친 launch measurement/승인 interface와 state가 필요하다.

후보 B는 package 검증과 실행을 같은 protected loader에 둔다.
대신 protected parser의 공격면과 boot-path 검증 시간이 증가한다.

## 9. 검증 기준

- payload bit를 한 개씩 변조한 corpus를 만든다.
- manifest, signature와 payload 변조를 각각 시험한다.
- rollback package를 별도로 시험한다.
- 검증 실패 후 실행된 instruction 수를 확인한다.
- 검증 추가 start latency를 1,000회 측정한다.
- peak memory를 측정한다.
- 신규 Workload package를 추가한다.
- core diff LoC를 측정한다.
- Host root 권한으로 사전 필터를 비활성화하고 image를 바꿔도 최종 승인이 거부되는지 확인한다.
- 승인 token을 다른 instance/measurement에 replay한다.
- 검증 완료 뒤 최초 instruction 실행 전 byte 변경을 시도한다.
- manifest와 image version을 함께 rollback하고 protected counter가 거부하는지 확인한다.
- baseline pKVM의 launch measurement/pVM firmware 제공 범위를 확인하고 project-custom 변경을 분리 기록한다.

## 10. 검토 결과

사용자 요청에 따라 Claude와 교차 검토했다.
Host-only 검증은 AT-2 공격자에게 우회되므로 비교 기준선으로 격하했다.
두 후보 모두 non-Host 최종 승인, TOCTOU 차단과 anti-rollback gate를 통과하도록 재정의했다.
launch measurement/protected loader의 target 지원 여부 확인이 남아 있다.

## 11. 최종 결정
