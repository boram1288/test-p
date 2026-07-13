# tzdaemon 정리 — 역할, 동작방식, TEE 데몬과의 차이, REE 필요성

> **출처**: ExynosTEE REE SW skill map (page 1857270820), tzdaemon (page 988831677), [ExynosTEE] CA-TA Access Control (page 988831777), VM(Linux-Android) without PV (page 988831655), [Security] Secure OS comparison (page 3476748772), CC 검증 범위 문서 (page 988831627), BringupGuide_20220318 (page 988831717)
> **기준 스택**: ExynosTEE (Trustware/TEEgris 계열), REE = Linux / Android / QNX (sys-domain + guest VM 구조 포함)

---

## 1. tzdaemon 개요

tzdaemon은 **REE sys-domain에서 root 권한으로 상주하는 유저스페이스 데몬**이다.
init 서비스로 자동 시작되며 (`/usr/bin/tzdaemon --daemon=no`), CA(Client Application)와 TEE 사이의 **제어 경로(control plane) 중개자** 역할을 한다.

### ExynosTEE REE SW 구성 요소

| 구성 요소 | 위치 | 역할 |
|---|---|---|
| libteec / fe_libteec | REE user space (.so) | CA에 GP Client API 제공 |
| **tzdaemon** | REE sys-domain user space | CA 요청 중개, TA 로딩, REE FS 대행 |
| tzdev | REE kernel driver | 파라미터 재조립, 공유메모리 적재, SMC 발행 |
| vtee-fe (tzdev_fe) | guest VM kernel | VM 내 CA 요청을 vtee-be로 redirect |
| vtee-be | sys-domain kernel | vtee-fe 요청을 tzdev로 forward |

### 핵심 역할 (skill map 기준)

1. **CA 요청 중개** — libteec가 Unix Domain Socket으로 보낸 GP 명령(InitializeContext, OpenSession 등)을 재조립하여 `/dev/tzdev` ioctl로 tzdev에 전달
2. **TA 로딩** — TEE에는 파일시스템이 없으므로, REE 파일시스템에서 TA 이미지를 읽어 TEE로 로드
3. **REE 파일시스템 대행 (RPC)** — TEE의 secure storage 데이터와 로그를 REE 파일시스템에 읽고 쓰는 작업 수행
4. **CA 신원(identity) 생성** — `TEEC_LOGIN_APPLICATION` 세션 open 시 CA_PID·VM_ID 기반 CA_UUID를 **privileged 레벨에서** 생성 (CA 자신이 만들면 위조 가능하므로). sys-domain(be-domain)에서는 tzdaemon이, fe-domain에서는 be-driver가 담당

---

## 2. 동작 방식

### 내부 구조

C++ 프로그램으로 세 그룹의 클래스로 구성된다.

- **connection 계열**
  - `TZDConnection` — `/dev/tzdev` fd 관리
  - `TZMemConnection` — `/dev/tzmem` fd 관리
  - `ListenConnection` / `SocketConnection` — libteec 요청 수신용 소켓 관리
  - `EventConnection` — IPC용 event fd 관리
  - `EventLoop` — epoll 기반으로 위 connection들을 listen
- **command 계열** — `CommandInvokeQueue`, `Command`, `CommandBuffer`
- **기타** — 로깅, main

### 초기화 시퀀스

1. `/dev/tzmem`, `/dev/tzdev`, `/dev/tzlog` open
2. logger 스레드 시작
3. socket server 셋업
4. eventloop 스레드 시작 (epoll I/O multiplexer)
5. worker 스레드 4개 시작 — 명령 처리 후 tzdev로 ioctl 발행

### 제어 경로 (control plane)

```
CA → libteec → UDS socket → tzdaemon → ioctl(/dev/tzdev) → SMC → TEE (TRM/root server)
```

- TEE 쪽 상대는 **TRM(root server)** 이며 `trm_message` 프로토콜로 대화한다.
- OpenSession 처리(`onOpenSession`) 시 tzdev로 devctl(ioctl)을 두 번 호출:
  ① REE 파일시스템에서 TA 이미지 로딩 → ② 세션 수립

### 데이터 경로 (data plane) — tzdaemon을 거치지 않음

세션이 열리면 tzdaemon이 `tzdev_invoke` fd를 열어 소켓으로 libteec에 전달한다(fd passing, `teecSession::_endpoint_fd`).
이후:

- `TEEC_InvokeCommand` — libteec가 `/dev/tzdev_invoke`로 **직접** 수행
- 공유메모리 (`TEEC_RegisterSharedMemory`, `TEEC_AllocateSharedMemory`) — libteec가 `/dev/tzmem`으로 **직접** 수행

즉 tzdaemon은 **컨텍스트/세션 수명주기와 TA 로딩만 관장**하고, 성능이 중요한 invoke/데이터 이동은 커널 드라이버 직행 경로를 쓴다.

---

## 3. TEE 영역 root/device daemon과의 차이

TEE(secure world)에는 다음 구성 요소들이 있다 (CC 검증 범위 문서 기준):

- **TRM (root server / root task)** — 로그 태그 `[TZ_ROOT]`, trm.cpp. TA 생명주기·세션 관리, TA 검증(서명, anti-rollback), client identity 관리
- **Storage Server** — secure storage 암복호화·무결성 보장
- **Communication Manager** — REE↔TEE 통신 관리
- **Secure drivers (device daemons)** — 보안 HW(OTP, RPMB, crypto 등) 직접 제어

### 비교

| 구분 | tzdaemon (REE) | TRM · Storage Server · secure drivers (TEE) |
|---|---|---|
| 신뢰 수준 | **untrusted** — TCB 밖 | **trusted** — TCB 안, CC 인증 범위 |
| 역할 성격 | 중개자/대리인 (proxy, RPC servant) | 보안 기능 수행 주체 |
| TA 로딩 | 파일을 읽어 **전달**만 함 | **서명 검증, anti-rollback, 복호화** 수행 |
| Secure storage | 암호화된 blob을 REE FS에 저장/회수만 | 암복호화·무결성 보장 |
| HW 접근 | 없음 (디바이스 노드 경유 SMC뿐) | secure driver가 보안 HW 직접 제어 |

### 핵심: 신뢰 경계

차이의 본질은 기능이 아니라 **신뢰 경계**다. tzdaemon이 장악당해도 기밀성·무결성은 깨지지 않도록 설계되어 있다:

- tzdaemon은 TEE가 검증할 데이터를 나르는 역할 → 공격자가 tzdaemon을 통제해도 **TA 위조나 secure storage 복호화는 불가능**
- 영향 범위는 **가용성(DoS)** 과 **CA identity 신뢰**(sys-domain의 CA_UUID 생성)에 한정
- 반대로 TEE 쪽 root/device daemon이 뚫리면 **TCB 자체가 무너짐**

---

## 4. REE에 tzdaemon이 꼭 필요한가?

**결론: "데몬 프로세스 자체"는 필수가 아니지만, 그 기능들은 REE 어딘가에 반드시 있어야 한다.**

### 데몬 형태가 선택임을 보여주는 실증 — fe-domain에는 tzdaemon이 없다

POIP guest VM(Android/Linux)의 fe_libteec는 소켓 대신 `/dev/tzdev_invoke`·`/dev/tzmem`으로 **vtee-fe(be-driver)에 직접** 연결한다:

```c
#ifdef BUILD_ANDROID
    int _tzdev_fd;   // fd connected to tzdev_fe driver
#else
    int _tzd_sock;   // socket connected to tzdaemon
#endif
```

CA_UUID 생성도 tzdaemon 대신 **be-driver가 vlink shmem의 VM_ID로** 수행한다.
→ 데몬의 역할을 커널 드라이버로 옮긴 사례. 다만 그 경우에도 요청은 sys-domain으로 포워딩되고, **거기서는 tzdaemon이 TA 로딩과 파일시스템 RPC를 처리**한다. 시스템 전체에서 사라진 것이 아니라 be 쪽으로 집약된 것이다.

### 역할 자체가 사라질 수 없는 이유 — TEE의 구조적 의존성

1. **TEE에는 파일시스템이 없다** — TA 이미지, secure storage blob, 로그는 REE 스토리지에 있어야 하고, 누군가 REE에서 파일 I/O를 대행해야 한다. 커널에서 파일 I/O는 가능은 하나 안티패턴이므로 유저스페이스 데몬이 자연스러운 위치
2. **CA identity는 CA보다 높은 권한에서 생성해야 한다** — untrusted CA의 자기 신원 자가 신고는 위조 가능
3. **다중 CA 요청의 직렬화/다중화, 죽은 CA 정리** — 소켓 연결 단절로 세션 정리를 감지하는 주체 필요

### 표준 패턴

이는 ExynosTEE만의 설계가 아니라 GP TEE 아키텍처의 표준 패턴이다 — **OP-TEE도 같은 이유로 `tee-supplicant`라는 REE 데몬**을 둔다 (TA 로딩, secure storage RPC 담당).

이론적으로 TA를 전부 TEE 이미지에 내장하고 secure storage를 RPMB 직결로만 쓰면 없앨 수 있으나, TA OTA 프로비저닝·로그·저장 용량 확장성을 포기하게 된다.

---

## 5. sys-domain에서 tzdaemon 역할의 커널 이관 검토

**결론: 부분적으로 가능하고 실증 사례(fe-domain, OP-TEE)도 있으나, 전부 옮기는 것은 비추천. tzdaemon을 supplicant로 얇게 만드는 하이브리드가 현실적.**

### 커널로 옮기기 쉬운 역할 (실증 있음)

| 역할 | 이관 가능성 | 근거 |
|---|---|---|
| ① 명령 중개/다중화 | **가능** | data plane은 이미 커널 직행. fe-domain은 control plane까지 fe_libteec → tzdev_fe ioctl 직결. 업스트림 Linux TEE subsystem(`/dev/tee0`)도 동일 구조 |
| ② CA_UUID 생성 | **가능, 오히려 유리** | ioctl 시점에 `current` task에서 PID·실행 바이너리(`get_task_exe_file()`)를 직접 획득 → `/proc/{pid}/exe` 방식(platform dependent, CA-TA Access Control 문서 지적)보다 위조에 강함. fe-domain에서는 이미 be-driver가 VM_ID 확인 수행 |
| ③ 세션 수명주기 정리 | **가능, 더 신뢰성 있음** | CA 사망 시 fd `release()` 콜백이 보장됨 → 소켓 단절 감지보다 확실 |

### 커널로 옮기기 어려운 역할 (파일시스템 의존)

- **④ TA 로딩 — 절반만 가능.** `request_firmware()` 계열로 고정 경로에서 TA 이미지를 읽는 것은 커널에서 허용되는 패턴. 그러나 TA 검색 경로 정책(`app_res_path`), OTA 프로비저닝(`ClientContext::tryProvision`) 같은 정책 로직까지 커널에 넣는 것은 부적절
- **⑤ secure storage/로그의 REE FS 쓰기 — 실질적 블로커.**
  - 데이터 파티션 마운트 시점보다 드라이버 로드가 빠를 수 있음 (부팅 순서 의존성)
  - Android의 경우 `/data`가 FBE 암호화 → user unlock 전 접근 불가
  - SELinux 라벨링, quota, fsync 오류 처리를 커널 컨텍스트에서 감당해야 함
  - OP-TEE가 control plane을 커널 TEE subsystem으로 옮기고도 **tee-supplicant를 없애지 못한 이유**가 정확히 이것 (RPC 기반 secure storage와 TA 로딩만 남김)

### 얻는 것 vs 잃는 것

**얻는 것 (적음)**: control plane(세션 open/close)은 빈도가 낮아 UDS 홉 제거의 성능 이득 미미. 상주 프로세스 하나 제거 + identity 강화 정도.

**잃는 것 (뚜렷함)**:

- **커널 attack surface 증가** — tzdaemon 버그는 프로세스 crash로 끝나지만, 같은 버그가 커널에 있으면 REE 커널 전체 장악. tzdaemon을 "untrusted해도 되는 위치"에 둔 설계 이점이 일부 상쇄됨
- **C++ 코드베이스 재작성** — 현재 tzdaemon은 C++ (epoll 이벤트루프 + 워커 스레드 4개), 커널은 C
- **OS 간 one-source 유지 어려움** — QNX에서는 tzdev·tzdaemon 모두 유저 프로세스(resmgr)라 "커널로 옮긴다"는 개념 자체가 성립하지 않음. Linux/Android만 커널화하면 QNX와 코드 구조가 갈라져 "PV driver one-source solution" 방향과 상충

### 권장 방향

전부 옮기기보다 **tzdaemon을 supplicant로 얇게 만드는 하이브리드**: ①②③(중개·identity·수명주기)은 tzdev로 내리고, ④⑤(파일시스템 의존 RPC)만 남긴 최소 데몬 유지 — OP-TEE가 검증한 분할선과 동일.

> **확인 필요**: skill map에 "secure storage RPC 시 tzdev가 최종적으로 REE 파일시스템에 저장한다"는 문장이 있음. 정확하다면 ExynosTEE는 이미 일부 FS 작업을 커널에서 수행 중이라는 뜻 → 실제 코드(ree-user gerrit, `vendor/exynostee/tzdaemon`)에서 RPC 처리 주체 확인 필요.

---

## 한 줄 요약

> tzdaemon은 "TEE의 REE 쪽 대리인(untrusted helper)"으로 보안 기능의 주체가 아니라 파일시스템·CA 신원·요청 중개를 대행하며, 데몬이라는 **형태**는 선택(fe-domain에선 드라이버가 대체)이지만 그 **역할** 자체는 TEE가 REE 리소스에 의존하는 한 없앨 수 없다.
