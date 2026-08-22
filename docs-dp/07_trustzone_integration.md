# DP-07. TrustZone 연동 구조

## 1. 상태

평가 중

## 2. 결정 목적

pVM과 기존 TEE의 호출 경로를 정한다.
호출자 식별 위치를 정한다.
기존 GlobalPlatform 자산의 변경 범위를 정한다.

## 3. 문제 상황

- 선행 DP: DP-04 Workload identity/measurement
- 연관 DP: DP-08 저장 데이터와 키 보호
- 범위: FF-A는 VM-to-SP messaging을 정의하지만, target pKVM/EL3/SPMC/TEE 조합의 pVM 직접 routing 제공 여부는 별도 실현 가능성 gate다.
- 연쇄 gate: DP-04 launch measurement가 성립하지 않으면 두 후보의 measured identity와 DP-08 key release도 함께 중단한다.

기존 TA는 TrustZone TEE에서 실행된다.
pVM Workload도 기존 TA 기능을 호출해야 한다.
plaintext Host proxy는 command와 shared memory를 볼 수 있다.
직접 호출은 FF-A endpoint와 routing 지원이 필요하다.
기존 Host Client API는 계속 동작해야 한다.

## 4. 결정 질문

pVM 요청을 인증 암호화하고 Host proxy가 opaque하게 TEE로 전달할 것인가?
아니면 EL2와 FF-A가 pVM 요청을 직접 TEE로 전달할 것인가?

## 5. 후보 구조

### 후보 A. 인증된 암호화 Payload와 Opaque Host Proxy 구조

pVM이 measurement-bound identity로 session token을 발급받는다.
pVM은 command와 parameter를 인증 암호화하고 token을 함께 보낸다.
Host proxy는 opaque envelope를 기존 GlobalPlatform Client API 경로로 relay한다.
TA가 token, nonce, sequence와 ciphertext tag를 직접 검증한다.

### 후보 B. EL2 중재 Direct TEE 연동 구조

pVM이 FF-A message를 전송한다.
EL2가 endpoint identity와 memory share를 검증한다.
TEE가 pVM endpoint의 요청을 직접 처리한다.

## 6. 후보별 동작 구조

### 후보 A

```text
pVM Workload
  -> pVM channel
  -> encrypted envelope + signed session token
  -> opaque Host Proxy
  -> GlobalPlatform Client API
  -> TEE Driver
  -> Trusted Application: identity/tag/replay 검증
```

- 실행 위치: proxy를 Host userspace에 둔다.
- 제어 흐름: proxy가 transport session을 만들지만 TA가 실제 pVM identity와 request를 승인한다.
- 데이터 흐름: Host에는 ciphertext envelope와 제한된 routing metadata만 지난다.
- 신뢰 경계: measurement/token 발급자, pVM endpoint와 TA를 신뢰한다. Proxy는 비신뢰다.
- 자원 소유권: proxy는 transport context를, pVM/TA는 보안 session과 nonce state를 소유한다.
- 자원 회수: proxy가 transport context/buffer를 해제하고 pVM/TA가 token, session key와 nonce state를 폐기한다.

### 후보 B

```text
pVM Workload
  -> guest TEE client adapter
  -> FF-A
  -> EL2 endpoint policy
  -> SPMC / TEE
  -> Trusted Application
```

- 실행 위치: routing policy를 EL2와 SPMC에 둔다.
- 제어 흐름: pVM endpoint가 TA session을 요청한다.
- 데이터 흐름: memory share가 pVM과 TEE 사이에 설정된다.
- 신뢰 경계: EL2, SPMC와 TEE가 호출 경계에 포함된다.
- 자원 소유권: pVM endpoint가 session과 share handle을 가진다.
- 자원 회수: relinquish와 reclaim으로 memory를 회수한다.

## 7. 품질속성 비교

### 7.1 필수 gate

| Gate | 합격 기준 | 후보 A | 후보 B |
|---|---|---|---|
| SEC-06 호출자 신뢰 | 비인가 주체 TEE 호출 성립 0건 | TA의 measured token 검증 필요 | VMID 외 measured identity binding 필요 |
| 민감 parameter 기밀성/무결성 | Host 관찰 가능 plaintext 0 byte, 변조 수락 0건 | AEAD/replay state 확인 필요 | protected memory share 확인 필요 |
| SEC-06 후방호환 | 기존 Host GP 경로 회귀 0건 | 기존 transport 재사용 | SPMC/guest adapter 병존 확인 필요 |
| 실현 가능성 | target stack의 호출자 ID/routing 제공 확인 | token 발급 경로 확인 필요 | pVM→SP direct FF-A 확인 필요 |

암호화만으로 호출자를 인증할 수 없다.
두 후보 모두 VMID 단독이 아니라 DP-04 measurement에 결합된 identity를 TA가 검증해야 한다.

### 7.2 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.
SEC-06의 비인가 호출 0건은 별점이 아니라 위 필수 gate다.
성능 임계값은 PERF-03 E2E p99 100ms의 crypto/TEE 구간 세부 예산으로 추적한다.
아래 1ms/5ms 구간은 세부 예산이 승인되기 전까지 PoC 작업값이다.

| 품질속성 | KPI | 별 1개 | 별 2개 | 별 3개 |
|---|---|---|---|---|
| 보안성 | Host에서 관찰 가능한 민감 parameter byte 비율 | 1% 초과 | 0% 초과 1% 이하 | 0% |
| 성능 | TA command 추가 지연 p99 | 5ms 초과 | 1ms 초과 5ms 이하 | 1ms 이하 |
| 확장성 | 신규 TA 연결 시 integration core 변경량 | 100 LoC 초과 | 1~100 LoC | 0 LoC |
| 변경 용이성 | TEE 구현 교체 시 수정 module 수 | 4개 이상 | 2~3개 | 1개 이하 |
| 자원 효율 | command당 world/VM boundary 전환 횟수 | 4회 초과 | 3~4회 | 2회 이하 |

GlobalPlatform Client API는 REE client와 TEE application의 통신을 정의한다.
기존 Client API 호환성 KPI의 근거다.
[GlobalPlatform TEE Client API](https://globalplatform.org/specs-library/tee-client-api-specification/)

FF-A는 VM-to-SP direct request/response 모델을 정의한다.
규격 지원과 target pKVM/SPMC 구현 지원은 구분해 확인한다.
[Trusted Firmware-A SPMC](https://trustedfirmware-a.readthedocs.io/en/latest/components/el3-spmc.html)

OP-TEE는 재사용 가능한 shared memory를 권장한다.
Temporary memory는 추가 TEE 진입을 만든다.
전환 횟수와 추가 지연 KPI의 근거다.
[OP-TEE GlobalPlatform API](https://optee.readthedocs.io/en/4.9.0/architecture/globalplatform_api.html)

TA memory reference는 exclusive access를 보장하지 않는다.
TA는 parameter type과 bounds를 검증해야 한다.
Host-visible shared memory를 보안성 KPI에 포함한 근거다.
[OP-TEE Trusted Applications](https://optee.readthedocs.io/en/latest/building/trusted_applications.html)

### 7.3 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | ★★★ | Host proxy는 opaque envelope만 relay하고 TA가 identity/tag/replay를 검증한다. | ★★★ | pVM endpoint와 TEE 사이에서 protected share를 중재한다. |
| 성능 | ★★ | proxy IPC와 TEE 호출이 직렬로 추가된다. | ★★★ | Host userspace proxy 단계를 제거한다. |
| 확장성 | ★★★ | 기존 Client API와 proxy adapter를 재사용한다. | ★★ | endpoint discovery와 routing policy가 필요하다. |
| 변경 용이성 | ★★★ | TEE 차이를 Host adapter에 가둘 수 있다. | ★ | EL2, SPMC와 guest adapter가 함께 바뀐다. |
| 자원 효율 | ★★ | proxy process와 shadow buffer 가능성이 있다. | ★★★ | 직접 shared memory를 재사용할 수 있다. |

## 8. 핵심 트레이드오프

후보 A는 기존 GlobalPlatform transport를 재사용하면서 민감 payload를 opaque하게 유지한다.
대신 token 발급/검증과 종단간 crypto가 추가되고 traffic metadata는 Host에 남는다.

후보 B는 Host proxy를 호출 경로에서 제거한다.
대신 EL2와 SPMC의 endpoint routing 범위가 증가한다.

## 9. 검증 기준

- 기존 Host Client API 회귀 시험을 수행한다.
- pVM client에서 같은 TA command를 호출한다.
- command별 boundary 전환 횟수를 trace한다.
- 호출 지연 p50, p95와 p99를 측정한다.
- Host memory에서 민감 parameter marker를 검색한다.
- 잘못된 endpoint ID와 TA UUID를 주입한다.
- shared memory bounds와 parameter type 오류를 주입한다.
- client 종료 후 session과 share handle 회수를 확인한다.
- 위조/rollback된 measurement token, 다른 pVM token과 VMID-only 요청을 주입한다.
- ciphertext/tag/nonce/sequence를 변조하거나 replay해 TA가 거부하는지 확인한다.
- pVM별 rate limit, 동시 session 상한과 malformed request flood로 기존 Host TEE 기능의 DoS를 시험한다.
- target pKVM/EL3/SPMC에서 pVM caller identity와 VM-to-SP routing 제공 범위를 확인한다.

## 10. 검토 결과

사용자 요청에 따라 Claude와 교차 검토했다.
Host proxy 후보를 measured token과 AEAD를 사용하는 opaque relay로 보완했다.
두 후보 모두 VMID 단독 인증을 금지하고 SEC-06/후방호환/DoS gate를 적용했다.
target pKVM/SPMC의 VM-to-SP routing과 caller identity 지원 확인이 남아 있다.

## 11. 최종 결정
