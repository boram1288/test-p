# Decision Point 선정 목록

## 1. 상태

선정안

이 문서는 상세 DP를 작성하기 전 목록을 합의하기 위한 문서다.
후보 평가와 최종 결정은 포함하지 않는다.

## 2. 선정 근거

- `DP-RULE.md`
- `docs/02_requirements.md`
- `docs/03_qa_quality_scenarios.md`
- `docs/04_architectural_drivers.md`
- `docs/99_reference_scenario_flow.md`

기존 DP 문서의 후보와 결론은 선정 근거로 사용하지 않았다.
PoC 결과는 기술 실현 가능성을 확인하는 관찰 근거로만 사용한다.

모든 DP는 다음 조건을 만족한다.

- 하나의 구조적 결정 변수만 다룬다.
- 후보 구조는 정확히 두 개다.
- 두 후보의 책임, 실행 위치 또는 신뢰 경계가 다르다.
- 두 후보 모두 상위 필수 gate를 통과할 가능성이 있다.
- 문제 상황, 비교 기준과 트레이드오프에 같은 품질속성을 사용한다.
- 제품 선택, 검증 방법과 다른 DP의 세부 구현을 제외한다.

## 3. 선정 DP

### DP-01. pVM 생명주기 실행 경계

- 결정 질문: pVM 제어와 실행을 한 프로세스에 둘 것인가, 제어기와 VM별 실행기로 분리할 것인가?
- 후보 A: 단일 제어 프로세스
- 후보 B: 제어기와 VM별 실행기 분리
- 책임과 경계: 후보 A는 모든 pVM의 제어와 실행 책임을 하나의 Host 프로세스 경계에 둔다. 후보 B는 제어 정책과 VM 실행 책임을 분리하고 pVM마다 별도 프로세스 경계를 둔다.
- 관련 요구: FR-01, FR-02
- 정렬 품질속성: 가용성(AVL-01), 성능(PERF-07)
- 핵심 트레이드오프: VM별 실행기 분리는 한 실행기 장애의 전파 범위를 줄인다. 대신 프로세스 생성과 IPC가 cold start 경로에 추가된다.

### DP-02. Workload 최종 검증 경계

- 결정 질문: 비-Host 신뢰 앵커가 launch measurement를 승인할 것인가, protected loader가 서명된 package를 최종 검증할 것인가?
- 후보 A: 비-Host 신뢰 앵커의 launch measurement 승인
- 후보 B: Protected Loader의 package 최종 검증
- 책임과 경계: 후보 A는 실제 실행 byte의 측정과 승인 책임을 분리된 신뢰 앵커에 둔다. 후보 B는 package 검증과 실행 승인 책임을 protected loader 경계 안에 함께 둔다.
- 관련 요구: FR-03
- 정렬 품질속성: 보안성(SEC-04), 확장성(EXT-01, EXT-02), 성능(PERF-07)
- 핵심 트레이드오프: 측정 승인 구조는 protected parser를 줄이는 대신 여러 신뢰 도메인의 승인 상태를 결합해야 한다. Protected Loader 구조는 검증과 실행을 한 경계에 두는 대신 protected parser와 시작 지연을 늘린다.

### DP-03. zero-copy buffer 채널의 Host 경로 참여

- 결정 질문: Host가 요청 routing만 중계하고 EL2가 각 transfer를 검증할 것인가, pVM이 Host 없이 EL2 lease lifecycle을 직접 호출할 것인가?
- 후보 A: Host routing 중계와 EL2 authoritative 검증
- 후보 B: Host 비경유 pVM-to-EL2 직접 lease
- 책임과 경계: 두 후보 모두 EL2가 owner, receiver, token과 revoke 상태를 최종 집행한다. 후보 A는 Host가 요청 순서와 routing을 중계하고, 후보 B는 pVM peer가 EL2에 직접 요청한다.
- 관련 요구: FR-05
- 정렬 품질속성: 보안성(SEC-01), 성능(PERF-02), 확장성(EXT-07)
- 핵심 트레이드오프: Host routing은 기존 transport와 API를 재사용하는 대신 요청 metadata의 Host 관찰면을 남긴다. 직접 lease는 Host 관찰면을 줄이는 대신 EL2 UAPI와 guest driver의 변경 범위를 늘린다.

### DP-04. HW 사용 주체 전환 scheduler 배치

- 결정 질문: Camera/AI HW의 사용 순서를 Host가 scheduling할 것인가, protected broker pVM이 scheduling할 것인가?
- 후보 A: Host Scheduler와 EL2 원자 집행
- 후보 B: Protected Broker pVM Scheduler와 EL2 원자 집행
- 책임과 경계: 두 후보 모두 EL2가 S2MPU/DMA 권한의 회수, 잔류 데이터 소거와 재부여를 원자적으로 집행한다. scheduling 정책과 queue 상태의 실행 위치만 Host와 protected broker pVM으로 나뉜다.
- 관련 요구: FR-04
- 정렬 품질속성: 보안성(SEC-02, SEC-03), 성능(PERF-04), 자원 효율(TBD)
- 핵심 트레이드오프: Host Scheduler는 기존 driver 자산과 Host 자원을 재사용한다. Protected Broker는 scheduling 상태의 침해 반경을 줄이는 대신 상주 pVM 자원과 IPC 지연을 추가한다.

### DP-05. pVM-TEE 호출 경로

- 결정 질문: Host가 종단간 인증된 TEE 요청을 opaque하게 중계할 것인가, EL2/FF-A가 pVM 요청을 TEE로 직접 routing할 것인가?
- 후보 A: Host Opaque Proxy와 종단간 요청 인증
- 후보 B: EL2/FF-A 직접 routing과 transport-bound identity
- 책임과 경계: 후보 A는 Host를 비신뢰 transport로 사용하고 TEE가 message identity와 무결성을 검증한다. 후보 B는 Host를 호출 경로에서 제거하고 EL2/FF-A transport가 caller identity를 TEE에 결합한다.
- 관련 요구: FR-06, CS-02
- 정렬 품질속성: 보안성(SEC-06), 확장성(EXT-06), 성능(PERF-03)
- 핵심 트레이드오프: Opaque Proxy는 기존 GP Client API 경로를 재사용하는 대신 proxy hop과 종단간 인증 처리를 추가한다. 직접 routing은 호출 hop을 줄이는 대신 EL2, SPMC와 Secure OS의 통합 범위를 늘린다.

### DP-06. 저장 데이터 암복호화 실행 경계

- 결정 질문: TEE가 key 관리와 대용량 암복호화를 모두 수행할 것인가, TEE는 key를 관리하고 측정된 pVM이 암복호화를 수행할 것인가?
- 후보 A: TEE 완결 암복호화
- 후보 B: TEE key 관리와 pVM 암복호화 실행 분리
- 책임과 경계: 후보 A는 key와 평문 처리 책임을 TEE 경계 안에 둔다. 후보 B는 TEE가 측정된 pVM에 session key를 release하고 대용량 연산 책임을 pVM 경계에 둔다.
- 관련 요구: FR-06
- 정렬 품질속성: 보안성(SEC-05), 성능(PERF-03), 자원 효율(TBD)
- 핵심 트레이드오프: TEE 완결 구조는 key 노출 경계를 좁히는 대신 world switch와 TEE 자원을 사용한다. pVM 실행 구조는 대용량 처리 지연과 TEE 부하를 줄이는 대신 key attestation, 회수와 zeroization 책임을 늘린다.

## 4. 선행 및 연관 관계

- DP-01은 다른 pVM 기반 구조의 실행 토대다.
- DP-02의 측정된 Workload identity는 DP-05의 caller identity와 DP-06의 key release에 사용될 수 있다.
- DP-05는 DP-06의 TEE 명령 전달 경로를 정한다.
- DP-01과 DP-02는 같은 cold start 예산을 사용하므로 PERF-07의 세부 예산을 함께 배분해야 한다.
- DP-03과 DP-04는 같은 frame 주기 예산을 사용하므로 PERF-02와 PERF-04의 예산을 함께 배분해야 한다.
- DP-05와 DP-06은 같은 E2E 지연 예산을 사용하므로 PERF-03의 세부 예산을 함께 배분해야 한다.

## 5. 제외 및 병합 항목

- Host-only Workload 검증, Host raw frame relay와 Host key 관리는 필수 보안 gate를 구조적으로 실패하므로 선택 후보에서 제외한다.
- buffer와 metadata의 channel 분리, token 형식과 timeout 규칙은 DP-03의 하위 결정으로 둔다.
- 잔류 데이터 소거 알고리즘과 S2MPU 설정 순서는 DP-04의 하위 결정으로 둔다.
- 암호 알고리즘, TEE 제품, VMM과 통신 라이브러리 선택은 제품/구현 선택이므로 DP로 만들지 않는다.
- 실물 장치와 simulator 선택은 검증 환경의 차이이므로 DP로 만들지 않는다.
- 장애 주입 목록, soak 횟수와 성능 측정 방법은 검증 방법이므로 DP로 만들지 않는다.
- OTA, fleet 운영과 감사 체계는 현재 Secure Vision AI Framework 개발 범위 밖이거나 선정 DP의 후속 운영 결정으로 둔다.

## 6. Claude 협의 결과

Claude가 상위 요구사항에서 독립적으로 DP 후보를 도출했다.
초안의 Host authoritative lease와 EL2 scheduling 구조는 각각 보안 gate와 TCB 최소화 관점에서 재검토했다.
최종적으로 lease의 authoritative state와 HW 권한 집행은 EL2에 공통으로 두고, Host 경로 참여 여부와 scheduling 정책 위치만 결정 변수로 남겼다.
여섯 DP는 서로 다른 책임 축을 다루며 FR-01~FR-06을 모두 포함한다는 데 합의했다.
