# DP-08. 저장 데이터와 키 보호 구조

## 1. 상태

평가 중

## 2. 결정 목적

대용량 데이터의 암복호화 위치를 정한다.
암호화 key의 보관 위치를 정한다.
key 발급과 폐기 책임을 정한다.

## 3. 문제 상황

- 선행 DP: DP-04 Workload identity/measurement, DP-07 TrustZone 연동
- 범위: 일반 REE `TEEC_SharedMemory`에 plaintext를 두지 않는다. Host 비가시 memory share 또는 종단간 암호화 pVM-TEE channel과 measured key release는 target stack의 실현 가능성 gate다.
- 연쇄 gate: DP-04 measurement가 실패하면 key release를 중단한다. DP-07 protected channel이 실패하면 두 후보 모두 중단한다.

AI model과 frame은 Host storage에 저장될 수 있다.
Host storage는 비신뢰 영역이다.
평문 key가 Host에 노출되면 저장 보호가 무너진다.
대용량 frame을 TEE로 매번 보내면 지연이 증가한다.
pVM에서 암호화하면 pVM의 key 노출 면적이 커진다.

## 4. 결정 질문

TEE가 key와 bulk crypto를 모두 처리할 것인가?
아니면 TEE는 key를 관리하고 pVM이 bulk crypto를 처리할 것인가?

## 5. 후보 구조

### 후보 A. Protected Channel 기반 TEE Streaming Crypto 구조

Key는 TEE secure storage에 둔다.
Host 비가시 memory share 또는 종단간 암호화 pVM-TEE channel을 사용한다.
종단간 암호화 proxy를 사용할 때 transport session key는 storage key와 분리한다.
TA가 chunk 단위 streaming AEAD와 key lifecycle을 처리한다.
TA가 protected monotonic state로 manifest version과 key epoch를 대조한다.
일반 REE shared memory에는 plaintext를 두지 않는다.

### 후보 B. Envelope Encryption 구조

TEE는 Key Encryption Key를 보관한다.
pVM은 Data Encryption Key를 받아 bulk crypto를 수행한다.
Host에는 ciphertext와 wrapped key만 저장한다.
wrapped key는 asset ID, manifest version과 key epoch에 결합한다.
TEE는 protected monotonic state보다 오래된 version/epoch를 거부한다.

## 6. 후보별 동작 구조

### 후보 A

```text
pVM data
  -> protected/AEAD pVM-TEE chunk channel
  -> Crypto TA
       -> TEE key
       -> streaming AEAD encrypt/decrypt
  -> ciphertext
  -> Host storage
```

- 실행 위치: key와 crypto operation을 TEE에 둔다.
- 제어 흐름: pVM client가 TA command를 호출한다.
- 데이터 흐름: chunk data가 Host 비가시 memory share 또는 opaque ciphertext envelope로 pVM과 TEE 사이를 이동한다.
- 신뢰 경계: TEE, pVM endpoint와 protected channel을 신뢰한다. plaintext storage key는 TEE만 소유한다.
- 자원 소유권: TA가 key object를 소유한다.
- 자원 회수: TA가 key와 operation handle을 폐기한다.

### 후보 B

```text
TEE
  -> measured pVM identity 확인
  -> protected pVM-TEE channel로 Data Encryption Key 발급 또는 unwrap
  -> protected pVM memory
       -> bulk encrypt/decrypt
       -> 정상 종료 시 key zeroization
  -> ciphertext + wrapped key
  -> Host storage
```

- 실행 위치: key root는 TEE에 둔다.
- 실행 위치: bulk crypto는 pVM에 둔다.
- 제어 흐름: pVM identity와 policy에 따라 key를 발급한다.
- 데이터 흐름: bulk plaintext는 TEE로 이동하지 않는다.
- 신뢰 경계: TEE와 승인된 pVM이 key 경계에 포함된다.
- 자원 소유권: TEE는 KEK를 소유한다.
- 자원 소유권: pVM은 session DEK를 임시 소유한다.
- 자원 회수: 정상 종료에서는 DEK를 zeroize하고, crash에서는 DP-03의 pVM memory 회수/소거로 잔류를 차단한다.

## 7. 품질속성 비교

### 7.1 필수 gate

| Gate | 합격 기준 | 후보 A | 후보 B |
|---|---|---|---|
| SEC-05 저장 기밀성 | Host filesystem/memory에서 plaintext와 storage key 노출 0건 | protected channel 확인 필요 | protected DEK 전달 확인 필요 |
| Key release identity | 미승인/rollback Workload에 key 발급 0건 | DP-04 measurement binding 필요 | DP-04 measurement binding 필요 |
| Replay/rollback | old manifest/key epoch와 ciphertext replay 수락 0건 | protected monotonic state 필요 | wrapped key version/epoch 필요 |
| 실행 중 철회 | key 폐기 뒤 기존 instance의 평문 접근이 승인 시간 안에 종료됨 | session/TA handle 철회 필요 | pVM 종료와 channel 철회 필요 |

두 후보 모두 DP-07이 Host 비노출 buffer 또는 동등한 종단간 보호 경로를 제공해야 한다.
단순 Host proxy가 plaintext/key를 relay하면 gate 실패다.

### 7.2 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.
SEC-05의 노출 0건은 별점이 아니라 위 필수 gate다.
crypto latency 임계값은 PERF-03 E2E p99 100ms의 저장/복호화 구간 예산이 승인되기 전까지 PoC 작업값이다.

| 품질속성 | KPI | 별 1개 | 별 2개 | 별 3개 |
|---|---|---|---|---|
| 보안성 | plaintext storage DEK/KEK가 존재하는 protection domain 수 | 3개 이상 | 2개 | 1개 |
| 성능 | 1080p frame crypto 지연 p99 | 10ms 초과 | 5ms 초과 10ms 이하 | 5ms 이하 |
| 확장성 | 신규 보호 자산 유형 추가 시 storage core 변경량 | 100 LoC 초과 | 1~100 LoC | 0 LoC |
| 변경 용이성 | crypto algorithm 교체 시 수정 module 수 | 4개 이상 | 2~3개 | 1개 이하 |
| 자원 효율 | bulk data의 protection-domain 간 복사 횟수 | 2회 이상 | 1회 | 0회 |

NIST SP 800-57은 key material의 기밀성과 무결성 보호를 요구한다.
불필요한 key는 가능한 빨리 폐기하도록 권고한다.
Key domain 수와 zeroization KPI의 근거다.
[NIST SP 800-57 Part 1](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final)

OP-TEE secure storage는 GlobalPlatform Trusted Storage를 구현한다.
REE filesystem과 RPMB backend를 지원한다.
TEE key 보관 후보의 근거다.
[OP-TEE Secure Storage](https://optee.readthedocs.io/en/latest/architecture/secure_storage.html)

OP-TEE의 일반 Client API shared memory는 non-secure world가 관리한다.
따라서 후보 A에는 Host 비가시 memory share 또는 종단간 암호화 channel이 필요하다.
[OP-TEE Shared Memory](https://optee.readthedocs.io/en/latest/architecture/core.html)

### 7.3 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | ★★★ | plaintext storage key가 TEE 밖으로 나오지 않는다. | ★★ | session DEK가 pVM memory에 존재한다. |
| 성능 | ★ | protected chunk 전달과 world switch가 반복된다. | ★★★ | bulk crypto를 pVM memory에서 수행한다. |
| 확장성 | ★★ | TA command와 secure storage schema가 늘어난다. | ★★★ | 공통 envelope format으로 자산을 추가할 수 있다. |
| 변경 용이성 | ★★ | TA와 client를 함께 변경할 수 있다. | ★★ | pVM crypto와 wrapping 정책을 함께 변경할 수 있다. |
| 자원 효율 | ★★ | chunk window로 peak memory를 제한하지만 protected buffer와 TA 시간이 필요하다. | ★★★ | bulk data의 domain 간 이동을 줄인다. |

## 8. 핵심 트레이드오프

후보 A는 storage key를 TEE에만 두고 protected chunk channel에서 crypto를 수행한다.
대신 protected memory share 또는 transport crypto와 world switch/TEE 실행 시간이 증가한다.

후보 B는 bulk crypto 지연과 copy를 줄인다.
대신 pVM이 session key의 신뢰 경계에 포함된다.

## 9. 검증 기준

- model, frame과 result를 각각 암복호화한다.
- 1080p frame crypto 지연 p50, p95와 p99를 측정한다.
- command당 world switch와 copy 횟수를 측정한다.
- Host memory와 storage에서 plaintext marker를 검색한다.
- pVM memory에서 key 잔류 시간을 측정한다.
- pVM crash 후 key material을 검색한다.
- key rotation과 old key 거부를 시험한다.
- wrapped key 변조와 ciphertext replay를 시험한다.
- 저장 실패 후 partial object 정리를 확인한다.
- Host가 protected memory share를 mapping하거나, opaque proxy의 transport encryption을 끄고 plaintext를 ordinary REE shared memory로 보내려는 시도를 차단한다.
- chunk별 nonce/AAD/tag와 manifest hash, asset ID, key epoch의 결합을 변조 시험한다.
- TEE monotonic counter보다 오래된 manifest/key epoch와 snapshot을 replay한다.
- 실행 중 key 폐기 시 channel revoke, pVM 강제 종료와 memory 소거까지의 시간 경계를 측정한다.
- per-device/per-fleet key scope, rotation 중 dual-key 기간과 old key 폐기 절차를 기록한다.

## 10. 검토 결과

사용자 요청에 따라 Claude와 교차 검토했다.
후보 A의 일반 REE plaintext 경로를 Host 비가시 memory share 또는 종단간 암호화 protected channel로 교체했다.
후보 B의 DEK 전달, measured identity, anti-rollback과 실행 중 철회 gate를 명시했다.
DP-04/07 선행 gate와 key scope/rotation 정책 확인이 남아 있다.

## 11. 최종 결정
