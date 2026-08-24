# 품질 위협 문제 3: pVM–GlobalPlatform 표준 연동 경로 부재

> 통합 문서: [과제의 필요성: 품질을 위협하는 세 가지 기술 문제](과제의_필요성_품질_위협_3가지_문제점.md)
>
> 상세 조사: [pVM–Host 중계–GlobalPlatform TEE 구간의 양방향 보안 분석](pVM_Host중계_GlobalPlatform_양방향_보안분석.md)

## 1. 핵심 결론

고객이 보유한 키 관리·인증·암복호화 자산은 기존 Host(REE)에서 GlobalPlatform TEE Client API로 Secure OS를
호출하는 구조를 전제로 한다. pVM을 새로운 호출 주체로 추가하면 API, 전송 계층, 공유 메모리, 호출자 신원과
세션을 가상화 경계에 맞게 연결해야 하지만, **pKVM의 메모리 격리만으로 이 연동 경로가 자동으로 제공되지는 않는다.**

pVM 내부 SW와 private memory의 기밀성·무결성이 보장되어도 Host가 중계한 응답의 진위는 별도 문제다. Host는 pVM
메모리를 직접 변조하지 않고 정상 I/O 경로로 TA 응답을 폐기한 뒤 위조 성공값을 주입할 수 있다. TEE가 악성 CA
입력을 방어하는 설계는 요청을 받는 TEE를 보호할 뿐, 응답을 받는 pVM의 보안 판단을 보호하지 않는다.

| 실제 실패 결과 | 구조적으로 어려운 이유 | 설계 결과로 증명해야 할 것 |
|---|---|---|
| 기존 Secure OS 자산 재사용 실패, Host의 키·평문 관찰, 요청 변조 또는 TA 응답 위조 | 기존 Host 호출을 유지하면서 pVM 신원·세션과 양방향 메시지 진위를 새 경로에서 보장해야 함 | 기존 GP 회귀 시험 100%, 비인가 호출·위조 응답 수용 0건, Host 평문 노출 0건, 호출 지연 수치 |

## 2. 관련 시스템 전제와 용어

- **Host Linux**: 기존 GP Client가 실행되지만 본 과제에서는 커널까지 침해될 수 있는 비신뢰 영역
- **pVM**: Secure Camera/AI Workload가 실행되는 보안 VM
- **TEE/Secure OS**: TrustZone 신뢰 영역에서 키 관리, 인증, 암복호화를 수행하는 실행 환경
- **GP API**: GlobalPlatform이 정의한 TEE Client API로 기존 Client와 TA 자산의 호환 기준
- **GP 호환 Frontend**: pVM에서 기존 CA에 GP API 표면을 제공하고 비신뢰 전송 결과를 검증하는 신뢰 모듈
- **TEE Secure-channel Gateway**: TEE에서 pVM 신원·보안 채널을 검증하고 기존 GP 세션과 TA 호출로 변환하는 신뢰 모듈
- **TEE Relay 서비스 pVM**: 여러 Workload pVM의 TEE 세션·인가를 대리 관리할 수 있는 별도 신뢰 pVM
- **SMC/FF-A**: 일반 영역과 TrustZone 사이에서 명령과 메모리 정보를 전달하는 하위 통신 방식
- **TA**: Secure OS 안에서 키 관리나 암복호화 기능을 제공하는 Trusted Application

보호 대상은 암호화 키, 인증 정보, GP 명령 인자, 평문/암호문 버퍼, 호출자 신원과 세션 상태다.

## 3. 기존 호출 경로와 새로 필요한 경로

```text
[기존 경로]
Host Application
    └─ GlobalPlatform Client API(libteec)
        └─ Linux TEE driver(/dev/tee*)
            └─ SMC 또는 FF-A
                └─ Secure OS / Trusted Application

[추가로 필요한 경로]
pVM Workload
    └─ GP 호환 Client API
        └─ GP 호환 Frontend
            └─ 비신뢰 Host를 배제한 양방향 인증 채널
                └─ TEE Secure-channel Gateway
                    └─ Secure OS / 기존 Trusted Application
```

GlobalPlatform 표준은 Client API와 TEE 세션/명령의 의미를 제공하지만, 특정 pKVM 구조에서 pVM 요청을
TrustZone으로 어떻게 전달하고 pVM의 신원을 어떻게 증명할지까지 자동으로 해결하지 않는다.

즉, **상위 GP API 호환성**과 **하위 가상화 전송 계층** 사이에 접합 계층이 필요하다. Host를 물리 경로에서
제거하지 못해도 기밀성·무결성의 신뢰 경계에서는 배제해야 하며, Host는 opaque message를 전달하는 비신뢰
transport로만 동작해야 한다.

## 4. 구체적인 기술 공백

### 4.1 pVM의 TEE 호출 전송 계층

pVM에서 발생한 SMC를 그대로 Secure World에 전달할지, Host 중계를 사용할지, 별도 중계 서비스나 FF-A 통신
종단점으로 표현할지 결정해야 한다. 전송 방식에 따라 다음 구현이 달라진다.

- EL2의 호출 가로채기와 경로 지정
- pVM 페이지와 Secure World 간 공유 메모리 전달
- interrupt와 처리 결과 반환
- 시간 초과, 취소 및 재시도 처리

현재 pVM이 독립 TEE endpoint가 아니고 물리 TEE driver에 직접 접근할 수 없다면 Host relay를 없애려면 EL2와
Secure World routing의 변경이 필요하다. 이 변경이 과제 범위 밖이라면 Host의 물리 중계는 유지하되 pVM과 TEE의
신뢰 종단점 사이에서 메시지를 인증·암호화해야 한다.

### 4.2 호출자 신원과 권한

기존 Host 호출 경로에 pVM 요청을 단순 합류시키면 Secure OS는 요청이 정상 pVM에서 왔는지, 침해된 Host가
pVM을 사칭했는지 구분하기 어렵다. 여러 pVM이 동일 TA를 호출할 때 다음을 분리해야 한다.

- pVM 신원과 Workload 신원
- GP 세션과 공유 메모리 식별자 공간
- pVM별 허용 TA/명령 정책
- pVM 종료 시 세션, 키 식별자와 공유 메모리의 일괄 회수

GP login token의 신뢰도는 이를 생성하는 Rich OS의 보안 수준에 한정된다. 따라서 Host가 제시한
`TEEC_LOGIN_APPLICATION` 등의 정보는 pVM 신원 증거로 사용할 수 없고, DICE/attestation과 Host가 바꿀 수 없는
trust anchor로 실제 pVM·Workload 신원을 검증해야 한다.

### 4.3 공유 메모리 전달

GP Client API는 명령 인자와 공유 메모리를 사용한다. pVM 버퍼를 Host 중계가 평문으로 매핑하면 Host 비노출
요구를 위반한다. 매 호출마다 복사·암호화하면 성능이 저하된다. Secure World에 전달할 페이지를 누가 검증하고,
호출 종료 후 언제 회수할지도 정의해야 한다.

Host가 접근할 수 있는 frame과 Shared Memory는 volatile한 악성 입력으로 취급한다. pVM Frontend와 TEE Gateway는
length·offset을 검증한 뒤 private memory로 복사하고, 인증을 마친 복사본만 사용해야 한다. 인증 전 frame parser의
memory safety도 pVM 플랫폼의 필수 보안 책임이다.

### 4.4 기존 Host 경로와의 공존

새 pVM 경로를 추가하면서 기존 Host의 GP Client, TA, SMC/FF-A 호출 흐름을 변경하면 기존 제품 자산에 회귀가
발생한다. 반대로 Host 경로를 그대로 복제하면 pVM이라는 별도 신뢰 도메인의 신원과 메모리 소유권을 표현하지 못한다.

### 4.5 반환 결과의 진위와 GP 외부 상태

`TEEC_Result`, `returnOrigin`, session handle과 parameter metadata 일부는 TA가 아니라 GP Client stack, driver
또는 Host relay가 만들거나 바꿀 수 있다. pVM CA가 외부 `TEEC_SUCCESS`와 output parameter를 그대로 믿으면
Host가 정상 TA 응답을 폐기하고 위조 성공값을 주입해 서명 검증, 권한 승인 또는 정책 판단을 우회할 수 있다.

pVM Frontend는 외부 GP 결과를 비신뢰 transport 상태로만 사용하고, TEE Gateway가 인증한 inner response를
검증한 뒤에만 CA에 semantic success를 반환해야 한다. inner response에는 secure session, request ID, counter,
command, 실제 type·length·status와 payload를 binding한다.

### 4.6 응답 유실과 세션 수명주기

Host는 TA에 요청을 전달한 뒤 정상 응답만 삭제할 수 있다. 이때 CA는 연산 실행 여부를 알 수 없으므로 단순 재시도
시 키·상태 변경이 중복될 수 있다. request ID별 idempotent 처리나 처리 결과 조회가 필요하다.

pVM 종료 또는 relay 장애 시 Host의 정리 보고를 신뢰하지 않고, TEE Gateway가 세션 timeout·epoch·counter를
기준으로 stale session과 key를 fail-closed로 회수해야 한다.

## 5. 구체적인 실패 경로

### 5.1 Host 중계에서 요청 기밀 데이터 노출·변조

1. pVM Workload가 ENC/DEC 명령과 대상 버퍼를 Host 중계에 전달한다.
2. 침해된 Host가 명령 인자나 평문 버퍼를 읽고 변경한다.
3. Secure OS가 변조된 요청을 정상 pVM 요청으로 처리하거나 pVM을 사칭한 Host에 키 연산을 허용한다.

API 형태가 GP와 같더라도 전송 계층이 Host를 신뢰하면 전체 구간의 기밀성과 무결성이 성립하지 않는다.

### 5.2 Host의 TA 응답 위조로 pVM 판단 우회

1. pVM CA가 서명 검증, 복호화 또는 보안 정책 조회 명령을 전송한다.
2. Host가 TA의 정상 응답을 폐기하고 `TEEC_SUCCESS`와 조작된 output parameter를 반환한다.
3. 정상 코드가 실행 중인 pVM CA가 위조 결과를 TA의 보안 판단으로 믿고 후속 권한이나 데이터를 사용한다.

이 공격은 pVM private memory를 변경하지 않으므로 pKVM의 memory integrity 보장과 충돌하지 않는다. TEE의 악성
CA 입력 검증도 반대 방향의 pVM 응답 진위를 보장하지 않는다.

### 5.3 호출자 사칭과 세션 혼선

1. 여러 pVM의 요청이 하나의 Host TEE 장치와 프로세스 신원으로 합쳐진다.
2. Host가 다른 pVM의 세션 ID 또는 공유 메모리 식별자를 재사용한다.
3. TA가 잘못된 호출자에게 키 연산을 허용하거나 다른 pVM의 결과를 반환한다.

### 5.4 예외 처리 중 자원 누수

1. pVM이 GP 명령 수행 중 비정상 종료되거나 시간 초과된다.
2. Secure OS 세션과 공유 메모리가 열린 채 남는다.
3. 이후 pVM이 동일 식별자를 재사용하거나 Secure OS 자원이 고갈되어 다른 서비스까지 장애가 전파된다.

### 5.5 벤더별 접합 모듈 확산

1. Secure OS별로 pVM 전용 API와 전송 계층을 각각 구현한다.
2. Workload가 특정 Secure OS와 드라이버에 직접 결합된다.
3. Secure OS 교체나 SoC 변경 시 Workload, Framework, Host 구성까지 연쇄 수정된다.

기능은 동작하더라도 GP 표준 채택의 목적인 자산 재사용성과 이식성이 사라진다.

## 6. 위협받는 품질 속성

| 품질 속성 | 위협 내용 |
|---|---|
| 보안성 | Host가 요청·평문을 관찰·변조하고 pVM을 사칭하거나 TA 응답을 위조해 정상 pVM의 보안 판단을 우회할 수 있음 |
| 호환성 | 기존 GP Client/TA의 API와 동작 의미가 달라져 기존 보안 자산을 재사용하지 못함 |
| 이식성 | Secure OS 또는 SoC별 전용 접합 모듈이 Workload와 Framework에 확산됨 |
| 성능 | pVM–Host–TEE의 여러 중계 단계, 데이터 복사와 암복호화로 호출 지연이 증가함 |
| 신뢰성 | 응답 유실·재시도, pVM 비정상 종료와 세션 회수 실패가 중복 연산 또는 Secure OS 자원 고갈로 이어짐 |
| 확장성 | pVM 수와 Secure OS 종류가 늘 때 경로, 신원과 세션 조합이 급증함 |

## 7. 핵심 트레이드오프

- Workload pVM별 Frontend가 TEE 보안 세션을 직접 소유하면 지연과 장애 반경을 줄이지만 pVM마다 채널 코드와
  검증 상태가 중복된다.
- 전용 TEE Relay 서비스 pVM이 세션·인가를 중앙 소유하면 변경과 Secure OS 교체를 한곳에 집중할 수 있지만 추가
  pVM 왕복, 단일 장애점과 confused-deputy 위험이 생긴다.
- Secure OS별 전용 API는 초기 구현이 빠르지만 GP 자산 재사용성과 이식성을 훼손한다.
- 완전한 GP 동작 호환은 기존 자산에 유리하지만 pVM 신원과 메모리 소유권을 표현할 확장 지점이 필요하다.

따라서 이 문제는 **보안성–표준 호환성–구현 변경량–성능 간 아키텍처 트레이드오프**다.

Host를 물리적으로 우회하는 직접 경로는 보안과 성능에 유리할 수 있으나, 현재 pKVM에 protected guest→Secure
World routing이 없거나 EL2 수정이 금지된 환경에서는 선택 가능한 후보가 아니라 **실현 가능성 gate 실패
기준선**으로 분류한다.

## 8. GP 호환성의 구분

| 호환성 수준 | 확인 질문 |
|---|---|
| API 호환성 | Workload가 표준 GP Client API를 그대로 호출할 수 있는가? |
| 소스 호환성 | 기존 Client 코드를 수정 없이 다시 빌드할 수 있는가? |
| 바이너리 호환성 | 기존 `libteec` 기반 바이너리를 재빌드 없이 사용할 수 있는가? |
| 동작 호환성 | 세션, 명령, 취소, 공유 메모리의 의미가 기존과 같은가? |
| 보안 호환성 | pVM 신원과 권한이 TA까지 위조 불가능하게 전달되는가? |
| 응답 보안성 | CA가 Host의 외부 성공값이 아니라 TEE가 인증한 실제 결과만 신뢰하는가? |
| 공존성 | 기존 Host→TEE 경로에 기능·성능 회귀를 만들지 않는가? |

함수 이름과 인자 형식을 맞추는 것만으로는 GP 표준 지원이 완성되지 않는다.

## 9. 설계가 반드시 보장해야 할 조건

1. pVM Workload에는 GP 표준 Client API 표면을 유지한다.
2. API 계층과 전송 계층을 분리하여 Secure OS/SoC별 차이를 접합 모듈 내부에 한정한다.
3. Secure OS가 Host의 주장만 믿지 않고 실제 pVM 신원과 권한을 검증할 수 있어야 한다.
4. pVM 신뢰 종단점과 TEE Gateway는 Host가 바꿀 수 없는 trust anchor로 상호 인증한다.
5. 명령 인자, 공유 메모리와 반환 payload가 비신뢰 Host에 평문으로 노출되지 않아야 한다.
6. Host가 위조·변조·재전송한 요청과 응답을 모두 탐지하고 fail-closed한다.
7. outer `TEEC_Result`와 metadata는 transport 상태로만 취급하고, 인증된 inner response 뒤에만 성공을 반환한다.
8. command, session, request ID, counter, 실제 type·length·status를 암호학적으로 binding한다.
9. pVM별 세션, 공유 메모리 식별자와 키 식별자 공간을 분리한다.
10. Host frame과 Shared Memory parser는 인증 이전 malformed input에도 memory-safe해야 한다.
11. 기존 CA·TA와 Host→TEE GP 호출 경로를 회귀 없이 유지한다.
12. 시간 초과, 취소, pVM 비정상 종료와 Secure OS 재시작 시 세션과 메모리를 결정적으로 회수한다.
13. 다중 pVM 동시 요청의 공정성, 요청률 제한과 장기 대기 방지 정책을 정의한다.
14. 응답 유실 후 재시도가 상태를 중복 변경하지 않도록 request ID, idempotency와 결과 조회 규칙을 둔다.

## 10. 검증 지표

- 기존 GP Client/TA 회귀 시험 통과율: **100%**
- 비인가 pVM의 TA 명령 거부율: **100%**
- Host에서 민감 인자와 평문 버퍼가 관찰된 건수: **0건**
- Host가 위조·변조·재전송한 응답을 보안 성공으로 수용한 건수: **0건**
- outer GP 성공값만으로 보안 성공을 판단한 건수: **0건**
- malformed Host frame에서 pVM Frontend crash·memory corruption: **0건**
- 동일 request ID 재처리로 발생한 중복 상태 변경: **0건**
- pVM 간 세션/공유 메모리 식별자 오인식 건수: **0건**
- 시간 초과/비정상 종료 후 Secure OS 세션과 공유 메모리 회수율: **100%**
- Host와 pVM의 동시 GP 호출 시 평균·최악·상위 백분위 응답 시간 측정
- Secure OS 교체 시 Secure OS 패키지 외부 변경 파일 수 측정

위 수치는 완료 결과가 아니라 설계 판정 기준이다. 실제 HW와 Secure OS가 준비되면 PoC, 회귀 시험과 공격 시험으로
측정하고, 준비 전에는 호출 경로 시뮬레이션과 오류 주입 시험으로 후보 구조를 비교한다.

## 11. 요구사항 추적성

- 기능 요구사항: `FR-06` Secure OS ENC/DEC 명령 전송
- 제약사항: `CS-02` GlobalPlatform 표준 규격 준수(`docs/02_requirements.md` 기준)
- 이해관계자 요구: `VOS-11`, `VOS-12`
- 품질 속성: `QS-01`, `QS-02`, `QS-08`

`docs/05_decision_points.md`의 DP5는 동일 제약을 `CS-03`으로 표기하므로 상위 요구사항 문서와 ID 정합화가 필요하다.

## 12. 관련 자료

- [과제의 필요성 슬라이드](SW_Architect_개인과제/슬라이드5.PNG)
- [유즈케이스 UC-06](../docs/01_use_case_spec.md)
- [기능 요구사항 FR-06과 제약사항 CS-02](../docs/02_requirements.md)
- [GP API 호환을 위한 TrustZone 연동 Decision Point](../docs/05_decision_points.md)
- [문제 3 해결 후보 구조](후보구조_문제3_GlobalPlatform_연동.md)
- [pVM–Host 중계–TEE 양방향 보안 분석](pVM_Host중계_GlobalPlatform_양방향_보안분석.md)
- [FF-A 조사](../docs/99_ffa.md)
