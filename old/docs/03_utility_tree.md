# 품질 속성 선정 및 측정 (Utility Tree)

> 본 문서는 핵심 품질 속성을 ISO/IEC 25010 품질 모델에 따라 **성능/신뢰성/보안성/유지보수성/이식성**의 5개 품질 특성과 8개 부특성으로 분류하고,
> 각 리프 지표의 측정 함수(ISO/IEC 25023), KPI, 중요도와 난이도, 우선순위를 Utility Tree로 구조화하여 정리한다.
>
> 진행 순서: 요구사항 수집 → 요구사항 도출 → **품질 속성 선정 및 측정(본 문서)** → Architectural Driver 선정

관련 문서: [`02_requirements.md`](02_requirements.md), [`03_quality_attribute_specification.md`](03_quality_attribute_specification.md), [`05_decision_points.md`](05_decision_points.md), [`99_ios_standard.md`](99_ios_standard.md), [`99_reference_scenario_flow.md`](99_reference_scenario_flow.md)

---

## 1. 평가 및 측정 기준

| 구분 | 기준 |
|---|---|
| 품질 특성/부특성 | ISO/IEC 25010:2023 품질 모델의 품질 특성과 부특성에 매핑한다 |
| 측정 함수 | ISO/IEC 25023의 측정 지표(측정 함수)를 우선 적용한다. 조사 내역은 `99_ios_standard.md`를 따른다 |
| 중요도 | 미충족 시 비즈니스 영향(사업 진입, 제품 출시, 사고 피해). H/M/L |
| 난이도 | 아키텍처 구조에 미치는 영향과 달성의 기술적 어려움. H/M/L |
| 우선순위 | 중요도와 난이도 평가를 종합하여 상위 5개 지표에 1~5순위를 부여한다. 나머지는 미부여(-) |

> 수치 목표는 협의 및 PoC 결과에 따라 보정한다.

---

## 2. Utility Tree

```plantuml
@startmindmap
<style>
mindmapDiagram {
  boxless {
    FontColor #1F2933
  }
}
</style>
*[#FFFFFF] Utility
**[#FFFFFF] 성능 (Performance Efficiency)
***[#D6EAF8] 반환 시간 적정성 (Turnaround time adequacy)
****_ 카메라 영상 입력부터 Host Application 전달 완료까지의\n평균 시간(ms)이 목표 시간을 만족함\n(KPI: 10ms / 720p, RGB24, AI 추론 구간 제외)
***[#D6EAF8] 평균 메모리 사용률 (Mean memory utilization)
****_ 다중 시나리오가 운용 중일 때 사용되는 메모리 사용량을\n가능한 낮게 유지함 (KPI: 낮을수록 좋음, 상대 평가)
**[#FFFFFF] 신뢰성 (Reliability)
***[#D6EAF8] 고장 회피 (Failure avoidance)
****_ 결함 테스트에서 시스템에 Critical 고장이\n발생하지 않음 (KPI: 100%)
**[#FFFFFF] 보안성 (Security)
***[#D6EAF8] 접근 통제성 (Access controllability)
****_ 도메인 간 전달되는 데이터는 시스템에 의해서\n접근 통제됨 (KPI: 100%)
**[#FFFFFF] 유지보수성 (Maintainability)
***[#FFFFFF] 컴포넌트 결합도 (Coupling of components)
****_ 신규 요구사항 추가 시 다른 모듈에 영향을 주지 않는\n모듈의 비율을 최대화함 (KPI: 높을수록 좋음, 상대 평가)
***[#D6EAF8] 자산 재사용성 (Reusability of assets)
****_ 신규 시나리오 추가 시 전체 자산의 100%가\n재사용 가능하도록 설계/구축됨 (KPI: 100%)
**[#FFFFFF] 이식성 (Portability)
***[#FFFFFF] 하드웨어 환경 적응성 (Hardware environmental adaptability)
****_ SoC 변경에 따라 변경되는 모듈이 없음 (KPI: 0%)
***[#FFFFFF] 시스템 소프트웨어 환경 적응성 (System software environmental adaptability)
****_ OS update에 따라 변경되는 모듈 수를 최소화함\n(KPI: 낮을수록 좋음, 상대 평가)
@endmindmap
```

> 파란색 배경 노드는 우선순위 1~5 지표이다.

---

## 3. 측정 지표 및 측정 방법

| 품질 속성 | 설명 | 중요도 | 난이도 | 우선순위 |
|---|---|:---:|:---:|:---:|
| 성능 (반환 시간) | 카메라 영상 입력부터 Host Application 전달 완료까지의 평균 시간(ms)이 목표 시간을 만족해야 한다.<br>[X <= B. A: 카메라 영상 입력부터 Host 전달 완료까지의 평균 시간(ms)] KPI: 10ms (720p, RGB24, AI 추론 구간 제외) | H | H | 1 |
| 성능 (메모리 사용량) | 다중 시나리오가 운용 중일 때 사용되는 메모리 사용량을 가능한 낮게 유지해야 한다.<br>[X = A. A: 다중 시나리오에 사용되는 총 메모리 크기.] KPI: 낮을수록 좋음 (시나리오에 따라 사용량이 다름으로 상대 평가) | H | H | 2 |
| 신뢰성 (고장 회피) | 결함 테스트에서 시스템에서 Critical 고장이 발생되면 안된다.<br>[X = A/B. A: 고장으로 이어지지 않은 테스트 수, B: 전체 테스트 수] KPI: 100% | H | M | 5 |
| 보안성 (접근 통제) | 도메인 간 전달되는 데이터는 시스템에 의해서 접근 통제되어야 한다.<br>[X = A/B. A: 접근 통제된 기밀 데이터 항목 수, B: 접근 통제가 요구되는 기밀 데이터 항목 수] KPI: 100% | H | M | 3 |
| 유지보수성 (모듈 결합도) | 신규 요구사항 추가시 다른 모듈에 영향을 주지 않는 모듈의 비율이 최대가 되어야 한다.<br>[X = A/B. A: 영향을 주지 않는 모듈 수, B: 전체 모듈 수] KPI: 높을수록 좋음 (상대 평가) | M | M | - |
| 유지보수성 (모듈 재사용) | 신규 시나리오 추가 시 전체 자산의 100%가 재사용 가능하도록 설계/구축되어야 한다.<br>[X = A/B. A: 재사용되는 모듈수, B: 전체 모듈수] KPI: 100% | H | M | 4 |
| 이식성 (SOC 변경) | SoC 변경에 따라 변경되는 모듈이 없어야 한다.<br>[X = A/B. A: 변경되는 모듈 수, B: 전체 모듈 수] KPI: 0% | M | M | - |
| 이식성 (OS update) | OS update에 따라 변경되는 모듈 수를 최소화하여야 한다.<br>[X = A/B. A: OS update시 변경이 필요한 모듈 수, B: 전체 모듈수] KPI: 낮을수록 좋음 (상대평가) | M | M | - |

---

## 4. 근거 출처

- ISO/IEC 25010:2023 (System and software quality models) — 품질 특성/부특성 분류 기준
- ISO/IEC 25023 (Measurement of system and software product quality) — 측정 함수 도출 기준
- [`99_ios_standard.md`](99_ios_standard.md) — 본 프로젝트의 ISO 25010/25023 조사 정리 문서
