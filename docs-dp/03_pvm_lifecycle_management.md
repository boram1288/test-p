# DP-03. pVM 생명주기 관리 구조

## 1. 상태

평가 중

## 2. 결정 목적

pVM의 생성과 종료 책임을 정한다.
VM별 장애 경계를 정한다.
자원 회수 주체를 정한다.

## 3. 문제 상황

- 선행 DP: 없음
- 연관 요구: FR-01, FR-02, SEC-01, AVL-01, PERF-07
- 범위: Linux/KVM의 process/FD 수명주기는 baseline으로 사용한다. `controller + VM별 runner` PoC 결과는 관찰 근거이며 최종 제품 구조의 자동 확정 근거가 아니다.

Camera pVM과 AI pVM은 동시에 실행된다.
각 pVM은 독립적으로 시작하고 종료해야 한다.
한 pVM의 장애가 다른 pVM으로 전파되면 안 된다.
비신뢰 Host는 pVM의 private memory를 읽으면 안 된다.
관리 구조는 신규 pVM 역할을 수용해야 한다.

## 4. 결정 질문

pVM 제어와 실행을 한 프로세스에 둘 것인가?
아니면 제어기와 VM별 실행기를 분리할 것인가?

## 5. 후보 구조

### 후보 A. 통합 Manager 구조

하나의 Manager 프로세스가 모든 pVM을 실행한다.
Manager가 정책과 상태를 관리한다.
Manager 내부의 thread가 각 vCPU를 실행한다.

### 후보 B. Controller와 VM별 Runner 분리 구조

Controller는 요청과 정책만 관리한다.
각 pVM은 별도 Runner 프로세스가 실행한다.
Runner는 private KVM backend를 가진다.

## 6. 후보별 동작 구조

### 후보 A

```text
Host Application
  -> Manager
       -> Camera vCPU thread
       -> AI vCPU thread
       -> KVM backend
```

- 실행 위치: 모두 Host userspace에 둔다.
- 제어 흐름: 요청은 Manager가 직접 처리한다.
- 데이터 흐름: Manager memory 안에서 상태를 공유한다.
- 신뢰 경계: Manager 전체가 하나의 권한 경계다.
- 자원 소유권: Manager가 모든 VM FD와 memory FD를 소유한다.
- 자원 회수: Manager가 종료 순서를 직접 수행한다.

### 후보 B

```text
Host Application
  -> Controller
       -> Camera Runner -> private KVM backend
       -> AI Runner     -> private KVM backend
```

- 실행 위치: Controller와 Runner를 Host userspace에 둔다.
- 제어 흐름: Controller가 Runner에 명령을 보낸다.
- 데이터 흐름: 상태 message만 IPC로 전달한다.
- 신뢰 경계: Runner마다 별도 process boundary를 둔다.
- 자원 소유권: 각 Runner가 자신의 VM FD를 소유한다.
- 자원 회수: Runner가 VM 자원을 닫는다.
- 강제 회수: Controller가 pidfd로 Runner를 종료한다.

## 7. 품질속성 비교

### 7.1 필수 gate

| Gate | 합격 기준 | 후보 A | 후보 B |
|---|---|---|---|
| SEC-01 Host 침해 기밀성 | Host 전체 덤프에서 pVM canary 노출 0건 | 확인 필요 | 확인 필요 |
| AVL-01 장애 격리 | Camera 실행기 장애 시 Host/AI pVM 다운타임 0초 | 구조상 위험, PoC 필요 | 구조상 유리, PoC 필요 |
| 자원 회수 완결성 | stop/crash 후 VM FD, memory FD와 locked memory 누수 0건 | 확인 필요 | 확인 필요 |

Process boundary는 Host userspace backend의 결함/침해 반경을 줄인다.
Host kernel 권한 공격자에 대한 pVM memory 기밀성은 두 후보 모두 pKVM/EL2 격리에 의존한다.
SEC-01은 두 후보의 공통 prerequisite이며 후보를 가르는 차등 평가축은 아니다.

### 7.2 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.
PERF-07은 전체 cold start p95 2초를 요구한다.
아래 create-to-first-run 임계값은 전체 예산의 세부 배분이 승인되기 전까지 PoC 작업값이다.

| 품질속성 | KPI | 별 1개 | 별 2개 | 별 3개 |
|---|---|---|---|---|
| 보안성 | 단일 VM 실행기 침해 시 접근 가능한 타 pVM 제어 FD 수 | 2개 이상 | 1개 | 0개 |
| 성능 | create 요청부터 first-run까지 p99 | 3초 초과 | 1초 초과 3초 이하 | 1초 이하 |
| 확장성 | 신규 pVM role 추가 시 관리 core 변경량 | 100 LoC 초과 | 1~100 LoC | 0 LoC |
| 변경 용이성 | KVM backend 교체 시 수정 module 수 | 4개 이상 | 2~3개 | 1개 이하 |
| 자원 효율 | pVM 1개 추가 시 Host 관리 RSS 증가량 | 64 MiB 초과 | 16 MiB 초과 64 MiB 이하 | 16 MiB 이하 |

KVM의 `guest_memfd`는 VM에 귀속된다.
마지막 reference가 닫히면 자동 해제된다.
VM별 FD 소유권을 KPI에 포함한 근거다.
[Linux KVM API](https://www.kernel.org/doc/html/latest/virt/kvm/api.html)

pidfd는 특정 process의 안정된 reference다.
PID 재사용 race를 줄인다.
Runner 강제 회수 구조의 근거다.
[Linux pidfd_send_signal](https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html)

cgroup v2는 process별 자원 제한을 제공한다.
Runner별 memory와 CPU 측정에 사용할 수 있다.
[Linux cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)

### 7.3 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | ★★ | 현재 2-pVM 구성에서 Manager 침해가 다른 pVM 제어 FD 1개에도 닿는다. | ★★★ | Runner는 다른 pVM의 VM FD와 backend를 소유하지 않는다. |
| 성능 | ★★★ | process 생성과 IPC가 없다. | ★★ | Runner 생성과 IPC 비용이 추가된다. |
| 확장성 | ★★ | role 분기가 Manager에 모일 수 있다. | ★★★ | 동일 Runner 계약을 반복할 수 있다. |
| 변경 용이성 | ★★ | backend 변경이 Manager와 연결된다. | ★★★ | backend를 Runner 내부에 가둘 수 있다. |
| 자원 효율 | ★★★ | 하나의 process가 공통 자원을 공유한다. | ★★ | Runner별 stack과 page table이 추가된다. |

## 8. 핵심 트레이드오프

후보 A는 시작 비용과 Host memory 사용을 줄인다.
대신 Manager 장애의 영향 범위가 커진다.

후보 B는 VM별 장애 경계를 만든다.
대신 process와 IPC 자원이 증가한다.

## 9. 검증 기준

- Camera Runner를 강제 종료한다.
- AI pVM의 frame 처리가 계속되는지 측정한다.
- create-to-first-run p99를 1,000회 측정한다.
- stop 이후 VM FD와 memory FD 수를 확인한다.
- stop 이후 locked memory가 기준값으로 복귀하는지 확인한다.
- 신규 role을 하나 추가한다.
- 관리 core의 diff LoC를 측정한다.
- pVM당 Host RSS 증가량을 측정한다.
- Host root 권한에서 pVM canary를 전체 덤프해 노출 0건을 확인한다.
- pidfd와 cgroup v2 지원 여부, 권한과 실패 동작을 baseline 환경에서 확인한다.
- Manager process 자체와 개별 Runner를 각각 중단해 장애 반경 차이를 측정한다.

## 10. 검토 결과

사용자 요청에 따라 Claude와 교차 검토했다.
Process boundary의 효과를 Host kernel 침해 방어가 아니라 userspace 장애/권한 반경으로 한정했다.
SEC-01, AVL-01과 자원 회수 gate를 별점보다 먼저 검증하도록 보완했다.
사용자의 gate/KPI 승인과 PoC 결과 확인이 남아 있다.

## 11. 최종 결정
