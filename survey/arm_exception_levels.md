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
| EL2는 항상 Secure world다 | EL과 Security state는 별개다. 일반 pKVM은 Non-secure EL2에서 실행된다. |

## 9. 공식 자료

- [S1] [Arm: Exception model](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Exception%20model.pdf)
- [S2] [Arm: Armv8-A Instruction Set Architecture](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20Instruction%20Set%20Architecture.pdf)
- [S3] [Arm: Armv8-A virtualization](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20virtualization.pdf)
- [S4] [Arm: Changing Exception Level and Security State with an Armv8-A FVP](https://developer.arm.com/community/arm-community-blogs/b/tools-software-ides-blog/posts/changing-exception-level-and-security-state-with-an-armv8a-fixed-virtual-platform)
- [S5] [Arm Architecture Reference Manual for A-profile](https://developer.arm.com/documentation/ddi0487/latest/)

[S1]: https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Exception%20model.pdf
[S2]: https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20Instruction%20Set%20Architecture.pdf
[S3]: https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20virtualization.pdf
[S4]: https://developer.arm.com/community/arm-community-blogs/b/tools-software-ides-blog/posts/changing-exception-level-and-security-state-with-an-armv8a-fixed-virtual-platform
[S5]: https://developer.arm.com/documentation/ddi0487/latest/
