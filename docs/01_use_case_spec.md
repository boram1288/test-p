# 유즈케이스 명세

---

| UC-01 | pVM 생성/시작/정지/종료 |
|---|---|
| Actor | 사용자 |
| Pre-Condition | 시스템이 부팅되어 있고 pVM 이미지가 서명된 상태로 준비되어 있다 |
| Post-Condition | pVM이 요청된 상태(Running 또는 Stopped)로 전환되었다 |
| Main Flow | 1. 사용자가 pVM API로 pVM 생성을 요청한다<br>2. 시스템이 메모리/CPU 자원을 할당하고 pVM 인스턴스를 초기화한다<br>3. 사용자가 pVM 시작 명령을 호출한다<br>4. pVM이 격리된 상태로 Running 상태가 된다<br>5. 사용자가 pVM 정지 명령을 호출한다<br>6. 시스템이 pVM을 종료하고 할당 자원을 회수한다 |
| Alternative Flow | pVM생성 실패 시 pVM 생성을 중단하고 사용자에게 오류를 반환한다 |

---

| UC-02 | 다중 pVM 동시 운용 |
|---|---|
| Actor | 사용자 |
| Pre-Condition | Secure Camera pVM과 Secure AI pVM 이미지가 준비되어 있다 |
| Post-Condition | 복수의 pVM이 격리된 상태로 독립적으로 동시 운용 중이다 |
| Main Flow | 1. 사용자가 Secure Camera pVM을 생성하고 시작한다<br>2. 사용자가 Secure AI pVM을 생성하고 시작한다<br>3. 두 pVM이 독립된 메모리 공간에서 동시에 실행된다 |
| Alternative Flow | pVM 중 하나가 종료 혹은 Crash되어도 나머지 pVM은 영향받지 않고 계속 동작한다 |

---

| UC-03 | Camera/AI HW 공유 사용 |
|---|---|
| Actor | 사용자 |
| Pre-Condition | Secure Camera pVM과 Host가 모두 실행 중이다 |
| Post-Condition | 사용자가 Camera/AI HW를 충돌/데이터 유출 없이 사용했다 |
| Main Flow | 1. Secure Camera pVM이 Camera HW 사용을 요청한다<br>2. 시스템이 S2MPU를 통해 Camera HW 접근 권한을 Secure Camera pVM에 전용 할당한다<br>3. Secure Camera pVM이 Camera HW로 영상을 처리한다<br>4. 처리 완료 후 시스템이 Camera HW 버퍼의 잔류 데이터를 삭제하고 접근 권한을 반환한다<br>5. Host의 일반 카메라 기능이 동일한 Camera HW를 이어서 사용한다 |
| Alternative Flow | HW IP 접근 충돌 발생 시 요청을 큐에 대기시키고 현재 사용 완료 후 순차 처리한다 |

---

| UC-04 | 격리 도메인 간 보안 데이터 전송 |
|---|---|
| Actor | 사용자 |
| Pre-Condition | Secure Camera pVM과 Secure AI pVM이 모두 실행 중이다 |
| Post-Condition | 영상 데이터가 Host에 노출되지 않고 Secure AI pVM에 전달되었다 |
| Main Flow | 1. Secure Camera pVM이 영상 프레임 데이터를 보안 공유 버퍼에 기록한다<br>2. 공유 버퍼는 두 pVM만 접근 가능하며 Host는 직접 읽을 수 없다<br>3. Secure AI pVM이 공유 버퍼에서 데이터를 읽어 NPU 추론 입력으로 사용한다<br>4. 전송 완료 후 공유 버퍼가 초기화된다 |
| Alternative Flow | 수신 pVM이 응답 없는 경우 전송을 중단하고 공유 버퍼를 초기화한다 |

---

| UC-05 | 보안 워크로드 동적 탑재 |
|---|---|
| Actor | 사용자 |
| Pre-Condition | 플랫폼이 실행 중이고 신규 워크로드 이미지가 서명되어 있다 |
| Post-Condition | 신규 보안 워크로드가 펌웨어 재배포 없이 격리 환경에서 실행 중이다 |
| Main Flow | 1. 사용자가 신규 보안 워크로드 이미지를 pVM 관리 API에 전달한다<br>2. 시스템이 이미지 서명을 검증한다<br>3. 시스템이 새 pVM 인스턴스를 생성하고 워크로드를 탑재한다<br>4. 새 워크로드가 기존 pVM들과 독립적으로 실행된다 |
| Alternative Flow | 서명 검증 실패 시 탑재를 중단하고 사용자에게 오류를 반환한다 |

---

| UC-06 | Secure OS ENC/DEC 명령 전송 |
|---|---|
| Actor | 사용자 |
| Pre-Condition | Secure AI pVM이 실행 중이고 pVM 내 Secure OS가 초기화되어 있다 |
| Post-Condition | 데이터가 암호화/복호화된 상태로 반환되었다 |
| Main Flow | 1. 사용자가 Secure OS에 ENC/DEC 명령과 대상 데이터를 전달한다<br>2. Secure OS가 데이터를 암호화 또는 복호화한다<br>3. 처리된 데이터가 사용자에게 반환된다<br>4. 사용자가 처리된 데이터를 외부 시스템으로 전달한다 |
| Alternative Flow | ENC/DEC 실패 시 오류를 반환하고 평문 데이터는 pVM 외부로 유출하지 않는다 |

---

| UC-07 | pVM 모니터링 및 장애 복구 |
|---|---|
| Actor | 사용자 |
| Pre-Condition | pVM이 실행 중이고 모니터링이 활성화되어 있다 |
| Post-Condition | 장애 pVM이 재시작되었고 다른 pVM과 Host는 영향받지 않았다 |
| Main Flow | 1. 시스템이 pVM 상태 이상을 감지한다<br>2. 사용자에게 장애 알림이 전달된다<br>3. 시스템이 해당 pVM의 자원을 안전하게 회수한다<br>4. 다른 pVM과 Host는 정상 동작을 유지한다<br>5. 자동 재시작 정책 또는 사용자 명령에 따라 pVM이 재시작된다<br>6. 재시작된 pVM이 정상 상태로 복귀한다 |
| Alternative Flow | 재시작 실패 시 pVM을 종료하고 사용자에게 알린다 |
