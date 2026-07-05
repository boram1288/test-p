# Reference Scenario Flow

본 문서는 `01_vos_collection.md`의 레퍼런스 시나리오 워크스루와 `01_use_case_spec.md`, `02_requirements.md`, `05_context_view.md`를 기준으로 Secure Vision AI 파이프라인의 실행 순서를 정리한다.

레퍼런스 시나리오는 **Host Application이 Secure Camera pVM과 Secure AI pVM 기반 파이프라인을 시작하고, Camera HW 처리 → 영상 저장 데이터 암호화 → 보안 채널 전달 → AI HW 추론 → AI 저장 데이터 암호화 → 결과 전달**까지 수행하는 흐름을 대상으로 한다.

## 1. 참여 주체

| 주체 | 역할 |
|---|---|
| Host Application | pVM 생성/운용, Workload 탑재, 파이프라인 시작/정지 요청 |
| Linux pKVM 기반 가상화 보안 Framework | pVM 생명주기, Workload 검증/탑재, HW 중재, 보안 채널, Secure OS 연동 관리 |
| pKVM(EL2 Hypervisor) | pVM 생성/삭제, CPU/Memory 할당, Stage-2 기반 메모리 격리 |
| Secure Camera pVM | Camera Workload 실행, Camera HW 사용, 영상 프레임 보안 처리 |
| Secure AI pVM | AI Workload 실행, AI HW 사용, 모델/추론 데이터 보안 처리 |
| Camera HW Driver | Camera HW 접근 수행 |
| AI HW Driver | AI HW 접근 수행 |
| S2MPU/DMA HW Driver | HW 접근 권한과 DMA 격리 설정 |
| Secure OS(TEE) | ENC/DEC 등 보안 서비스 수행 |

## 2. 실행 순서

| 단계 | 요청/동작 | 주요 처리 | 관련 모듈 |
|---|---|---|---|
| 1 | Host Application이 파이프라인 시작 요청 | Secure Camera pVM과 Secure AI pVM 생성 및 Workload 탑재를 요청한다. | Host Application, Framework API |
| 2 | 요청 권한 및 정책 확인 | 요청 주체, 허용 Workload, 필요 HW, Secure OS 기능 사용 가능 여부를 확인한다. | Framework API, Multi-pVM Orchestrator |
| 3 | Workload 이미지 검증 | Camera/AI Workload 이미지 서명과 manifest를 검증한다. 실패 시 탑재하지 않는다. | Workload Loader / Verifier |
| 4 | pVM 생성 및 자원 할당 | pKVM을 통해 Secure Camera pVM과 Secure AI pVM을 생성하고 CPU/Memory를 할당한다. | pVM Lifecycle Manager, pKVM(EL2) |
| 5 | Workload 탑재 및 실행 | 검증된 Camera Workload와 AI Workload를 각 pVM에 탑재하고 실행한다. | Workload Loader / Verifier, Multi-pVM Orchestrator |
| 6 | 보안 채널 구성 | Secure Camera pVM과 Secure AI pVM 사이의 보안 데이터 전달 채널을 구성한다. | Secure Inter-domain Channel |
| 7 | Camera HW 사용 요청 | Camera Workload가 Camera HW 사용을 요청한다. | Camera Workload, HW IP Mediation Layer |
| 8 | Camera HW 접근 권한 부여 | S2MPU/DMA 권한을 Secure Camera pVM에만 부여한다. | HW IP Mediation Layer, DMA/S2MPU Isolation Controller, Camera HW Driver |
| 9 | 영상 프레임 캡처/처리 | Camera HW가 입력 프레임을 처리하고, 프레임 버퍼는 Host에 노출되지 않도록 pVM 소유 메모리로 유지한다. | Secure Camera pVM, Camera HW Driver, pKVM(EL2) |
| 10 | 영상 저장 데이터 암호화 수행 | 필요 시 Camera Workload가 Secure OS에 ENC/DEC 명령을 전달한다. 잘못된 명령이나 권한 없는 요청은 거부한다. | Secure OS Adapter, Secure OS(TEE) |
| 11 | Camera HW 권한 회수 | Camera 처리 완료 후 권한을 회수하고 잔류 데이터 격리/소거를 수행한다. | DMA/S2MPU Isolation Controller |
| 12 | 영상 프레임 전달 | Secure Camera pVM이 프레임 또는 dma-buf 핸들을 Secure AI pVM으로 전달한다. Host는 데이터 내용을 볼 수 없다. | Secure Inter-domain Channel |
| 13 | AI HW 사용 요청 | AI Workload가 AI HW 추론을 요청한다. | AI Workload, HW IP Mediation Layer |
| 14 | AI HW 접근 권한 부여 | S2MPU/DMA 권한을 Secure AI pVM에만 부여한다. | HW IP Mediation Layer, DMA/S2MPU Isolation Controller, AI HW Driver |
| 15 | AI 추론 수행 | AI HW가 모델/프레임을 기반으로 추론을 수행한다. 모델 가중치와 중간 데이터는 pVM 외부로 노출되지 않는다. | Secure AI pVM, AI HW Driver, pKVM(EL2) |
| 16 | AI 저장 데이터 암호화 수행 | 필요 시 AI Workload가 Secure OS에 ENC/DEC 명령을 전달한다. 잘못된 명령이나 권한 없는 요청은 거부한다. | Secure OS Adapter, Secure OS(TEE) |
| 17 | AI HW 권한 회수 | 추론 완료 후 AI HW 접근 권한을 회수하고 잔류 데이터를 격리/소거한다. | DMA/S2MPU Isolation Controller |
| 18 | 결과 전달 | 추론 결과 또는 판단 결과를 Host Application으로 전달한다. 민감 원본/모델/중간 데이터는 전달하지 않는다. | Secure Inter-domain Channel, Framework API |
| 19 | 장애/종료 처리 | pVM crash, 무응답, HW 오류가 발생하면 해당 pVM에 장애를 한정하고 자원을 회수/재시작한다. | Fault/Recovery Manager, pVM Lifecycle Manager |
| 20 | 파이프라인 정지 | Host Application 요청 또는 정책에 따라 Workload 중지, pVM 종료, HW 권한 회수, 채널 정리를 수행한다. | Multi-pVM Orchestrator, pVM Lifecycle Manager |

## 3. Flow Chart

```mermaid
flowchart TD
    A[1. Host Application 파이프라인 시작 요청] --> B{2. 요청 권한 / 정책 확인}
    B -- 실패 --> B1[요청 거부 / 오류 반환]
    B -- 통과 --> C{3. Workload 이미지 서명 / manifest 검증}
    C -- 실패 --> C1[탑재 중단 / 오류 반환]
    C -- 통과 --> D[4. Secure Camera pVM / Secure AI pVM 생성 및 자원 할당]
    D --> E[5. Camera / AI Workload 탑재 및 실행]
    E --> F[6. Camera pVM ↔ AI pVM 보안 채널 구성]
    F --> G[7. Camera Workload가 Camera HW 사용 요청]
    G --> H[8. S2MPU/DMA 권한을 Camera pVM에 부여]
    H --> I[9. 영상 프레임 캡처 / 처리]
    I --> J{10. 영상 저장 데이터 암호화 필요?}
    J -- 예 --> K[Secure OS Adapter를 통해 ENC/DEC 요청]
    K --> L{Secure OS 처리 성공?}
    L -- 실패 --> L1[오류 반환 / 평문 외부 유출 차단]
    L -- 성공 --> M[암호화 결과 반환]
    J -- 아니오 --> N[11. Camera HW 권한 회수 / 잔류 데이터 격리]
    M --> N
    N --> O[12. 보안 채널로 영상 프레임 전달]
    O --> P[13. AI Workload가 AI HW 사용 요청]
    P --> Q[14. S2MPU/DMA 권한을 AI pVM에 부여]
    Q --> R[15. AI HW 추론 수행]
    R --> S{16. AI 저장 데이터 암호화 필요?}
    S -- 예 --> T[Secure OS Adapter를 통해 ENC/DEC 요청]
    T --> U{Secure OS 처리 성공?}
    U -- 실패 --> U1[오류 반환 / 평문 외부 유출 차단]
    U -- 성공 --> V[암호화 결과 반환]
    S -- 아니오 --> W[17. AI HW 권한 회수 / 잔류 데이터 격리]
    V --> W
    W --> X[18. 추론/판단 결과를 Host Application으로 전달]
    X --> Y{19. 장애 또는 종료 조건 발생?}
    Y -- 장애 --> Y1[해당 pVM에 장애 한정 / 자원 회수 / 재시작]
    Y -- 종료 --> Y2[20. Workload 중지 / pVM 종료 / 채널 정리]
    Y -- 계속 --> G
```

## 4. 보안상 중요한 체크포인트

| 체크포인트 | 실패 시 처리 |
|---|---|
| 요청 주체 권한 확인 | 허용되지 않은 Host Application 요청은 pVM 생성/Workload 탑재 전 거부 |
| Workload 서명/manifest 검증 | 검증 실패 시 pVM에 탑재하지 않음 |
| pVM 생성 및 자원 할당 | 자원 부족 또는 pKVM 오류 시 기존 pVM 상태를 유지하고 시작 요청 실패 처리 |
| HW 사용 주체 전환 | 이전 주체 권한 회수 후 다음 주체 권한 부여 |
| S2MPU/DMA 권한 설정 | 권한 중첩 또는 미회수 상태가 발생하면 HW 사용 중단 |
| 영상 저장 데이터 암호화 | Secure OS 오류 또는 권한 없는 요청은 fail-closed 처리 |
| 도메인 간 데이터 전달 | Host에 원본 프레임/모델/중간 데이터 노출 금지 |
| AI 저장 데이터 암호화 | Secure OS 오류 또는 권한 없는 요청은 fail-closed 처리 |
| 장애 처리 | 장애 pVM에 영향 범위를 한정하고 Host/타 pVM은 유지 |

## 5. 시나리오가 커버하는 요구사항

| 요구사항 | 커버 지점 |
|---|---|
| FR-01 pVM 생성/시작/정지/종료 | 단계 4, 19, 20 |
| FR-02 다중 pVM 동시 운용 | 단계 4~6 |
| FR-03 Camera/AI HW 공유 사용 | 단계 7~11, 13~17 |
| FR-04 도메인 간 보안 데이터 전송 | 단계 6, 12, 18 |
| FR-05 보안 Workload 동적 탑재 | 단계 3, 5 |
| FR-06 Secure OS ENC/DEC 명령 전송 | 단계 10, 16 |
| QA-01 Host 침해 시 기밀성 | 단계 9, 10, 12, 15, 16, 18 |
| QA-02 HW 접근 격리 | 단계 8, 11, 14, 17 |
| QA-03 실시간 처리 | 단계 9, 15 |
| QA-05 통신 오버헤드 | 단계 12 |
| QA-06 pVM 장애 격리 | 단계 19 |

