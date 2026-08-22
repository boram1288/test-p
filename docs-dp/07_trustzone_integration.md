# DP-07. TrustZone 연동 구조

## 1. 상태

도출

## 2. 결정 목적

pVM과 기존 TEE의 호출 경로를 정한다.
호출자 식별 위치를 정한다.
기존 GlobalPlatform 자산의 변경 범위를 정한다.

## 3. 문제 상황

기존 TA는 TrustZone TEE에서 실행된다.
pVM Workload도 기존 TA 기능을 호출해야 한다.
Host proxy는 command와 shared memory를 볼 수 있다.
직접 호출은 FF-A endpoint와 routing 지원이 필요하다.
기존 Host Client API는 계속 동작해야 한다.

## 4. 결정 질문

pVM 요청을 Host proxy가 TEE로 전달할 것인가?
아니면 EL2와 FF-A가 pVM 요청을 직접 TEE로 전달할 것인가?

## 5. 후보 구조

### 후보 A. Host Proxy 연동 구조

pVM이 Host proxy에 명령을 보낸다.
Proxy가 GlobalPlatform Client API를 호출한다.
TEE는 Host client의 요청으로 처리한다.

### 후보 B. EL2 중재 Direct TEE 연동 구조

pVM이 FF-A message를 전송한다.
EL2가 endpoint identity와 memory share를 검증한다.
TEE가 pVM endpoint의 요청을 직접 처리한다.

## 6. 후보별 동작 구조

### 후보 A

```text
pVM Workload
  -> pVM channel
  -> Host Proxy
  -> GlobalPlatform Client API
  -> TEE Driver
  -> Trusted Application
```

- 실행 위치: proxy를 Host userspace에 둔다.
- 제어 흐름: proxy가 TA session을 생성한다.
- 데이터 흐름: parameter와 shared memory가 Host를 지난다.
- 신뢰 경계: proxy가 민감 command 경계에 포함된다.
- 자원 소유권: proxy가 TEE context와 session을 소유한다.
- 자원 회수: proxy가 session과 shared memory를 해제한다.

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

### 7.1 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.

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

OP-TEE는 재사용 가능한 shared memory를 권장한다.
Temporary memory는 추가 TEE 진입을 만든다.
전환 횟수와 추가 지연 KPI의 근거다.
[OP-TEE GlobalPlatform API](https://optee.readthedocs.io/en/4.9.0/architecture/globalplatform_api.html)

TA memory reference는 exclusive access를 보장하지 않는다.
TA는 parameter type과 bounds를 검증해야 한다.
Host-visible shared memory를 보안성 KPI에 포함한 근거다.
[OP-TEE Trusted Applications](https://optee.readthedocs.io/en/latest/building/trusted_applications.html)

### 7.2 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | ★ | Host proxy가 command와 shared memory를 처리한다. | ★★★ | pVM endpoint와 TEE 사이에서 share를 중재한다. |
| 성능 | ★★ | proxy IPC와 TEE 호출이 직렬로 추가된다. | ★★★ | Host userspace proxy 단계를 제거한다. |
| 확장성 | ★★★ | 기존 Client API와 proxy adapter를 재사용한다. | ★★ | endpoint discovery와 routing policy가 필요하다. |
| 변경 용이성 | ★★★ | TEE 차이를 Host adapter에 가둘 수 있다. | ★ | EL2, SPMC와 guest adapter가 함께 바뀐다. |
| 자원 효율 | ★★ | proxy process와 shadow buffer 가능성이 있다. | ★★★ | 직접 shared memory를 재사용할 수 있다. |

## 8. 핵심 트레이드오프

후보 A는 기존 GlobalPlatform 경로를 재사용한다.
대신 Host proxy가 민감 요청을 관찰할 수 있다.

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

## 10. 검토 결과

검토 전이다.

## 11. 최종 결정

