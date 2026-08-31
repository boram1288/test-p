# 임원용 1장 요약 — ARM Exception Level

- 용도: ARM Exception Level을 처음 접하는 임원 대상 설명 슬라이드
- 범위: ARMv8-A/AArch64와 본 과제의 pKVM 배치
- 상세 근거: [ARM Exception Level과 전환 방법](./arm_exception_levels.md)

## 슬라이드 제목

**ARM Exception Level — CPU 권한과 격리를 나누는 4단계 실행 계층**

## 핵심 메시지

> ARM은 Application부터 보안 Firmware까지 CPU 권한을 4단계로 분리한다.
>
> 높은 Level일수록 통제 권한과 장애 영향이 커지므로, 핵심 격리만 상위 EL에 두고
> EL 간 전환은 최소화해야 한다.

## 슬라이드 본문

### 1. 4단계 실행 계층

| Level | 임원용 표현 | 일반 주체 | 핵심 역할 |
| --- | --- | --- | --- |
| **EL3** | Platform 보안 통제 | Secure Monitor, TF-A/Firmware | Secure/Non-secure 전환, Platform 보안 Service와 최상위 제어 |
| **EL2** | VM 격리 통제 | Hypervisor, **pKVM** | VM별 Memory·CPU·Interrupt 격리, Stage-2 기반 접근 통제 |
| **EL1** | OS 자원 통제 | Host/pVM Linux Kernel, Driver | Process·Memory·Device와 System Resource 관리 |
| **EL0** | Service 실행 | Host Application, pVM Workload | 사용자 기능과 Business Logic 실행 |

슬라이드 중앙에는 다음처럼 **아래에서 위로 권한이 커지는 4단 Stack**으로 표현한다.

```text
높은 권한 · 작은 코드 · 큰 장애 영향

┌───────────────────────────────────────────┐
│ EL3  Platform 보안 통제                   │  Secure Monitor / Firmware
├───────────────────────────────────────────┤
│ EL2  VM 격리 통제                         │  Hypervisor / pKVM
├───────────────────────────────────────────┤
│ EL1  OS 자원 통제                         │  Linux Kernel / Driver
├───────────────────────────────────────────┤
│ EL0  Service 실행                         │  Application / Workload
└───────────────────────────────────────────┘

낮은 권한 · 많은 기능 · 제한된 접근
```

위 표와 Stack을 슬라이드에 각각 중복 배치하지 않는다. 표의 `일반 주체`와 `핵심 역할`을
각 Stack bar 안의 짧은 문구로 합쳐 표현한다.

### 2. 각 Level의 Component를 호출하는 방법

#### 낮은 EL → 높은 EL: 보호된 Service 요청

```text
EL0 ── SVC / System Call ────────────────→ EL1
EL1 ── HVC / Trap ──────────────────────→ EL2
EL1·EL2 ── SMC ─────────────────────────→ EL3
HW Event ── IRQ/FIQ/SError Routing ─────→ 설정된 EL
```

- 일반 함수 호출이 아니라 CPU가 정해진 **Exception Handler**로 진입하는 통제된 경로다.
- 낮은 EL은 높은 EL의 Memory나 System Register에 직접 접근할 수 없다.
- 높은 EL의 Handler가 요청 종류, 인자와 권한을 검증한 뒤 Service를 수행한다.

#### 높은 EL → 낮은 EL: 실행 복귀와 비동기 알림

```text
실제 실행 복귀 : Higher EL ── ERET ───────────────→ Lower EL

비동기 알림    : Higher EL ── Event Queue 기록
                            └─ IRQ/vIRQ Pending ──→ Lower EL Handler
```

- 같은 CPU에서 실제 실행 Level을 낮추는 정상 경로는 `ERET`이다.
- 높은 EL이 낮은 EL의 임의 함수를 직접 호출하는 별도 instruction은 없다.
- 비동기 event는 shared queue/mailbox에 기록하고 IRQ 또는 vIRQ로 알린다.
- 낮은 EL이 실행 중이 아니면 event는 pending되고, `ERET` 또는 scheduling 뒤 처리된다.
- 따라서 EL1의 선행 `HVC` 없이도 EL2가 pVM EL1에 event를 알릴 수 있다.

### 3. EL 전환의 특징

| **보안·신뢰** | **성능·확장성** |
| --- | --- |
| Hardware 권한 분리로 침해 범위를 제한 | Exception 처리와 VM exit/entry(Hypervisor 전환) 비용 발생 |
| 높은 EL일수록 System 전체에 미치는 영향 증가 | 전환 빈도가 높을수록 지연과 처리량에 불리 |
| EL2/EL3은 가장 엄격히 검증할 작은 신뢰 코드(TCB)로 유지 | Event batching, IRQ coalescing과 shared queue 활용 |

슬라이드의 두 카드 아래에 다음 운영 원칙을 한 줄로 표시한다.

> **Interrupt는 알림만, Data는 Queue로 전달하고 무응답에는 Timeout·안전 회수로 대응**

## 슬라이드 하단 결론

> **권한은 위로 갈수록 강해지고 전환 비용과 실패 영향도 커진다.**
>
> Application은 EL0, OS 자원 관리는 EL1, VM 격리 집행은 EL2, Platform 보안만 EL3에
> 배치하고 상위 EL 호출 빈도와 코드 크기를 최소화한다.

## 한 장 배치 제안

```text
┌───────────────────────────────────────────────────────────────────────────┐
│ 제목 + 핵심 메시지                                                        │
├───────────────────────┬──────────────────────────┬────────────────────────┤
│                       │ 상향 호출                │ 보안                    │
│ EL3                   │ SVC / HVC / SMC          │ 권한 분리·정책 집행     │
│ EL2    4단 Stack      ├──────────────────────────┼────────────────────────┤
│ EL1                   │ 하향 비동기 알림         │ 성능                    │
│ EL0                   │ Queue + IRQ/vIRQ + ERET  │ 전환 최소화·Batching    │
├───────────────────────┴──────────────────────────┴────────────────────────┤
│ 하단 결론: 상위 EL에는 최소 격리 기능만 배치                              │
└───────────────────────────────────────────────────────────────────────────┘
```

- 권장 비율: 계층도 40%, 호출 흐름 32%, 보안·성능 28%
- 권장 강조색: EL3/EL2는 진한색, EL1/EL0는 밝은색으로 권한 차이 표현
- 상향 화살표는 주황색, 하향 비동기 알림은 청록색으로 구분
- 본문에는 register 이름을 넣지 않고 `SVC`, `HVC`, `SMC`, `ERET`, `IRQ/vIRQ`만 표시

## 30초 설명 문안

ARM Exception Level은 CPU 권한을 네 단계로 분리하는 Hardware 구조입니다. Application은
EL0, OS는 EL1, pKVM은 EL2, Platform 보안 Firmware는 EL3에서 실행됩니다. 낮은 Level이
높은 Level의 Service를 사용할 때는 SVC, HVC, SMC라는 통제된 예외 경로를 거칩니다.
반대로 높은 Level은 ERET으로 실행을 돌려주고, 비동기 event는 Queue와 Interrupt로
알립니다. 이 구조는 침해 범위를 제한하지만 전환마다 처리 비용이 발생하므로, EL2와
EL3에는 격리와 정책 집행 같은 최소 기능만 두는 것이 핵심입니다.

## 발표자 참고

- EL 숫자는 CPU 권한을 뜻하며 software가 자동으로 신뢰된다는 의미는 아니다.
- Exception Level과 Secure/Non-secure state는 서로 다른 개념이다.
- 같은 CPU에서는 두 EL이 동시에 실행되지 않는다.
- pVM용 비동기 알림은 per-vCPU vIRQ가 일반적이다. Host EL1 알림은 physical IRQ/SGI
  또는 해당 pKVM port의 Host notification mechanism을 사용한다.
- `SVC`/`HVC`/`SMC`는 임의 주소로 분기하는 call이 아니라 target EL의 exception
  vector로 진입하는 instruction이다.

## 공식 근거

- [Arm: Exception model](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Exception%20model.pdf)
- [Arm: Armv8-A virtualization](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/Armv8-A%20virtualization.pdf)
- [Arm: GICv3/v4 Software Overview](https://developer.arm.com/-/media/Arm%20Developer%20Community/PDF/Learn%20the%20Architecture/GICv3_v4_overview.pdf)
