# DP-C-03 세부 결정 후보

본 문서는 DP-C-03에서 세부적으로 검토할 수 있는 결정사항 후보를 정리한다.
각 항목의 채택 여부와 우선순위는 이후 DP-C-03 본문을 재정리할 때 확정한다.

| 세부 결정사항 | 설계 질문 | 후보 예시 |
|---|---|---|
| pVM 관리 주체 | 누가 pVM 생명주기를 소유하는가? | 중앙 관리 데몬 / pVM별 VMM + 공용 관리 서비스 / 커널 중심 |
| pVM 식별·소유 모델 | pVM은 Host app 소유인가, workload 소유인가, framework 소유인가? | app 기준 / workload 기준 / app+workload 결합 기준 |
| 생명주기 상태 머신 | 생성, 로드, 실행, 정지, 장애, 회수 상태를 어떻게 정의할 것인가? | 단순 create/start/stop / 명시적 prepare/load/run/destroy |
| 제어 API 모델 | Host app이 pVM을 어떻게 생성·제어하는가? | 동기 API / 비동기 job API / 이벤트 기반 API |
| 권한 컨텍스트 전달 | DP-C-02의 Host app 권한과 workload 권한을 pVM 생성 시 어떻게 묶는가? | app 권한만 사용 / workload label 별도 전달 / 둘 다 검증 |
| 자원 할당 단위 | 메모리, vCPU, 디바이스, 버퍼를 어떤 단위로 예약·회수하는가? | 정적 예약 / 동적 할당 / hybrid |
| 메모리 소유권 전환 | donate/share/unshare/reclaim을 어떤 규칙으로 처리하는가? | 최소 donate/reclaim / share 포함 / zeroization 보장 포함 |
| VMM 격리 단위 | 여러 pVM을 하나의 VMM이 관리할지, pVM별로 분리할지? | 단일 VMM / pVM별 VMM / VMM pool |
| 장애 감지·복구 | pVM 장애 시 누가 감지하고 어떻게 회수·재시작하는가? | 수동 회수 / 정책 기반 재시작 / watchdog 연계 |
| 상태·이벤트 보고 | Host가 pVM 상태를 어디까지 관찰할 수 있게 할 것인가? | 상태 조회만 / 이벤트 큐 / fault reason 포함 |
| pKVM 최소 계약 | DP-C-03에서 확정해야 하는 hypercall 범위는 어디까지인가? | 생성·소멸만 / 메모리까지 / 이벤트·SMMU·attestation 포함 |
| PoC 착수 기준 | 어떤 결정이 확정되면 DP-C-06 등 후속 PoC를 병행할 수 있는가? | H1/H2 우선 / H1~H4 우선 / H6 포함 |

## 재정리 시 우선 검토할 흐름

1. pVM 관리 주체와 프로세스 모델
2. pVM 생명주기 상태 머신과 제어 API
3. Host app 권한과 workload 권한의 pVM 생성 시 결합 방식
4. 메모리·CPU·디바이스 자원 할당 및 회수 모델
5. pKVM 최소 hypercall 계약
6. 장애 감지, 상태 보고, 회수·재시작 정책
7. 후속 PoC 착수 조건

DP-C-02에서 Host app 권한과 workload 권한을 분리하기로 했기 때문에,
DP-C-03에서는 pVM 생성 요청 안에 workload의 SELinux 권한 컨텍스트를
어떤 객체로 전달하고 보존할지 함께 검토해야 한다.
