# pvmfw (protected VM firmware) 정리

> 출처: [AOSP `packages/modules/Virtualization/guest/pvmfw/README.md`](https://android.googlesource.com/platform/packages/modules/Virtualization/+/refs/heads/main/guest/pvmfw/README.md) (main 브랜치, 2026-07-08 조회)
>
> 본 문서는 AVF(Android Virtualization Framework)의 pVM 부트 신뢰 루트인 pvmfw의 역할, 통합 방식, 설정 데이터 포맷, DICE 체인 전달, 부팅 프로토콜을 정리한 것이다. 본 과제와의 접점: DP-A1(제어 평면 — Host 비신뢰 하에서 pVM에 비밀을 프로비저닝하는 방법), DP-E2(격리 증빙/측정), `99_ffa.md`·`99_tcb_basics.md`와 상호 참조.

---

## 목차

1. [Protected VM (pVM)](#1-protected-vm-pvm)
2. [pVM의 신뢰 루트: pvmfw](#2-pvm의-신뢰-루트-pvmfw)
3. [통합 (Integration)](#3-통합-integration)
4. [pVM 부팅](#4-pvm-부팅)
5. [개발/디버깅](#5-개발디버깅)
6. [본 과제 관점 시사점](#6-본-과제-관점-시사점)

---

## 1. Protected VM (pVM)

- AVF에서 하이퍼바이저(예: pKVM)는 VM과 호스트 간 **완전한 메모리 격리**를 강제하여 VM의 기밀성과 무결성을 보장한다.
- pVM은 non-secure world(또는 realm world)에서 실행되며, **신뢰되지 않는 Android 호스트의 VMM 프로세스가 동적으로 기동**한다. 호스트가 침해되어도 pVM 메모리에는 접근할 수 없다.
- pVM은 Google 전용 개념이 아니다. 격리·메모리 접근 제한 조건을 만족하면 SoC 벤더/OEM이 정의한 VM도 pVM에 해당한다.

## 2. pVM의 신뢰 루트: pvmfw

**문제**: VMM이 비신뢰이므로 VMM이 구성한 VM 초기 상태도 신뢰할 수 없다. 격리만으로는 부팅 시 **비밀(secret) 프로비저닝** 문제가 해결되지 않는다 — 위협 모델상 호스트가 비밀에 접근하면 안 되므로 VMM이 비밀을 전달할 수 없다.

**해결**: 하이퍼바이저가 보호된 메모리 영역에 pvmfw를 안전하게 로드하고 VM의 진입점으로 설정한다.

- pvmfw는 **pVM 안에서 최초로 실행되는 코드**가 되어 실행 환경을 직접 검증하고, 검증 실패 시 부팅을 중단한다. 이 과정을 호스트가 방해할 수 없다.
- pvmfw는 VMM이 구성한 가상 플랫폼(디바이스, 메모리 레이아웃)을 신뢰하지 않고 모든 검증을 직접 수행한다. 하이퍼바이저 인터페이스도 검증한다.
- 플랫폼 신뢰가 확인되면 **DICE(Open Profile for DICE) 체인으로 게스트 고유 비밀을 파생**한다. 이로써 pVM이 자신의 신원을 로컬/원격 주체에게 증명(attestation)할 수 있다.
- 검사가 모두 통과하면 부트로더처럼 게스트 커널의 첫 명령으로 점프한다.
- 현재 AArch64만 지원한다.

## 3. 통합 (Integration)

### 3.1 pvmfw 로딩

- pKVM에서 pvmfw가 놓일 물리 메모리는 하이퍼바이저가 아닌 **신뢰된 pvmfw 로더(보통 ABL)가 미리 채우고**, 하이퍼바이저는 이후 그 영역의 보호만 담당한다. 하이퍼바이저를 범용적이고 작게 유지하기 위한 설계다(TCB 최소화).
- Android T부터 `PRODUCT_BUILD_PVMFW_IMAGE` 빌드 변수로 `pvmfw.img`(boot 파티션 포맷의 chained static partition) 생성. ABL이 이를 검증한 후 boot.img 헤더의 `kernel_size`로 `pvmfw.bin` 크기를 얻는다.
- pvmfw는 4KiB 정렬된 IPA에 로드되어야 하며, ABL은 reserved memory DT 노드로 영역을 하이퍼바이저에 기술한다:

```dts
reserved-memory {
    ...
    pkvm_guest_firmware {
        compatible = "linux,pkvm-guest-firmware-memory";
        reg = <0x0 0x80000000 0x40000>;
        no-map;
    }
}
```

### 3.2 설정 데이터 (Configuration Data)

- 로더가 **디바이스별 설정 데이터를 pvmfw 바이너리 뒤에 붙여** 같은 보호 영역으로 전달한다. 덕분에 pvmfw 자체는 디바이스 독립적인 중앙 서명 바이너리로 유지된다.
- 설정 데이터는 바이너리 끝 다음 4KiB 경계에서 읽힌다. 헤더 정의: `src/config.rs`.

**포맷 레이아웃** (원문 다이어그램):

```
+===============================+
|          pvmfw.bin            |
+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
|  (Padding to 4KiB alignment)  |
+===============================+ <-- HEAD
|      Magic (= 0x666d7670)     |
+-------------------------------+
|           Version             |
+-------------------------------+
|   Total Size = (TAIL - HEAD)  |
+-------------------------------+
|            Flags              |
+-------------------------------+
|           [Entry 0]           |
|  offset = (FIRST - HEAD)      |
|  size = (FIRST_END - FIRST)   |
+-------------------------------+
|           [Entry 1]           |
|           [Entry 2]           | <-- since version 1.1
|           [Entry 3]           | <-- since version 1.2
|           [Entry 4]           | <-- since version 1.3
|              ...              |
+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~+
| (Padding to 8-byte alignment) |
+===============================+ <-- FIRST
|   {First blob: DICE chain}    |
+===============================+ <-- SECOND
|       {Second blob: DP}       |
+===============================+ <-- THIRD
|     {Third blob: VM DTBO}     |
+===============================+ <-- FOURTH
| {Fourth blob: VM reference DT}|
+===============================+ <-- FIFTH
| {Fifth blob: Reserved Memory} |
+===============================+ <-- TAIL
```

- 버전 인코딩: `((major << 16) | (minor & 0xffff))`. major가 바뀌면 헤더 포맷·블롭 개수가 달라질 수 있다.
- 블롭은 엔트리 배열의 오프셋으로 참조되며, 누락 엔트리는 size 0으로 표기한다(배열 끝을 잘라내는 것은 불허). 헤더는 VM 엔디언을 따른다.

**버전별 엔트리**:

| 버전 | 엔트리 | 내용 | 필수 여부 |
|------|--------|------|-----------|
| 1.0 | entry 0 | DICE chain handover | 필수 |
| 1.0 | entry 1 | pVM DT에 적용할 DTBO (예: debug policy) | 선택 |
| 1.1 | entry 2 | device assignment용 VM DA DTBO — 할당 장치 프로비저닝 | 선택 |
| 1.2 | entry 3 | VM reference DT — VM DT 속성값 일치 검증용 (해석·적용은 안 함) | 선택 |
| 1.3 | entry 4 | 특정 게스트(VM 이름 식별)에 전달할 기밀 가능 데이터 — reserved-memory로 전달 | 선택 |

- entry 3(reference DT)의 사용 사례: Secretkeeper HAL 공개 키를 각 VM에 전달, vendor hashtree digest 전달. 부트로더는 동일 속성·값을 호스트 Android DT의 `/avf/reference` 노드에 추가해야 한다.
- entry 4의 기밀 데이터는 악의적 호스트의 **롤백 공격** 방지를 위해 고정 롤백 보호가 있는 게스트에서만 사용해야 한다. 포맷:

```rust
#[repr(C)]
struct ReservedMemConfigEntry<const N: usize> {
  /// The number of headers contained in this blob.
  count: u32,
  /// The reserved memory headers (src/reserved_mem.rs) describing the passed data.
  headers: [RMemHeader; N],
  /// The actual data being passed. The reserved memory headers point to
  /// offsets within this array.
  data: [u8],
}
```

### 3.3 DICE Chain Handover

- Open Profile for DICE 참조 구현의 `AndroidDiceHandover`(open-dice `src/android.c`)와 호환. CDDL 정의:

```cddl
PvmfwDiceHandover = {
  1 : bstr .size 32,     ; CDI_Attest
  2 : bstr .size 32,     ; CDI_Seal
  3 : DiceCertChain,     ; Android DICE chain
}
```

- CDI(Compound Device Identifiers) 2종은 다음 단계 비밀 파생에, 인증서 체인은 전체 pVM DICE chain 구성(원격 증명에 필요)에 사용된다. 원 사양과 달리 `DiceCertChain` 필드가 **필수**다.
- DICE를 완전 구현하는 디바이스는 pvmfw 로더 이전 부트 스테이지(보통 ABL)에서 UDS 루트 인증서를 제공하고 `DiceAndroidHandoverMainFlow`에 전달한다. 이 단계의 권장 DICE 입력:
  - **Code**: pvmfw 이미지, 하이퍼바이저(`boot.img`), 기타 관련 코드(`vendor_boot.img` 등)의 해시
  - **Configuration Data**: pvmfw 보안 관련 추가 입력
  - **Authority Data**: Code를 서명·검증하는 모든 공개 키 (필수)
  - **Mode**: secure boot가 제대로 강제될 때만 `Normal` (예: AVB 잠금 상태)
  - **Hidden Inputs**: FRS(Factory Reset Secret — 변조 방지 저장소, 공장 초기화마다 변경) 등
- pvmfw는 이 handover에서 **DICE 레이어를 하나 더 파생**하여, `compatible = "google,open-dice"`로 표시된 `/reserved-memory` DT 노드로 게스트에 전달한다.
- 참고: 과거 문서의 BCC(Boot Certificate Chain) 용어는 현재 "DICE Chain / DICE Chain Handover"로 대체되었다.

### 3.4 플랫폼 요구사항

- crosvm protected VM 메모리 레이아웃 가정: 로드 주소 `0x7fc0_0000`, 스크래치 메모리 `0x7fe0_0000`부터 2MiB. 가상 PCI 버스로 virtio 인터페이스, 16550 UART(`0x3f8`)로 로그 출력.
- 부팅 시 하이퍼바이저를 탐지해 메모리 공유/해제, MMIO 표시, 신뢰된 엔트로피 획득, 재부팅 호출을 수행한다. 요구 인터페이스:
  - **Arm SMCCC v1.1+**: `SMCCC_VERSION`, Vendor Specific Hypervisor Service Call UID Query
  - **Arm PSCI v1.0+**: `PSCI_VERSION`, `PSCI_FEATURES`, `PSCI_SYSTEM_RESET`, `PSCI_SYSTEM_SHUTDOWN`
  - **Arm TRNG FW Interface v1.0**: `TRNG_VERSION`, `TRNG_FEATURES`, `TRNG_RND`
  - **pKVM 전용 hypercall** (KVM 하에서):
    - `MEMINFO` (`0xc6000002`), `MEM_SHARE` (`0xc6000003`), `MEM_UNSHARE` (`0xc6000004`)
    - `MMIO_GUARD_INFO` (`0xc6000005`), `MMIO_GUARD_ENROLL` (`0xc6000006`), `MMIO_GUARD_MAP` (`0xc6000007`), `MMIO_GUARD_UNMAP` (`0xc6000008`)

## 4. pVM 부팅

### 4.1 부트 프로토콜

- VMM이 설정하는 초기 레지스터는 Linux arm64 부팅 ABI를 따른다: `x0` = DTB 물리 주소, `x1`/`x2`/`x3` = 0 (예약).
- VMM이 미리 로드한 검증 대상 커널 이미지는 DT(`x0`)로 기술한다:

```dts
/ {
    config {
        kernel-address = <0x80200000>;
        kernel-size = <0x1000000>;
    };
};
```

- 선택적 ramdisk는 표준 `/chosen` 노드로 기술:

```dts
/ {
    chosen {
        linux,initrd-start = <0x82000000>;
        linux,initrd-end = <0x82800000>;
    };
};
```

### 4.2 Handover ABI

- 커널 검증 후 Linux ABI로 부팅하며, DT로 AVF 전용 속성과 DICE chain을 전달한다:

```dts
/ {
    reserved-memory {
        #address-cells = <0x02>;
        #size-cells = <0x02>;
        ranges;
        dice {
            compatible = "google,open-dice";
            no-map;
            reg = <0x0 0x7fe0000>, <0x0 0x1000>;
        };
    };
};
```

### 4.3 게스트 이미지 서명

- **AVB(Android Verified Boot)의 도구·포맷을 재사용**한다. 커널 영역 끝에 appended VBMeta 구조를 기대한다:

```
avbtool add_hash_footer --image <kernel.bin> \
    --partition_name boot \
    --dynamic_partition_size \
    --key $KEY
```

- ramdisk가 필요하면 커널 VBMeta의 hash descriptor로 커버한다(임시 파일로 descriptor만 생성, VMM에는 서명되지 않은 원본 initrd 전달):

```
cp <initrd.bin> /tmp/
avbtool add_hash_footer --image /tmp/<initrd.bin> \
    --partition_name $INITRD_NAME \
    --dynamic_partition_size \
    --key $KEY
avbtool add_hash_footer --image <kernel.bin> \
    --partition_name boot \
    --dynamic_partition_size \
    --include_descriptor_from_image /tmp/<initrd.bin> \
    --key $KEY
```

- `$INITRD_NAME`(`initrd_debug` / `initrd_normal`)으로 디버그 가능 여부를 지정하며, 이는 게스트 인증서와 프로비저닝되는 비밀에 반영된다(디버그/일반 비밀 분리).

**VBMeta 속성**:

| 속성 | 의미 |
|------|------|
| `com.android.virt.cap` | `\|` 구분 capability 목록: `remote_attest`(하드코딩 인덱스 롤백 보호), `secretkeeper_protection`(롤백 보호를 게스트에 위임), `supports_uefi_boot`(EFI payload 부팅, 실험적), `trusty_security_vm`(롤백 보호 생략) |
| `com.android.virt.page_size` | (선택) 게스트 페이지 크기 KiB, 기본 4 |
| `com.android.virt.name` | (선택) VM 이름 — 게스트 DICE 인증서의 `component_name`(기본 `vm_entry`)으로 사용, 특수 VM 식별 |

## 5. 개발/디버깅

- 물리 파티션에 플래시하지 않고 빌드 → `adb push` → 커스텀 pvmfw로 pVM 실행 가능. ABL이 하는 "바이너리 + 설정 데이터" 합성을 파일 하나로 재현하면 된다.
- 테스트 DICE chain(`tests/pvmfw/assets/dice.dat`)을 `pvmfw-tool`로 첨부:

```
m pvmfw-tool pvmfw_bin
PVMFW_BIN=${ANDROID_PRODUCT_OUT}/system/etc/pvmfw.bin
DICE=${ANDROID_BUILD_TOP}/packages/modules/Virtualization/tests/pvmfw/assets/dice.dat

pvmfw-tool custom_pvmfw ${PVMFW_BIN} ${DICE}
```

- 디바이스에서 시스템 속성으로 커스텀 pvmfw 경로 지정 후 실행(`adb root` 필요):

```
adb push custom_pvmfw /data/local/tmp/pvmfw
adb root
adb shell setprop hypervisor.pvmfw.path /data/local/tmp/pvmfw
adb shell /apex/com.android.virt/bin/vm run-microdroid --protected
```

- **pvmfw 없이 pVM 실행** (초기 부트 이슈 디버깅용): `setprop hypervisor.pvmfw.path "none"` 후 동일하게 실행.

**참조 파일/문서 위치** (Virtualization 모듈 기준):

- `guest/pvmfw/src/config.rs` — 설정 데이터 헤더
- `guest/pvmfw/src/reserved_mem.rs` — reserved memory 헤더
- `docs/debug/README.md#debug-policy`, `docs/device_assignment.md`, `docs/device_trees.md`, `docs/pvm_dice_chain.md`, `docs/vm_remote_attestation.md`
- open-dice: `src/android.c`(`AndroidDiceHandover`, `DiceAndroidHandoverMainFlow`)
- `microdroid/Android.bp` — Microdroid 커널 서명(`avb_add_hash_footer` Soong 모듈) 예시

## 6. 본 과제 관점 시사점

- **비밀 프로비저닝의 구조적 해법**: "Host 비신뢰(R-1)" 하에서 pVM에 비밀을 넣는 문제를, AVF는 "하이퍼바이저가 보호하는 최초 실행 코드(pvmfw) + DICE 파생"으로 푼다. DP-A1의 A1-5(Control pVM)가 안았던 부트스트랩 문제("관리 pVM은 누가 검증·기동하는가")에 대한 업계 답이 곧 pvmfw 패턴이다 — `08_DP-A1_ccandidates.md`의 매니페스트 서명 검증 주체 논의와 연결된다.
- **TCB 최소화 설계**: pvmfw 로딩을 하이퍼바이저가 아닌 부트로더에 맡겨 EL2를 작게 유지하는 결정은 CS-02(EL2 수정 불가) 제약과 같은 방향이다.
- **게스트 검증 = AVB 재사용**: Workload 서명 검증(시나리오 3단계)을 새 포맷이 아닌 avbtool/VBMeta 재사용으로 해결한 사례 — 구현 비용 축의 참고점.
- **pKVM hypercall 목록**: 3.4절의 `MEM_SHARE`/`MEM_UNSHARE`/`MMIO_GUARD_*`는 DP-C1(프레임 전달 채널) 후보들이 의존하는 hypercall 의미론(CS-02 범위 확인)의 실제 인터페이스 목록이다.
