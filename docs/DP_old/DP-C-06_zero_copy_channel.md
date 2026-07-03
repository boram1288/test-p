# DP-C-06 결정 과정: 성능(통신 오버헤드)을 위한 zero-copy 보안 채널 구조 설계

> 일자: 2026-06-11
> 관련 문서: `05_decision_points.md` DP-C-06, `06_dpc01_trust_model.md`, `07_dpc02_policy_model.md`, `11_dpc06_hwip_mediation.md`, `08_dpc03_trustzone_integration.md` (G3)
> 성격: Design Point 결정 기록 (생성: Claude / 평가: Codex / 검수: Claude)
> 상태: 조건부 채택 (검수 완료) — 5절 게이트 조건 참조

---

## 1. 결정 범위와 전제

**산출근거 Driver (05 DP-C-06)**: FR-04, QA-01/QA-02(채널 격리/기밀성), QA-04, QA-05, QA-06(버퍼 자원 효율)

### 1.1 설계질문 (05 문서 DP-C-06)

- Secure Camera→Secure AI 영상 데이터는 어떤 공유 메모리 구조로 zero-copy 전달할 것인가?
- RPC 제어 경로와 공유 메모리 데이터 경로를 어떻게 분리할 것인가?
- 채널 수립/해제/재협상 절차와 실패 처리는 어떻게 정의할 것인가?
- Host가 채널 버퍼를 열람하거나 재매핑하지 못하도록 어떤 Stage-2/SMMU 정책을 적용할 것인가?
- 채널 상대 인증의 상대 인증 결과를 채널 수립 절차에 어떻게 반영할 것인가?

### 1.2 선행 DP 결정이 주는 전제

- **DP-C-02**: 채널 수립 권한은 manifest의 정적 선언(허용 채널 상대)이며, 집행은 채널 수립 길목에서 "양단 pVM의 상호 수락 + 채널 상대 인증 상대 인증"으로 fail-closed 게이트한다. 채널 강제 해제(철회) 경로를 본 DP가 설계한다(G4).
- **DP-C-06**: HW IP 출력 버퍼가 pVM Stage-2 도메인에 바인딩된 상태가 zero-copy의 출발점이다. 버퍼 소유권/DMA 경로는 SMMU 게이트 구조를 전제한다.
- **DP-C-03 (H2)**: 메모리 donate/share/unshare와 pVM 측 accept 의미론, 회수 시 소거 완료 조건이 hypercall 계약으로 제공된다.
- **DP-C-05 G3 (위임 인수)**: TEE가 pVM 메모리를 Stage-2 격리와 양립하며 참조하는 방법(SMC 파라미터 버퍼 소유권)을 본 DP의 공유 메모리 구조에서 함께 정의한다.

---

## 2. 후보 구조 (생성: Claude)

### 후보 A: 정적 공유 영역 + 프레임 링버퍼 (share 기반)

채널 수립 시 H2(share)로 두 pVM만 접근 가능한 공유 메모리 영역을 고정 할당하고(Host 매핑 제외), 그 안에 프레임 링버퍼와 인덱스(생산자/소비자 커서)를 둔다. 데이터는 한 번 쓰여진 뒤 이동/복사 없이 소비자가 직접 읽는다.

- **데이터 경로**: Camera pVM이 링버퍼 슬롯에 프레임 기록 → 커서 갱신 → AI pVM이 슬롯 직접 참조 (복사 0회)
- **제어 경로**: 채널 수립/해제/흐름 제어 신호는 별도 저대역 경로(vsock 류 가상 디바이스, Host 경유 가능)로 분리. 제어 메시지에는 데이터가 포함되지 않으며 무결성은 양단 인증 세션(채널 상대 인증)으로 보호.
- **장점**: 수립 후 hypercall 개입 없이 프레임이 흐르므로 정상 상태(steady-state) 오버헤드가 최소(QS-05). 링버퍼 구조는 영상 파이프라인의 표준 패턴이라 검증이 쉽다.
- **단점**: 두 pVM이 동시에 같은 영역에 접근하므로 한쪽 침해 시 진행 중 프레임의 기밀성/무결성이 채널 내에서 공유된다(QA-02 영향은 채널 데이터에 한정). 공유 영역 크기를 수립 시점에 고정해야 한다.

### 후보 B: 프레임 단위 소유권 이전 (donate 체인)

프레임 버퍼마다 소유권을 Camera→AI로 이전(donate/이양)하고, 각 시점에 정확히 한 도메인만 해당 버퍼에 접근 가능하게 한다. dma-buf 핸들 흐름과 정합하며, HW IP(ISP) 출력 버퍼를 그대로 다음 단계(NPU 입력)로 인계하는 구조와 자연스럽게 연결된다.

- **데이터 경로**: ISP 출력 버퍼(Camera 도메인 바인딩) → 소유권 이전 hypercall → AI 도메인 바인딩 → NPU 입력으로 사용 (복사 0회, 매핑 전환만)
- **장점**: 동시 접근이 없어 도메인 간 노출 면적이 최소(QA-02 가장 강함). DP-C-06의 SMMU 버퍼 바인딩과 같은 메커니즘 단위(버퍼 소유권)로 일원화된다.
- **단점**: 프레임마다 hypercall(소유권 전환 + Stage-2/SMMU 갱신 + TLB 무효화)이 발생해 30fps × 다중 스트림에서 전환 비용이 누적될 수 있다(QS-05 위험). H2 의미론이 버퍼 단위 고빈도 이전을 지원하는지에 의존한다.

### 후보 C: Host 중계 암호화 채널 (비교 기준선)

공유 메모리를 Host와도 공유하되 내용을 pVM 간 세션 키로 암호화해 전달한다.

- **장점**: hypercall/Stage-2 정책 의존이 가장 적고 어떤 전달 매체로도 동작한다.
- **단점**: 암복호화 비용이 프레임마다 발생해 zero-copy의 목적(QS-05) 자체를 부정한다. 대용량 영상에서 실시간성(QA-04) 미달이 거의 확실하다. 단독 후보가 아니라 비교 기준선이다.

### 공통 설계 요소

- **채널 생명주기**: 수립(양단 manifest 허용 대조 → 채널 상대 인증 상호 인증 → H2 영역 할당/accept) → 운용(흐름 제어, 오류 통지) → 해제(정상: 양단 합의 unshare+소거 / 비정상: 한쪽 크래시 시 생명주기 관리자(FR-09) 통지 기반 회수 / 강제: DP-C-02 철회 시 EL2 매핑 회수 — fail-closed).
- **Stage-2/SMMU 정책**: 채널 영역은 양단 pVM 도메인에만 매핑, Host IPA 공간에서 제외. Host의 재매핑 시도는 Stage-2 fault로 차단/기록(탐지/로깅).
- **TEE 참조 버퍼 (DP-C-05 G3 인수)**: pVM→TEE SMC의 파라미터 버퍼는 채널과 동일한 H2 share 의미론으로 "pVM↔Secure World" 공유 영역을 정의해 해결한다.

### 평가 기준

| 기준 | 설명 |
|------|------|
| E1. Host 접근 차단 | 채널 버퍼에 대한 Host 열람/재매핑이 구조적으로 차단되는가 (QA-01) |
| E2. zero-copy 성립 | 프레임 복사 0회 또는 전달 지연 5ms 이하 (QS-05) |
| E3. 파이프라인 실시간성 | 1080p30 지속 유입에서 E2E 지연 목표 기여 (QA-04, steady-state hypercall 빈도) |
| E4. 도메인 간 노출 면적 | 한쪽 pVM 침해 시 채널을 통한 타 도메인 노출 범위 (QA-02) |
| E5. 생명주기/철회 완결성 | 수립/해제/비정상 회수/강제 철회(DP-C-02 G4)의 fail-closed 처리 |
| E6. 선행 결정 정합 | H2 의미론(DP-C-03)/HW IP 버퍼 바인딩(DP-C-06)/manifest 게이트(DP-C-02)와의 정합 |

---

## 3. 평가 (평가: Codex)

> 수행: `omc ask codex` (gpt-5.5, reasoning effort xhigh). 원문은 `.omc/artifacts/ask/` 아래에 보존되어 있다.

### 3.1 후보별 평가 (상/중/하)

| 기준 | A: share 링버퍼 | B: donate 체인 | C: Host 중계 암호화 |
|------|:---:|:---:|:---:|
| E1 Host 접근 차단 | 상(조건부) — H2 share가 Host IPA를 배제하면 성립 | 상(조건부) — 이전이 EL2/H2/H6에서 집행되면 성립 | 하 — Host가 버퍼/경로에 접근, 구조적 차단 아님 |
| E2 zero-copy | 상(조건부) — 링 슬롯을 ISP 출력/NPU 입력 버퍼로 직접 쓰면 복사 0회 | 상 — 매핑 전환만 발생 | 하 — 암복호화가 목적 자체를 부정 |
| E3 1080p30 실시간성 | 상 — 정상 상태에서 per-frame hypercall/SMMU rebind 없음 | 중 — 매 프레임 donate/recycle 비용과 jitter 누적 | 하 — 대용량 영상에서 비용/지연 큼 |
| E4 도메인 노출 | 중 — 양단 동시 매핑이라 침해 pVM이 채널 데이터/커서 접근 가능 | 상 — 한 시점 한 도메인 소유 | 중하 — replay/drop/tamper 표면 큼 |
| E5 생명주기/철회 | 중 — crash/강제 revoke/in-flight DMA 처리 보강 필요 | 중 — owner crash/revoke/sanitize 실패 처리 미정 | 하 — Host 큐 소거를 TCB로 닫기 어려움 |
| E6 선행 결정 정합 | 중상 — H2/DP-C-02와 정합, DP-C-06 소유권 모델과 권한 세분화 필요 | 상(조건부) — DP-C-06과 가장 자연스러우나 H2 고빈도 이전 지원이 전제 | 하 — 전 전제와 충돌 |

### 3.2 종합 판정과 권고 (30fps 실효성 정량 비교 포함)

- **A: 기본 데이터 경로로 채택 적합** — 수립 후 프레임마다 hypercall이 없는 점이 결정적.
- **B: 보조/예외 경로** — 격리는 가장 강하나 hot path로는 실측 전 위험.
- **C: 부적합** — 비교 기준선으로만.

**정량 근거**: 1080p30은 프레임 주기 33.3ms, NV12 기준 약 3MB/frame(90MB/s/stream). A는 고정 매핑이라 per-frame EL2 개입이 없고 메모리 대역/cache coherency가 핵심 변수. B는 donate+recycle로 최소 2회 전환/frame = 60 ownership transition/s/stream이며, DP-C-06의 전환 1ms 목표 대입 시 stream당 최대 2ms/frame의 구조적 지연 여지 + 다중 스트림에서 TLB/SMMU invalidation 비용 증가.

**권고안**: 하이브리드 — A를 steady-state 영상 채널로 채택(수립 시 manifest+채널 상대 인증 인증 통과 후 고정 frame pool을 H2 share로 열고 운용 중에는 ring cursor만 이동). B(donate)는 채널 생성 전 private buffer의 pool 편입, 철회/재구성, 고격리 일회성 전달에 한정. C 제외.

### 3.3 지적된 결함/누락

1. A의 "Camera가 슬롯에 기록"이 CPU copy인지 ISP DMA 직접 출력인지 불명확 — ISP 출력이 private buffer 후 ring copy면 zero-copy가 아님.
2. ring metadata 무결성 모델 부족 — cursor, slot state, sequence, bounds check, cache maintenance, backpressure/drop 정책 필요.
3. B는 return/recycle 경로까지 포함한 H2 상태 머신과 비용 실측 부재.
4. 강제 철회 시 in-flight ISP/NPU DMA, stuck device, unshare 실패, scrub 완료 기준이 비어 있음.
5. DP-C-05 G3의 pVM↔TEE SMC 파라미터 버퍼를 pVM↔pVM 채널과 "동일 H2 share"로 뭉뚱그리면 안 됨 — Secure World는 별도 소유권/ABI 규칙 필요.

---

## 4. 검수 (검수: Claude)

> 수행: critic 에이전트 (별도 Context, 읽기 전용). 판정: **유보부 승인 (ACCEPT-WITH-RESERVATIONS)**

**동의**: 하이브리드 권고(A steady-state + B 제한 용도)와 Codex의 정량 비교(B = 60 transition/s/stream, DP-C-06 1ms 목표 대입 시 stream당 최대 2ms/frame), 결함 5건 전부 타당.

**이견 1 (MAJOR)**: 후보 B의 "H2 고빈도 이전 지원" 단서는 단순 의존이 아니라 DP-C-03 G1/G2(HV 확정 게이트)에 직접 걸리는 미확인 게이트다 — 결정문에서 게이트로 승격해야 한다.

**이견 2 (MAJOR, 신규 발견)**: 후보 A의 zero-copy 성립 조건(ISP가 share 영역에 직접 DMA 출력)과 DP-C-06 H6의 단일 도메인 재바인딩 시퀀스가 같은 물리 버퍼에 상충 적용될 수 있다 — "ISP가 share 영역에 DMA 출력하는 동안 SMMU 스트림은 어느 도메인에 바인딩되는가, AI pVM의 동시 read 매핑은 H6 시퀀스와 양립하는가"가 미해결. 현재 상태는 "정합 미증명"이며 게이트로 닫아야 한다.

**이견 3 (MAJOR)**: 2절 공통 설계 요소의 "pVM↔TEE 버퍼를 채널과 동일 H2 share로 해결" 기술은 DP-C-05 G3의 의도와 어긋난다(Codex 결함 5 동의). Secure World는 별도 소유권/ABI 모델이 필요하다.

**이견 4 (MINOR)**: 비정상 해제의 회수 트리거가 비신뢰 Host(생명주기 관리자) 통지에만 의존하면 in-flight DMA가 살아있는 채로 회수가 지연될 수 있다 — EL2 fault 기반 경로 병기 필요.

---

## 5. 결정

**하이브리드를 채택한다.** 후보 A를 steady-state 영상 채널로 한다 — 채널 수립 시 manifest 대조(DP-C-02)와 채널 상대 인증 상호 인증을 통과한 뒤 고정 frame pool을 H2 share로 열고(Host IPA 제외), 운용 중에는 ring cursor만 이동한다. 후보 B(donate)는 채널 생성 전 private buffer의 pool 편입, 철회/재구성, 고격리 일회성 전달에 한정한다. 후보 C는 제외한다.

### 부트스트랩 순서 (채널 상대 인증과 공통 명시)

(i) pVM↔TEE 최소 credential 버퍼(G3 정본의 부트스트랩 서브셋) 정의 → (i.5) 부트로더가 H7 경로(EL2 매개)로 측정값을 **자격 없이** TEE에 보고(DP-C-04 G5 역반영 — 측정 보고 경로는 credential buffer와 별개, 이 단계가 "자격 발급에 측정값 필요 ↔ 측정 보고에 자격 필요"의 순환을 끊는다) → (ii) TEE가 부팅 시 measured 자격 방출(채널 상대 인증, DP-C-04 측정값 전제) → (iii) 방출된 자격으로 pVM↔pVM 상호 인증(채널 상대 인증) → (iv) 인증 성공 후 H2 share 영역 할당/accept(후보 A). 이 순서로 DP-C-06↔채널 상대 인증 순환을 끊는다.

### 채택 조건 (게이트)

| # | 조건 | 처리 |
|---|------|------|
| G1 | **(정합 미증명) HW IP DMA 버퍼의 H6/H2 경계 정의**: ISP/NPU 직접 출력 버퍼의 SMMU 바인딩(H6 단일 도메인 재바인딩)과 채널 share 매핑(H2 양단 동시 매핑)이 같은 버퍼에서 양립하는 의미론을 DP-C-06 G2의 H6 8항목과 1:1 대조로 정의. PoC 검증 항목 등록. 양립 불가 시 해당 구간은 후보 B(donate)로 처리 | DP-C-03 계약 문서, DP-C-06 PoC |
| G2 | **후보 B 성립 게이트**: B는 DP-C-03 G1의 H2 계약 명세(소유권 상태 머신/accept/unshare 실패/회수 시 소거 조건)와 고빈도 이전 지원에 종속. H2 미지원 시 B 폐기, A 단독 + pool 편입은 수립 시 1회 share로 대체. 두 경로 모두 DP-C-03 G2(HV 확정) 미통과 시 폴백 발동 | DP-C-03 G1/G2 |
| G3 | **DP-C-05 G3 인수 분리/정본화**: pVM↔TEE SMC 파라미터/credential 버퍼는 pVM↔pVM 채널과 **별도의 Secure World 전용 소유권 모델**로 본 DP가 정본으로 정의한다(2절 공통 설계 요소의 "동일 H2 share" 기술은 본 게이트로 교정/대체). 채널 상대 인증의 최소 credential buffer는 이 정본의 부트스트랩 서브셋 | 상세 설계, 채널 상대 인증 설계 |
| G4 | **생명주기 완결성**: ring metadata 무결성 모델(cursor/slot state/sequence/bounds check/cache maintenance/backpressure/drop 정책)과 강제 철회 시 in-flight DMA 처리/scrub 완료 기준/unshare 실패 처리를 상세 설계로 고정. DP-C-02 G4/DP-C-06 G4와 연동 | 상세 설계 |
| G5 | **회수 트리거 신뢰 주체**: 비정상 회수는 비신뢰 Host 통지에만 의존하지 않으며, EL2 fault/H2 상태 기반 회수 경로를 병기 | 상세 설계, DP-C-03 G3 |

### 후속 DP에 주는 전제

- DP-C-08: 복호화 키의 pVM 전달 경로는 G3의 Secure World 전용 버퍼 모델을 사용한다(일반 채널 경유 금지).
- DP-C-04: pVM↔Framework 통신 규약의 표준화는 "frame pool + ring + 제어 경로 분리" 구조를 전제한다.
- 채널 상대 인증: 부트스트랩 순서와 G3 정본/서브셋 관계를 공유한다.

> 상태: **조건부 채택 (검수 완료)** — G1(H6/H2 경계)/G2(H2 계약) 확인 결과에 따라 확정
