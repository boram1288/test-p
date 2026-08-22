# DP-08. 저장 데이터와 키 보호 구조

## 1. 상태

도출

## 2. 결정 목적

대용량 데이터의 암복호화 위치를 정한다.
암호화 key의 보관 위치를 정한다.
key 발급과 폐기 책임을 정한다.

## 3. 문제 상황

AI model과 frame은 Host storage에 저장될 수 있다.
Host storage는 비신뢰 영역이다.
평문 key가 Host에 노출되면 저장 보호가 무너진다.
대용량 frame을 TEE로 매번 보내면 지연이 증가한다.
pVM에서 암호화하면 pVM의 key 노출 면적이 커진다.

## 4. 결정 질문

TEE가 key와 bulk crypto를 모두 처리할 것인가?
아니면 TEE는 key를 관리하고 pVM이 bulk crypto를 처리할 것인가?

## 5. 후보 구조

### 후보 A. TEE 집중 암호화 구조

Key는 TEE secure storage에 둔다.
평문 data를 TEE shared memory로 전달한다.
TA가 암복호화와 key lifecycle을 처리한다.

### 후보 B. Envelope Encryption 구조

TEE는 Key Encryption Key를 보관한다.
pVM은 Data Encryption Key를 받아 bulk crypto를 수행한다.
Host에는 ciphertext와 wrapped key만 저장한다.

## 6. 후보별 동작 구조

### 후보 A

```text
pVM data
  -> TEE shared memory
  -> Crypto TA
       -> TEE key
       -> encrypt/decrypt
  -> ciphertext
  -> Host storage
```

- 실행 위치: key와 crypto operation을 TEE에 둔다.
- 제어 흐름: pVM client가 TA command를 호출한다.
- 데이터 흐름: bulk data가 pVM과 TEE 사이를 이동한다.
- 신뢰 경계: TEE만 plaintext key를 소유한다.
- 자원 소유권: TA가 key object를 소유한다.
- 자원 회수: TA가 key와 operation handle을 폐기한다.

### 후보 B

```text
TEE
  -> Data Encryption Key 발급 또는 unwrap
  -> protected pVM memory
       -> bulk encrypt/decrypt
       -> key zeroization
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
- 자원 회수: pVM 종료 전 DEK를 zeroize한다.

## 7. 품질속성 비교

### 7.1 KPI와 별점 기준

별점은 구조 예상치다.
실측 전에는 확정하지 않는다.

| 품질속성 | KPI | 별 1개 | 별 2개 | 별 3개 |
|---|---|---|---|---|
| 보안성 | plaintext key가 존재하는 protection domain 수 | 3개 이상 | 2개 | 1개 |
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

OP-TEE는 `TEEC_AllocateSharedMemory()`를 zero-copy에 적합한 방식으로 설명한다.
등록 실패 시 shadow buffer가 생길 수 있다.
Bulk data copy KPI의 근거다.
[OP-TEE GlobalPlatform API](https://optee.readthedocs.io/en/4.9.0/architecture/globalplatform_api.html)

### 7.2 후보 평가

| 품질속성 | 후보 A | 근거 | 후보 B | 근거 |
|---|---:|---|---:|---|
| 보안성 | ★★★ | plaintext key가 TEE 밖으로 나오지 않는다. | ★★ | session DEK가 pVM memory에 존재한다. |
| 성능 | ★ | bulk data 이동과 world switch가 반복된다. | ★★★ | bulk crypto를 pVM memory에서 수행한다. |
| 확장성 | ★★ | TA command와 secure storage schema가 늘어난다. | ★★★ | 공통 envelope format으로 자산을 추가할 수 있다. |
| 변경 용이성 | ★★ | TA와 client를 함께 변경할 수 있다. | ★★ | pVM crypto와 wrapping 정책을 함께 변경할 수 있다. |
| 자원 효율 | ★ | TEE shared memory와 shadow buffer가 필요할 수 있다. | ★★★ | bulk data의 domain 간 이동을 줄인다. |

## 8. 핵심 트레이드오프

후보 A는 plaintext key의 domain을 TEE 하나로 제한한다.
대신 bulk data 이동과 TEE 실행 시간이 증가한다.

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

## 10. 검토 결과

검토 전이다.

## 11. 최종 결정

