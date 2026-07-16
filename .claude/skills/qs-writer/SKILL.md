---
name: qs-writer
description: 이 프로젝트의 Quality Scenario/Specification(QS) 작성 스킬. 품질 속성 시나리오, QS, 품질 시나리오, Response Measure, KPI, 별점 평가 기준 작성 요청 시 사용한다. ISO/IEC 25010 품질 모델과 ISO/IEC 25023 품질 측정 지표에 근거하여 QS와 평가 기준 문서를 작성한다.
---

# QS 작성 스킬 (qs-writer)

본 스킬은 pKVM 기반 가상화 보안 Framework 프로젝트의 Quality Scenario/Specification(QS)을 작성하는 절차와 형식을 정의한다.

## 1. 표준 근거

QS 작성은 다음 두 표준에 근거한다.

- **ISO/IEC 25010** (System and software quality models): 품질 특성/하위 특성의 분류 기준. 모든 QS는 ISO 25010의 품질 특성 및 하위 특성 중 하나에 매핑되어야 한다.
  - 품질 특성: Functional Suitability, Performance Efficiency, Compatibility, Interaction Capability(Usability), Reliability, Security, Maintainability, Flexibility(Portability), Safety
- **ISO/IEC 25023** (Measurement of system and software product quality): Response Measure의 측정 함수(measurement function) 도출 기준. 해당 하위 특성에 대해 ISO 25023이 정의한 측정 지표(예: X = A/B 형태의 측정 함수)가 존재하면 이를 우선 사용하고, 프로젝트 특성상 변형이 필요하면 변형 근거를 명시한다.

## 2. QS 형식

각 QS는 다음 7개 필드를 갖는 표로 작성한다. 필드 순서와 명칭을 변경하지 않는다.

| Field | 작성 규칙 |
|-------|-----------|
| Description | 시나리오가 보장하려는 품질을 한 문장으로 서술. ISO 25010 품질 특성/하위 특성 매핑을 함께 표기 |
| Source | 자극(Stimulus)을 발생시키는 주체 (공격자, 사용자, 외부 시스템, 개발자, 운영자 등) |
| Stimulus | 시스템에 도달하는 구체적 자극 (요청, 공격, 장애, 변경 등) |
| Environment | 자극이 발생하는 시점의 시스템 상태 (정상 운용 중, 부하 상태, 개발/통합 단계 등) |
| Artifact | 자극의 영향을 받는 시스템 요소 (설계 대상인 Framework 내부 요소로 한정. Camera/AI Framework 등 시스템 외부 요소는 Artifact가 될 수 없음) |
| Response | 자극에 대해 시스템이 보여야 하는 동작 |
| Response Measure | Response의 달성 여부를 판정하는 정량 지표. 반드시 KPI를 포함 (3절 규칙 적용) |

QS ID는 `QS-{품질특성 약어}-{번호}` 형식을 사용한다 (예: QS-SEC-01, QS-PERF-01, QS-AVAIL-01).

## 3. KPI 작성 규칙 (필수)

Response Measure에 포함되는 KPI는 다음 규칙을 반드시 지킨다.

1. **가정치 금지**: 작성자가 임의로 정한 수치("적당히 1초 이내" 등)를 사용하지 않는다. 모든 수치는 조사를 통해 확보한 객관적 근거를 갖는다.
2. **근거 조사 우선순위**: 다음 순서로 근거를 조사한다 (WebSearch/WebFetch 활용).
   - (1) 국제 표준/규격 문서 (ISO/IEC 25023의 측정 함수와 기준, 관련 도메인 표준)
   - (2) 학술 논문, 공개 벤치마크 (예: 가상화 오버헤드, vsock/공유메모리 처리량, pKVM 성능 측정 논문)
   - (3) 공식 기술 문서 (Linux 커널 문서, ARM 아키텍처 문서, AVF/pKVM upstream 문서)
   - (4) 산업 보고서, 벤더 공식 자료
3. **근거 명기**: 각 KPI에는 근거 출처(문서명, 저자/기관, 연도, URL)를 반드시 병기한다. QS 표 아래에 "KPI 근거" 절을 두어 정리한다.
4. **근거 부재 시 처리**: 조사로도 객관적 근거를 찾지 못한 경우 수치를 지어내지 않고 `TBD(근거 조사 필요)`로 표기한 뒤 사용자에게 보고한다.
5. **측정 가능성**: KPI는 시험/측정 방법이 존재해야 한다. 측정 방법(도구, 시험 절차)을 한 줄 이상 명시한다.

## 4. 별점 평가 기준 (별도 문서)

QS별 평가는 별 3개 척도로 진행하며, 평가 기준은 QS 본문이 아닌 **별도 문서**로 작성한다.

1. **파일 분리**: 평가 기준 문서는 QS 문서와 같은 번호 prefix에 `_evaluation` suffix를 붙여 분리한다 (예: QS 문서가 `06_qs.md`이면 평가 문서는 `06_qs_evaluation.md`).
2. **별점 정의**: 각 QS에 대해 별 3개/2개/1개의 판정 기준을 정량적으로 정의한다.
   - 별 3개: KPI 목표치를 완전히 충족
   - 별 2개: 부분 충족 (허용 구간을 정량적으로 정의)
   - 별 1개: 미충족 (하한선을 정량적으로 정의)
3. **기준의 근거**: 3/2/1개를 가르는 경계값 자체도 가정치가 아니라 객관적 근거(표준의 등급 기준, 벤치마크 분포, 산업 통계 등)를 가져야 하며, 각 경계값에 출처를 병기한다. 3절의 KPI 작성 규칙(근거 조사, 근거 명기, TBD 처리)을 경계값에도 동일하게 적용한다.
4. **평가 문서 형식**: QS ID별로 다음 표를 작성한다.

| QS ID | 별 3개 기준 | 별 2개 기준 | 별 1개 기준 | 경계값 근거 |
|-------|------------|------------|------------|-------------|

## 5. 작성 절차

1. 대상 품질 속성을 확인하고 ISO 25010 품질 특성/하위 특성에 매핑한다.
2. ISO 25023에서 해당 하위 특성의 측정 지표를 확인하고 Response Measure의 측정 함수를 도출한다.
3. KPI 수치의 근거를 조사한다 (3절 우선순위에 따라 WebSearch/WebFetch로 조사하고 출처를 수집).
4. QS 표를 작성한다 (2절 형식).
5. 별점 평가 기준 문서를 별도 파일로 작성한다 (4절 형식).
6. 검증: 필드 7개 완비, ISO 25010 매핑 존재, 모든 KPI에 근거 출처 존재, 평가 문서 분리 여부를 확인하고 결과를 보고한다.
7. 프로젝트 규칙에 따라 git commit/push 한다.

## 6. 프로젝트 공통 규칙

- 문서는 한글(UTF-8)로 작성하고 이모지를 사용하지 않는다.
- 파일명은 생성 순서 `{nn}_` prefix 관례를 따른다.
- 설계 대상은 pKVM 기반 가상화 보안 Framework뿐이다. Camera Framework, AI Framework, Host Application, Workload, pKVM 커널(EL2), Secure OS는 시스템 외부이므로 QS의 Artifact로 지정하지 않는다.
