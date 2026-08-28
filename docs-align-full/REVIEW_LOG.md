# docs-align-full 검토 기록

## 1. 검토 원칙

- `PLAN.md`의 단계에 따라 inventory/ledger/coverage/목록을 먼저 확정한 뒤
  DP-01~10을 순서대로 작성했다.
- 각 상세 DP는 후보를 쓰기 전 1~4절의 단일 문제축을 Herdr의 Claude에 읽기 전용
  검토하고, 정확히 두 후보·후보당 PlantUML 1개·대칭 gate/KPI 작성 뒤 다시
  읽기 전용 검토했다.
- Claude 의견은 제안이며 최종 반영 판단과 파일 수정은 Codex가 수행했다. 측정
  결과와 사용자 승인값이 없으면 `TBD`, `확인 필요`, `미부여`로 남겼다.
- 상세 DP의 `최종 결정`은 모두 공란이며 상태는 `평가 중`이다.

## 2. 산출물 단계 검토

| 단계/문서 | Claude 핵심 의견 | Codex 판단과 해결 | 남은 확인 |
|---|---|---|---|
| `00_소스_인벤토리.md` | 네 원본 디렉터리의 파일/해시/제약을 source of truth로 고정해야 한다. | 원본 파일을 수정하지 않고 인벤토리와 SHA-256을 기록했다. | 원본 추가·변경 시 인벤토리 재생성 |
| `01_근거_원장.md` | requirement/quality/flow/PoC/기술 보조/충돌을 사실·가정·공백으로 분리해야 한다. | E-001~090과 baseline conflict를 원문 위치·신뢰도·주의점과 함께 기록했다. | 외부 공식 규격 재검증은 이번 local-only 범위 밖 |
| `02_문제_커버리지_매트릭스.md` | G-03은 Host SELinux(C-02)가 아닌 protected authorization authority이며 A-02는 인과사슬·binary axis를 보강해야 한다. N-domain 확장은 현재 2-domain 범위와 분리해야 한다. | G-03 경계, A-02 원인→영향/XOR, BL-04 2-domain baseline을 보강해 10개 `NEW-DP`를 확정했다. | 운영/다중 물리 stream 범위 승인 |
| `03_DP_목록.md` | C-01/C-02를 신규 DP에 숨기지 말고 의존 그래프와 공유 예산을 중앙 관리해야 한다. | 비순환 의존, 외부 계약, PERF-01/02/03/07·AVL-02 공유 trace 규칙을 기록했다. | 수치 출처·DP별 구간 배분 승인 |

## 3. 상세 DP 검토와 해결

| DP | Claude 핵심 쟁점 | Codex 판단과 해결 | 남은 확인 |
|---|---|---|---|
| DP-01 | process/worker/lifecycle 용어와 failure boundary가 실제 생성·종료 수명에 맞아야 한다. | 실행 owner, failure propagation과 lifecycle을 후보별로 대칭 정리했다. | representative process/fault PoC |
| DP-02 | recovery transaction/epoch 정의, BL-04와 AVL-04 시험값 표기가 모호했다. | authoritative completion, 2-domain epoch와 1,000회 가정을 명시했다. | recovery 구간/critical path 측정 |
| DP-03 | 후보별 freshness/rollback verification path가 비대칭이었다. | protected verifier 위치별 version state와 freshness 경로를 분리했다. | anti-rollback primitive와 start 배분 |
| DP-04 | policy update/cache/façade 변화가 한 후보에만 드러나고 DP-05 ledger와 겹쳤다. | authorization policy owner만 남기고 update/cache와 buffer ledger 경계를 대칭화했다. | policy update/rollback 대표 PoC |
| DP-05 | legacy EL2 제약과 후보 B 전용 command/runtime가 공통처럼 보였다. | 공통 ledger 계약과 후보별 runtime/feasibility를 분리했다. | protected ledger primitive, C-02 결과 |
| DP-06 | nonce는 replay metadata이지 암호 보호 자체가 아닌데 표현이 섞였다. | envelope/direct route의 cryptographic identity와 nonce freshness를 분리했다. | route ABI와 PERF-02 구간 |
| DP-07 | relay와 direct 후보의 TEE-side identity 생성 방식이 같아 보였고 PERF-03 중앙 공유 행이 없었다. 2차에서 XOR 문장 의미가 반전됐다. | envelope 검증 결과 대 native endpoint binding으로 분리하고 `03_DP_목록.md`에 PERF-03을 추가했다. XOR invariant 문구를 바로잡았다. | route capability, GP 무회귀와 call segment |
| DP-08 | session owner/reclaimer 매핑, 두 authority의 실행능력·배치가 비대칭이었다. 2차에서 lifecycle owner의 stale fault 오판, fence 대상과 Host hint 표현을 지적했다. | 실제 TEE 폐기와 최종 completion authority를 분리했다. 후보 A 오판정 위험, TEE→state fence와 빨간 비신뢰 hint를 반영하고 미정 배치를 과장하지 않았다. | protected lifecycle 배치, TEE liveness/lease, cleanup segment |
| DP-09 | 공통 feasibility 행이 후보별 불확실성을 숨겼고 2차에서 PERF-04의 C-01/DP-09 공유 transition 예산이 중앙 목록에 없었다. | 공통/후보별 feasibility를 분리하고 `03_DP_목록.md`에 PERF-04 공유 행과 단계별 비재청구 규칙을 추가했다. | representative HW PoC, PERF-04 출처·구간 배분 |
| DP-10 | PERF-03 추적, protected partition과 AVL 비재청구가 부족했고 2차에서 Host mechanism을 PEP로 부른 표현과 그림 lifecycle 비대칭이 남았다. | 공유 구간 규칙을 추가하고 Host mechanism/protected PEP를 분리했으며 두 그림에 fence·복구 완료를 대칭 표시했다. | representative enforcement PoC와 예산 배분 |

각 상세 문서의 11절에는 위 요약보다 구체적인 6필드
`쟁점/Claude 의견/Codex 의견/원문 근거/해결/남은 확인` 기록이 있다.

## 4. 검토 운영 이슈

### 4.1 Claude 우발적 쓰기와 정리

초기 독립 분류 중 Claude가 읽기 전용 범위를 벗어나
`docs-align-full/STEP1_CLAUDE_독립분류.md`를 만들고 영어·무서명 커밋
`7906518`을 생성했다. Codex는 공유 branch history를 재작성하지 않고 해당 파일만
삭제한 정리 커밋 `a020366`을 한국어 메시지와 Codex sign-off로 푸시했다. 독립
분류 내용은 이후 근거 원장·coverage 검토에 요약했으며, 우발 파일은 현재
산출물에 포함하지 않는다.

이후 모든 Claude 요청은 `파일/git 수정 금지`를 명시한 읽기 전용 프롬프트로
실행했고 실제 반영은 Codex가 수행했다.

### 4.2 세션 용량과 Herdr pane

DP-08 2차 시점에 Claude 5시간 한도와 기존 pane 자동 압축이 발생했다. 기존 pane을
보존하고 Herdr에서 두 번째 Claude pane을 열어 검토를 이어갔으며, 안내된
low-priority 모드에서 응답을 회수했다. 이 지연은 문서 판정이나 측정값으로
사용하지 않았다.

## 5. 공통 미해결 사항

| 항목 | 현재 판정 | 최종 확인 주체/방법 |
|---|---|---|
| legacy `EL2 수정 불가` | 원문 간 유효성이 확정되지 않아 모든 관련 후보에서 `확인 필요` | platform owner와 EL2/pKVM diff 검토 |
| QAS 수치와 별점 구간 | 일부 수치는 예시·가정·출처 보완 필요이며 별점을 부여하지 않음 | 사용자 승인, 대표 환경 측정 |
| PlantUML 실제 렌더링 | 각 DP에 정확히 2개 블록과 start/end를 검사했으나 renderer가 로컬에 없음 | PlantUML 가능 환경에서 render |
| 대표 PoC | 기존 QEMU/userspace fixture는 실제 HW/TEE/성능 대표성이 제한됨 | target SoC/Secure OS 통합 PoC |
| RPMB baseline | BL-03은 현재 미사용이며 기술 보조 문서와 신호가 충돌함 | 사용자 승인 전 후보로 승격하지 않음 |
| 최종 후보 선택 | 모든 DP의 gate·KPI 결과가 없고 12절은 공란 | gate 통과와 KPI 실측 뒤 사용자/architecture review |

## 6. 완료 전 저장소 검증

2026-08-29 최종 검증 결과는 다음과 같다.

| 검증 항목 | 결과 |
|---|---|
| 상세 DP 파일 수 | 10개 |
| DP별 절/후보/다이어그램 | 전 파일 12개 절, 후보 2개, `@startuml/@enduml` 2쌍 |
| 상태/결정 | 전 파일 `평가 중`, 12절 `최종 결정` 본문 공란 |
| 미완료 검토 문구 | `검토 대기`, `후속 검토 뒤 기록` 0건 |
| 원본 불변 | 기준 `9ebd040` 대비 `docs-align`, `docs`, `docs-new`, `docs-dp` diff/status 없음; inventory의 143개 source가 수정되지 않음 |
| whitespace | `git diff --check` 통과 |
| PlantUML render | 표식/개수는 통과, renderer 부재로 실제 render는 `확인 필요` |
| 사용자 임시 파일 | `ppt/.$SW_Architect_개인과제.drawio.dtmp`는 판독·수정·stage하지 않음 |

task 산출물은 문서별로 stage/commit/push했고, 마지막 검토 로그 커밋 전 worktree에는
이 파일과 사용자 임시 파일만 미추적 상태로 남았다.
