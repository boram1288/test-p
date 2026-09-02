# [8G][xxx] xxx (xxx) ⬝ 3.SDD

- 원본: https://confluence-mirror.samsungds.net/pages/3738353538
- 작성자: xxx / xxx
- 수정일: 2026-08-07T20:33:32.000+09:00

---
\

# [8G][xxx] xxx (xxx) ⬝ 3.SDD

---

# 1. Introduction

## 1.1 Overview

본 문서는 Android 17(Ulysses) 기반 \*\*AICore on pVM\*\* 솔루션의 소프트웨어 설계를 기술한다.\
목표는 Google이 요구하는 \*\*Protected VM(pVM) 환경에서 NPU를 Device Assignment로 할당\*\*하여, Guest VM 안에서\
`App → ENN Framework → NPU Driver → RTOS → NPU H/W` 전체 경로가 동작하고, 동시에 사용자 민감 데이터가\
Non-secure Host로부터 하드웨어 수준으로 격리되도록 하는 것이다.

작년 선행과제(Thetis, PT 방식)와의 근본적 설계 변경점은 다음과 같다.

\

| 항목 | '25 Thetis (Halla / Pass-Through) | '26 본 과제 (pKVM / Device Assignment) |
| --- | --- | --- |
| Hypervisor | 자체 솔루션 Halla | Google pKVM + 삼성 vendor pKVM 모듈(H-ARX) |
| VM 환경 | Non-pVM (VM/메모리 보호 미지원) | pVM (VM/NPU 메모리 + IP protection) |
| NPU 드라이버 할당 | Guest kernel에 직접 Porting | Linux VFIO Framework 기반 Device Assignment |
| IOMMU 구현 | Guest EL1 SysMMU + Halla HVC로 IPA→PA | 목표: SysMMU(pvIOMMU)를 EL2 pKVM으로 이관(stage-1까지 EL2 관리). 현재(과도기): Guest EL1 SysMMU + 임시 HVC로 PA 획득 |
| MMIO 접근 | Halla API로 SFR 영역 Mapping | VFIO donate + guest ioremap 시 MMIO_GUARD_MAP/RGUARD HVC 자동 호출 |
| Interrupt | Halla가 VM별 IRQ 등록·핸들링 | 표준 VFIO irqfd → KVM → pKVM vGIC (Single VM). Multi VM은 별도 설계(안) |
| Power | Always-On | Runtime PM ( pkvm,device-power HVC) |
| Language Model | 300MB 이하 Small Model | LLM (Gemini Nano, 1.5GB) |
| Multi VM | 미지원 | Host + pVM 동시 사용 목표 |

\

이 변경으로 인해, 작년 Halla에 구현했던 기능(MMIO mapping, VM별 IRQ, Contiguous Memory 등)을 pKVM 표준 프레임워크(VFIO / pvIOMMU / S2MPU 연동) 위에서 재구현하는 것이 본 설계의 핵심이다.

\

## 1.2 Design Consideration

\

| 구분 | 고려 사항 | 설계 반영 (해당 절) |
| --- | --- | --- |
| Security | pVM에 할당된 NPU가 접근하는 메모리는 S2MPU(IO Stage-2)로 격리되어야 하며, Host↔Guest 간 상호 접근이 차단되어야 한다. NPU FW/모델 데이터가 Non-secure 영역으로 유출되지 않아야 한다. | [3.4] Stage-2 CPU+IO 이중 격리(pKVM core가 host CPU 접근, S2MPU가 NPU DMA 접근 차단), [4.6] vendor pKVM이 guest memory를 S2MPU AP=NO_ACCESS로 보호/RW로 해제 |
| Performance | Non-pVM Host 대비 AI Benchmark 성능 오버헤드 3% 이내 (정규 조건: Mid-Low Cluster 고정, NPU IP clock min_lock). 일반 원칙으로 pKVM 환경에서는 EL2로의 HVC(trap 왕복)가 누적 오버헤드의 주요인이므로, 반복 경로의 HVC 총량을 줄이는 것이 성능 최적화의 핵심 이다. (단, 현 과도기의 IPA_TO_PA 등은 SysMMU@EL1 구조상 필수 호출이며, EL2 이관 시 호출 형태 자체가 바뀐다.) | [4.4.1] SysMMU를 EL2로 이관하여 반복 경로 HVC(`IPA_TO_PA`/`ALLOC_PAGES`/`GET_MMIO`)를 제거하는 최종 구조 목표, [4.3] 과도기 HVC는 EL1 구조에 국한, [4.5] `SET_MEM_NC`로 DMA 버퍼를 NC 재매핑하여 반복 cache flush 부담 회피 |
| Portability | Host VM과 pVM이 동일 SW 모듈 (NPU driver, SysMMU driver, ENN Framework)을 사용하도록 하여 개발 효율성 및 유지보수성 확보. Host 드라이버를 guest 조건부 빌드( CONFIG_VIRT_NPU )로 재사용. | [4.4] host `samsung-iommu-v9` 드라이버를 compatible만 `pkvm,pviommu`로 바꿔 guest 재사용, [4.5] host NPU 드라이버를 `CONFIG_VIRT_NPU` 조건부 빌드로 재사용 |
| Compatibility | Google Device Assignment 표준 API 를 준수하고, Vendor customization을 최소화. AICore on pVM CTS/VTS 100% 통과. | [3.1] 표준 VFIO Device Assignment(VM DTBO `id=0x80000000` 계약) 사용, [3.5] 표준 VFIO irqfd → KVM → pKVM vGIC 경로 그대로 사용(신규 IRQ 코드 없음) |
| Constraints | Halla가 아닌 pKVM 사용(A17 정책). Guest IOMMU는 pvIOMMU driver 사용, EL2에서 구현. Exynos SoC NPU만 대상. | [4.2] `exynos-pkvm-module`이 S2MPU를 pKVM에 IOMMU로 등록, [4.4.1] pvIOMMU를 EL2에서 구현하는 목표 구조, [4.3] 현재는 EL1 과도기 |

\

# 2. SW Architecture Design

## 2.1 Overall Architecture

pVM 환경의 NPU Device Assignment는 Host / Hypervisor(EL2) / Guest 3계층으로 구성된다.

![](images/pc28x_aicore_pvm_sdd/제목%20없는%20다이어그램-1785459536550.png)

\

개발 범위

LSI: VM DTBO, Host IOMMU drv(exynos-pkvm-module), Hypervisor IOMMU drv(pKVM pvIOMMU EL2 + vendor pKVM S2MPU), Guest NPU driver, Guest pvIOMMU/SysMMU driver, pvmfw VM DTBO 처리, ENN Framework.

Google 범위: pKVM core, crosvm/virtmgr, pvIOMMU 프레임워크, Microdroid, AICore 상위 로직.

## 2.2 Composition of Architecture

|  | Block Name | 계층 | Description | 담당 |
| --- | --- | --- | --- | --- |
| 1 | VM DTBO / pvmfw | Host/Boot | Guest VM용 Device Tree Overlay. NPU/SysMMU device를 /host (물리검증 메타)+ &{/} (guest node) 이중구조로 기술. pvmfw가 dtbo를 검증·config에 복사 | LSI (Security) |
| 2 | Host IOMMU drv (samsung-iommu-v9) | Host Kernel | Host kernel SysMMU driver. VFIO unbind 시 host domain에서 NPU를 detach하여 host DMA 매핑 해제. Device Assignment 전/후 host 측 IOMMU lifecycle 담당 | LSI (Kernel) |
| 3 | exynos-pkvm-module | Host Kernel + EL2 | S2MPU를 pKVM에 등록하는 모듈(EL1/EL2 쌍). EL1 side( exynos-pkvm.c )가 kvm_iommu_driver ops로 S2MPU id 조회·등록, EL2 side( hyp/exynos-pkvm-module.c )가 kvm_iommu_ops 로 실제 S2MPU 제어 | LSI (Security) |
| 4 | Hypervisor pvIOMMU (pKVM core, EL2) | Hypervisor | Guest용 para-virtualized IOMMU. IPA→PA 변환, MMIO idmap, IOMMU page 할당을 HVC로 제공. Stage-1 pgtable 관리 | Google + LSI (Kernel) |
| 5 | vendor pKVM module (H-ARX, EL2) | Hypervisor | S2MPU를 IO Stage-2 protection unit으로 구동 — SysMMU(1차 변환) 뒤단에서 PA 접근 허용/차단으로 guest 메모리 격리. pKVM HVC(activate/HCR/record) 처리, plug-in 관리 | LSI (Security) |
| 6 | Guest pvIOMMU/SysMMU drv (samsung-iommu-v9) | Guest Kernel | pkvm,pviommu 노드에 bind. IPA/PA 이중 페이지테이블 관리, HVC로 MMIO·변환·page 확보 | LSI (Kernel) |
| 7 | Guest NPU drv (virt NPU) | Guest Kernel | Device Assignment로 할당된 NPU 접근. CONFIG_VIRT_NPU 로 host 의존 배제, VM DMA sync | LSI (Kernel) |
| 8 | ENN Framework / AICore | Guest App | Host의 ENN Framework를 guest에서 동작시켜 AICore와 NPU driver 연결 | LSI(AI), Google |

## 2.3 Interface

Guest ↔ Hypervisor ↔ Host 간 핵심 인터페이스를 Input/Output 중심으로 정의한다. 각 Interface의 식별자(FID, 주소 등 구체 값)은 부가 정보로 보아 본 절 하단 각주로 분리하고, 여기서는 무엇을 주고받아 어떤 효과를 내는지를 기술한다.

|  | Interface Name | 경로 | Input | Output | Description | 성격 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | MMIO_GUARD_MAP / RGUARD_MAP | Guest → EL2 pKVM ( ioremap 훅 자동) | 대상 IPA (RGUARD는 IPA 범위) | 성공/실패 | guest가 Device 속성으로 ioremap 시 커널 훅이 자동 호출 → 해당 IPA를 EL2 stage-2에 "MMIO 영역"으로 annotation. 실제 매핑 설치가 아니라, 이후 stage-2 fault 시 허용 판정 근거가 되는 표시 | 표준(유지) |
| 2 | PVIOMMU_GET_MMIO | Guest EL1 SysMMU → EL2 pKVM | (pviommu_id, vsid) | SysMMU SFR (pa_base, size) | token으로 SysMMU SFR PA를 조회해 guest stage-2에 idmap. EL1 SysMMU가 자기 SFR을 ioremap하기 위한 용도 | 과도기 |
| 3 | IPA_TO_PA | Guest EL1 SysMMU → EL2 pKVM | guest IPA (page-aligned) | 대응 PA | guest Stage-2 leaf를 읽어 PA를 반환(새 매핑 아님). EL1 SysMMU가 H/W PTE에 넣을 PA 확보용 | 과도기 |
| 4 | IOMMU_ALLOC_PAGES | Guest EL1 SysMMU → EL2 pKVM | (ipa, order) | 성공/실패 (연속 PA backing) | EL2 예약풀에서 물리연속 블록을 donate하여 해당 IPA에 매핑. SysMMU 페이지테이블의 연속 backing 확보 | 과도기 |
| 5 | kvm_iommu_driver ops | Host kernel ↔ EL2 pKVM | device of-node / device 핸들 | IOMMU id, stream id 개수·값 | exynos-pkvm-module(EL1)이 S2MPU를 pKVM에 IOMMU로 등록하고, VFIO device의 IOMMU id/stream을 조회 | 유지 |
| 6 | HVC_FID_PKVM_* | Kernel ↔ vendor pKVM(H-ARX) | 요청 종류 + 파라미터 (HCR 값 등) | 성공/상태 | pKVM 활성화, HCR/HFGWTR fine-grained trap 갱신, EL2 info record, CPU context 등록 | 유지 |
| 7 | VM DTBO contract | Build → pvmfw → Guest | VM overlay (태그 id) | pvmfw가 소비한 guest FDT | build 시 VM overlay를 특정 flag로 태깅 → bootloader가 host DT merge에서 제외, pvmfw만 소비하여 guest DT 생성 | 유지 |

\

> 식별자(부가 정보): 1~4·6은 `OWNER_VENDOR_HYP` vendor HVC(base `0xC6000000`)이며 FID 값은 `MMIO_GUARD_MAP`=7, `MMIO_RGUARD_MAP`=10, `IPA_TO_PA`=12, `PVIOMMU_GET_MMIO`=13, `IOMMU_ALLOC_PAGES`=14, `HVC_FID_PKVM_*`=base+0x80~0x85이다. VM DTBO contract의 태그는 `id = 0x80000000`(`1<<31`)이다. FID 값은 현재 `arm-smccc.h` 계산값이며, 과도기 3종(12/13/14)은 `PKVM_RESV_12/13/14` 예약 슬롯을 임시 사용 중이라 정식 UAPI 확정 시 변경될 수 있다.

\

# 3. SW Behavioral Design

## 3.1 NPU Device Assignment (VFIO Bind & VM DTBO 전달)

VM 생성부터 NPU가 pVM에 할당되기까지의 흐름.

![](images/pc28x_aicore_pvm_sdd/제목%20없는%20다이어그램-1785460535640.png)

시퀀스 요약: platform이 VM overlay를 `id=0x80000000`으로 태깅(dtboimg.cfg) → bootloader가 host DT merge에서 제외하고 pvmfw config Entry[2]에 복사 → 인덱스를 `androidboot.hypervisor.vm_dtbo_idx`로 Android에 통지. VFIO group 성립 조건: `npu_exynos`, `hwdev_npu`, `nshare_mem`이 동일 IOMMU group을 공유하므로, 셋 다 vfio-platform에 bind되어야 group이 viable. 따라서 3개 compatible(`samsung,exynos-npu`, `-npu-hwdev`, `-npu-nshare`)에 reset handler 등록.

\

## 3.2  Guest NPU/SysMMU Probe & MMIO Mapping

pVM의 guest는 자신에게 할당된 device의 물리 SFR 주소를 알지 못한다. pvmfw가 VM DT에 전달하는 정보의 형태가 device마다 달라, MMIO 확보 경로가 두 갈래로 나뉜다.

![](images/pc28x_aicore_pvm_sdd/제목%20없는%20다이어그램-1786098664575.png)

- 경로 ① NPU SFR — VM DT의 접근용 IPA 사용: VM DT의 NPU 노드에는 device의 접근 IPA base(`reg`)가 들어온다. guest NPU driver는 DT가 준 IPA로 곧바로 `ioremap`하여 SFR에 접근한다(별도 HVC 불필요). guest가 그 IPA에 실제로 접근할 때 발생하는 stage-2 처리는 mainline pKVM의 표준 MMIO 경로를 따른다(SRS\_VFIO/SEC).
- 경로 ② SysMMU SFR — HVC로 PA 조회(과도기): VM DT의 SysMMU 노드는 접근 주소(`reg`)가 아니라 IOMMU 식별용 token만 제공한다. SysMMU driver가 자신의 SFR을 직접 다뤄야 하는 현재 과도기 구조(SysMMU@EL1)에서는 실제 PA가 필요하므로, driver가 `PVIOMMU_GET_MMIO` HVC로 EL2에서 SFR PA를 받아와 `ioremap`한다. SysMMU가 EL2로 이관되면(4.4) 이 경로는 사라진다.

두 경로의 공통점은 "물리 SFR 주소가 guest probe 시점에 자원으로 주어지지 않는다"는 것이며, 그래서 확보 시점을 device 노드 파싱 시점으로 미룬다. 차이는 NPU는 DT가 준 IPA로 충분한 반면, SysMMU는 H/W를 guest가 직접 제어하기 위해 실제 PA를 HVC로 조회해야 한다는 점이다.

\

## 3.3  DMA Buffer Mapping (IPA→PA) (과도기)

SysMMU는 VA→PA 변환 IP이므로 H/W PTE에는 실제 PA가 필요하나, Guest EL1은 IPA만 안다. 이 간극을 임시 HVC로 메우고, IPA↔PA 이중 페이지테이블로 처리한다.

![](images/pc28x_aicore_pvm_sdd/제목%20없는%20다이어그램-1785460886046.png)

설계 포인트 (모두 EL1 과도기 산물):

- 물리연속 요구: SysMMU H/W는 LV1 page table을 물리연속으로 요구하나 guest IPA는 연속 PA 보장이 안 됨 → `IOMMU_ALLOC_PAGES`로 EL2 buddy 예약풀의 연속 PA를 backing (작년 Thetis "Physically Contiguous Memory"와 동일 문제, pKVM donate로 해결).
- 이중 테이블: `page_table`(PA 기반, H/W가 읽음) ∥ `ipa_table`(IPA shadow). PTE가 PA로 바뀌면 커널 VA가 아니게 되므로 VA 기반 참조는 전부 `ipa_table` 사용.

\

## 3.4  Stage-2 Memory Protection (CPU + IO)

메모리 격리는 두 축으로 이뤄진다.

- CPU 측 (pKVM core): pKVM은 부팅 시 host(Android)를 EL2 CPU Stage-2 아래로 격리한다(host도 하나의 VM처럼 취급). pVM에 donate된 메모리는 host Stage-2에서 제거되어 host CPU가 접근할 수 없고, 반대로 pVM은 자기 Stage-2에 매핑된 영역만 본다. 이는 mainline pKVM의 표준 격리 메커니즘이다.\
- IO(DMA) 측 (S2MPU / vendor pKVM): NPU 같은 DMA-capable IP는 CPU Stage-2를 거치지 않으므로, S2MPU가 IO Stage-2 관점에서 DMA 목적지 PA 접근을 허용/차단한다.

CPU 측만으로는 NPU DMA를 막을 수 없고 IO 측만으로는 host CPU 접근을 막을 수 없으므로 두 축이 함께 필요하다. 핵심은 이 두 축의 갱신이 \*\*하나의 페이지 donate 경로 안에서 함께\*\* 일어난다는 점이다.

![](images/pc28x_aicore_pvm_sdd/제목%20없는%20다이어그램-1786099032869.png)

pVM의 물리 페이지는 VM 시작 시 통째로 할당되지 않고, guest가 해당 IPA에 최초 접근하는 순간(stage-2 fault) 페이지 단위로 지연(lazy) donate된다. 이 donate 경로에서 guest 매핑 추가와 host(CPU·IO) 차단이 함께 처리된다.

- CPU 측: core pKVM이 `\_\_pkvm\_host\_donate\_guest`에서 guest Stage-2에 페이지를 매핑함과 동시에, host Stage-2에서는 소유권을 guest로 이전(`\_\_host\_stage2\_set\_owner\_locked`)하여 host CPU 접근을 차단한다.\
- IO 측: 같은 경로에서 core pKVM이 IOMMU 훅(`kvm\_iommu\_host\_stage2\_idmap`)을 호출한다. 이 훅이 `exynos-pkvm-module`(EL2)을 거쳐 vendor pKVM(H-ARX)의 `exynos\_vm\_stage2\_request(base, end, prot)`로 전달되어, 해당 영역의 S2MPU AP를 갱신한다.\
  - `prot = NO\_ACCESS` → `exynos\_vm\_stage2\_map\_protect()`: S2MPU 접근 차단(관리 bitmap에 등록 + 모든 subsystem의 S2MPU 테이블 갱신).\
  - `prot = RW` → `exynos\_vm\_stage2\_map\_unprotect()`: 회수 시 host로 접근 재허용.

전원 가드: S2MPU SFR에 접근하기 전 반드시 해당 S2MPU power domain이 켜져 있는지 확인한다(전원 꺼진 S2MPU SFR 접근 시 Power Down access error → async SError → 커널 panic 방지).

격리 검증: pVM에서 Host 메모리 주소 접근 시 S2MPU AP(NO\_ACCESS)에 의해 fault 발생 → SRS\_MVM\_03 / SRS\_SEC 충족.

\

## 3.5  NPU Interrupt 전달

![](images/pc28x_aicore_pvm_sdd/제목%20없는%20다이어그램-1785462353001.png)

\

④는 pKVM의 공통 경로다. pKVM에서는 vGIC LR(list register)을 EL2가 소유하므로, 일반 VM·pVM 모두 host가 준비한 LR을 hyp이 `flush_hyp_vgic_state`/`sync_hyp_vgic_state`로 host↔hyp 간 중개한다(vCPU run 구조상 EL2를 거치기 때문이며 protection과 무관). pVM에서 추가로 다른 점은 vGIC이 아니라 vCPU의 일반 상태(GPR/sysreg/memory)로, host가 이를 직접 접근·수정할 수 없다는 것이다. Host가 NPU를 쓸 때는 Guest가 unbind되어 동일 IRQ가 Host NPU driver로 간다. 즉 bind 상태가 목적지를 결정한다.

> 검증: VM dtso에 interrupt 속성이 없고, guest/host/mainline 커널 패치에 커스텀 IRQ routing/GSI/irqfd 코드가 없다 → 표준 VFIO+KVM irqfd + pKVM vGIC 경로를 그대로 사용한다(신규 IRQ 코드 없음).

Multi VM — 목표 설계(안). Host와 pVM이 하나의 NPU를 동시 공유할 때는 device를 한 VM에 통째로 bind할 수 없으므로, 이는 IRQ 분리 문제가 아니라 NPU 공유/스케줄링 문제다. 후보: (a) EL2 IRQ routing으로 active VM 확인 후 주입(작년 Halla 방식), (b) VM-aware Mailbox를 H/W에 연결(Google 견해), (c) NPU 스케줄링 + PV. 현 Device Assignment는 Multi VM 동시 사용을 미고려(LM-01)하므로 양산 준비 단계에서 구조 설계·계획 수립 중심으로 진행(SRS\_IRQ\_02~04, SRS\_MVM).

\

## 3.6  NPU Power Management (Runtime PM)

목표 설계(안). `pkvm,device-power` compatible의 `pkvm_device_pm_driver`를 사용하여 power domain get/put 시 HVC로 전원 제어.

```
Guest NPU D/D: pm_runtime_get/put()
  → pkvm,power-domain (Guest) → HVC(power on/off) → pKVM
     → power_lock to pKVM module/FW → HVC(on/off) to crosvm → VFIO
        → pm_runtime_get/put() to Host Power Domain Driver
```

Device Assigned→UnAssigned 구간 Power 상태 유지(SRS\_PM\_02), S2MPU Power On/Off 상태 추적(SRS\_PM\_04) 포함.

\

## 3.7  Multi VM NPU 동시 사용

### 3.7.1 문제 정의

단일 NPU를 Host와 pVM이 동시에 쓰려면 device를 한 VM에 통째로 bind할 수 없다. 이는 IRQ 분리 문제가 아니라 NPU라는 공유 자원에 대한 접근 중재(arbitration) 문제다. NPU Compute Engine은 한 번에 하나의 실행 컨텍스트만 처리하므로, Host/Guest의 요청을 어떤 계층에서 직렬화(중재)하고 각 실행에 맞는 메모리 보호(SysMMU/S2MPU의 VID)를 어떻게 전환할지가 설계의 핵심이다.

### 3.7.2 설계 방향 — EL2 Arbitration

중재 주체를 어디에 두느냐(EL2 vs NPU RTOS)를 검토한 결과, 구현 용이성과 EL2 복잡도 최소화를 근거로 EL2에서 중재하는 방향으로 진행한다.

핵심은 EL2 NPU Plugin이 Inference 실행 구간을 임계 구역(Critical Section)으로 보고 Bakery 알고리즘으로 한 번에 하나의 OS만 진입하도록 중재하되, Job queue 관리·submit은 각 kernel(EL1)에 남겨 EL2 코드를 최소화하는 것이다.

\

![](images/pc28x_aicore_pvm_sdd/제목%20없는%20다이어그램-1786101921464.png)

- Guest 측 준비: NPU driver가 메모리를 할당하고(①) SysMMU/S2MPU driver에 Mapping/Protection을 요청(②)하면, EL2가 guest용 SysMMU Page Table / S2MPU Protection Table을 구성(③)한다. 이후 NPU driver가 Job을 submit(④)한다.

- 중재: Host/Guest의 NPU driver가 자원 할당을 요청(⑤)하면 EL2 NPU Plugin(vendor pKVM 확장)이 다음에 동작할 OS를 결정(⑥)한다.

- 컨텍스트 전환: 결정된 실행에 맞춰 VGEN driver에 VID 설정을 요청(⑦)하고, VGEN이 실제 설정(⑧)되어 NPU Core/DMA가 거치는 SysMMU/S2MPU가 해당 VM의 VID로 전환된다. 이어 NPU Control Core에서 대상 RTOS로 전환·실행을 요청(⑨)한다.

- 격리: VGEN이 부여한 VID로 SysMMU/S2MPU가 트래픽을 구분하므로, DRAM의 NPU Data 영역이 RTOS/Host/Guest용으로 분리되어 상호 접근이 차단된다.

\

2.1의 module view와의 대응: 중재를 담당하는 "EL2 NPU Plugin"은 vendor pKVM(H-ARX)의 plug-in으로 구현되며, VID 전환에 쓰이는 SysMMU/S2MPU는 3.4에서 기술한 IO Stage-2 보호 경로와 동일한 블록을 VM별로 전환하는 형태다.

양산 준비 단계에서는 위 1안을 기준으로 EL2 Arbiter(Bakery)·VID 전환·per-VM 스케줄링(fairness)의 구체 설계를 확정한다(SRS\_MVM, SRS\_IRQ\_02~04). IRQ 전달 자체는 [3.5](#35-npu-interrupt-전달-single-vm--multi-vm)에서 다룬다.

\

# 4. SW Detailed Design

## 4.1 VM Device Tree Overlay & pvmfw

### 4.1.1 Structure

VM DTBO(`s5e9975-vm.dtso`)는 `/dts-v1/; /plugin/;` 오버레이로 두 영역 구성.

- `/host` 노드: pvmfw가 물리 자원을 검증하는 메타데이터 (`#address-cells=<2> #size-cells=<1>`)
- `&{/}` 루트 오버레이: guest FDT에 실제 들어갈 device 노드

> 참고: assignable device는 host DT의 `pkvm,device-assignment` 노드(`devices` 속성)로 선언하며, pKVM이 부팅 후반(host 권한 drop 직전)에 이 목록을 EL2에 등록한다. → 관련 host DT 패치는 4.2/DT 절 참조.

### 4.1.2 Procedure

VM DTBO 생성·전달 체인은 3.1 참조. 빌드: `BUILD.bazel`의 `dtbo(dtcopts=["-@"])` → `dtboimg.cfg`에서 `id=0x80000000`.

### 4.1.3  Interface / Data structure

pvmfw config 엔트리 (magic 0x666d7670"pvmf", version 0x10002):

| Index | 매크로 | 값 소스 |
| --- | --- | --- |
| 0 | PVMFW_CONFIG_ENTRY_DICE_INDEX | pvmfw_build_dice_handover() |
| 1 | PVMFW_CONFIG_ENTRY_DP_INDEX | 미사용(size 0) |
| 2 | PVMFW_CONFIG_ENTRY_VM_DTBO_INDEX | pvmfw_build_vm_dtbo(entry) |
| 3 | PVMFW_CONFIG_ENTRY_VM_REF_DT_INDEX | pvmfw_build_vm_reference_dt() |

```
static uint32_t pvmfw_build_vm_dtbo(uint64_t entry_base);   // pvmfw.c:178
int             pvmfw_get_vm_dtbo_idx(void);                // pvmfw.c:166 (없으면 -1)
```

NPU DT 노드 (`/host/npu_phys`, dtso:31-41):

```
npu_phys {
    reg = <0x0 0x20000000 0x100000>;              /* NPUCON SFR base, 1MB */
    iommus = <&sysmmu_npucon_s0_vm 0x1>,
             <&sysmmu_npucon_s1_vm 0x2>,
             <&sysmmu_npucon_s2_vm 0x3>;
    android,pvmfw,target = <&npu_exynos>;
};
```

| SysMMU 토큰 | android,pvmfw,token (물리 base = iommu id) |
| --- | --- |
| sysmmu_npucon_s0_vm | <0x0 0x21460000> |
| sysmmu_npucon_s1_vm | <0x0 0x21490000> |
| sysmmu_npucon_s2_vm | <0x0 0x21790000> |

\

guest 노드(`&{/}`): `npu_exynos`(`samsung,exynos-npu`, `vertex_name`, `configs` 32셀, `samsung,iommu-group`), `iommu_group_npu`(`samsung,sysmmu-group-v9`), `hwdev_npu`, `nshare_mem`, `manual_mem`(`dma-coherent`), `nshare_manual`.

\

## 4.2 exynos-pkvm-module (S2MPU pKVM 등록)

### 4.2.1 Structure

`exynos-pkvm-module`(EL1/EL2 쌍)은 S2MPU를 pKVM에 IOMMU로 등록하고, VFIO device의 IOMMU id/stream을 lookup한다. (VFIO device assignment의 host측 IOMMU lifecycle — unbind 시 host domain detach — 은 host SysMMU driver `samsung-iommu-v9`가 담당하며 2.2 블록 2에 해당한다.)

- kernel(EL1)측: `drivers/soc/samsung/exynos/exynos-pkvm-module/exynos-pkvm.c`
- EL2(hyp)측: `.../exynos-pkvm-module/hyp/exynos-pkvm-module.c`

### 4.2.2 Procedure

- Host 부팅 시 `kvm_iommu_register_driver(&exynos_pkvm_s2mpu_ops, 64)` (reserved pool 64 pages).
- EL2 `exynos_pkvm_s2mpu_init(drv_id)` → `saved_ops->iommu_register_pviommu_drv(drv_id)`로 pviommu 등록(미등록 시 `kvm_iommu_id_to_token`이 `-ENODEV` 반환하던 버그 해소).

### 4.2.3  Interface / Data structure

```
struct kvm_iommu_driver exynos_pkvm_s2mpu_ops = {          // exynos-pkvm.c:203
    .init_driver              = exynos_pkvm_s2mpu_init_driver,
    .get_iommu_id_by_of       = exynos_pkvm_s2mpu_id_by_of,   // reg → *out_id = res.start
    .get_device_iommu_num_ids = exynos_pkvm_s2mpu_num_ids,    // iommus 엔트리 카운트
    .get_device_iommu_id      = exynos_pkvm_s2mpu_device_id,  // idx번째 iommus → id, sid
};
struct kvm_iommu_ops exynos_kvm_iommu_ops = {              // hyp/exynos-pkvm-module.c:481
    .init                  = exynos_pkvm_s2mpu_init,       // → iommu_register_pviommu_drv
    .host_stage2_idmap     = exynos_pkvm_s2mpu_stage2_idmap,
    .get_iommu_token_by_id = exynos_pkvm_s2mpu_get_iommu_token,  // *out = id (token==id)
};
```

설계 규약: `iommu_id = token = S2MPU/SysMMU MMIO base 주소`(부팅 간 불변, 인스턴스별 유일). Stream ID가 아닌 인스턴스 단위로 트래픽 통제. Multiple masters: NPU처럼 SysMMU 3개를 갖는 device는 `get_device_iommu_num_ids`가 `iommus` 엔트리 수를 반환하고, `get_device_iommu_id(idx)`가 각 엔트리를 등록.

\

## 4.3 Hypervisor pvIOMMU Interface (pKVM core, EL2) — 과도기 HVC

> 과도기 인터페이스. 이 절의 HVC 3종(IPA\_TO\_PA / IOMMU\_ALLOC\_PAGES / PVIOMMU\_GET\_MMIO)은 SysMMU 드라이버가 Guest EL1에 위치하는 현재 과도기 구조를 위한 임시 인터페이스다(4.4 참조). SysMMU가 목표대로 EL2로 이관되면 세 HVC 모두 불필요해져 제거된다. 상세는 참고용이며 최종 아키텍처가 아니다.

### 4.3.1 Structure

\

Guest EL1 SysMMU 드라이버에 노출하는 vendor HVC 3종(mainline pKVM `arch/arm64/kvm/hyp/nvhe/`). 소비자는 guest `samsung-iommu-v9.c` 하나뿐이며, 세 FID는 `arm-smccc.h`의 `PKVM_RESV_12/13/14` 예약 슬롯을 임시로 사용한다(정식 pKVM UAPI 확정 전 잠정값).z

### 4.3.2 Procedure / 4.3.3 Interface

| Interface | 함수 / 위치 | 입력 → 출력 | 핵심 동작 | EL1 과도기 이유 |
| --- | --- | --- | --- | --- |
| IPA→PA | pkvm_ipa_to_pa_call / pkvm.c | IPA → PA | guest stage-2 leaf 조회( kvm_pgtable_get_leaf ), block offset 복원 | EL1 SysMMU가 PTE에 넣을 PA를 조회 |
| ALLOC_PAGES | pkvm_iommu_alloc_pages / device.c | (IPA, order) → ret | buddy(연속) donate → guest stage-2에 연속 PA로 매핑 | SysMMU LV1 page table(256KB)이 물리연속이어야 하나 guest IPA는 연속 PA 보장 못 함 |
| GET_MMIO | pkvm_pviommu_get_mmio / device.c | (id, vsid) → (PA, 0xA000) | route→token→guest stage-2 idmap(RW|DEVICE) | EL1 SysMMU가 자기 레지스터 ioremap |

\

- 세 HVC 모두 "SysMMU가 stage-1 변환/페이지테이블/SFR을 guest EL1에서 직접 다룬다"는 전제에 종속된 임시 해법이다.
  - IPA\_TO\_PA: EL1이 SysMMU PTE에 넣을 PA를 모름 → 조회 필요
  - ALLOC\_PAGES: SysMMU H/W가 LV1 page table(65536×4B=256KB, order 6)을 물리연속으로 요구하나, guest가 `kmalloc`한 IPA는 연속 PA로 매핑된다는 보장이 없음 → EL2가 buddy 예약풀에서 연속 PA를 뽑아 그 IPA에 재매핑 (작년 Thetis의 "Physically Contiguous Memory"와 동일 문제)
  - GET\_MMIO: EL1 SysMMU가 자기 SFR을 ioremap해야 함
- EL2 이관 시 EL2가 stage-2·SysMMU SFR·페이지테이블(연속 메모리)을 모두 직접 소유하므로 세 HVC 모두 불필요해져 제거된다.
- dispatch: `kvm_handle_pvm_hvc64()` switch (`pkvm.c`). `guest_lock_component`/`pkvm_request_vcpu_memcache`를 static→외부 링키지로 전환.
- [HACK] `pkvm_device_reset`(`device.c`): device를 host↔guest로 넘길 때 device 초기화를 `dev->reset_handler` 콜백에 위임하는데, 이 핸들러는 vendor 모듈(NPU 등)이 `pkvm_device_register_reset()`으로 나중에 채워준다. 그런데 부팅 초기 `pkvm_load_early_modules` 단계에서 리셋 경로가 한 번 먼저 타면서, 아직 핸들러가 등록되기 전이라 `dev->reset_handler == NULL`인 상태로 호출된다. mainline은 리셋을 필수(mandatory)로 가정해 NULL 체크가 없어 NULL 함수 포인터 역참조(EL2 크래시)가 발생 → 핸들러가 NULL이면 리셋을 skip하도록 완화. (정공법은 핸들러 등록 이후에만 리셋 경로가 타도록 부팅 순서를 보장하는 것.)

> 참고: MMIO\_GUARD\_MAP/RGUARD\_MAP은 과도기 HVC가 아니다. 이는 mainline pKVM 표준 기능으로, guest가 Device 속성(`PROT_DEVICE_nGnRE/nGnRnE`)으로 `ioremap`하면 커널 ioremap 훅(`arm-pkvm-guest.c`, `CONFIG_ARM_PKVM_GUEST`)이 자동 호출된다. 이 HVC는 실제 stage-2 매핑을 설치하는 것이 아니라 해당 IPA 범위를 EL2 stage-2 pgtable에 MMIO 영역으로 annotation(마킹)하는 것으로, 이후 guest가 그 MMIO에 접근해 stage-2 fault가 나면 EL2가 이 마킹을 보고 "허용된 MMIO 접근"으로 판정해 처리한다. SysMMU 구조와 무관하게 유지된다(3.2 참조).

## 4.4 Guest pvIOMMU / SysMMU Driver (samsung-iommu-v9) — 목표 EL2 / 현재 EL1 과도기

![](images/pc28x_aicore_pvm_sdd/제목%20없는%20다이어그램-1786099884696.png)

### 4.4.1 목표 구조 (EL2 이관)

Google 가이드 방향은 SysMMU(pvIOMMU)를 EL2 하이퍼바이저로 이관하는 것이다. 이 구조에서는 EL2가 SysMMU H/W와 stage-1 페이지테이블을 직접 소유·관리하고, guest는 pvIOMMU para-virtual 인터페이스로 매핑을 요청만 한다. guest는 PA를 알 필요가 없고, SysMMU SFR도 guest에 노출되지 않는다. → 이것이 본 과제가 지향하는 최종 아키텍처다.

### 4.4.2 현재(과도기) 구조 — SysMMU driver를 Guest EL1에 배치

SysMMU를 EL2로 내리는 작업의 난이도가 높아, 우선 host와 동일하게 SysMMU driver를 Guest EL1에 올려 end-to-end 동작을 검증하는 단계다.

이때 발생하는 근본 제약: SysMMU는 ARM SMMU와 달리 VA→PA(IPA 아님)를 변환하는 IP다. 따라서 driver가 SysMMU H/W PTE에 써넣을 값은 실제 PA여야 하는데, Guest EL1은 원래 IPA만 안다. 이 간극을 메우기 위해 임시 HVC 3종(4.3)을 도입했다.

- Host SysMMU v9 드라이버를 guest에 이식. compatible을 `pkvm,pviommu`로 변경(pvmfw가 guest DT에 패치).
- Probe 지연 + MMIO/DMA 매핑 흐름은 3.2, 3.3 참조.
- 아래 구현(HVC 래퍼, IPA/PA 이중 테이블)은 모두 EL1 과도기 산물이며 EL2 이관 시 재설계된다.

### 4.4.3 Interface / Data structure (과도기)

```
/* HVC 래퍼 (samsung-iommu-v9.c) — 전부 과도기용 */
static phys_addr_t convert_ipa_to_pa(phys_addr_t ipa);              // HVC IPA_TO_PA (PTE에 넣을 PA 조회)
static int __sysmmu_get_linear_region(phys_addr_t ipa, int order); // HVC IOMMU_ALLOC_PAGES (PT backing)
static int __sysmmu_get_mmio_resource(struct sysmmu_drvdata *data);// HVC PVIOMMU_GET_MMIO (SFR base)
/* SysMMU가 VA→PA IP이므로 map 경로에 ipa 인자 추가 (paddr = convert_ipa_to_pa(ipa)) */
samsung_sysmmu_map(domain, l_iova, phys_addr_t ipa, ...);
```

```
struct sysmmu_drvdata {
    phys_addr_t pa_base;  size_t pa_size;   // GET_MMIO 결과 → ioremap
    u32 pviommu_id;       u32 vsid;         // DT "id" / fwspec->ids[0]
};
struct samsung_sysmmu_domain {
    sysmmu_pte_t *page_table;   // lv2 base=PA  → SysMMU H/W가 walk
    sysmmu_pte_t *ipa_table;    // lv2 base=IPA → 커널이 walk (phys_to_virt로 lv2 접근)
};
```

IPA/PA 이중 테이블: SysMMU는 VA→PA IP이나 guest는 IPA만 알아, 동일 매핑을 담은 페이지테이블을 `page_table`과 `ipa_table` 두 벌로 병렬 유지한다.

\

| 테이블 | lv2 base 저장값 | walk 주체 | 용도 |
| --- | --- | --- | --- |
| page_table | PA | SysMMU H/W | 레지스터에 base 등록, H/W 주소변환 |
| ipa_table | IPA | 커널(CPU) | phys_to_virt(IPA)로 lv2 접근(매핑 추가/삭제/조회) |

\

커널의 lv2 순회는 `phys_to_virt()`에 의존하는데 guest에선 IPA↔VA 변환이므로, PA가 담긴 `page_table`만으론 커널이 하위 테이블을 못 찾는다(`phys_to_virt(PA)`가 엉뚱한 VA를 가리킴). 즉 H/W가 walk할 `page_table`(PA)과 커널이 순회할 `ipa_table`(IPA)을 분리한 것으로, EL1에서 PA를 직접 다루는 데서 오는 과도기 복잡성이다.

\

```
\
```

## 4.5 Guest NPU Driver (virt NPU)

### 4.5.1 Structure

Host NPU 드라이버를 `CONFIG_VIRT_NPU`로 조건부 빌드하여 guest에서 재사용. host 전용 의존(exynos-soc, pm\_qos, dvfs, bts, llc, exynos-smc, debug-snapshot, memlog, esca\_ipc 등)을 현재는 스텁 처리(no-op 반환 또는 조건부 컴파일 제외)하여 guest 부팅·동작을 우선 확보한다.

> 과도기 스텁 주의: 위 의존 중 특히 성능 관련 기능(pm\_qos, dvfs, bts, llc 등)은 본 선행과제 범위에서는 개발 진행 편의상 잠정 비활성화한 것으로, 양산화 시 재활성화가 필요하다(성능 목표 3% 오버헤드와 직결). 각 기능이 최종적으로 어느 계층(guest/host/EL2)에서 어떻게 동작해야 하는지는 별도 검토 대상이다.

### 4.5.2 Procedure

- FW mailbox/공유버퍼 Non-Cacheable 재매핑 (SET\_MEM\_NC HVC): guest는 fwmbox를 stage-1에서 write-combine(NC)로 매핑하지만, pVM은 stage-2가 `HCR_EL2.FWB=1`로 동작하여 매핑을 강제로 Write-Back cacheable로 승격시킨다. 그 결과 CPU 캐시 coherency 없이 SysMMU 경유로 같은 버퍼를 보는 NPU(non-coherent)와 뷰가 어긋난다. 이를 해소하려 `npu_memory_set_nc_for_vm()`이 버퍼 sgt를 페이지 단위로 순회하며 각 페이지 guest PA(=EL2 관점 IPA)에 대해 `SET_MEM_NC` HVC(vendor hyp, FID=15)를 호출해 stage-2를 Normal Non-Cacheable로 재매핑한다. `npu_system_resume()`에서 fwmbox/fwmem/fwmem\_cc1/CC1\_SHARED 4개 영역에 적용. 비-pVM 빌드는 no-op. (근거: `npu-memory.c:119`, `npu-system.c`)
- SFR IPA/PA 분리 매핑: guest는 IOMMU domain이 없으므로, SFR 매핑 시 NPU reg base + DTS vaddr offset을 IPA로 써서 `devm_ioremap`(일반 MMIO 접근용). 별도로 DTS의 절대 PA(`reg->paddr`)를 보관하는데, 이는 secure world 전용 영역을 다루기 위해 EL3로 SMC를 보낼 때 쓴다(EL3는 guest IPA를 모르고 PA를 요구하므로). DT에 `iomem`이 없으면 에러 대신 skip. (근거: `npu-system.c:301` 주석 및 `init_sfr_area`)
- 물리연속 제약: VIRT\_NPU에서 `npu_memory_create_sgt()`가 `order=0` 강제 (4KB 초과 물리연속 미지원 — 향후 Contiguous Memory/DMA-BUF 확장 대상, SRS\_MEM\_01).
- release routine (VFIO unbind/rebind): Device Assignment 환경에서 driver가 반복 remove→re-probe되므로, probe마다 재등록되는 전역 리소스(debugfs 노드, memlog 등록, IRQ, session 테이블 등)를 되돌려 re-bind가 깨지지 않도록 정리 경로를 보강. (세부 항목은 NPU 담당과 협의하여 확정 예정.)
- [hack] probe 시 host-only 모듈 차단: platform IRQ affinity, IOMMU domain, mailbox SFR(sfrmbox0/1) 직접 매핑, DVFS/QoS boost, dbg\_snapshot watchdog 등 물리자원·보안도메인 직접접근 모듈을 probe 경로에서 배제. bring-up용 hack 성격이며 정식화 대상.
- [방어코드] VM DMA sync: mailbox IPC 지점에 `npu_memory_sync_for_vm()`(내부 `dma_sync_sg_for_device/cpu`)을 삽입해 두었으나, 위 `SET_MEM_NC`로 해당 버퍼가 이미 Non-Cacheable이므로 실질 효과는 거의 없다. 캐시 경로 회귀에 대비한 방어적 코드 성격. (근거: `npu-memory.c:103`)

### 4.5.3 Interface

```
// pVM stage-2를 Normal Non-Cacheable로 재매핑 (FWB 승격 상쇄) — 핵심
int  npu_memory_set_nc_for_vm(struct npu_memory_buffer *buffer);  // npu-memory.c:119
```

> 주의: `8ce0bb955`의 "pKVM reset handler"는 NPU용 VFIO reset node 등록이 아니라, guest에서 host 리셋/watchdog/IOMMU fault handler를 비활성화(`return 0` 스텁)하는 처리다. NPU device의 VFIO reset은 mainline kernel(`vfio_platform_exynosnpu.c`)에서 담당.

## 4.6 vendor pKVM Module (H-ARX) — S2MPU IO Stage-2

### 4.6.1 Structure

vendor pKVM(H-ARX)은 mainline pKVM(nVHE hyp)에 링크되는 삼성 EL2 모듈로, 기존 S2MPU 제어 인프라를 pKVM 환경에서 제공한다. 본 과제에서의 역할은 NPU에 할당된 guest memory를 S2MPU로 격리하는 것이며, 아래에서는 그 부분을 중심으로 기술한다(활성화·hVHE·plug-in 등 모듈 내부 상세는 vendor pKVM 자체 설계 범위).

pKVM은 VA≠PA(PIE)이므로 `ENABLE_PIE=1`, `ENABLE_VENDOR_PKVM=1`로 빌드한다. HVC는 `exynos_harx_hvc_handler`가 common→s2mpu→pkvm 순으로 위임한다.

### 4.6.2 S2MPU를 통한 Guest Memory 격리 (본 과제 핵심)

NPU는 SysMMU(1차 변환) 뒤단의 S2MPU를 거쳐 물리 메모리에 접근하며, S2MPU는 IO Stage-2 관점에서 DMA 목적지 PA에 대한 접근 허용/차단(AP) 을 결정한다(주소 변환 아님). pVM에 NPU가 할당되면, 해당 guest memory를 S2MPU 상에서 guest 소유로 전환하여 Host를 포함한 다른 주체의 접근을 차단한다.

```
// guest memory를 S2MPU에서 보호(AP=NO_ACCESS) / 해제(AP=RW)
uint64_t exynos_subsystem_protect_guest_memory(uint64_t addr, uint64_t size);              // :94
uint64_t exynos_subsystem_unprotect_guest_memory(uint64_t addr, uint64_t size, bool inv);  // :116
uint64_t exynos_hyp_s2mpu_prepare(start, end, prot, ...);   // 부팅 시 초기 S2MPU AP (OWNER_PKVM)
```

소유자 태그: `SUBSYSTEM_OWNER_PKVM`(95), `SUBSYSTEM_OWNER_GUEST`(93).

### 4.6.3 vendor pKVM 인프라 HVC (참조)

\

pKVM 활성화·EL2 상태 관리용 request FID (`hvc_pkvm_handler`, base `0xC6000000`). 부팅/인프라 성격이며 NPU 격리 로직과 직접 관계는 없다.

\

| offset | FID | 동작 |
| --- | --- | --- |
| 0x80~0x81 | ACTIVATE_PROTECTED_KVM / GET_PROTECTED_KVM_ENABLED | pKVM 활성화, 초기화 여부 조회 |
| 0x82~0x83 | PKVM_UPDATE_HCR / PKVM_UPDATE_FG_WRITE_TRAP | HCR_EL2 / HFGWTR_EL2 fine-grained trap 갱신 |
| 0x84~0x85 | PKVM_RECORD_EL2_INFO / PKVM_SET_CPU_CONTEXT | EL2 sysreg/offset·CPU context 기록(디버깅) |

\

관련: `HVC_FID_PVMFW_INFO`(0x52), `HVC_FID_REQUEST_FW_STAGE2_AP`(0x111). EL3↔EL2 핸드오프는 SMC(`ACTIVATE_PROTECTED_KVM` 등)로 수행.

\

\

# 5. SW Code Structure

\

|  | Module Name | Repository | Branch / Tag | File List |
| --- | --- | --- | --- | --- |
| 1 | vendor pKVM (H-ARX) | halla/vendor_pkvm | s5e9985-zebu-feature | plat/samsung/exynos/pkvm/{exynos_pkvm.c, exynos_pkvm_interface.c} , exception/exynos_hvc_svc.c , s2mpu/interface/exynos_s2mpu_guest_protection.c , vm/guest_memory.c |
| 2 | mainline pKVM core | product/pro_17_aicore/kernel/kernel-6.18 | tag DCB1-260413-Android17-6.18-T145770 + 8 | arch/arm64/kvm/hyp/nvhe/{pkvm.c, device/device.c, mem_protect.c} , include/linux/arm-smccc.h , drivers/vfio/platform/reset/vfio_platform_exynosnpu.c |
| 3 | Host kernel (Exynos) | product/pro_17_aicore/kernel/exynos/soc-series/common | tag + 22 | drivers/soc/samsung/exynos/exynos-pkvm-module/{exynos-pkvm.c, hyp/exynos-pkvm-module.c} , drivers/vision/npu/ , drivers/iommu/samsung/samsung-iommu-v9.c |
| 4 | Host kernel DTS | product/pro_17_aicore/kernel/exynos/soc-series/u-android17 | tag + 6 | arch/arm64/boot/dts/exynos/{s5e9975.dts, s5e9975-npu.dtsi, s5e9975-sysmmu.dtsi, s5e9975-sk2.dtsi} , dtbo Bazel rule |
| 5 | Guest kernel | product/pro_17_aicore/kernel/guest-kernel-6.18 | tag + 29 | drivers/iommu/samsung-iommu-v9.c , drivers/vision/npu/ (symlink), microdroid_defconfig |
| 6 | Bootloader (pvmfw) | product/pro_17_aicore/bootloader/common | tag + 3 | platform/s5e9975/security/pvmfw.c , platform/s5e9975/bootargs.c , app/exynos_main/boot/cmd_boot.c |
| 7 | Platform VM DTBO | platform/plat_17_aicore/device/samsung/erd9975 | (latest) | arch/arm64/boot/dts/erd/s5e9975-vm.dtso , arch/arm64/boot/dts/BUILD.bazel , dtboimg.cfg |

# 6. References

| 항목 | 출처 |
| --- | --- |
| Android Device Assignment 문서 | AOSP packages/modules/Virtualization — docs/ device_assignment.md (android16-qpr2-release) |
| pKVM / AVF 아키텍처 | Android Virtualization Framework 공식 문서 ( source.android.com/docs/core/virtualization ) |
| Google 2026 Bootcamp | AVF / pKVM / AI on pVM 세션 자료 |
| ARM SMCCC | ARM DEN 0028 (SMC Calling Convention), Vendor Hypervisor Service |

\

Document Review

# **※** **설계 단계 Checklist**

| Milestone | 기능 Checklist | Self-Review(Yes/No) |
| --- | --- | --- |
| 3. 설계서 | 1. SWArchitecture Design 상에 구성 요소 들의 역할과 책임이 명확히 제시되어 있는가? | Yes |
| 3. 설계서 | 2. 각 구성 요소들의 interface는 명확히 정의되어 있는가? (기존 framework과의 interface포함) | Yes |
| 3. 설계서 | 3. 요구사항이 모두 만족되는 Software Architecture가 설계되었는가? | Yes |
| 3. 설계서 | 4. SW architecture와 Software Detailed Design 간 일관성이 있는가? | Yes |
| 3. 설계서 | 5. 설계 operation이 state machine 혹은 procedure의 진행이 구체적으로 제시되어 있는가? | Yes |
| 3a. 개발 계획서 | 3a. 개발 계획이 변경된 경우 개발 계획서가 업데이트 되었는가? (변경이 없다면 "N/A") | N/A |
| 3b. 요구 사양서 | 3b. 요구사항이 변경된 경우 요구사양서가 업데이트 되었는가? (변경이 없다면 "N/A") | N/A |

\

| 의견 내용 | 답변 내용 | 상태 |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| xxx / TL / xxx xxx " Guest 3계층으로 구성된다. " kernel 과 platform도 그림에 구분되면 이해하는데 도움이 될듯합니다. 전체 architecture에서 개발 범위를 별도로 구분해 줘도 좋겠네요 id 정보는 현재 수준의 architecture 그림에서는 조금 detail한 정보로 보여서..좀더 추상화 시켜도 좋겠습니다. | xxx / TL / xxx | xxx / xxx xxx 수정하였습니다. | xxx / xxx | xxx / xxx | xxx 수정하였습니다. | Open |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 수정하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " Host + pVM 동시 사용 목표 " 이것도 구현 범위는 아니지만, 설계 완료가 과제 목표이니.. multi vm 지원에 대한 설계 내용도 포함을 하면 좋을것 같습니다. | xxx / TL / xxx | xxx / xxx xxx 3.7 Multi VM NPU 동시 사용 절에 추가하였습니다. | xxx / xxx | xxx / xxx | xxx 3.7 Multi VM NPU 동시 사용 절에 추가하였습니다. | Open |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 3.7 Multi VM NPU 동시 사용 절에 추가하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " 개발 범위 " 이 정보가..그림에 같이 표현되면 좋겠네요 | xxx / TL / xxx | xxx / xxx xxx 수정하였습니다. | xxx / xxx | xxx / xxx | xxx 수정하였습니다. | Resolved |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 수정하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " Composition of Arc " table에서 담당은.. xxx 내부 그룹 단위로 구분해주면 좀 더 의미 있어 보입니다. | xxx / TL / xxx | xxx / xxx xxx 수정하였습니다. | xxx / xxx | xxx / xxx | xxx 수정하였습니다. | Resolved |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 수정하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " Host 간 핵심 인터페이스 " 설계 단계에서 각 module 간의 interface에 대한 내용은.. input / output 에 대한 정의가 가장 필수 정보로 중요할것 같고, 추가적으로 내부적인 동작에 대한 설명 정도가 있으면 될것 같습니다. 이외 정보는 부가적인 정보로 봐도 될것 같습니다. | xxx / TL / xxx | xxx / xxx xxx 수정하였습니다. | xxx / xxx | xxx / xxx | xxx 수정하였습니다. | Resolved |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 수정하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " 흐름. " 아래 "핵심 계약"은 뭔가 좀 어색해 보이고.. 시퀀스 정도로 해도 될것 같네요.ㅎ | xxx / TL / xxx | xxx / xxx xxx 수정하였습니다. | xxx / xxx | xxx / xxx | xxx 수정하였습니다. | Resolved |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 수정하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " VM 생성부터 NPU가 pVM " behavior view는.. 각 module이 어떻게 연결 되어 동작하는지를 설명하는 내용이라.. sequence는 앞에 그림 static view(module view)에 있는 module를 중심으로 dynamic view(sequce diagram 등)을 그려주면 좋을것 같습니다. | xxx / TL / xxx | xxx / xxx xxx 넵 아래 내용들 전반적으로 수정하였습니다. | xxx / xxx | xxx / xxx | xxx 넵 아래 내용들 전반적으로 수정하였습니다. | Resolved |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 넵 아래 내용들 전반적으로 수정하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " uest에서 물리 자원(SFR)에 DT resource로 접근할 수 없으므로, MMIO 확보를 HVC로 지연 처리한다. " 디자인 단계에서..아래 code 수준 내용은 너무 세부적인 내용으로 보입니다. 아래 내용도 sequence diagram 정도로 추상화 해서 그려도 좋을것 같습니다. | xxx / TL / xxx |  | Dangling |  |  |  |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " SysMMU는 VA→PA 변 " 중요한건 최종 단계 구조이니.. 최종 단계 구조도 함께 그려주면 좋을것 같습니다. 아님, 최종 단계 구조만 표현되어도 될것 같습니다. | xxx / TL / xxx | xxx / xxx xxx 네 수정하였습니다. | xxx / xxx | xxx / xxx | xxx 네 수정하였습니다. | Resolved |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 네 수정하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " PU Interru " 아래 그림도.. 앞에 그린 module view를 기준으로 각 module이 어떤 역할을 하는지 매핑을 시켜줘도 좋을것 같네요.. ex, 아래 그림이서.. 1/2번은 Host VM → 3/4번은 pKVM → 5번은 Guest VM 정도로 매핑 시켜줘도 좋겠네요 | xxx / TL / xxx | xxx / xxx xxx 수정하였습니다. | xxx / xxx | xxx / xxx | xxx 수정하였습니다. | Resolved |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 수정하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " 메모리 격리는 두 축으로 이뤄 " 아래 내용도.. detail한 내용이 많은데..  글 보다는 간단한 그림으로 표현해줘도 좋겠네요 | xxx / TL / xxx | xxx / xxx xxx 네 수정하였습니다. | xxx / xxx | xxx / xxx | xxx 네 수정하였습니다. | Resolved |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 네 수정하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |
| xxx / TL / xxx xxx " Security " 이건 지금 문서에 수정하자는 comment는 아니고, 이후에 디자인 문서 작성할때 참고용으로 드리는 의견입니다.ㅎ 일반적으로  Design consideration의 내용은.. 설계하는 sw에서 가장 중요하게 고려해야 되는 내용을 정리하는거라, 여기에 포함된 내용은.. 이후에 설명되는 SW architecture에서 design consideration을 어떻게 설계에 반영하고 있는지 위주로 내용이 작성되면 좋습니다. 예를 들어, performance로 3% 이내 overhead를 잡았다면, SW architecture design 내용에는 해당 목표를 달성하기 위해서 어떤 design이 적용되었다는 내용들이 포함되는것이 좋습니다. 현재의 design 문서는 전체 sw 구조에 대한 설명 위주로 작성되어 있고, 개발하는 solution에서 가장 중요한 요소로 정의한 design considration 항목이 구체적으로 design에 어떻게 반영되었는지에 대한 내용은 이후 설명에 많이 없어서.. 향후에는 이런 내용도 고려해서 디자인 문서를 작성해 주셔도 좋을거 같습니다. | xxx / TL / xxx | xxx / xxx xxx 감사합니다. 우선 "설계 반영" 절 정도만 우측에 추가하여, 어떤 부분에 해당 고려사항이 반영되었는지 정도 표시하였습니다. | xxx / xxx | xxx / xxx | xxx 감사합니다. 우선 "설계 반영" 절 정도만 우측에 추가하여, 어떤 부분에 해당 고려사항이 반영되었는지 정도 표시하였습니다. | Open |
| xxx / TL / xxx |  |  |  |  |  |  |
| xxx / xxx | xxx / xxx | xxx 감사합니다. 우선 "설계 반영" 절 정도만 우측에 추가하여, 어떤 부분에 해당 고려사항이 반영되었는지 정도 표시하였습니다. |  |  |  |  |
| xxx / xxx |  |  |  |  |  |  |

\

Document Information

| Date | Revision | State | Author | Participants |
| --- | --- | --- | --- | --- |
| xxx | 29 |  | xxx / xxx | xxx / xxx , xxx / TL / xxx |

\

---

\
