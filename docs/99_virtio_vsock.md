# virtio-vsock 정리 — pVM 간 직접 메시지 교환이 가능한가?

pVM 간에 vsock으로 직접(호스트 개입 없이) 메시지를 주고받을 수 있는지 확인한 결과를 정리한다.

> 조사일: 2026-07-08. 주요 근거: [QEMU VirtioVsock 문서](https://wiki.qemu.org/Features/VirtioVsock), [KVM Forum 2019 vsock 발표(vsock 메인테이너 Stefano Garzarella)](https://stefano-garzarella.github.io/posts/2019-11-08-kvmforum-2019-vsock/), [ChromiumOS virtio-vsock 문서](https://chromium.googlesource.com/chromiumos/platform2/+/HEAD/vm_tools/docs/vsock.md), [Firecracker vsock 문서](https://github.com/firecracker-microvm/firecracker/blob/main/docs/vsock.md), [crosvm vsock 문서](https://crosvm.dev/book/devices/vsock.html), [AOSP VirtualizationService 문서](https://source.android.com/docs/core/virtualization/virtualization-service)

---

## 결론 (요약)

**불가능하다.** virtio-vsock은 설계상 **guest↔host 전용** 채널이며, guest-to-guest(VM 간 직접) 통신은 스펙과 구현 양쪽에서 **의도적으로 제외**되어 있다. 한 pVM이 다른 pVM의 CID를 목적지로 패킷을 보내도 호스트의 vhost-vsock이 이를 전달하지 않는다. pVM 간에 vsock을 쓰려면 **반드시 Host 유저스페이스 릴레이(프록시)를 경유**해야 하며, 이는 본 과제의 DP-C1 후보(C1-2, C1-4)에서 "vsock 채널"의 의미를 정확히 규정하는 중요한 사실이다.

## 1. vsock 기본 구조

- vsock은 `AF_VSOCK` 주소 패밀리를 쓰는 소켓 통신으로, 주소는 **CID(Context ID) + 포트** 쌍이다. TCP/IP 스택 없이, 게스트 네트워크 구성과 무관하게 동작하는 것이 장점이다.
- 전송 계층이 분리되어 있다: 게스트 쪽은 `virtio_transport`(virtio-vsock 디바이스 프론트엔드), 호스트 쪽은 `vhost-vsock`(in-kernel 백엔드) 또는 VMM 유저스페이스 백엔드(crosvm, Firecracker 등)가 담당한다.

**CID 특수값**:

| CID | 의미 |
|-----|------|
| 0 | Hypervisor |
| 1 | Local(루프백) |
| 2 | `VMADDR_CID_HOST` — 호스트 |
| 3 이상 | 각 게스트 VM에 부여 |

## 2. 왜 guest-to-guest가 안 되는가

1. **스펙 수준의 설계 결정**: virtio-vsock 디바이스 모델은 각 VM과 호스트 사이의 **점대점(point-to-point) 링크**다. 디바이스에는 라우팅/포워딩 개념이 없으며, 통신 상대는 항상 호스트다. QEMU 문서와 vsock 메인테이너의 KVM Forum 2019 자료 모두 guest-to-guest를 비지원으로 명시하고, VM 간 통신이 필요하면 호스트 릴레이(vsock-bridge 등)나 일반 virtio-net 네트워킹을 쓰라고 안내한다.
2. **구현 수준의 강제**: 호스트 커널의 vhost-vsock은 게스트가 보낸 패킷의 목적지 CID가 호스트(CID 2)인 경우만 호스트 소켓 계층으로 전달한다. 다른 게스트의 CID를 목적지로 한 패킷을 이웃 VM의 virtqueue로 넘겨주는 경로 자체가 없다.
3. **의도**: 이 제한은 결함이 아니라 격리·단순성을 위한 선택이다. VM 간 임의 통신 경로를 커널이 기본 제공하면 VM 격리 경계에 상시 개방된 측면 채널이 생기므로, "VM 간 통신은 호스트(관리자)가 명시적으로 개통해야 한다"는 모델을 유지한 것이다. pKVM의 "pVM 간 채널은 명시적 배선으로만 존재"(본 과제 시나리오 6단계)와 같은 철학이다.

## 3. 그러면 pVM 간 vsock "통신"은 실제로 어떻게 구성되는가

모두 **Host가 경로에 상주**하는 형태다.

| 방법 | 구성 | 특성 |
|------|------|------|
| Host 유저스페이스 릴레이 | 호스트 데몬(socat, vsock-bridge 등)이 VM A로부터의 vsock 연결을 수락하고 VM B로의 vsock 연결로 바이트를 중계 | 가장 일반적. guest→host→guest로 데이터가 두 번 이동하며 호스트 프로세스가 평문(암호화하지 않았다면)을 그대로 봄 |
| 일반 네트워킹(virtio-net) | VM 간 통신을 vsock이 아닌 가상 네트워크(브리지/tap)로 | vsock의 장점(무설정)을 포기. 역시 호스트 브리지 경유 |
| Firecracker/cloud-hypervisor hybrid vsock | 게스트 vsock을 호스트 Unix 도메인 소켓에 매핑 | VM 간에는 호스트에서 두 Unix 소켓을 잇는 프로세스 필요 — 구조는 릴레이와 동일 |
| AVF의 실제 사용 | `VirtualizationService`/RpcBinder가 vsock으로 host↔pVM 통신. pVM 간 Binder 통신도 호스트 서비스가 중개 | AVF도 vsock을 guest↔host 채널로만 사용한다 |

## 4. 본 과제(DP-C1) 관점의 함의

`08_candidate_architectures.md`의 C1-2(vsock 스트림 채널), C1-4(vsock 제어 + 공유 풀 데이터)를 해석할 때 다음이 전제되어야 한다.

1. **"vsock 채널"은 곧 "Host 릴레이 경유 채널"이다**: C1-2 다이어그램의 "Host vsock 백엔드/스위치"는 선택적 구성요소가 아니라, guest-to-guest 미지원이라는 구조적 사실 때문에 **반드시 존재해야 하는 릴레이 프로세스**다. Camera pVM과 AI pVM이 vsock으로 "직접" 연결되는 구성은 존재하지 않는다.
2. **기밀성은 오직 암호화로만**: 프레임이든 제어 메시지든 vsock으로 흐르는 모든 바이트는 Host 프로세스의 주소 공간을 지나간다. C1-2가 "전달 구간 보호 = 프레임 암호화"를 전제한 것은 이 구조 때문이며, 암호화해도 트래픽 패턴·타이밍은 노출된다(VOS-09와의 긴장).
3. **가용성**: Host 릴레이는 데이터/제어 경로의 단일 장애점이자, Host(비신뢰)가 언제든 연결을 끊을 수 있는 서비스 거부 지점이다. "Host 장애 시 실행 중 파이프라인 유지"(QA-05) 논증에서 vsock 의존 경로는 예외로 분리해서 다뤄야 한다.
4. **성능**: guest→host→guest 2홉이므로 최소 복사 2회 + 컨텍스트 전환이 프레임 주기마다 발생한다. C1-2의 "복사 2회" 비용 산정의 근거가 바로 이 구조다.
5. **제어 채널로 쓸 때(C1-4, FF-A handle 전달 등)**: 제어 메시지가 Host를 지나므로 위변조 가능성을 전제해야 한다. 수신 측이 메시지를 "힌트"로만 취급하고 최종 검증(예: FF-A retrieve 시 하이퍼바이저의 endpoint 대조, 공유 링 쪽 유효성 검사)을 신뢰 경로에서 수행하는 방어적 설계가 필요하다 — `99_ffa.md`의 handle 전달 논의와 08 문서 C1-4의 단점 항목이 이 지점을 가리킨다.

## 5. 결론

- pVM 간 vsock 직접 통신은 **스펙·구현 모두에서 불가능**하며, 앞으로도 vsock 자체가 라우팅을 갖게 될 가능성은 낮다(설계 철학상 의도적 제외).
- 따라서 설계 문서에서 "pVM 간 vsock 채널"이라는 표현은 항상 "Host 릴레이를 경유하는 채널"로 읽어야 하고, 그 순간 기밀성(암호화 전제)·가용성(Host DoS)·성능(2홉 복사)의 비용이 함께 따라온다.
- pVM 간 **직접** 채널이 필요하면 vsock이 아니라 하이퍼바이저가 중재하는 공유 메모리 계열(C1-1/C1-3, FF-A 메모리 공유 — `99_ffa.md`)이 유일한 구조적 선택지다. vsock은 빈도가 낮고 암호화·검증이 쉬운 **제어 평면**에 한정하는 것(C1-4의 역할 분담)이 구조적 사실과 정합하는 사용법이다.
