# QA 품질 시나리오 명세

> 본 문서는 [`06_qa_utility_tree_metrics.md`](06_qa_utility_tree_metrics.md)의 4개 관점 28개 QA 각각을
> 6-파트 품질 속성 시나리오(Source / Stimulus / Environment / Artifact / Response / Response Measure)로 명세한다.
> 시나리오 형식은 [`03_quality_attribute_specification.md`](03_quality_attribute_specification.md)를 따르고,
> 응답 측정치는 `06_qa_utility_tree_metrics.md`의 게이트/KPI를 그대로 사용한다.
>
> 관련 문서: [`02_requirements.md`](02_requirements.md), [`05_decision_points.md`](05_decision_points.md), [`99_reference_scenario_flow.md`](99_reference_scenario_flow.md)
>
> 수치 목표는 가정치이며, 로봇 제조사 협의 및 PoC 결과에 따라 보정한다.

---

## 1. 보안 (Security)

### SEC-01: 기밀성 (Host 침해)

| Field | Specification |
|-------|---------------|
| Description | Host가 완전히 침해되어도 pVM 생명주기 전 구간에서 영상 원본, AI 모델 가중치, 추론 중간 데이터가 노출되지 않아야 한다. |
| Source | Host OS 루트 권한을 탈취한 공격자 |
| Stimulus | `/proc/kcore`, `/dev/mem`, DMA 경로를 통한 pVM 메모리 전체 덤프 시도 |
| Environment | Secure Vision AI 파이프라인 동작 중, 레퍼런스 시나리오 13단계 각각의 상태(특히 pVM 메모리 할당/회수 시점 포함) |
| Artifact | pVM 격리 메모리 내 영상 원본, AI 모델 가중치, 추론 중간 데이터 |
| Response | Stage-2 격리에 의해 모든 접근이 차단되고, pVM 내 주입한 canary 마커가 덤프 결과에서 검출되지 않으며, 비정상 접근 시도가 기록된다. |
| Response Measure | **게이트**: 격리 메모리 노출 0건 / **KPI**: 공격 벡터 자동화 커버리지 100%, TCB 규모(KLoC) 릴리스당 증가율 5% 이내, 경계 돌파 최소 공격 잠재력(CEM) 25점 이상 |
| 연관 | QA-01, DP1 |

### SEC-02: HW 접근 격리 (S2MPU)

| Field | Specification |
|-------|---------------|
| Description | Camera/AI HW 사용 주체 전환 시 S2MPU 권한 상태에 두 주체의 중첩 구간이 없어야 하고, 잔류 데이터가 다음 주체에 노출되지 않아야 한다. |
| Source | Camera/AI HW 사용을 경합하는 주체(보안 Workload와 Normal Camera Application) |
| Stimulus | 고빈도의 HW 사용 주체 전환 요청(경합 스트레스 하네스에 의한 강제 전환 포함) |
| Environment | 단일 Context Camera/AI HW를 Host와 pVM이 SW 중재로 시분할 공유 중 |
| Artifact | S2MPU 접근 권한 설정, HW 내부 버퍼의 잔류 데이터 |
| Response | 전환 시 이전 주체 권한 회수, 잔류 데이터 소거, 다음 주체 권한 부여가 원자적으로 수행되어 권한 중첩 구간이 발생하지 않는다. |
| Response Measure | **게이트**: 권한 중첩 0 / **KPI**: 무위반 누적 전환 10^6회, 잔류 데이터 스캔 커버리지 100% |
| 연관 | QA-02, DP4 |

### SEC-03: DMA 경로 격리

| Field | Specification |
|-------|---------------|
| Description | 침해된 Host가 DMA-capable 디바이스를 이용해도 자신에게 할당되지 않은 도메인의 메모리에 접근할 수 없어야 한다. |
| Source | DMA-capable 디바이스를 제어하는 침해된 Host(Thunderclap형 공격자) |
| Stimulus | 비할당 도메인 메모리(pVM 격리 영역)에 대한 DMA 읽기/쓰기 시도 |
| Environment | 보안 파이프라인 동작 중, Camera/AI HW가 pVM에 할당된 상태 |
| Artifact | pVM 격리 메모리, HW DMA 버퍼 |
| Response | SMMU/S2MPU 설정에 의해 비할당 도메인으로의 모든 DMA 접근이 차단된다. |
| Response Measure | **게이트**: 비할당 도메인 접근 0 / **KPI**: DMA 공격 벡터 카탈로그 구현율 100%(SMMU/S2MPU 설정 조합별 전수 시험) |
| 연관 | QA-02, DP4 |

### SEC-04: Workload 무결성 검증

| Field | Specification |
|-------|---------------|
| Description | Host의 파일시스템/로딩 경로가 침해되어도 변조되거나 미검증된 Workload 이미지가 pVM에 탑재되지 않아야 한다. |
| Source | Host 파일시스템과 Workload 로딩 경로를 장악한 공격자 |
| Stimulus | 서명/manifest/버전/해시가 변조된 Workload 이미지의 동적 탑재 요청 |
| Environment | 보안 Workload 동적 탑재 수행 중(레퍼런스 시나리오 3단계, UC-05) |
| Artifact | Workload 이미지/패키지, 서명 검증 및 로딩 경로 |
| Response | Host 침해와 독립인 신뢰 주체가 서명/무결성을 검증하고, 변조 이미지는 탑재를 거부하며 이후 단계를 진행하지 않는다. |
| Response Measure | **게이트**: 미검증 이미지 탑재 0건, 변조 이미지 탐지율 100% / **KPI**: 검증 소요 p99, IEC 62443-4-2 EDR 요구항목 충족률(SL2 100%, SL3 추적 목표 90% 이상) |
| 연관 | DP2, IEC 62443 |

### SEC-05: 저장 데이터 기밀성

| Field | Specification |
|-------|---------------|
| Description | Host 파일시스템이 침해되어도 저장 상태의 영상/AI 모델/추론 데이터의 평문과 암호화 키가 노출되지 않아야 한다. |
| Source | Host 파일시스템 접근 권한을 가진 공격자 |
| Stimulus | 저장된 영상/모델/추론 데이터 blob의 덤프 및 평문 패턴 스캔, ENC/DEC 경로에 대한 전력/EM 부채널 계측 시도 |
| Environment | 암호화 저장 경로 운용 중(레퍼런스 시나리오 8, 11단계) |
| Artifact | 저장 상태의 영상/AI 모델/추론 데이터, 암호화 키 |
| Response | 저장 매체에는 암호문만 존재하고, 키와 평문은 비신뢰 Host에 닿지 않으며, ENC/DEC 경로에서 유의미한 부채널 누출이 발생하지 않는다. |
| Response Measure | **게이트**: 파일시스템 침해 시 평문 노출 0건 / **KPI**: 부채널 TVLA t-값 4.5 미만(ISO/IEC 17825), 키 회전 지연 |
| 연관 | QA-01, DP6 |

### SEC-06: 보안 채널 신뢰

| Field | Specification |
|-------|---------------|
| Description | 침해된 Host가 승인된 pVM으로 위장하여도 TEE 호출이 성립하지 않아야 하며, 기존 Host→TEE 경로는 무회귀로 유지되어야 한다. |
| Source | 승인된 pVM으로 위장한 침해된 Host |
| Stimulus | 위조된 신원 또는 무결성 미확인 상태로 pVM→TEE RPC 호출 주입 |
| Environment | pVM→TEE 연동 경로 운용 중(레퍼런스 시나리오 6단계, DP5), 기존 Host→TEE SMC 경로 동시 운용 |
| Artifact | TEE 세션/키 자산, pVM→TEE 보안 RPC 채널 |
| Response | TEE가 호출 주체의 신원과 무결성을 검증하여 비인가 호출을 거부하고, 기존 Host→TEE 기능은 회귀 없이 동작한다. |
| Response Measure | **게이트**: 비인가 주체 TEE 호출 성립 0건 / **KPI**: 호출자 신원·무결성 검증 커버리지 100% |
| 연관 | DP5 |

### SEC-07: 침해 탐지/감사증적

| Field | Specification |
|-------|---------------|
| Description | 침해 시도가 발생하면 탐지·기록되고, 규제(CRA/GDPR) 보고 기한 내 대응 가능한 포렌식 증적이 확보되어야 한다. |
| Source | 침해 시도 공격자, 그리고 증적/보고를 요구하는 규제 기관 및 보안 운영 조직 |
| Stimulus | 격리 경계에 대한 비정상 접근 시도 발생 및 보안 사건 보고 요구 |
| Environment | 제품 상용 운용 단계(fleet 운용 중) |
| Artifact | 감사 로그, 침해 탐지 체계, 취약점 대응 프로세스 |
| Response | 비정상 접근이 탐지되어 감사 로그가 생성/수집되고, 포렌식 로그가 기한 내 확보되며, 심각 취약점은 정의된 리드타임 내 패치된다. |
| Response Measure | **KPI**: 비정상 접근 탐지 MTTD, 포렌식 로그 확보 24h 이내, 심각 패치 리드타임(Critical 30일), CRA 취약점 보고(24h/72h/14일)·GDPR 72h 통지 이행 가능 |
| 연관 | CRA, GDPR |

---

## 2. 성능 (Performance)

### PERF-01: 실시간 처리 (격리 오버헤드)

| Field | Specification |
|-------|---------------|
| Description | 격리 환경에서도 Camera/AI HW 가속으로 영상 파이프라인의 실시간 처리 성능이 비격리 구성 대비 유지되어야 한다. |
| Source | 카메라 센서 |
| Stimulus | 1080p 30fps 영상 스트림 지속 유입 |
| Environment | 격리 파이프라인(Secure Camera→Secure AI) 동작 중, Host 부하 idle/통상/스트레스 각 조건 |
| Artifact | End-to-End 파이프라인(캡처→Camera HW→AI HW 추론→판단) |
| Response | Camera/AI HW 가속으로 프레임 드롭 없이 실시간 처리한다. |
| Response Measure | **KPI**: 비격리 baseline 대비 성능 저하 10% 이내, 30fps 유지, 프레임 드롭율 0.1% 이하 |
| 연관 | QA-03 |

### PERF-02: 통신 오버헤드 (zero-copy)

| Field | Specification |
|-------|---------------|
| Description | 도메인 간 대용량 프레임 전달이 복사 없이 이루어져 통신 오버헤드가 실시간성과 전력 예산을 잠식하지 않아야 한다. |
| Source | Secure Camera pVM(Camera Workload) |
| Stimulus | 프레임 단위 대용량 영상 버퍼를 Secure AI pVM으로 지속 전달(레퍼런스 시나리오 9단계) |
| Environment | 파이프라인 정상 동작 중(30fps, 프레임 주기 33ms) |
| Artifact | zero-copy 보안 채널(dma-buf 공유 버퍼, 소유권/권한 전환 규약) |
| Response | 데이터 경로에서 복사 없이 버퍼 소유권/접근권 전환만으로 프레임이 전달되며, Host에는 노출되지 않는다. |
| Response Measure | **게이트**: 데이터 경로 memcpy 0회 / **KPI**: 전달 지연 p99 5ms, 프레임당 전환 비용 1ms 이하, 파이프라인 전력 효율(fps/W) 저하 10% 이내 |
| 연관 | QA-05, QA-07, DP3 |

### PERF-03: E2E 지연 (캡처→판단)

| Field | Specification |
|-------|---------------|
| Description | 프레임 캡처부터 판단 결과 전달까지의 E2E 지연이 실시간 예산 이내여야 한다. |
| Source | 카메라 센서(프레임 캡처 이벤트) |
| Stimulus | 캡처된 프레임 1건에 대한 판단 결과 생성 요구 |
| Environment | 격리 파이프라인 정상 동작 중, 통상 부하 |
| Artifact | 캡처→전처리→프레임 전달→AI 추론→결과 전달의 전체 경로 |
| Response | 캡처 시점의 HW 타임스탬프(PTS)가 파이프라인 끝까지 전파되어 단계별 지연이 분해 계측되고, 판단 결과가 예산 내 전달된다. |
| Response Measure | **KPI**: E2E 지연 p99 100ms 이하, 표준 모델 SingleStream 추론 지연 p90 비격리 대비 상대 성능 90% 이상(MLPerf Inference Edge 방식) |
| 연관 | QA-03, MLPerf |

### PERF-04: HW 주체 전환 지연

| Field | Specification |
|-------|---------------|
| Description | Camera/AI HW 사용 주체 전환(권한 회수→잔류 소거→권한 부여) 오버헤드가 실시간 파이프라인을 해치지 않아야 한다. |
| Source | HW 사용 주체 전환을 요청하는 주체(보안 Workload, Normal Camera Application) |
| Stimulus | Host↔pVM 간 HW 사용 주체 전환 요청 |
| Environment | 30fps 보안 파이프라인 동작 중(프레임 주기 33ms) |
| Artifact | HW IP 중재 경로의 전환 절차(권한 회수, 잔류 데이터 소거, 권한 부여) |
| Response | 전환 절차가 격리 보장(SEC-02)을 유지한 채 프레임 예산의 일부 이내에 완료된다. |
| Response Measure | **KPI**: 전환 지연 p99 10ms 이하(프레임 주기 33ms의 1/3), DP4 조기 PoC 합격 기준으로 사용 |
| 연관 | DP4 |

### PERF-05: Glass-to-glass 지연

| Field | Specification |
|-------|---------------|
| Description | 로봇 카메라 캡처부터 원격 운영자 화면 표시까지의 지연이 관제/원격 개입 요건을 만족해야 한다. |
| Source | 원격 관제 운영자 |
| Stimulus | 로봇 영상의 실시간 모니터링 요청 |
| Environment | 상품 레벨 구성(보안 파이프라인 + 인코딩/전송/표시 포함) 운용 중 |
| Artifact | 캡처→파이프라인→인코딩→전송→운영자 화면 표시 전 구간 |
| Response | 영상이 운영자 화면에 관제 가능한 지연 이내로 표시된다. |
| Response Measure | **KPI**: glass-to-glass 지연 p95 200ms 이하(화면 타임코드 캡처 방식 실측) |
| 연관 | 시장(관제) |

### PERF-06: 다중 스트림 처리량

| Field | Specification |
|-------|---------------|
| Description | 다중 카메라 스트림이 동시에 유입되어도 보안 파이프라인이 드롭 없이 지속 처리해야 한다. |
| Source | 다중 카메라를 탑재한 로봇 플랫폼 |
| Stimulus | 1080p30 스트림 2개 이상 동시 유입 |
| Environment | 다중 스트림 동시 인가 상태의 보안 파이프라인 운용 중 |
| Artifact | 보안 채널 및 파이프라인의 처리 용량 |
| Response | 각 스트림이 프레임 드롭 없이 동시에 처리된다. |
| Response Measure | **KPI**: 1080p30 동시 2스트림 이상(4스트림 목표), 채널 지속 처리량 190MB/s 이상 |
| 연관 | 시장(다중 카메라) |

### PERF-07: 파이프라인 시작 지연

| Field | Specification |
|-------|---------------|
| Description | 파이프라인 시작 요청부터 첫 프레임 처리까지의 cold start 지연이 서비스 기동 요건을 만족해야 한다. |
| Source | Host Application |
| Stimulus | 파이프라인 시작 요청(pVM 미생성 상태에서의 cold start) |
| Environment | 플랫폼 기동 완료, Secure Camera/Secure AI pVM 미생성 상태 |
| Artifact | 레퍼런스 시나리오 1~9단계 경로(권한 확인, 이미지 검증, pVM 생성, 탑재, 채널 구성, 첫 캡처/전달) |
| Response | 검증·생성·탑재·채널 구성이 순차 완료되어 첫 프레임 처리에 도달하며, 단계별 소요가 분해 계측된다. |
| Response Measure | **KPI**: 시작 요청→첫 프레임 cold start p95 2초 이하(예시치) |
| 연관 | 시나리오 1~9단계 |

---

## 3. 확장성 (Extensibility)

### EXT-01: 신규 Workload 코어 무수정 수용

| Field | Specification |
|-------|---------------|
| Description | 신규 보안 Workload 추가 시 Framework 코어 수정 없이 패키징/탑재만으로 수용되어야 한다. |
| Source | 로봇 제조사 / Workload 개발자 |
| Stimulus | 신규 보안 Workload 추가 요구 |
| Environment | Framework가 제품에 배포/운용 중인 상태 |
| Artifact | Framework 코어(Middleware/커널 드라이버) |
| Response | 표준 패키지 계약에 따른 패키징/탑재만으로 신규 Workload가 수용되고, 코어 디렉터리에는 변경이 발생하지 않는다(CI diff 자동 검사). |
| Response Measure | **게이트**: Framework 코어 수정 0 LoC / **KPI**: breaking change 0건 추세 |
| 연관 | QA-04, DP2 |

### EXT-02: 이질 런타임 수용

| Field | Specification |
|-------|---------------|
| Description | 런타임과 의존성이 서로 다른 이질 Workload도 동일한 패키지/로딩 계약으로 수용되어야 한다. |
| Source | 서드파티 Workload 개발자 |
| Stimulus | 이질 런타임 Workload(C 네이티브, Python 추론, 서드파티 바이너리) 3종의 패키징/탑재 요청 |
| Environment | 표준 Workload 패키지 계약이 정의된 플랫폼 운용 중 |
| Artifact | Workload 패키지 형식(이미지, manifest, 서명)과 표준 실행/로딩 인터페이스 |
| Response | 3종 모두 계약 수정 없이 동일한 절차로 탑재/실행되어 계약의 일반성이 검증된다. |
| Response Measure | **KPI**: 이질 파일럿 Workload 수용 3종 이상 |
| 연관 | DP2 |

### EXT-03: 온보딩 리드타임

| Field | Specification |
|-------|---------------|
| Description | 신규 Workload 개발자가 표준 절차만으로 단기간에 개발→통합을 완료할 수 있어야 한다. |
| Source | 신규 고객사(로봇 제조사) 개발팀 |
| Stimulus | 신규 Workload의 개발 착수부터 플랫폼 통합까지의 온보딩 수행 |
| Environment | API 문서/SDK/패키징 도구가 제공되는 상태 |
| Artifact | 개발자 온보딩 경로(pVM API, 패키징, 시험 절차) |
| Response | 표준 온보딩 절차만으로 신규 Workload 통합이 완료되고 공수가 실측된다. |
| Response Measure | **KPI**: 신규 Workload 통합 평균 5인일 이내 |
| 연관 | 시장 |

### EXT-04: Fleet 배포 성공률

| Field | Specification |
|-------|---------------|
| Description | Framework/Workload 릴리스가 fleet 전체에 수동 개입 없이 안정적으로 배포되어야 한다. |
| Source | fleet 운영자(로봇 제조사 운영 조직) |
| Stimulus | 릴리스 wave 단위 OTA 배포 실행 |
| Environment | 수백 대 규모 로봇 fleet 상용 운용 중, canary 1% 선행 배포 적용 |
| Artifact | OTA 배포 파이프라인(배포/재개/재시도 경로) |
| Response | 배포가 canary 검증을 거쳐 wave 전체에 수동 개입 없이 완료되고, 결과가 집계된다. |
| Response Measure | **KPI**: 릴리스 wave당 배포 성공률 98.5% 이상(수동 개입 없이) |
| 연관 | 시장 OTA(arc42) |

### EXT-05: 배포 롤백

| Field | Specification |
|-------|---------------|
| Description | 배포 실패가 발생해도 fleet이 벽돌화되지 않고 이전 버전으로 신속히 복원되어야 한다. |
| Source | 불량 업데이트/배포 실패 이벤트 |
| Stimulus | 배포 중 업데이트 실패 또는 부팅 불가 상태 발생(500대급 장애 주입 시험 포함) |
| Environment | A/B 슬롯 기반 fleet OTA 배포 진행 중 |
| Artifact | 업데이트 대상 로봇의 시스템 이미지와 A/B 슬롯 롤백 메커니즘 |
| Response | 실패 검출 시 이전 버전 슬롯으로 자동 복원되어 서비스가 재개된다. |
| Response Measure | **게이트**: 배포 실패 시 fleet 벽돌화 0건 / **KPI**: 이전 버전 복원 2분 이내, 실패 케이스 롤백 성공률 99.9% |
| 연관 | 시장 OTA, DP2 |

### EXT-06: Secure OS/TEE 교체성

| Field | Specification |
|-------|---------------|
| Description | Secure OS 교체 시 GP 표준 인터페이스 경계 밖의 SW는 수정/재이식하지 않아야 한다. |
| Source | 서드파티 Secure OS 벤더 / 로봇 제조사 |
| Stimulus | 탑재된 Secure OS를 다른 Secure OS로 교체 |
| Environment | 설계/통합 단계 또는 제품 유지보수 단계 |
| Artifact | Secure OS와 무관한 SW(Framework, Host Middleware, 타 Workload) |
| Response | GP 표준 인터페이스 경계 내에서 Secure OS 패키지 교체만으로 완료되며, 무관 SW는 수정되지 않는다(교체 전후 diff로 확인). |
| Response Measure | **게이트**: 인터페이스 외 재이식 파일 0개 / **KPI**: 교체 대응 공수 |
| 연관 | QA-09, DP5 |

### EXT-07: API 계약 안정성

| Field | Specification |
|-------|---------------|
| Description | Framework 버전이 릴리스되어도 기존 Workload 자산이 수정 없이 계속 동작해야 한다. |
| Source | Framework 신규 버전 릴리스 |
| Stimulus | Framework 업그레이드 배포 |
| Environment | 기존 Workload 자산이 fleet에서 운용 중인 상태 |
| Artifact | 공개 Workload API 표면(pVM API, 패키지 계약) |
| Response | 기존 Workload가 재작성/재컴파일 없이 동작하며, 릴리스마다 API 표면 diff로 호환성 파괴 변경이 계수된다. |
| Response Measure | **KPI**: Workload API breaking change 건수/릴리스 0 유지 |
| 연관 | DP2 |

---

## 4. 가용성 (Availability)

### AVL-01: pVM 장애 격리

| Field | Specification |
|-------|---------------|
| Description | pVM 장애가 Host, 다른 pVM, 로봇 기본 동작으로 전파되지 않아야 한다. |
| Source | 오동작하는 보안 Workload |
| Stimulus | pVM 비정상 종료(크래시, 무응답) 발생 |
| Environment | 다중 pVM(Secure Camera, Secure AI) 운용 중인 로봇 통상 동작 상태 |
| Artifact | Host OS, 타 pVM, 로봇 기본 동작 |
| Response | 장애 영향이 해당 pVM에 한정되고, 이웃 pVM과 Host는 동작을 지속한다. |
| Response Measure | **게이트**: 장애 전파로 인한 Host/타 pVM 다운타임 0 |
| 연관 | QA-06, DP1 |

### AVL-02: 장애 복구 시간 (MTTR)

| Field | Specification |
|-------|---------------|
| Description | 장애 pVM이 신속히 검출·회수·재기동되어 보안 Workload 서비스가 재개되어야 한다. |
| Source | pVM 장애 이벤트(크래시/무응답) |
| Stimulus | 장애 발생 후 서비스 재개 요구 |
| Environment | 보안 파이프라인 운용 중 |
| Artifact | 장애 pVM과 그 위의 Workload 서비스, 격리 자원(메모리/CPU/디바이스) |
| Response | watchdog이 장애를 검출하고, 격리 자원을 안전하게 회수한 뒤 pVM/Workload를 재기동하여 서비스를 재개한다. 각 구간이 타임스탬프로 분해 계측된다. |
| Response Measure | **KPI**: 복구 시간 p99 3초 이내(검출 0.5s / 회수 1s / 재기동 1.5s 분해) |
| 연관 | DP1 |

### AVL-03: 장애 모드 커버리지

| Field | Specification |
|-------|---------------|
| Description | 정의된 장애 카탈로그의 모든 모드가 자동 주입 시험으로 재현·검증 가능해야 한다. |
| Source | 검증 조직(장애 주입 프레임워크) |
| Stimulus | 장애 카탈로그 모드별 자동 주입(크래시, hang, 부팅 실패, OOM, 채널 소실) |
| Environment | 통합 시험 및 회귀 시험 단계 |
| Artifact | Framework의 장애 처리 경로(검출, 자원 회수, 재시작, 채널 정리) |
| Response | 각 장애 모드가 정의된 절차대로 처리되고, 처리 결과가 자동 판정된다. |
| Response Measure | **KPI**: 장애 카탈로그 주입 구현율 100% |
| 연관 | DP1 |

### AVL-04: 자원 누수 방지

| Field | Specification |
|-------|---------------|
| Description | 장애-재시작이 장기간 반복되어도 격리 메모리 등 자원 누수가 누적되지 않아야 한다. |
| Source | 반복되는 pVM 장애(soak 시험의 crash-restart 주입) |
| Stimulus | 1,000회 crash-restart 반복 수행 |
| Environment | 장기 운용 soak 시험(다중 pVM 운용 상태) |
| Artifact | Framework 자원 원장(격리 메모리, 공유 버퍼, HW 권한, 핸들)과 실제 커널 자원 상태 |
| Response | 매 장애 회수 후 Framework 자원 원장과 실제 커널 상태가 일치하고(reconciliation), 잔여 자원이 누적되지 않는다. |
| Response Measure | **KPI**: 1,000회 crash-restart soak 기준 누수율 0 수렴 |
| 연관 | DP1 |

### AVL-05: 이웃 성능 간섭

| Field | Specification |
|-------|---------------|
| Description | 한 pVM의 장애 처리/재시작이 진행되어도 정상 pVM의 실시간 처리 성능이 유지되어야 한다. |
| Source | 장애 pVM의 복구 절차(자원 회수/재기동 동작) |
| Stimulus | 이웃 pVM 장애 및 재시작 진행 |
| Environment | 정상 pVM이 30fps 파이프라인 처리 중인 다중 pVM 운용 상태 |
| Artifact | 정상 pVM의 파이프라인 처리 성능(fps) |
| Response | 장애 처리와 병행하여 정상 pVM의 프레임 처리가 유의미한 저하 없이 지속된다. |
| Response Measure | **KPI**: 장애/재시작 중 정상 pVM fps 저하 5% 이내 |
| 연관 | QA-06 |

### AVL-06: 서비스 가동률 (SLA)

| Field | Specification |
|-------|---------------|
| Description | 보안 파이프라인 서비스가 상용 운용 SLA 수준의 가동률을 유지해야 한다. |
| Source | SLA를 계약한 로봇 제조사/서비스 운영자 |
| Stimulus | 월 단위 연속 상용 운용 |
| Environment | fleet 상용 운용 환경(운용 텔레메트리 수집 중) |
| Artifact | 보안 파이프라인 서비스 전체(Framework + pVM + Workload) |
| Response | 서비스가 가동 상태를 유지하고, 다운타임이 월 예산 이내로 관리된다(가동률 = MTBF/(MTBF+MTTR)). |
| Response Measure | **KPI**: 가동률 99.9% 이상/월(월 다운타임 예산 약 43분) |
| 연관 | 시장 AMR SLA |

### AVL-07: SW 기인 MTBF

| Field | Specification |
|-------|---------------|
| Description | 플랫폼 SW에 기인한 장애의 평균 무고장 시간이 상용 신뢰성 수준을 만족해야 한다. |
| Source | fleet 운용 누적(전체 population의 장기 가동) |
| Stimulus | fleet 전체의 누적 가동 시간 증가 |
| Environment | fleet 상용 운용 환경(장애 원인 분류 체계 운용 중) |
| Artifact | 플랫폼 SW(Framework, pVM 런타임, 연동 계층) |
| Response | SW 기인 장애만 분리 계수되어 population MTBF가 산정되고, 목표 수준을 유지한다. |
| Response Measure | **KPI**: SW 기인 MTBF 5,000시간 이상(누적 가동시간/SW 기인 장애 수) |
| 연관 | 시장 신뢰성 |

---

## 5. 커버리지 확인

| 관점 | 시나리오 | 게이트 보유 | KPI 전용 |
|---|---|---|---|
| 보안 | SEC-01~07 (7건) | SEC-01~06 | SEC-07 |
| 성능 | PERF-01~07 (7건) | PERF-02 | PERF-01, 03~07 |
| 확장성 | EXT-01~07 (7건) | EXT-01, 05, 06 | EXT-02, 03, 04, 07 |
| 가용성 | AVL-01~07 (7건) | AVL-01 | AVL-02~07 |

총 28건으로 `06_qa_utility_tree_metrics.md`의 28개 QA 전체를 커버한다.
