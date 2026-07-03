# 유즈케이스 명세

---

| UC-01 | pVM 생성/시작/정지/종료 |
|---|---|
| Actor | Host Application |
| Pre-Condition | 시스템이 부팅되어 있고 pVM 이미지가 서명된 상태로 준비되어 있다 |
| Post-Condition | pVM이 요청된 상태(Running 또는 Stopped)로 전환되었다 |
| Main Flow | 1. Host Application이 pVM API로 pVM 생성을 요청한다<br>2. 시스템은 메모리/CPU 자원을 할당하고 pVM 인스턴스를 초기화한다<br>3. Host Application이 pVM 시작 명령을 호출한다<br>4. 시스템은 pVM을 Running 상태로 전환한다<br>5. Host Application이 pVM 정지 명령을 호출한다<br>6. 시스템은 pVM을 종료하고 할당 자원을 회수한다 |
| Alternative Flow | 1. 시스템은 pVM 생성 실패 시 생성을 중단하고 Host Application에 오류를 반환한다<br>2. 시스템은 pVM 시작 실패 시 할당 자원을 회수하고 Host Application에 실패 상태를 반환한다<br>3. 시스템은 pVM 정지 명령이 시간 내 완료되지 않으면 강제 종료 절차를 수행하고 결과를 기록한다 |

---

| UC-02 | 다중 pVM 동시 운용 |
|---|---|
| Actor | Host Application |
| Pre-Condition | Secure Camera pVM과 Secure AI pVM 이미지가 준비되어 있다 |
| Post-Condition | 복수의 pVM이 격리된 상태로 독립적으로 동시 운용 중이다 |
| Main Flow | 1. Host Application이 Secure Camera pVM 생성을 요청한다<br>2. 시스템은 Secure Camera pVM을 생성하고 시작한다<br>3. Host Application이 Secure AI pVM 생성을 요청한다<br>4. 시스템은 Secure AI pVM을 생성하고 시작한다<br>5. 시스템은 두 pVM을 독립된 메모리 공간에서 동시에 실행한다 |
| Alternative Flow | 1. 시스템은 pVM 중 하나가 종료 혹은 Crash되어도 나머지 pVM을 계속 실행한다<br>2. 시스템은 두 번째 pVM 생성에 필요한 자원이 부족하면 기존 pVM을 유지하고 Host Application에 신규 생성 실패를 반환한다<br>3. 시스템은 pVM 간 격리 검증이 실패하면 실패한 pVM을 시작하지 않고 Host Application에 오류를 반환한다 |

---

| UC-03 | Camera/AI HW 공유 사용 |
|---|---|
| Actor | Workload(Camera/AI), Normal Camera Application |
| Pre-Condition | Workload(Camera/AI)가 실행 중이고 Normal Camera Application이 Camera HW 사용을 요청할 수 있다 |
| Post-Condition | Workload(Camera/AI)와 Normal Camera Application이 Camera/AI HW를 서로 배타적으로(동시 점유 없이) 사용했고, 주체 전환 시 잔류 데이터 유출이 없었다 |
| Main Flow | 1. Workload(Camera/AI)가 Camera/AI HW 사용을 요청한다<br>2. 시스템은 현재 HW를 점유한 다른 주체가 없음을 확인하고, S2MPU를 통해 HW 접근 권한을 Workload(Camera/AI)에 배타적으로 전용 할당한다 (점유 중 다른 주체의 접근은 차단)<br>3. Workload(Camera/AI)는 배타적으로 확보한 Camera/AI HW로 보안 데이터를 처리한다<br>4. 시스템은 처리 완료 후 HW 버퍼의 잔류 데이터를 보안 격리하고 접근 권한을 회수하여 HW를 유휴 상태로 전환한다<br>5. Normal Camera Application이 Camera HW 사용을 요청한다<br>6. 시스템은 HW가 유휴 상태(어떤 주체도 점유하지 않음)임을 확인하고 Camera HW 접근 권한을 Normal Camera Application에 배타적으로 할당한다 |
| Alternative Flow | 1. 시스템은 한 주체가 HW를 점유 중일 때 다른 주체의 사용 요청이 들어오면 동시 접근을 허용하지 않고 요청을 큐에 대기시켜, 현재 사용 완료 및 권한 회수 후 순차 처리한다<br>2. 시스템은 Camera/AI HW 사용 주체 전환 전 잔류 데이터 보안 격리가 실패하면 접근 권한 회수/재할당을 중단하고 오류를 기록한다<br>3. 시스템은 허가되지 않은 pVM 또는 애플리케이션이 Camera/AI HW 접근을 요청하면 S2MPU 정책으로 접근을 차단한다 |

---

| UC-04 | 도메인 간 보안 데이터 전송 |
|---|---|
| Actor | Host Application, Workload(Camera/AI) |
| Pre-Condition | Host Application이 데이터 전송을 요청할 수 있고 Workload(Camera/AI)가 실행 중이다 |
| Post-Condition | 데이터가 Host에 노출되지 않고 대상 도메인에 전달되었다 |
| Main Flow | 1. Host Application이 도메인 간 보안 데이터 전송을 요청한다<br>2. 시스템은 송신/수신 도메인에만 접근 가능한 보안 공유 버퍼를 생성한다<br>3. Workload(Camera/AI)는 데이터를 보안 공유 버퍼에 기록한다<br>4. Workload(Camera/AI)는 대상 도메인에서 공유 버퍼의 데이터를 읽어 처리한다<br>5. 시스템은 전송 완료 후 공유 버퍼를 초기화한다 |
| Alternative Flow | 1. 시스템은 수신 Workload가 응답 없는 경우 전송을 중단하고 공유 버퍼를 초기화한다<br>2. 시스템은 공유 버퍼 권한 설정에 실패하면 버퍼를 해제하고 Host Application에 오류를 반환한다<br>3. Workload(Camera/AI)는 전송 중 데이터 무결성 검증이 실패하면 데이터를 폐기하고 재전송을 요청한다 |

---

| UC-05 | 보안 Workload 동적 탑재 |
|---|---|
| Actor | Host Application |
| Pre-Condition | 플랫폼이 실행 중이고 신규 Workload 이미지가 서명되어 있다 |
| Post-Condition | 신규 보안 Workload가 펌웨어 재배포 없이 격리 환경에서 실행 중이다 |
| Main Flow | 1. Host Application이 신규 보안 Workload 이미지를 pVM 관리 API에 전달한다<br>2. 시스템은 이미지 서명을 검증한다<br>3. 시스템은 새 pVM 인스턴스를 생성하고 Workload를 탑재한다<br>4. 시스템은 새 Workload를 기존 pVM들과 독립적으로 실행한다 |
| Alternative Flow | 1. 시스템은 서명 검증 실패 시 탑재를 중단하고 Host Application에 오류를 반환한다<br>2. 시스템은 Workload 이미지 형식이 지원되지 않으면 pVM 생성을 수행하지 않고 Host Application에 오류를 반환한다<br>3. 시스템은 신규 Workload에 필요한 자원이 부족하면 기존 pVM 상태를 유지하고 탑재 요청을 실패 처리한다 |

---

| UC-06 | Secure OS ENC/DEC 명령 전송 |
|---|---|
| Actor | Workload(Camera/AI) |
| Pre-Condition | Workload(Camera/AI)가 실행 중이고 pVM 내 Secure OS의 기능을 사용할 준비가 되어 있다 |
| Post-Condition | 데이터가 암호화/복호화된 상태로 Workload(Camera/AI)에 반환되었다 |
| Main Flow | 1. Workload(Camera/AI)가 Secure OS에 ENC/DEC 명령과 대상 데이터를 전달한다<br>2. 시스템은 Secure OS를 통해 데이터를 암호화 또는 복호화한다<br>3. 시스템은 처리된 데이터를 Workload(Camera/AI)에 반환한다<br>4. Workload(Camera/AI)는 처리된 데이터를 후속 보안 처리에 사용한다 |
| Alternative Flow | 1. 시스템은 ENC/DEC 실패 시 오류를 반환하고 평문 데이터는 pVM 외부로 유출하지 않는다<br>2. 시스템은 Secure OS가 응답하지 않으면 요청을 시간 초과 처리하고 세션을 정리한다<br>3. 시스템은 잘못된 명령 또는 권한 없는 요청이 전달되면 처리를 거부하고 오류를 반환한다 |
