# ARM Exception Level과 전환 방법

- 조사일: 2026-08-31
- 범위: ARMv8-A의 AArch64 Exception Model
- 제외: AArch32 mode 상세, Armv9 RME/Realm state 상세
- 관련 문서: [시스템 개요](../docs/01_시스템_개요.md),
  [Host-pVM 통신 조사](./host_pvm_communication.md)

## 1. 한눈에 보는 결론

Exception Level(EL)은 CPU가 현재 실행 중인 코드에 허용하는 **권한 단계**다.
현재 EL은 일반적인 branch나 function call로 바뀌지 않고, 다음 두 경우에 바뀐다.[S1]

- 낮은 EL에서 같거나 높은 EL로: exception 진입
- 높은 EL에서 원래 또는 낮은 EL로: exception return인 `ERET`

높은 EL이 낮은 EL에 **비동기 이벤트를 알리는 것**은 별도 문제다. EL2는 EL1용
virtual interrupt를 pending시킬 수 있지만, 같은 PE에서 EL2가 실행 중이라면 EL1이
실제로 실행되기 위해서는 여전히 `ERET` 또는 이후의 vCPU scheduling이 필요하다.

Reset은 실행 중인 software 전환이 아니라 최초 EL과 Execution state를 정하는 별도
진입점이다. 실제 reset state와 boot hand-off EL은 CPU와 platform 구성을 확인해야 한다.

숫자가 클수록 CPU와 system resource를 제어할 권한이 크다. 일반적인 software 배치는
다음과 같지만, 이는 Architecture가 특정 software를 강제 배치한다는 뜻은 아니다.[S1]

| Level | 일반적인 실행 주체 | 대표 역할 |
| --- | --- | --- |
| EL0 | User Application, pVM Workload | 비특권 application 실행, system call로 kernel service 요청 |
| EL1 | Host/pVM OS kernel과 driver | process, Stage-1 MMU, exception, device와 kernel resource 관리 |
| EL2 | Hypervisor, pKVM | EL0/EL1 trap, VM context, Stage-2 translation과 virtual interrupt 관리 |
| EL3 | Secure Monitor, 저수준 firmware | Security state 전환과 platform/secure monitor service |

EL0와 EL1은 필수지만 EL2와 EL3은 Architecture상 선택 사항이다. pKVM을 실행하는
대상 CPU에는 virtualization 기능을 가진 EL2가 필요하다.[S1][S3]

대표적인 전환을 단순화하면 다음과 같다.

```text
EL3  Secure Monitor / Firmware
 ↑   SMC from EL1 or EL2, routed IRQ/FIQ/SError
 ↓   ERET
EL2  Hypervisor / pKVM
 ↑   HVC from EL1, trap, routed exception
 ↓   ERET
EL1  OS Kernel / Driver
 ↑   SVC from EL0, fault, IRQ/FIQ/SError
 ↓   ERET
EL0  Application / Workload
```

이 그림은 대표 경로다. `SMC`는 EL1에서 EL2를 거치지 않고 EL3을 target으로 할 수
있고, interrupt와 trap의 실제 목적지는 EL2/EL3 설정에 따라 달라질 수 있다.

## 2. 각 Exception Level

### 2.1 EL0: Application level

- 가장 낮은 권한이며 일반 application과 pVM workload가 실행된다.
- memory access는 unprivileged permission으로 검사된다.
- EL1 이상에서만 허용한 System register와 MMU 설정에 직접 접근할 수 없다.
- OS service가 필요하면 보통 `SVC`로 EL1 system call handler에 진입한다.
- EL0 자체는 `HVC`나 `SMC`로 EL2/EL3을 직접 호출할 수 없다.[S2]

### 2.2 EL1: OS kernel level

- Linux 같은 OS kernel, scheduler, filesystem과 device driver가 실행되는 일반적인 EL이다.
- EL0/EL1의 Stage-1 translation, memory permission과 exception handler를 관리한다.
- EL0의 `SVC`, fault와 interrupt를 처리한 뒤 `ERET`으로 EL0에 복귀한다.
- Hypervisor service는 `HVC`로 EL2에, Secure Monitor service는 `SMC`로 EL3에
  요청할 수 있다. 단, EL2 설정이 `SMC`를 먼저 trap할 수 있다.

### 2.3 EL2: Hypervisor level

- VM의 EL0/EL1 실행을 중재하는 Hypervisor 또는 pKVM이 사용하는 일반적인 EL이다.
- Stage-2 translation, EL0/EL1 instruction·System register trap과 virtual exception을
  제어한다.[S3]
- EL1의 `HVC`, 설정된 trap 또는 routed exception으로 진입한다.
- guest/Host context로 돌아갈 때 `ERET`을 사용한다.
- EL3 firmware service가 필요하면 `SMC`를 실행할 수 있다.

### 2.4 EL3: Secure Monitor와 firmware level

- 고전적인 ARMv8-A TrustZone 구성에서 Secure Monitor와 저수준 firmware가 실행된다.
- `SCR_EL3`로 lower EL의 Secure/Non-secure state와 일부 exception routing을 제어한다.
- EL1 또는 EL2의 `SMC`와 EL3으로 routing된 exception으로 진입한다.
- `ELR_EL3`과 `SPSR_EL3`을 준비하고 `ERET`하여 EL2, EL1 또는 EL0 같은 lower EL로
  내려간다. boot hand-off에서는 중간 EL을 반드시 하나씩 거칠 필요가 없다.[S4]

## 3. 낮은 EL에서 높은 EL로 가는 방법

### 3.1 Software가 의도적으로 발생시키는 synchronous exception

| Instruction | 기본 target | 일반적인 호출 | EL0 실행 가능 | 대표 용도 |
| --- | --- | --- | --- | --- |
| `SVC #imm` | EL1 | EL0 → EL1 | 가능 | Application system call |
| `HVC #imm` | EL2 | EL1 → EL2 | 불가 | Hypercall, guest/Host kernel이 Hypervisor service 요청 |
| `SMC #imm` | EL3 | EL1/EL2 → EL3 | 불가 | Secure Monitor Call, firmware/TEE service 요청 |

표의 target은 기본 의미다. EL2/EL3 구현 여부와 `HVC`/`SMC` enable·trap 설정에 따라
실제 exception 처리 위치가 달라질 수 있으므로 platform register 설정을 함께 확인한다.

이 명령들은 지정 EL에 임의 코드로 jump하는 명령이 아니다. CPU가 해당 EL의
exception vector로 진입시키고 handler가 요청 번호, 인자와 권한을 확인한다.[S1][S2]

또한 exception은 실행 권한을 낮추지 않는다. 예를 들어 EL2에서 `SVC`를 실행해도
EL1로 내려가지 않고 EL2의 exception으로 처리된다. EL0는 `HVC`/`SMC`를 실행할 수
없으므로 application이 이를 이용해 EL2/EL3 권한을 직접 얻을 수 없다.[S2]

### 3.2 Fault, trap과 asynchronous exception

instruction을 명시적으로 호출하지 않아도 다음 사건으로 같거나 높은 EL에 진입한다.

- synchronous fault: 잘못된 instruction, permission fault, alignment fault 등
- virtualization trap: EL1의 특정 System register, MMIO 또는 instruction 접근을 EL2가
  가로채도록 설정한 경우
- asynchronous exception: `IRQ`, `FIQ`, `SError` 및 virtual interrupt

Physical IRQ/FIQ/SError는 `HCR_EL2`와 `SCR_EL3` 설정에 따라 EL1, EL2 또는 EL3으로
routing할 수 있다. 현재 EL보다 낮은 EL로 routing된 exception은 EL을 낮추지 않고
pending/masked 상태로 남는다.[S1]

특수한 Hypervisor 설정에서는 EL0 exception 중 원래 EL1으로 갈 사건을 EL2로
routing할 수도 있다. 그러나 EL0가 `HVC`를 실행한 것은 아니며, 일반적인 OS syscall
경로는 `EL0 --SVC--> EL1`이다. EL3으로 routing된 physical interrupt라면 EL0에서
EL3으로 exception을 취할 수도 있지만, EL0가 `SMC`로 EL3 service를 직접 호출하는
경로는 아니다.

## 4. Exception 진입과 복귀에서 CPU가 하는 일

ELx로 exception을 취하면 CPU는 다음 핵심 동작을 수행한다.[S1]

1. 복귀할 instruction address를 target EL의 `ELR_ELx`에 저장한다.
2. 이전 `PSTATE`를 target EL의 `SPSR_ELx`에 저장한다.
3. 현재 `PSTATE`와 EL을 exception handler용 상태로 바꾼다.
4. `VBAR_ELx`가 가리키는 vector table의 해당 entry로 분기한다.
5. handler software가 필요한 general-purpose register를 별도로 저장하고 처리한다.

처리가 끝난 privileged handler는 `ERET`을 실행한다.

```text
PC     <- ELR_ELx
PSTATE <- SPSR_ELx
EL     <- SPSR_ELx에 기록된 유효한 target EL
```

`ERET`은 이 복원을 원자적으로 수행한다. 보통은 exception 발생 전 EL과 주소로
돌아가지만, boot firmware나 Hypervisor는 유효한 lower EL과 시작 주소를
`SPSR_ELx`/`ELR_ELx`에 준비하여 새 실행 환경을 시작할 수도 있다.

일반 function return인 `RET`은 `x30`의 주소로 분기할 뿐 EL을 바꾸지 않는다.
EL을 내려가는 동작에는 exception return인 `ERET`이 필요하다.

## 5. 전환별 요약

| 전환 | 대표 방법 | 돌아오는 방법 | 비고 |
| --- | --- | --- | --- |
| EL0 → EL1 | `SVC`, fault, EL1-routed interrupt | EL1의 `ERET` | Linux system call과 page fault의 일반 경로 |
| EL0 → EL2/EL3 | 해당 EL로 routing된 exception | target EL의 `ERET` | EL0는 `HVC`/`SMC`를 직접 실행할 수 없음 |
| EL1 → EL0 | EL1이 `ELR_EL1`/`SPSR_EL1` 문맥으로 `ERET` | `SVC`/exception으로 재진입 | 일반 branch나 `RET`으로는 불가 |
| EL1 → EL2 | `HVC`, EL2 trap, EL2-routed exception | EL2의 `ERET` | EL2가 구현되고 호출/routing이 허용돼야 함 |
| EL2 → EL1 | EL2가 `ELR_EL2`/`SPSR_EL2` 문맥으로 `ERET` | `HVC`/trap/exception | VM entry와 exit의 핵심 경로 |
| EL2 → EL0 | target을 EL0로 준비한 `ERET` | EL2-routed exception | 유효한 상태라면 EL1을 생략할 수 있음 |
| EL1 → EL3 | `SMC`, EL3-routed physical exception | EL3의 `ERET` | 설정에 따라 `SMC`가 EL2에 먼저 trap될 수 있음 |
| EL2 → EL3 | `SMC`, EL3-routed physical exception | EL3의 `ERET` | Secure Monitor/firmware service |
| EL3 → EL2/EL1/EL0 | target state/address를 준비한 뒤 `ERET` | `SMC` 또는 routed exception | boot/runtime hand-off, 중간 EL 생략 가능 |

`ERET`의 target은 바로 아래 EL로 제한되지 않는다. 다만 현재 EL보다 높거나 구현되지
않은 EL, 또는 `SCR_EL3`/`HCR_EL2`의 Execution·Security state와 맞지 않는 값을
`SPSR_ELx`에 지정하면 illegal exception return이 된다.[S1][S5]

중요한 원칙은 다음 두 문장으로 요약할 수 있다.

1. **상향 또는 같은 EL 진입은 exception이다.**
2. **하향 또는 이전 문맥 복귀는 `ERET`이다.**

### 5.1 하향 전환과 비동기 알림은 다르다

같은 PE에서는 EL2와 EL1이 동시에 실행되지 않는다. 따라서 EL2가 현재 실행 중일 때
EL1의 임의 함수로 내려가 실행하는 별도 `CALL` instruction은 없다. physical execution
level을 EL2에서 EL1로 바꾸는 정상 AArch64 경로는 exception return인 `ERET`이다.
Pointer Authentication을 결합한 `ERETAA`/`ERETAB`도 같은 exception-return 계열이지
별도의 down-call mechanism은 아니다.[S5]

반면 EL2가 EL1에 이벤트를 **pending**시키는 데에는 EL1의 선행 `HVC`가 필요하지 않다.
대표 수단은 다음과 같다.[S3]

- `HCR_EL2.VI`, `VF`, `VSE`로 vIRQ, vFIQ, vSError를 pending
- GIC virtualization interface에 특정 vCPU용 virtual interrupt를 등록
- EL2와 EL1이 합의한 shared mailbox/virtqueue에 payload를 기록하고 interrupt는
  notification으로만 사용
- target vCPU가 멈춰 있으면 event를 pending한 채 runnable로 만들고 나중에 schedule

Virtual interrupt는 EL0/EL1을 실행할 때만 signal된다. 같은 PE가 EL2/EL3에 있는
동안에는 받아들여지지 않으며, EL1로 돌아간 뒤 interrupt mask와 priority 조건을
만족할 때 exception handler가 실행된다.[S3]

EL2는 독립적으로 계속 실행되는 background thread가 아니다. event를 처리할 EL2
code가 실행되려면 다음 중 하나의 진입 원인이 있어야 한다.

- EL1 실행 중 EL2로 routing된 physical IRQ, timer 또는 SError
- EL1/EL0의 trap이나 `HVC`
- 이미 다른 PE에서 실행 중인 EL2 code

첫 번째 경우에는 EL1이 `HVC`를 호출하지 않았어도 physical event 자체가 asynchronous
exception을 발생시켜 `EL1 → EL2`로 진입한다.

### 5.2 EL2 → EL1 비동기 이벤트의 일반 흐름

```text
EL1 실행 중
  → physical IRQ/timer가 EL2로 routing되어 asynchronous exception 발생
  → EL2 handler 진입                 /* EL1의 HVC 호출은 없음 */
  → EL2가 bounded shared queue에 event record 기록
  → memory ordering을 보장한 뒤 target vCPU의 vIRQ를 pending
  → target vCPU를 runnable로 표시
  → 같은 PE라면 EL2 --ERET--> EL1, 미실행 vCPU라면 이후 schedule
  → EL1이 vIRQ vector로 진입
  → EL1 IRQ handler/workqueue가 queue를 읽고 처리
```

Arm의 interrupt forwarding 예제도 physical IRQ를 EL2가 받은 뒤 target vCPU를
선택하고 GIC에 virtual interrupt를 등록한다. GIC 신호는 EL2 실행 중에는 무시되고,
Hypervisor가 vCPU로 복귀한 다음 EL0/EL1에서 받아들여진다.[S3]

payload를 interrupt 자체에 넣지 않는다. interrupt는 pending work가 있다는 알림이고,
실제 opcode, length, sequence, generation과 status는 shared queue나 virtual device
state에 둔다. EL1 handler는 interrupt를 acknowledge한 뒤 queue를 검증하고, 오래 걸리는
처리는 workqueue 같은 일반 kernel context로 넘긴다.

### 5.3 상황별 ERET 필요 여부

| 상황 | 처리 | 현재 PE의 `ERET` |
| --- | --- | --- |
| EL1 실행 중 HW event를 EL1으로 직접 routing | EL1이 physical IRQ/FIQ를 바로 처리, EL2는 관여하지 않음 | 불필요 |
| EL2가 같은 PE에서 event를 중재한 뒤 EL1에 전달 | shared state 기록 + vIRQ pending 후 EL1 context로 복귀 | 필요 |
| target vCPU가 현재 미실행 | vIRQ를 pending하고 runnable로 만든 뒤 scheduler가 나중에 진입 | 실제 vCPU 진입 시 필요 |
| 다른 PE에서 target EL1이 실행 중 | GIC가 해당 PE로 interrupt를 routing하거나 구현 지원 시 direct injection | event 생성 PE의 EL 전환은 불필요 |
| EL2 실행 중인데 interrupt target이 EL1 | interrupt는 lower EL로 즉시 전환시키지 않고 pending | EL1 복귀 시 필요 |

GIC는 interrupt를 특정 PE affinity로 routing할 수 있고 SGI의 target PE도 지정할 수
있다.[S6] 이 경우 한 PE의 EL2가 다른 PE에서 이미 실행 중인 EL1에 알릴 수 있으므로
event를 생성한 PE 자체는 EL을 낮출 필요가 없다. 이것은 같은 PE의 EL2→EL1
transition을 대체한 것이 아니라, 이미 EL1인 다른 실행 문맥에 interrupt를 전달한 것이다.

### 5.4 pKVM에 적용할 권장 형태

이 프로젝트에서 EL2가 pVM EL1에 보내는 unsolicited event는 다음 형태가 적합하다.

```text
EL2 producer → bounded shared event queue → per-vCPU vIRQ → pVM EL1 IRQ handler/workqueue
```

- setup 시 queue, event type, virtual INTID와 target vCPU를 미리 등록한다.
- `HVC`는 setup/acknowledgement에 사용할 수 있지만 매 event의 선행 조건은 아니다.
- queue에는 producer/consumer index, generation, sequence와 최대 길이를 둔다.
- 여러 event를 한 IRQ로 합치는 coalescing과 queue-full policy를 정의한다.
- EL1이 IRQ를 mask하거나 event를 무시할 수 있으므로 EL2는 acknowledgement를 무한히
  기다리지 않고 timeout, drop 또는 안전한 자원 회수 정책을 사용한다.
- EL2가 검증해야 할 보안 상태와 EL1에 보내는 단순 progress notification을 구분한다.

Host EL1은 guest vCPU가 아니므로 같은 표현을 그대로 적용하지 않는다. Host kernel에
알릴 때는 Host-visible event state와 physical IRQ/SGI 또는 해당 pKVM port가 정의한
Host notification mechanism을 사용한다. 어느 경우에도 Host의 acknowledgement를
보호 권한 전환 완료의 증거로 신뢰하지 않는다.

따라서 정확한 표현은 다음과 같다.

> EL1의 선행 호출 없이도 EL2는 EL1에 비동기 이벤트를 pending시킬 수 있다.
> 다만 같은 PE에서 실제 실행을 EL2에서 EL1로 넘기는 동작은 여전히 `ERET`이다.

## 6. Security state와 EL은 다르다

EL은 privilege 축이고 Secure/Non-secure는 security state 축이다. 따라서 다음 표현은
정확하지 않다.

- `EL2이므로 Secure하다.`
- `EL1이므로 Non-secure하다.`

EL0와 EL1은 Secure 또는 Non-secure context에 존재할 수 있다. 전통적인 구성의 EL2는
Non-secure Hypervisor지만, Armv8.4-A부터 Secure EL2가 선택 기능으로 추가됐다.[S3]
이 프로젝트의 pKVM/EL2는 일반적으로 Non-secure EL2이고, TEE의 EL0/EL1은
S-EL0/S-EL1을 뜻한다.

## 7. 이 프로젝트의 pKVM 배치

| 실행 주체 | 일반적인 physical EL/state | 설명 |
| --- | --- | --- |
| Host Application | NS-EL0 | Host Linux user process |
| Host kernel/driver | NS-EL1 | 비신뢰 Host Linux kernel |
| pKVM Hypervisor | NS-EL2 | Stage-2 격리와 Host/pVM context 전환 |
| pVM Workload | NS-EL0 guest context | pVM 안의 application |
| pVM kernel/driver | NS-EL1 guest context | pVM 안의 Linux kernel |
| Secure Monitor/TF-A | EL3 | Security state 전환과 monitor service |
| TEE Trusted OS/service | S-EL1/S-EL0 | Secure world의 OS와 service |

Host kernel과 pVM kernel은 둘 다 EL1 코드지만 동시에 같은 context로 실행되는 것은
아니다. EL2가 vCPU를 전환하고 서로 다른 Stage-2 translation과 VM state를 적용한다.
따라서 `EL1`이라는 이름이 같다는 사실만으로 두 kernel의 memory가 공유되지는 않는다.

## 8. 자주 생기는 오해

| 오해 | 실제 의미 |
| --- | --- |
| EL 숫자가 높으면 software가 자동으로 더 신뢰된다 | 숫자는 CPU 권한을 뜻한다. software 신뢰 여부는 threat model과 검증에 달려 있다. |
| 아무 instruction이나 실행해 EL을 올릴 수 있다 | 정해진 exception, trap과 routing만 가능하며 target handler가 요청을 검증한다. |
| `HVC`가 Host kernel driver를 호출한다 | `HVC`는 EL2 exception handler에 진입한다. driver IPC는 별도 protocol이다. |
| `SMC`는 반드시 EL2를 순서대로 거친다 | Architecture상 EL3 target이다. 다만 EL2가 trap하도록 설정할 수 있다. |
| 높은 EL에서 낮은 EL로 `RET`하면 된다 | `RET`은 EL을 바꾸지 않는다. valid `SPSR_ELx`/`ELR_ELx`와 `ERET`이 필요하다. |
| vIRQ를 pending하면 EL2에서 즉시 EL1로 바뀐다 | vIRQ는 EL0/EL1에서만 signal된다. 같은 PE가 EL2라면 EL1로 복귀할 때까지 pending이다. |
| EL2는 event가 생기면 background task처럼 실행된다 | physical exception, trap/HVC 또는 이미 EL2인 PE처럼 EL2 code를 실행시킬 원인이 필요하다. |
| EL2는 항상 Secure world다 | EL과 Security state는 별개다. 일반 pKVM은 Non-secure EL2에서 실행된다. |

## 9. 공식 자료

- [S1] [Arm: Exception model](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Exception%20model.pdf)
- [S2] [Arm: Armv8-A Instruction Set Architecture](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20Instruction%20Set%20Architecture.pdf)
- [S3] [Arm: Armv8-A virtualization](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20virtualization.pdf)
- [S4] [Arm: Changing Exception Level and Security State with an Armv8-A FVP](https://developer.arm.com/community/arm-community-blogs/b/tools-software-ides-blog/posts/changing-exception-level-and-security-state-with-an-armv8a-fixed-virtual-platform)
- [S5] [Arm Architecture Reference Manual for A-profile](https://developer.arm.com/documentation/ddi0487/latest/)
- [S6] [Arm: GICv3/v4 Software Overview](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/GICv3_v4_overview.pdf)

[S1]: https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Exception%20model.pdf
[S2]: https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20Instruction%20Set%20Architecture.pdf
[S3]: https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20virtualization.pdf
[S4]: https://developer.arm.com/community/arm-community-blogs/b/tools-software-ides-blog/posts/changing-exception-level-and-security-state-with-an-armv8a-fixed-virtual-platform
[S5]: https://developer.arm.com/documentation/ddi0487/latest/
[S6]: https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/GICv3_v4_overview.pdf
