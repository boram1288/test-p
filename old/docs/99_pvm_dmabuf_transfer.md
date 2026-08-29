# pKVM 환경에서 pVM 간 DMA-BUF 전달 방법 조사

> 질문: pKVM 기반 환경에서 pVM과 pVM 간에 DMA-BUF를 어떻게 전달할 수 있는가? 통신 방식은 virtio-vsock밖에 없는 것으로 알고 있고, vsock은 pVM 간에는 통신이 안 되고 host와 pVM 간에만 가능한 것으로 알고 있다.
>
> 본 문서는 기존 레포 문서(`99_ffa.md`, `99_virtio_vsock.md` 등)와 독립적으로, upstream 커널 문서·메일링 리스트·컨퍼런스 자료를 기준으로 백지에서 재조사한 결과다. 조사 시점: 2026-07.

## 0. 결론 요약

질문의 전제 두 가지는 모두 사실로 확인됐다. 따라서 **upstream pKVM + 표준 AVF 스택만으로는 pVM↔pVM 간 zero-copy DMA-BUF 전달 방법이 현재 존재하지 않는다.** 가능한 경로는 두 갈래뿐이다.

1. Host를 경유하는 복사 기반 릴레이 (현재 스택으로 가능, zero-copy 아님, host에 노출)
2. EL2 확장 (pKVM vendor module이 공식 통로 — zero-copy pVM↔pVM의 실질적 유일 경로)

## 1. 전제 확인

### 1.1 vsock은 정말 guest↔host 전용인가 — 맞다

- virtio-vsock은 설계상 host와 guest 간 점대점(point-to-point) 채널이다. vhost-vsock은 목적지 CID가 host(CID 2)가 아닌 패킷을 다른 VM으로 포워딩하지 않는다.
- guest-to-guest 통신은 스펙·구현 양쪽에서 **의도적으로 제외**되어 있다 (격리 목적).
- VM 간에 vsock을 쓰려면 host 유저스페이스에 릴레이를 두는 방법뿐이다:
  - socat 브리지 (TUM 논문 사례: 실측 평균 처리량 약 1.5 Gbit/s — 다중 버퍼 복사가 원인)
  - rust-vmm `vhost-device-vsock`의 `--forward-cid` 포워딩
  - ByteDance의 multi-CID 커널 패치(2021)는 RFC 수준에서 머지되지 않고 종료
- 어느 방식이든 host가 데이터를 복사하며 중계한다.

### 1.2 pKVM에 guest-to-guest 메모리 프리미티브가 있는가 — 없다

최신 커널 문서(next-20260710) 및 게스트 하이퍼콜 문서 직접 확인 결과:

- pVM 메모리는 생성 시 host stage-2 identity map에서 unmap(donate)된다. 메타데이터 페이지(stage-2 페이지 테이블, `struct kvm_vcpu` 등)도 host에서 hypervisor로 기부된다.
- 게스트(pVM)가 쓸 수 있는 메모리 하이퍼콜은 `ARM_SMCCC_KVM_FUNC_MEM_SHARE` / `MEM_UNSHARE` / `MEM_RELINQUISH`로, 전부 **"자기 페이지를 KVM host와" 공유/회수/반납**하는 연산이다. 대상이 다른 pVM인 연산은 존재하지 않는다.
- 페이지 소유권 상태 기계에도 "두 guest가 공유" 또는 "guest→guest 이전" 상태가 없다.
- pKVM의 FF-A 지원(`arch/arm64/kvm/hyp/nvhe/ffa.c`, 약 880 LoC)은 **host↔TrustZone(Secure World) 프록시**다. 처리 ABI는 `FFA_FEATURES`, `FFA_RXTX_MAP/UNMAP`, `FFA_MEM_SHARE`, `FFA_MEM_LEND`, `FFA_MEM_RECLAIM` 및 fragmented descriptor이며, 목적은 host가 pVM/hypervisor 메모리를 TrustZone에 넘기는 confused-deputy 공격 차단이다. VM을 FF-A endpoint로 취급해 VM 간 메모리 트랜잭션을 중계하는 기능이 아니다.
- FF-A 스펙 자체는 하이퍼바이저가 Normal World VM들을 endpoint로 취급해 relaying하는 것을 허용하지만, pKVM은 이를 구현하지 않았다.
- 그 외 pKVM 격리 메커니즘 상태(커널 문서 기준): CPU state isolation 미구현, IOMMU 기반 DMA isolation 미구현(개발 중), pvmfw 항목 미구현(upstream 기준; AVF는 자체 pvmfw 사용).

## 2. DMA-BUF "전달"의 실체

dma-buf fd는 커널 인스턴스에 종속된 추상화라서 **fd 자체가 VM 경계를 넘을 수는 없다**. 전달의 실체는:

1. 밑에 깔린 물리 페이지에 대한 접근권을 상대 pVM의 stage-2에 만들어주고 (= EL2 소유권 연산),
2. 상대 pVM 커널에서 그 IPA 범위를 sg_table로 구성해 다시 dma-buf로 import하는 것이다.

1번이 곧 하이퍼바이저 소유권 조작이므로, 1.2절의 프리미티브 부재가 바로 병목이다.

## 3. 가능한 경로

### 경로 1 — Host 경유 릴레이 (현재 스택으로 가능)

- 흐름: pVM A가 버퍼 내용을 host와 공유된 페이지(virtio용 swiotlb bounce buffer)로 복사 → host 프록시가 pVM B의 공유 페이지로 복사 → B가 자기 dma-buf에 기록.
- 구현: vsock 두 구간(A↔host, host↔B) + host 유저스페이스 릴레이.
- 비용: 프레임당 복사 2회 이상, host에 평문 노출. 암호화로 가리면 기밀성이 구조적 비노출이 아닌 키 관리 강도에 위임된다.

### 경로 2 — VMM이 같은 버퍼를 양쪽 VM에 매핑 (non-protected VM 한정)

- 보호되지 않은 VM이라면 crosvm 같은 VMM이 host의 dma-buf(udmabuf, dma-buf heap)를 두 VM의 guest 메모리 또는 virtio shared-memory region으로 동시 매핑해 zero-copy가 가능하다.
- **protected VM에서는 불가**: pVM 페이지는 host에서 unmap되고, host 소유 페이지를 두 pVM에 동시 매핑하는 소유권 상태가 존재하지 않는다.

### 경로 3 — EL2 확장 (zero-copy pVM↔pVM의 실질적 유일 경로)

- **pKVM vendor module**: Android 14부터 SoC 벤더가 EL2에 모듈을 로드하고 `pkvm_register_el2_mod_call()`로 커스텀 하이퍼콜을 등록할 수 있다 (Android 15에서 핸들러 시그니처가 `struct user_pt_regs *`로 변경). 여기에 guest-to-guest share/lend 연산(한쪽 stage-2 unmap + 상대 stage-2 map + 소유권 추적)을 구현하는 것이 upstream을 포크하지 않는 공식 통로이며, 실제로 벤더 고유 EL2 기능들이 이 메커니즘으로 배포된다.
- **upstream 방향**: 2025~2026년 기준 pVM용 guest_memfd 지원, pKVM DMA isolation(IOMMU), LPC 2025의 "Protected DMAbufs" 논의 등 보호 VM과 dma-buf를 접목하는 작업이 진행 중이나, **guest-to-guest 공유 프리미티브가 머지되거나 게시된 패치는 확인되지 않았다.**
- **대비 사례**: Qualcomm Gunyah 하이퍼바이저는 VM 간 메모리 lending과 message queue를 네이티브로 제공한다. 즉 이것은 하이퍼바이저 설계 선택의 문제이지 기술적 불가능이 아니며, pKVM이 아직 그 기능을 upstream에 갖추지 않았을 뿐이다. Arm CCA 진영에서도 CVM 간 통신 연구(CAEC 등)가 나오고 있다.

## 4. 실무 시사점

1. 지금 당장 순정 스택으로: **복사 + host 노출을 감수하고 vsock/virtio 릴레이**.
2. zero-copy + host 비노출이 요구사항이면: **대상 SoC의 pKVM이 vendor module로 guest-to-guest 하이퍼콜을 이미 제공하는지 확인**이 첫 번째 할 일이고, 없으면 vendor module을 직접 작성해야 한다.
3. EL2 확장을 하더라도 버퍼 핸들·링 인덱스를 주고받을 제어 채널은 별도로 필요한데, 메타데이터만 오가므로 vsock(host 릴레이)으로 충분하다.

## 참고 자료

- [Protected KVM (pKVM) — The Linux Kernel documentation](https://www.kernel.org/doc/html/next/virt/kvm/arm/pkvm.html)
- [KVM/arm64-specific hypercalls exposed to guests](https://docs.kernel.org/virt/kvm/arm/hypercalls.html)
- [KVM: arm64: FF-A proxy for pKVM — LWN](https://lwn.net/Articles/929560/)
- [virtio-vsock — configuration-agnostic guest/host communication (TUM)](https://www.net.in.tum.de/fileadmin/TUM/NET/NET-2019-10-1/NET-2019-10-1_14.pdf)
- [vhost-device-vsock README (rust-vmm)](https://github.com/rust-vmm/vhost-device/blob/main/vhost-device-vsock/README.md)
- [vsock(7) man page](https://man7.org/linux/man-pages/man7/vsock.7.html)
- [Implement a pKVM vendor module — AOSP](https://source.android.com/docs/core/virtualization/pkvm-modules)
- [AVF architecture — AOSP](https://source.android.com/docs/core/virtualization/architecture)
- [KVM: arm64: Add support for protected guest memory (guest_memfd) — LWN](https://lwn.net/Articles/1053007/)
- [LPC 2025 program (Protected DMAbufs, Confidential Computing MC)](https://lpc.events/event/19/program)
- [CAEC: Confidential, Attestable, Efficient Inter-CVM Communication with Arm CCA](https://arxiv.org/pdf/2512.01594)
