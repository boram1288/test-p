# virtio-vsock / vhost-vsock / vhost-user 비교

> virtio-vsock, vhost-vsock, vhost-user는 이름이 비슷해 같은 층위의 대안처럼 보이지만, 실제로는 **서로 다른 계층**의 개념이다. virtio-vsock은 게스트가 보는 "디바이스 규격(프론트엔드)"이고, vhost-vsock과 vhost-user는 그 디바이스의 "호스트 쪽 백엔드를 어디서 구현하느냐"의 선택지다. 조사 시점: 2026-07.

## 0. 한 줄 정의

| 용어 | 계층 | 정의 |
|---|---|---|
| virtio-vsock | 디바이스/프로토콜 규격 | 게스트에 보이는 virtio 소켓 디바이스. 게스트 앱은 `AF_VSOCK` 소켓(CID + 포트)으로 host↔guest 통신 |
| vhost-vsock | 백엔드 구현 (호스트 커널) | virtio-vsock의 데이터 평면을 **호스트 커널 모듈**(`vhost_vsock.ko`)이 처리하는 in-kernel vhost 백엔드 |
| vhost-user | 백엔드 오프로드 프로토콜 (범용) | virtio 디바이스의 데이터 평면을 VMM 밖의 **별도 유저스페이스 프로세스**로 넘기기 위한 프로토콜. vsock 전용이 아니라 net/blk/gpu 등 범용 |

계층 관계:

```
게스트 커널:   virtio-vsock 드라이버 (AF_VSOCK)          ← 규격은 하나
                      │ virtqueue (공유 메모리 링)
호스트 쪽:     ┌──────┴───────────────────────┐
               │ 백엔드를 누가 구현하는가       │
               ├── VMM 내장 에뮬레이션          (예: crosvm 내장 vsock)
               ├── vhost-vsock: 호스트 커널     (QEMU/KVM 표준 경로)
               └── vhost-user-vsock: 별도 유저스페이스 데몬
                                    (예: rust-vmm vhost-device-vsock)
```

## 1. virtio-vsock — 게스트가 보는 소켓 디바이스

- **주소 체계**: TCP/IP 스택 없이 CID(Context ID) + 포트 쌍으로 주소를 지정한다. 게스트 네트워크 구성과 무관하게 동작하는 것이 존재 이유다(에이전트 통신, 디버깅, RPC 등).
- **CID 특수값**: 0 = hypervisor, 1 = `VMADDR_CID_LOCAL`(로컬 루프백), 2 = `VMADDR_CID_HOST`(호스트), 3 이상 = 각 게스트 VM.
- **토폴로지**: 설계상 host↔guest **점대점 전용**이다. guest-to-guest는 스펙·구현 양쪽에서 의도적으로 제외되어 있다. 한 게스트가 다른 게스트의 CID로 패킷을 보내도 표준 백엔드는 전달하지 않는다 (`99_pvm_dmabuf_transfer.md` 1.1절).
- **전송 방식**: 데이터는 virtqueue(TX/RX 링)를 통해 복사 기반으로 흐른다. zero-copy 대량 데이터 전달용이 아니라 제어·스트림 채널용이다.

## 2. vhost-vsock — 호스트 커널 in-kernel 백엔드

- **위치**: 호스트 커널 모듈 `vhost_vsock.ko`. VMM(QEMU)은 `/dev/vhost-vsock`을 열고 ioctl(`VHOST_SET_MEM_TABLE`, `VHOST_SET_VRING_KICK/CALL` 등)로 게스트 메모리 테이블과 virtqueue 정보를 커널에 등록한다. 이후 데이터 평면은 VMM을 거치지 않고 커널이 직접 처리한다.
- **성능 동기**: 패킷마다 VMM 유저스페이스로 나갔다 들어오는 왕복을 제거해 지연·처리량을 개선하는 것이 vhost 계열의 공통 목적이다.
- **라우팅 규칙**: 게스트가 보낸 패킷 중 목적지 CID가 호스트(CID 2)인 것만 호스트 소켓 계층으로 올린다. **다른 게스트 CID로 향하는 패킷은 버린다** — guest-to-guest가 안 되는 구현상의 직접 원인이 이 지점이다.
- **게스트 간 통신이 필요하면**: 호스트 유저스페이스 릴레이(socat 브리지 등)를 세워 guest A ↔ host ↔ guest B로 이어 붙여야 하며, 복사가 늘어 처리량이 떨어진다(TUM 실측 약 1.5 Gbit/s).

## 3. vhost-user — 유저스페이스 백엔드 오프로드 프로토콜

- **문제 의식**: in-kernel vhost는 백엔드 로직이 커널 안에 있어야 한다. vhost-user는 같은 구조(공유 메모리 + eventfd 신호)를 유지하면서 디바이스 로직을 **비특권 유저스페이스 프로세스**로 옮긴다. 커널 vhost의 ioctl 하나하나에 대응하는 메시지를 Unix domain socket으로 보내는 "vhost의 유저스페이스 판"이다.
- **제어 평면**: VMM(front-end)과 백엔드 데몬(back-end)이 Unix domain socket으로 메시지를 교환한다. fd는 SCM_RIGHTS 보조 데이터로 전달된다. 주요 메시지: `VHOST_USER_GET/SET_FEATURES`, `SET_MEM_TABLE`(메모리 영역 테이블 + fd), `SET_VRING_NUM/ADDR/BASE/KICK/CALL` 등. 멀티큐, IOMMU/IOTLB, 라이브 마이그레이션 로깅 등은 프로토콜 피처로 협상한다.
- **데이터 평면**: front-end가 게스트 RAM 영역 테이블을 fd와 함께 넘기면 **백엔드가 게스트 RAM 전체를 직접 mmap**한다. 이후 백엔드는 공유 메모리 안의 virtqueue 디스크립터·버퍼를 직접 읽고 쓴다. 알림은 eventfd 쌍으로 처리한다(`KICK` = 게스트→백엔드, `CALL` = 백엔드→게스트 인터럽트).
- **적용 디바이스**: vhost-user-net(원조, Snabbswitch·DPDK 스위치), vhost-user-blk, vhost-user-gpu, vhost-user-input, crypto 등 — vsock은 그중 하나의 적용 사례일 뿐이다.

### 3.1 vhost-user-vsock (vhost-device-vsock) — vsock에 vhost-user를 적용한 경우

rust-vmm의 `vhost-device-vsock` 데몬이 대표 구현이다. QEMU에 `-chardev socket,path=...` + `-device vhost-user-vsock-pci`로 붙인다.

- 게스트 RAM을 데몬이 mmap해야 하므로 QEMU를 `memory-backend-memfd`(공유 가능 메모리)로 띄워야 한다.
- **sibling VM 통신 지원**: 한 데몬에 `--vm`을 여러 개 등록하면 같은 그룹에 속한 VM끼리 CID로 직접 통신할 수 있다(게스트 쪽에서 `VMADDR_FLAG_TO_HOST` 플래그 필요). 표준 vhost-vsock이 버리는 guest-to-guest 트래픽을 **데몬이 두 VM의 virtqueue 사이에서 중계**해 주는 것이다.
- `--forward-cid`로 게스트 연결을 호스트의 다른 AF_VSOCK endpoint로, `--uds-path`로 호스트 AF_UNIX 소켓으로 포워딩할 수도 있다(Firecracker hybrid-vsock 스타일).
- 단, sibling 통신도 결국 **호스트 유저스페이스 데몬이 양쪽 게스트 메모리를 매핑하고 복사로 중계**하는 구조다. "vsock으로 guest-to-guest가 된다"는 것이지 zero-copy 직결 채널이 생기는 것이 아니다.

## 4. 비교표

| 항목 | virtio-vsock (규격) | vhost-vsock | vhost-user(-vsock) |
|---|---|---|---|
| 계층 | 게스트 프론트엔드 디바이스 규격 | 호스트 커널 백엔드 | 유저스페이스 백엔드 프로토콜 |
| 데이터 평면 위치 | — (백엔드가 결정) | 호스트 커널 | 별도 유저스페이스 데몬 |
| 제어 평면 | virtio 표준 (PCI/MMIO) | ioctl (`/dev/vhost-vsock`) | Unix domain socket 메시지 |
| 게스트 메모리 접근 | — | 커널이 메모리 테이블로 접근 | 데몬이 게스트 RAM 전체 mmap |
| guest-to-guest | 스펙에서 제외 | 불가 (host CID 외 패킷 폐기) | sibling 그룹으로 가능 (데몬 중계, 복사) |
| 성능 특성 | 복사 기반 스트림 | VMM 우회로 왕복 절감 | 커널 우회 + 폴링 가능, 백엔드 격리 |
| 장애 격리 | — | 커널 내 실행 (버그 = 커널 문제) | 비특권 프로세스 (crash가 호스트에 국한) |
| 대표 용도 | 에이전트/RPC/디버그 채널 | QEMU/KVM 표준 vsock 경로 | DPDK 스위치, 외부 디바이스 데몬, sibling 중계 |

## 5. pKVM/pVM 관점 시사점

1. **vhost-user는 protected VM과 근본적으로 충돌한다.** vhost-user의 전제는 "백엔드 데몬이 게스트 RAM 전체를 mmap"인데, pVM 메모리는 생성 시 호스트 stage-2에서 unmap되므로 호스트 유저스페이스 데몬이 매핑할 수 없다. pVM에서 virtio가 동작하는 것은 게스트가 `MEM_SHARE`로 명시적으로 공유한 bounce buffer(swiotlb) 영역에 한정되며, 이 구조에서는 vhost-user든 vhost-vsock이든 공유 창 안의 복사 기반 통신만 가능하다.
2. **vhost-device-vsock의 sibling 통신도 pVM 간 채널의 답이 아니다.** 데몬이 양쪽 VM 메모리를 매핑·중계하는 구조라서, pVM에 적용해도 "호스트에 노출되는 복사 릴레이"라는 성격은 표준 vsock 릴레이와 동일하다. 다만 일반(non-protected) VM 조합이라면 socat 브리지보다 정돈된 guest-to-guest vsock 경로로 쓸 수 있다.
3. **선택 기준 요약**: 게스트가 보는 인터페이스는 어차피 virtio-vsock 하나다. 백엔드는 (a) 표준 host↔guest 채널이면 vhost-vsock, (b) 백엔드 로직을 호스트 커널 밖으로 빼거나 VM 간 vsock 중계가 필요하면 vhost-user-vsock, (c) pVM 간 zero-copy 데이터 채널이 필요하면 vsock 계열이 아니라 EL2 확장(`99_pvm_dmabuf_transfer.md` 경로 3)으로 가야 한다.

## 참고 자료

- [vhost-user protocol specification — QEMU docs](https://www.qemu.org/docs/master/interop/vhost-user.html)
- [vhost-device-vsock README (rust-vmm)](https://github.com/rust-vmm/vhost-device/blob/main/vhost-device-vsock/README.md)
- [vsock(7) man page](https://man7.org/linux/man-pages/man7/vsock.7.html)
- [virtio-vsock — configuration-agnostic guest/host communication (TUM)](https://www.net.in.tum.de/fileadmin/TUM/NET/NET-2019-10-1/NET-2019-10-1_14.pdf)
- [Vsock — Book of crosvm](https://crosvm.dev/book/devices/vsock.html)
- [vhost-vsock: add virtio sockets device (원 패치)](https://patchwork.kernel.org/project/qemu-devel/patch/1470411926-15389-3-git-send-email-stefanha@redhat.com/)
