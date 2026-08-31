## Slide 1: ARM Exception Level — CPU 권한과 격리를 나누는 4단계 실행 계층

핵심은 ARM이 CPU 권한을 네 단계로 나눠 침해와 장애의 확산 범위를 제한한다는 점입니다. 왼쪽을 아래부터 보면 Host Application과 pVM Userspace Workload는 EL0, Host와 pVM의 Kernel 및 Driver는 EL1, pKVM 같은 Hypervisor는 EL2, Platform 보안 Firmware는 EL3에서 실행됩니다. 숫자가 높을수록 통제 권한과 System 전체에 미치는 영향이 커집니다.

가운데의 주황색 경로처럼 낮은 Level은 SVC, HVC, SMC라는 통제된 Exception 경로로 상위 Service를 요청합니다. 실제 실행 복귀는 ERET을 사용해 같은 Level 또는 유효한 하위 Level의 저장된 문맥으로 돌아갑니다. 이와 별개로 상위 Level의 비동기 Event는 Queue에 Data를 기록하고 IRQ 또는 vIRQ로 알리며, 대상 Level이 실행 중이 아니면 Pending 상태로 기다립니다.

따라서 설계 원칙은 단순합니다. 상위 EL에는 격리와 정책 집행처럼 꼭 필요한 작은 신뢰 코드만 두고, 반복 Data는 Queue와 Batching으로 처리해 EL 전환 빈도를 줄여야 합니다.
