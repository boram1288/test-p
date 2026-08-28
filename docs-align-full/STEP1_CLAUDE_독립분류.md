# 단계 1 독립 검토 — Claude 분류 (Codex 비대조)

## 0. 조사 조건 명시

- 조사 범위: 현재 working tree의 `docs-align`, `docs`, `docs-new`, `docs-dp` 전체.
- 외부 자료, `../poc-p` 원문은 사용하지 않았다. `docs-new`에 이미 요약된 PoC 관찰 사실만 관찰 근거로 사용했다.
- `docs-align`의 기존 후보 구조·채택 결과(`후보구조_문제1/2/3.md`)와 `docs`/`docs-dp`의 기존 후보·결론은 신규 후보를 만드는 입력으로 사용하지 않았다. 문제·결정축을 고정하기 위해서는 각 문서의 **현재 구조/위협/요구사항/품질 시나리오/제약/PoC 관찰 사실**만 인용했다.
- Codex의 분류 결과는 보지 않았고, 이 문서 작성 후에도 참조하지 않았다.
- 최종 선택이나 신규 후보 구조는 제안하지 않는다. 판정까지만 수행한다.

### 0.1 기존 세 문제의 결정축 기준선 (PLAN 3절 원문)

| 기존 문제 | 결정축 요약 |
|---|---|
| 문제 1: Camera/AI HW 공유 | HW 사용 순서 결정과 신뢰 영역의 최종 권한 집행 책임 |
| 문제 2: pVM 간 대용량 데이터 전달 | 프레임별 페이지 소유권 전환과 사전 등록 보호 버퍼 풀/slot 사용권 |
| 문제 3: pVM 수명과 암호화 파일 | pVM과 독립적인 암호화 파일의 보관/입출력 책임 위치 |

판정값: `COVERED` / `NEW-DP` / `SUBDECISION` / `BASELINE-CONSTRAINT` / `DUPLICATE` / `EVIDENCE-ONLY` / `OUT-OF-SCOPE`. 모두 잠정이며 Codex 대조 전 고정값이다.

---

## 1. G-01~G-10 판정

### G-01. pVM hang/crash의 공용 실행 흐름 전파와 회수/재기동 지연

- 원문 근거: 본편 슬라이드 31~32(미열람, 인벤토리 항목만 확인), appendix 15(미열람), `docs/05_decision_points.md` DP1, `docs/07_decision_point_candidates.md` DP-A1/A3, `docs-new/poc-customizations-and-decision-points.md` DP-1, `docs-dp/DP-01.md`·`DP-01-배경.md`·`DP-01-후보구조.md`(이미 "선정 DP"로 평가 중).
- 연결 요구 ID: FR-01, FR-02, AVL-01, AVL-02, AVL-04, PERF-07.
- 잠정 분류: **NEW-DP** (문제 1~3 대비)
- 이유: 문제 1(HW 순서/권한 집행), 문제 2(버퍼 소유권), 문제 3(저장 수명)의 결정축 어디에도 "Host 관리 프로세스의 실행 흐름 격리 경계"라는 변수가 없다. 원인(공용 실행 흐름 점유) → 실패(다른 pVM/Host 처리 중단) → 품질 영향(AVL-01)의 인과 사슬이 독립적이고, 결정 변수(단일 프로세스 내 Context 분리 vs 프로세스 분리)도 문제 1~3과 다르다. 단, `docs-dp/DP-01.md`가 이미 동일 축으로 "평가 중" 상태의 DP를 보유하므로, docs-align-full에서 신규로 쓸 경우 중복 방지를 위해 `docs-dp/DP-01`과의 결정축 일치 여부를 다음 단계에서 반드시 대조해야 한다(현재는 대조하지 않고 독립 판정만 기록).

### G-02. 비신뢰 Host가 전달한 pVM/Workload 이미지의 변조·rollback·미승인 실행 차단 주체

- 원문 근거: appendix 10~11/15(미열람), `docs/05_decision_points.md` DP2, `docs/99_additional_decision_points.md` DP-B(부팅 무결성), `docs-new` DP-2, `docs-dp/DP-02.md`(선정 DP, 평가 중).
- 연결 요구 ID: FR-03, SEC-04, EXT-01, EXT-02, PERF-07.
- 잠정 분류: **NEW-DP**
- 이유: 문제 1~3의 결정축은 "실행 중" 데이터 경로(HW 권한, 버퍼 소유권, 저장 수명)를 다루지만, G-02는 "탑재 이전" 시점의 이미지 신뢰 판정 주체를 다룬다. 원인(비신뢰 Host의 탑재 경로 장악)과 결정 변수(Host 밖 측정값 승인 vs 보호 로더 직접 검증)가 문제 1~3 어디와도 겹치지 않는다. `docs-dp/DP-02.md`가 이미 동일 축을 다루므로 마찬가지로 중복 대조가 필요하다.

### G-03. pVM 생성/Workload 로딩/HW/채널 요청의 정책 결정·집행 신뢰 가정 불일치

- 원문 근거: appendix 13/15(미열람), `docs/05_decision_points.md` 4절/261행(Reference Scenario 2단계 명시 제외), `docs/07_decision_point_candidates.md` DP-A2, `docs/DP/DP-C-02.md`(확정 상태, SELinux 기반 Host app/Workload 권한 분리 결정 보유).
- 연결 요구 ID: 명시적 FR/QA ID 없음(요구 추적성 자체가 확인 필요 항목). `docs/DP/DP-C-02.md`는 결과적으로 DP-C-03/04/06/07에 전제를 제공.
- 잠정 분류: **NEW-DP 후보이나 DUPLICATE 가능성 높음**
- 이유: 문제 1~3의 결정축은 신뢰 경계 자체는 고정하고 그 안에서의 소유권/수명/집행 순서를 다루는 반면, G-03은 "누가 정책을 결정(PDP)하고 누가 집행(PEP)하는가"라는 횡단 축이다. 이 축은 문제 1~3에서 다루지 않는다는 점에서 원인·결정변수가 독립적이므로 표면적으로는 NEW-DP다. 그러나 `docs/DP/DP-C-02.md`가 이미 이 결정("Host app 권한과 Workload 권한을 SELinux로 분리")을 **확정**했고, `docs-dp/DP-LIST.md`도 "DP-A2의 Host API 제공 방식은... 선정하지 않는다"고 명시했다. 즉 이미 다른 문서 계열(docs/DP/*)에서 같은 결정축을 정책 집행 관점에서 해결한 상태다. docs-align-full에서 이를 신규로 다시 쓰려면 `docs/DP/DP-C-02.md`와 결정축이 완전히 같은지(같으면 DUPLICATE로 흡수) 확인이 필요하다. 현재는 두 후보(EL2/SMMU 직접 집행 vs SELinux 기반 분리 집행)가 실제로 상호 배타적 트레이드오프 쌍인지 미확인이므로 `NEW-DP 후보(교차검증 필요)`로 잠정 고정한다.

### G-04. pVM의 TEE 요청에서 호출자 신원/무결성 보존 + 기존 GP/SMC 경로 유지

- 원문 근거: appendix 15(미열람), FR-06, `docs/05_decision_points.md` DP5, `docs-dp/DP-05.md`(선정 DP, 평가 중), `docs-align/품질위협_문제3_pVM수명_암호화파일_유실.md` 2절("GP Client API를 통한 pVM–TEE 호출 경로... 이미 정해진 기준선").
- 연결 요구 ID: FR-06, CS-02, SEC-06, EXT-06, PERF-03.
- 잠정 분류: **NEW-DP**
- 이유: 문제 3 문서가 **명시적으로** "이 문제에서는 호출 경로를 바꾸지 않고... 만 다룬다"고 선언해, pVM→TEE 호출 경로 자체는 문제 3의 결정 범위 밖(BASELINE)임을 스스로 확정한다. 따라서 G-04는 문제 3이 의도적으로 비워둔 축이며, 문제 1(HW)·문제 2(버퍼)와도 무관하다. 원인(Host 위장 가능성) → 결정변수(Host 중계+종단인증 vs EL2/FF-A 직접 전달)가 독립적인 구조 결정이다. `docs-dp/DP-05.md`가 이미 이 축을 다루므로 중복 대조 필요.

### G-05. frame backing과 descriptor/control metadata 분리 시 관찰/변조/순서역전/편측도착 회수

- 원문 근거: appendix 13(미열람), `docs-new/poc-customizations-and-decision-points.md` 2.1/2.5/2.6절 및 DP-5(EL2 metadata queue와 DMA-BUF lease 분리), `docs/05_decision_points.md` DP3 설계질문 2번("저빈도 제어 경로와 고대역 데이터 경로를 어떻게 분리"), `docs-dp/DP-LIST.md` 5절("버퍼와 부가 정보의 전달 경로 분리... DP-03의 하위 결정으로 둔다").
- 연결 요구 ID: FR-05, SEC-01, PERF-02.
- 잠정 분류: **SUBDECISION** (버퍼 전달 문제군, 문제 2 계열의 하위 결정)
- 이유: `docs-align/품질위협_문제2_pVM간_데이터전달.md` 설계 조건 1번이 이미 "실제 프레임 payload 경로와 권한 판정용 제어 경로를 분리하고, 제어 명령이 프레임마다 발생해도 payload를 싣지 않는다"를 **필수 조건(baseline)**으로 못박고 있어, "분리할지 여부" 자체는 문제 2에서 이미 결정된 전제다. 신호가 실제로 새로 묻는 것은 "분리된 두 채널의 join·순서·편측도착 회수 책임을 누가 지는가"인데, 이는 `docs-dp/DP-LIST.md`가 명시적으로 DP-03(버퍼 요청 경로)의 하위 결정으로 이미 분류해 두었다. 두 근거가 일치하므로 SUBDECISION으로 판정한다. 단, "Host의 관찰/변조 가능성"이라는 보안 축은 문제 2의 SEC-01/기밀성 gate에 이미 포함되어 있어 완전한 GAP은 아니다.

### G-06. 물리 HW lease를 client별 교대 vs 검증된 서비스 pVM 고정 — DP-07 목록 불일치

- 원문 근거: `docs-dp/DP-07.md`(전체 작성 완료, "평가 중" 상태) — **그러나 `docs-dp/DP-LIST.md`의 선정 DP 목록(DP-01~DP-06)에는 없음**. `docs-new` DP-3(장치 할당 구조, vfio-platform+pVIOMMU+EL2 PV IOMMU 채택), `docs/07_decision_point_candidates.md` DP-C2/C3, `docs-align/슬라이드14_16_설계고려사항_다이어그램_검토.md` 매핑표("슬라이드 15 → DP-04, DP-07").
- 연결 요구 ID: SEC-02, SEC-03, PERF-01, PERF-04, AVL-01, AVL-02, EXT-01.
- 잠정 분류: **NEW-DP (목록 불일치 명시적 확인)**
- 이유: 문제 1의 결정축은 "HW 사용 순서 결정과 신뢰 영역의 최종 권한 집행 책임"이며, 이는 `docs-dp/DP-04`(순서 결정 위치)와 대응한다. G-06/DP-07이 묻는 것은 순서가 아니라 **"EL2 lease의 수령 주체가 물리적으로 각 client(Host/Camera pVM/AI pVM)인가, 단일 서비스 pVM(virtual frontend 패턴)인가"**로, TCB 구성원 추가 여부(서비스 pVM을 신뢰 계층에 편입할지)를 가르는 별개의 구조 변수다. `DP-07.md` 3절도 "이 DP는... DP-04의 하위 결정이다"라며 두 축을 스스로 구분한다. 목록 불일치는 사실로 확인됨: `docs-dp/DP-07.md`는 상세 문서가 존재하나 `docs-dp/DP-LIST.md`의 선정 목록·의존관계 다이어그램·제외목록 어디에도 언급되지 않는다. 이는 누락이며, 이번 단계에서 COVERED/NEW-DP/SUBDECISION 중 하나로 명시적 재분류가 필요하다는 PLAN의 지적이 타당함을 확인했다.

### G-07. pVM 소멸/장애 후 TEE 세션·비동기 요청 자원의 authoritative 정리 주체

- 원문 근거: `docs-dp/DP-LIST.md` 5절("pVM 소멸 시 TEE 세션과 자원을 정리하는 책임은 별도 DP 후보로 남긴다" — **명시적으로 미확정 상태로 보류**), `docs/99_tzdaemon.md`(세션 수명주기 관장 주체), `docs/99_secure_storage.md`, `docs-dp/DP-05.md`(pVM-TEE 호출 경로, session 소유는 TEE, 회수는 "TEE session manager"/"TEE+EL2/FF-A 종료 통지"로만 간략히 언급).
- 연결 요구 ID: FR-06, SEC-06, AVL-01, AVL-04.
- 잠정 분류: **NEW-DP 후보 (docs-dp 자체가 미확정으로 남긴 항목)**
- 이유: `docs-dp/DP-LIST.md`가 스스로 "별도 DP 후보로 남긴다"고 선언했으므로 이는 누락이 아니라 **의도적 보류**다. 문제 1~3의 결정축과 겹치지 않으며(문제 3은 저장 파일 수명, 이 신호는 TEE 세션/비동기 요청 상태 수명), `DP-05`도 이 책임을 세부적으로 다루지 않는다. 따라서 "pVM 생명주기(DP-01)의 하위 절차인가, TEE 경계의 독립 회수 책임(DP-05 확장 또는 신규)인가"를 판정해야 하며, 현재 어떤 문서도 이 판정을 내리지 않았으므로 NEW-DP 후보로 고정한다.

### G-08. 시스템 전체 TCB/공격자 모델/신뢰 앵커 범위

- 원문 근거: appendix 10/15(미열람), `docs/99_tcb_basics.md`, `docs/99_trust_boundary_qna.md`, `docs/DP/DP-C-01.md`(**확정 상태**, AT-1~AT-6 공격자 모델, TCB 후보 A/B/C 평가 후 A 채택 + 앵커 우선순위 규칙 결정).
- 연결 요구 ID: QA-01(구 스킴), SEC-01~06 전반의 전제.
- 잠정 분류: **BASELINE-CONSTRAINT**
- 이유: `docs/DP/DP-C-01.md`가 이미 두 후보 비교(A 최소 TCB / B 서비스 pVM 확장 / C TrustZone 앵커)를 거쳐 "A를 기본 골격으로, 신뢰 앵커 우선순위(EL2→TEE→조건부 서비스 pVM)"를 **확정**했고, 이 결정은 "후속 DP에 주는 전제"로 DP-C-02~C-08 전체에 배분된다. 즉 이것은 개별 문제의 결정축이 아니라 문제 1~3을 포함한 모든 후보가 공유해야 하는 고정 전제다. 다만 `docs/DP/DP-C-01.md`는 `docs-align`에는 없는 문서이므로, docs-align-full 관점에서는 "다른 계열 문서의 기존 결론"으로만 참고(2.1절 규칙)하고, 문제 1~3과 신규 DP 각각의 문제 상황에 이 TCB 규칙을 baseline으로 명시해야 한다.

### G-09. 작은 영구 상태/작은 파일 보관 — 문제 3과의 중복 가능성

- 원문 근거: appendix 15(미열람), `docs-align/품질위협_문제3_pVM수명_암호화파일_유실.md` 2절("**RPMB를 사용하지 않는 기준선**에서는..."), `docs/99_secure_storage.md`(RPMB 상세), `docs/DP6.md`(구 스킴 S6-1~S6-6 및 T-1/T-2 2-트랙 후보, 트랙 B가 GP Trusted Storage+RPMB로 소용량을 담당).
- 연결 요구 ID: SEC-05, PERF-07.
- 잠정 분류: **충돌 플래그 — SUBDECISION 잠정, 사용자 확인 필요**
- 이유: `docs/DP6.md`의 2-트랙 후보(T-1/T-2)는 정확히 G-09가 예상한 대로 "용량이 아니라 책임/수명/신뢰 primitive 차이"로 소용량 트랙(RPMB 기반)과 대용량 트랙(블록 계층)을 분리하는 것이 타당함을 보여준다. 이 점에서는 문제 3의 저장 수명/입출력 책임 결정축과 같은 상위 질문(보관 주체를 어디에 둘 것인가)의 세분화이므로 SUBDECISION으로 볼 수 있다. **그러나 `docs-align/품질위협_문제3...md`는 RPMB를 명시적으로 "사용하지 않는 기준선"으로 고정**하고 있어, RPMB를 핵심 배경으로 삼는 `DP6.md`의 소용량 트랙 설계와 **baseline이 정면으로 충돌**한다. 이 충돌은 신규 후보 생성 이전에 해소해야 할 사항이며, 이번 단계에서는 판정을 SUBDECISION으로 잠정 고정하되 RPMB 사용 여부 자체를 확인 필요 항목으로 별도 기록한다.

### G-10. pVM 간 버퍼 전달 문제의 4개 결정축 대 DP-03/03-A/03-B/03-C 커버리지

- 원문 근거: `docs-align/품질위협_문제2_pVM간_데이터전달.md`, `docs-align/후보구조_문제2_pVM간_데이터전달.md`(미열람, 인벤토리만 확인), `docs-dp/DP-03.md`, `DP-03-A.md`, `DP-03-B.md`, `DP-03-C.md`.
- 연결 요구 ID: FR-05, SEC-01, PERF-02, AVL-04.
- 잠정 분류: **축별로 분리 판정** (`DP-03`: NEW-DP 후보, `DP-03-A`: COVERED 가능성 높음, `DP-03-B`: COVERED, `DP-03-C`: NEW-DP 후보)
- 이유(축별):
  - **DP-03(요청이 Host를 거칠지)**: 문제 2 문서는 "신뢰 중재자"의 존재만 전제하고 Host 중계 여부 자체를 결정 변수로 명시하지 않는다. 부가 정보 노출(누가 송수신자/순서를 관찰하는가)이라는 새 위험을 다루므로 NEW-DP 후보다.
  - **DP-03-A(버퍼 논리적 소유권 — 중앙 pool vs 송신 pVM)**: PLAN 3절의 문제 2 결정축 요약 자체가 "프레임별 페이지 소유권 전환과 사전 등록 보호 버퍼 풀/slot 사용권"이라고 명시하므로, 이 축은 문제 2의 원래 결정축과 사실상 동일한 질문이다. **COVERED 가능성이 높다** (단, `후보구조_문제2.md` 본문 대조가 필요해 현재는 "가능성 높음"으로만 고정).
  - **DP-03-B(매핑 수명 — 프레임별 대여 vs 상주 ring)**: 문제 2 문서의 "핵심 트레이드오프" 절이 이미 "프레임마다 권한을 전환하면 최소 권한은 강화되지만 Stage-2/SMMU 전환 비용이 증가한다" / "고정 공유 메모리 풀은... 공격 표면과 메모리 사용량이 증가한다"는 정확히 동일한 트레이드오프를 서술한다. **COVERED**로 판정한다.
  - **DP-03-C(grant 정책·lease 원장을 EL2가 가질지, 분리된 정책 서비스가 가질지)**: 문제 2 문서는 EL2/신뢰 중재자를 단일체로 전제하고 정책 소유를 분리하는 대안을 논하지 않는다. TCB 크기(EL2 KLoC)를 가르는 새 축이므로 NEW-DP 후보다.

---

## 2. 4.2절 목록 밖 보조 신호 판정

| 묶음 | 원문 근거 | 연결 요구 ID | 잠정 분류 | 이유 |
|---|---|---|---|---|
| 자원/운영(생성 시점, vCPU/메모리 예약, QoS, Host 과부하 간섭) | `docs/07_decision_point_candidates.md` DP-B2·DP-E1, `docs-dp/DP-LIST.md` 5절("pVM 자원 예약량과 생성 시점은 DP-01의 하위 결정으로 둔다", "DP-E1... 제외하고 후보 문서에 남긴다") | QA-06(구 스킴), PERF-01 | **SUBDECISION(생성시점, DP-01 하위) + 보류된 별도 후보(QoS, DP-E1)** | `docs-dp`가 생성 시점은 이미 DP-01 하위로, QoS/스케줄링은 별도 미선정 후보로 명시적으로 나눠 두어 그 판정을 그대로 승계한다. |
| 실행 파이프라인(동기/비동기, interrupt/polling, descriptor·buffer join/timeout) | `docs/07_decision_point_candidates.md` DP-P2, `docs-dp/DP-LIST.md`("DP-P2는... 선정 목록에서 제외하고 후보 문서에 남긴다") | PERF-02, PERF-04 | **SUBDECISION(문제 2/DP-03-B 계열) — 보류된 후보** | G-05와 동일 계열. `docs-dp`가 이미 DP-03의 하위/보류 후보로 분류했다. |
| Workload 진화(manifest schema, topology, API 협상) | `docs/07_decision_point_candidates.md` DP-S1(→DP-02 병합), DP-S2(제외), DP-E3(보류) | EXT-01, EXT-02, QA-08(구 스킴) | **혼합: SUBDECISION(schema, DP-02 흡수) / OUT-OF-SCOPE(2-domain 고정 확장, DP-S2) / 보류(API 버저닝, DP-E3)** | `docs-dp/DP-LIST.md` 5절이 세 항목을 각각 다르게 처리한다고 명시했다. |
| HW 진화(device class 추상화, SoC별 adapter) | `docs/07_decision_point_candidates.md` DP-S3, `docs-dp/DP-LIST.md`("Camera/AI HW로 한정한 FR-04의 현재 범위 밖이므로 선정하지 않는다") | FR-04 관련이나 범위 밖 | **OUT-OF-SCOPE** | 명시적 배제 근거 존재. |
| 모델 운용(가중치 reload/cache/hot swap) | `docs/07_decision_point_candidates.md` DP-P3, `docs-dp/DP-LIST.md`("AI Workload와 pVM 자원 수명의 하위 구현으로 둔다") | PERF-02(추론시작지연) | **SUBDECISION** | 명시적 하위 구현 분류. |
| 증빙/감사(attestation, 격리 증빙, 변조방지 로그) | `docs/07_decision_point_candidates.md` DP-E2, `docs-dp/DP-LIST.md`("서로 다른 결정 축을 섞고 있으며, fleet 감사 체계는 현재 개발 범위 밖이므로 선정하지 않는다") | SEC-07, VOS-13, VOS-15 | **OUT-OF-SCOPE(fleet 감사) + EVIDENCE-ONLY(단일 pVM 격리 증빙 시험 방법)** | 축이 섞여 있다는 지적과 시험 방법 성격이 둘 다 존재. |
| 제품 운영(OTA/rollback, fleet, SLA/MTBF, glass-to-glass, 다중 stream) | `docs/03_qa_quality_scenarios.md` EXT-04/05, AVL-06/07, PERF-05/06, `docs-dp/DP-LIST.md`("원격 업데이트, 다수 로봇 운영과 감사 체계는... 개발 범위 밖이거나... 운영 결정으로 둔다") | EXT-04/05, AVL-06/07, PERF-05/06 | **OUT-OF-SCOPE** | 아래 3절에서 개별 재확인. |
| API/사용성(비보안 전문가용 단순 API) | `docs/07_decision_point_candidates.md` DP-A2, `docs-dp/DP-LIST.md`("서로 다른 신뢰 경계를 만드는 두 후보가 없으므로 선정하지 않는다") | VOS-14 | **OUT-OF-SCOPE** | 명시적 배제(신뢰경계 차이 없음). |
| 실행 환경(guest OS/RTOS/unikernel, 실물 HW vs simulator) | `docs/07_decision_point_candidates.md` DP-B1, `docs-dp/DP-LIST.md`("제품과 런타임 선택이므로 선정하지 않는다"), `docs-new` DP-6(PoC 검증 환경 선택) | R-4 관련이나 범위 밖 | **OUT-OF-SCOPE(제품 선택) / EVIDENCE-ONLY(검증환경, PoC DP-6은 시험 방법 선택)** | 제품/구현 선택 및 시험 방법은 DP 대상이 아니라는 PLAN 2단계 판정 기준 3·10항에 해당. |

---

## 3. PLAN이 명시적으로 지정한 개별 항목 재확인

### 3.1 DP-07 목록 불일치

G-06에서 처리. `docs-dp/DP-07.md` 존재, `docs-dp/DP-LIST.md` 선정 목록·의존관계도·제외목록 어디에도 미등장 — 누락 사실 확인됨.

### 3.2 pVM 소멸 시 TEE 세션/자원 정리

G-07에서 처리. `docs-dp/DP-LIST.md` 5절이 "별도 DP 후보로 남긴다"고 스스로 명시한 미확정 항목.

### 3.3 Reference Scenario 2단계("요청 권한/정책 확인") 매핑 공백

- 원문 근거: `docs/05_decision_points.md` 4절 표 및 261행("2단계의 요청 권한 및 정책 확인은... 횡단 결정으로 본 문서의 DP 범위에서 제외하므로 표시하지 않는다"), `docs/99_reference_scenario_flow.md` 2단계 서술, `docs/DP/DP-C-02.md`(확정, SELinux 기반 pVM 리소스 권한 모델).
- 연결 요구 ID: 명시적 요구 ID 없음(원 시나리오 문서에 미부여).
- 잠정 분류: **NEW-DP 후보이나 사실상 DUPLICATE(다른 계열 문서에서 이미 확정)**
- 이유: `05_decision_points.md`(DP1~DP6 스킴)와 `docs-dp/DP-LIST.md`(DP-01~DP-06 스킴) 양쪽 모두 이 단계를 어떤 DP에도 매핑하지 않는다 — PLAN이 지적한 "어느 DP에도 매핑되지 않았다"는 사실이 두 문서 계열 모두에서 확인된다. 그러나 `docs/DP/DP-C-02.md`(서로 다른 문서 계열, `docs/DP/*`)는 이미 "pVM 생성/Workload 로딩/리소스/채널/HW IP 사용 요청"의 권한 결정·집행 모델을 SELinux 기반으로 **확정**했으며, 이는 Reference Scenario 2단계가 요구하는 "요청 권한 및 정책 확인"의 실질적 내용과 일치한다. 즉 이 신호는 G-03과 동일 사안이며, "매핑 공백"이라는 관찰은 DP1~DP6/DP-01~06 스킴 한정으로는 사실이지만 전체 저장소 기준으로는 이미 다른 계열에서 답이 존재하는 상태다.

### 3.4 metadata queue와 frame backing 분리

G-05에서 처리. SUBDECISION(DP-03/문제 2 계열)로 판정.

### 3.5 VOS-04/06/13/14 (Architectural Driver 직접 매핑 없음)

- 공통 근거: `docs/04_vos_requirement_matrix.md` — VOS-04, VOS-06, VOS-13, VOS-14 행 전체가 FR-01~06/QA-01~04/CS-01~02 열에 `O` 표시 없음(직접 확인).

| VOS | 원문(`docs/01_vos_collection.md`) | 잠정 분류 | 이유 |
|---|---|---|---|
| VOS-04 | "보안 기능의 전력/메모리 오버헤드는 탑재 가능 수준이어야 한다" | **BASELINE-CONSTRAINT(자원 예산, 공통 gate 후보)** | 특정 구조 결정의 트레이드오프가 아니라 모든 후보가 지켜야 할 자원 상한 기준이다. 문제 1(자원효율), 문제 2(자원효율 TBD), DP-07(자원효율 TBD), DP-03-A(자원효율 TBD) 등 여러 결정에 공통 KPI 출처로 배분되어야 하는 항목이며 그 자체가 두 후보 구조를 만들지 않는다. |
| VOS-06 | "2026-10-30까지 제한된 인력으로 E2E 데모를 완료해야 한다" | **OUT-OF-SCOPE(일정/자원 제약, 구조 결정 아님)** | 프로젝트 관리 제약이며 책임/실행위치/신뢰경계를 바꾸는 구조 변수가 아니다. DP 선정 규칙(제품/구현/시험방법 제외)과 같은 성격으로, DP 자체가 아니라 범위·우선순위 판단에만 영향을 준다. |
| VOS-13 | "Host 침해 시 격리 유지 여부를 객관적으로 검증할 수 있어야 한다" | **EVIDENCE-ONLY/OUT-OF-SCOPE** | 4.2절 "증빙/감사"(DP-E2) 신호와 동일 사안이며, `docs-dp/DP-LIST.md`가 이미 "서로 다른 결정 축을 섞고 있으며 범위 밖"이라고 배제했다. 시험 방법론 성격이 강해 PLAN 2단계 판정 기준 10항("검증 방법만 다른 경우 DP 아님")에 해당한다. |
| VOS-14 | "pVM API는 비보안 전문가도 사용할 만큼 단순해야 한다" | **OUT-OF-SCOPE** | `docs-dp/DP-LIST.md`가 DP-A2를 "신뢰 경계 차이가 있는 두 후보 없음"으로 명시 배제. 사용성 요구이며 구조 결정성(책임/실행위치/신뢰경계 변경)이 없다. |

### 3.6 SEC-07 / PERF-05 / PERF-06 / EXT-04 / EXT-05 / EXT-07 / AVL-06 / AVL-07 (운영 단계 항목)

공통 근거: `docs/03_qa_quality_scenarios.md`.

| ID | 원문 요약 | 잠정 분류 | 이유 |
|---|---|---|---|
| SEC-07 | 침해 탐지/감사증적, "제품 상용 운용 단계(fleet 운용 중)", CRA/GDPR 보고기한 | **OUT-OF-SCOPE(주) + SUBDECISION(부, 로그 저장소 위치)** | Environment 자체가 fleet 상용 운용으로 현재 개발 범위(00_overview.md 범위: pVM 관리/드라이버/E2E 통합/Secure OS 이식) 밖이다. 다만 `docs/DP/DP-C-01.md` 7.6절이 "탐지/로깅" DP에 "로그 저장소는 TCB 요소여야 한다"는 전제를 이미 남겨 두었으므로, 좁은 의미의 "변조 불가 로그 저장 위치" 축만은 향후 SUBDECISION 후보로 잔존한다. |
| PERF-05 | Glass-to-glass 지연(캡처→원격 운영자 화면), "상품 레벨 구성(인코딩/전송/표시 포함)" | **OUT-OF-SCOPE** | Artifact가 "캡처→파이프라인→인코딩→전송→운영자 화면"으로 레퍼런스 시나리오의 종단(판단 결과 전달)을 넘어선다. 00_overview.md 과제 범위표의 "포함" 항목(pVM 생명주기/드라이버/E2E 통합/Secure OS 이식)에 인코딩·전송·표시 파이프라인이 없다. |
| PERF-06 | 다중 카메라 스트림 동시 처리 | **COVERED(문제 2의 확장성 축에 흡수) 일부 + SUBDECISION(2-domain 초과 토폴로지)** | 문제 2 문서가 "송수신 pVM이 늘어날수록 점대점 경로와 권한 조합이 급증함"을 위협받는 품질 속성(확장성)으로 이미 명시한다. 다만 "물리 카메라 자체가 여러 개"인 토폴로지는 `docs-dp/DP-LIST.md`가 DP-S2를 "고정 2-domain 구조... 현재 선정 목록에서 제외"라 명시한 것과 같은 계열이라 SUBDECISION/보류로 남긴다. |
| EXT-04 | Fleet 배포 성공률(OTA wave) | **OUT-OF-SCOPE** | `docs-dp/DP-LIST.md` "원격 업데이트, 다수 로봇 운영... 개발 범위 밖" 명시. |
| EXT-05 | 배포 롤백(A/B 슬롯) | **OUT-OF-SCOPE** | 위와 동일 근거. |
| EXT-07 | API 계약 안정성(breaking change 0/릴리스) | **SUBDECISION/보류 후보(DP-E3)** | `docs-dp/DP-LIST.md`가 DP-E3을 "제외하고 후보 문서에 남긴다"로 명시 — 완전 배제가 아니라 보류이며, 승격 시 문제 1~3과 무관한 독립 인터페이스-버저닝 축이 될 수 있다. |
| AVL-06 | 서비스 가동률(SLA, 월간) | **OUT-OF-SCOPE(합성 지표)** | "시장 AMR SLA" 출처, fleet 월간 가동률이며 AVL-01~05(이미 문제 1/DP-01/DP-07 등에 흡수된 장애격리·복구 게이트)의 하류 합성치다. 그 자체로 두 구조 후보를 만드는 결정축이 아니다. |
| AVL-07 | SW 기인 MTBF(fleet 누적) | **OUT-OF-SCOPE(합성 지표)** | 위와 동일 성격. fleet 신뢰성 통계이며 개별 구조 결정 변수가 아니다. |

---

## 4. 요구 추적성/ID 충돌 메모 (근거 원장 예비 기록)

- **QA-ID 체계 3중 충돌 확인**: (a) `docs-align/품질속성_QA_Measure_ISO25010.md`의 QA-01~08(성능/기밀성/무결성/기능정확성/신뢰성/복구성/자원사용성/유연성), (b) `docs/05_decision_points.md`(구 DP1~DP6 스킴)의 QA-01~08(성능·확장성·실시간·강건성 등, (a)와 전혀 다른 정의), (c) `docs/04_architectural_drivers.md`의 QA-01~04(보안/확장성/성능/강건성, (a)(b)와 또 다름). 동일 ID가 디렉터리·문서 계열별로 다른 의미를 가지므로 PLAN 1.4절 규칙대로 원문 ID를 유지하되 근거 원장에서 별도 정규화 ID(예: `QA-01(align)`, `QA-01(구DP)`, `QA-01(driver)`)를 부여해야 한다.
- **RPMB 사용 여부 baseline 충돌**: `docs-align/품질위협_문제3...md`는 RPMB 미사용을 기준선으로 고정하나, `docs/DP6.md`(및 `docs/99_secure_storage.md`)는 RPMB를 소용량/rollback 방지의 핵심 메커니즘으로 전제한다(G-09 참조). 사용자 확인 필요 항목으로 남긴다.
- **VOS 번호 재사용 없음 확인**: `docs/01_vos_collection.md`의 VOS-01~16과 `docs-align` 문서들이 인용하는 VOS-01/02/08/09는 동일 정의로 일관됨(충돌 없음).

---

## 5. 파일/이미지 인벤토리 점검 결과 (누락 여부)

### 5.1 전체 파일 목록은 확정, 내용 검토 완료/미완료 구분

이번 단계 1 검토에서 **원문을 직접 읽고 인용한 파일**은 아래와 같다(경로 생략, 디렉터리별):

- `docs-align`: `품질위협_문제1/2/3*.md`, `과제의_필요성_품질_위협_3가지_문제점.md`, `슬라이드14_16_설계고려사항_다이어그램_검토.md`, `슬라이드_품질위협_문제1/2/3*.md`, `DP-RULE.md`, `후보_구조_작성_규칙.md`, `후보_구조_품질_평가_규칙.md`, `품질속성_QA_Measure_ISO25010.md`, `품질속성_Security.md`, `슬라이드_작성원칙.md`.
- `docs`: `00_overview.md`, `01_vos_collection.md`, `02_reference_scenario.md`, `02_requirements.md`, `03_qa_quality_scenarios.md`, `03_utility_tree.md`, `04_architectural_drivers.md`, `04_vos_requirement_matrix.md`, `05_decision_points.md`, `07_decision_point_candidates.md`, `08_DP_problem.md`, `08_DP-A1_ccandidates.md`, `08_DP-C1_candidates.md`(내용 없음, 빈 파일 확인), `99_additional_decision_points.md`, `99_ffa.md`, `99_pvm_dmabuf_transfer.md`, `99_pvm_dmabuf_transfer-codex.md`, `99_pvmfw.md`, `99_qualcomm_nvidia_gp.md`, `99_reference_scenario_flow.md`, `99_secure_storage.md`, `99_tcb_basics.md`, `99_trust_boundary_qna.md`, `99_tzdaemon.md`, `99_virtio_vsock.md`, `DP6.md`, `DP-C1.md`(1~440행만 읽음, 441~532행 미확인), `DP/DP-C-01.md`, `DP/DP-C-02.md`, `DP/DP-C-03-sub-candidates.md`.
- `docs-new`: `poc-customizations-and-decision-points.md`(디렉터리 내 유일 파일, 전체 읽음).
- `docs-dp`: `DP-01.md`, `DP-01-배경.md`, `DP-01-후보구조.md`, `DP-02.md`, `DP-03.md`, `DP-03-A/B/C.md`, `DP-04.md`, `DP-05.md`, `DP-06.md`, `DP-07.md`, `DP-LIST.md`, `DP-RULE.md`(모두 전체 읽음).

### 5.2 확인된 누락(미열람) — 후속 단계에서 반드시 보완 필요

- **docs-align 후보 구조 3종 미열람**: `후보구조_문제1_HW공유.md`, `후보구조_문제2_pVM간_데이터전달.md`, `후보구조_문제3_암호화파일_영구보관.md`. G-06/G-10 판정에서 "문제 1/2의 기존 후보 결정축과 완전히 동일한지"를 확정하려면 이 세 파일의 본문 대조가 필요하다(PLAN 2.2절 규칙상 신규 후보 입력으로는 쓰지 않지만, COVERED/DUPLICATE 판정의 근거로는 열람이 필요).
- **이미지 전수 미열람**: `docs-align/SW_Architect_개인과제/` 슬라이드 33장(소문자 변형 포함 35개 파일), `SW_Architect_개인과제_appendix/` 17장, 인포그래픽 PNG 3개(`인포그래픽_품질위협_문제1/2/3*.png`), `docs-dp/DP-01-배경.png`. PLAN 2.3절이 요구하는 "이미지마다 슬라이드 번호, 보이는 요구 ID, 문제 문장, 구조 단서 기록"을 이번 단계에서 수행하지 못했다. G-01(슬라이드 31~32), G-02(appendix 10~11/15), G-03(appendix 13/15), G-04(appendix 15), G-08(appendix 10/15), G-09(appendix 15) 등 다수 신호의 1차 근거가 이미지이므로, 이 공백은 판정의 신뢰도에 직접 영향을 준다. 현재 판정은 모두 텍스트 근거(문서 인용)만으로 내려졌고 이미지 자체는 대조하지 못했다.
- **docs 미열람 파일**: `01_use_case.md`, `01_use_case_spec.md`, `01_use_case_spec.docx`, `03_quality_attribute_specification.md`, `05_context_view.md`, `09_qs.md`, `09_qs_evaluation.md`, `AGENTS.md`, `TCB.md`, `99_communication.md`, `99_ios_standard.md`, `99_middleware_qa.md`, `99_qa_security.md`, `99_security_qa_metrics.md`, `DP_old/`(8개 파일 전부), `DP/temp.md`(0바이트로 추정, 목록에서만 확인). 이 중 `DP_old/`는 파일명상 이전 버전(구 DP-C 계열)으로 추정되나 확인하지 않았으므로 "읽지 않음"으로만 표기하고 대체/보완 관계를 단정하지 않는다.
- **docs-align의 임시/바이너리 파일**: `ppt/.$SW_Architect_개인과제.drawio.dtmp`는 git status상 미추적 임시 파일로 확인되나 형식·판독 가능 여부는 점검하지 않았다.

### 5.3 결론

전체 파일 목록(`find` 결과)은 고정했고 주요 텍스트 근거는 확보했으나, **이미지 전수 시각 검토와 `docs-align`의 후보 구조 3종 본문 대조는 이번 단계에서 완료하지 못했다.** PLAN 8.1절의 "인벤토리 완료 조건"(본편/appendix/인포그래픽 시각 검토 여부 표시)은 미충족 상태이며, 다음 단계로 넘어가기 전에 별도 인벤토리 문서(`00_소스_인벤토리.md`)에서 이 공백을 명시적으로 메워야 한다.
