# 품질 시나리오 명세

---

## QS-001: CPU/메모리 집약 워크로드 실행 오버헤드

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-001 |
| 품질 속성 | 성능 (Performance) |
| 관련 요구사항 | QA-P-01 |
| 관련 UC | UC-12 |

### 환경

**시스템 상태**: pKVM 하이퍼바이저가 EL2 nVHE 모드에서 실행 중이며 pVM이 생성·실행 상태

**초기 조건**
- Host OS가 EL1에서 정상 실행 중
- pVM이 생성되어 실행 상태
- CPU/메모리 집약 벤치마크 도구(예: sysbench) 준비 완료

**부하 조건**: CPU 연산 및 메모리 대역폭을 집중적으로 사용하는 워크로드 실행

**관련 컴포넌트**
- pKVM Hypervisor (EL2)
- Guest VM (EL1)
- Host Linux Kernel (EL1)

### 동작

1. 벤치마크 도구가 네이티브 Linux 환경에서 CPU/메모리 집약 워크로드를 실행하여 기준값(Baseline) 측정
2. 동일 워크로드를 pVM 내부에서 실행
3. 두 환경에서 실행 결과 수집 및 비교

### 측정

- **측정 항목**: pVM 환경의 CPU/메모리 워크로드 실행 오버헤드 (%)

```
오버헤드(%) = (pVM 실행 시간 - 네이티브 실행 시간) / 네이티브 실행 시간 × 100
```

---

## QS-002: I/O 집약 워크로드 실행 오버헤드

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-002 |
| 품질 속성 | 성능 (Performance) |
| 관련 요구사항 | QA-P-02 |
| 관련 UC | UC-12 |

### 환경

**시스템 상태**: pKVM 하이퍼바이저 실행 중, VirtIO 블록/네트워크 드라이버 초기화 완료

**초기 조건**
- pVM이 실행 상태, 파일시스템 마운트 완료
- I/O 집약 벤치마크 도구(예: fio, iperf) 준비 완료

**부하 조건**: 디스크 I/O 또는 네트워크 I/O를 집중적으로 사용하는 워크로드 실행

**관련 컴포넌트**
- pKVM Hypervisor (EL2)
- VirtIO 블록/네트워크 드라이버
- Host 블록/네트워크 드라이버

### 동작

1. 벤치마크 도구가 네이티브 Linux 환경에서 I/O 워크로드를 실행하여 기준값 측정
2. 동일 워크로드를 pVM 내부에서 실행
3. 두 환경의 I/O 처리량 및 레이턴시 수집

### 측정

- **측정 항목**: pVM 환경의 I/O 워크로드 실행 오버헤드 (%)

```
오버헤드(%) = (pVM I/O 처리 시간 - 네이티브 I/O 처리 시간) / 네이티브 I/O 처리 시간 × 100
```

---

## QS-003: pVM 부팅 시간

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-003 |
| 품질 속성 | 성능 (Performance) |
| 관련 요구사항 | QA-P-03 |
| 관련 UC | UC-02, UC-12 |

### 환경

**시스템 상태**: pKVM 하이퍼바이저 실행 중, Host OS 정상 가동 중

**초기 조건**
- pVM Payload(커널 이미지) 준비 완료
- 메모리 크기 및 vCPU 수 설정 완료

**부하 조건**: Host OS 일반 운영 부하

**관련 컴포넌트**
- pVM Framework API
- pKVM Hypervisor (EL2)
- Guest Linux Kernel

### 동작

1. pVM Framework API를 통해 pVM 생성 요청 (Payload, 메모리 크기, vCPU 수 지정)
2. pKVM이 Guest VM을 초기화하고 커널 부팅 시작
3. Guest 커널 부팅 완료 및 사용자 공간(init 프로세스) 준비 완료

### 측정

- **측정 항목**: pVM 부팅 완료 시간 (ms)

```
부팅 시간(ms) = 사용자 공간 준비 완료 시각 - pVM 생성 API 호출 시각
```

---

## QS-004: Host-pVM RPC 레이턴시

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-004 |
| 품질 속성 | 성능 (Performance) |
| 관련 요구사항 | QA-P-04 |
| 관련 UC | UC-04, UC-08, UC-12 |

### 환경

**시스템 상태**: Host OS와 pVM이 모두 실행 중, RPC 통신 채널(vsock 등) 설정 완료

**초기 조건**
- pVM 내부 RPC 서버가 대기 상태
- Host OS 앱이 실행 중

**부하 조건**: Host OS 일반 운영 부하

**관련 컴포넌트**
- Host OS 앱
- pVM Framework RPC 채널 (vsock 기반)
- pVM 내부 RPC 서버

### 동작

1. Host OS 앱이 pVM 내부 서비스로 RPC 요청 전송
2. pVM 내부 서비스가 요청을 수신하여 처리
3. pVM 내부 서비스가 Host OS 앱으로 RPC 응답 반환
4. Host OS 앱이 응답 수신

### 측정

- **측정 항목**: Host-pVM RPC 왕복 레이턴시 (μs)

```
레이턴시(μs) = RPC 응답 수신 시각 - RPC 요청 전송 시각
```

---

## QS-005: pVM 단일 장애 시 Host OS 무중단 유지

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-005 |
| 품질 속성 | 가용성 (Availability) |
| 관련 요구사항 | QA-A-01 |
| 관련 UC | UC-11 |

### 환경

**시스템 상태**: Host OS와 1개 이상의 pVM이 정상 실행 중

**초기 조건**
- Host OS에서 서비스 정상 운영 중
- pVM이 정상 실행 중

**부하 조건**: Host OS 일반 운영 부하

**관련 컴포넌트**
- pKVM Hypervisor (EL2)
- 장애 발생 pVM
- Host Linux OS

### 동작

1. 실행 중인 pVM에 크래시(커널 패닉, OOM 등) 강제 발생
2. pKVM이 장애 pVM을 격리 처리
3. Host OS 서비스 응답 지속 여부 확인

### 측정

- **측정 항목**: pVM 장애 발생 전후 Host OS 서비스 응답 성공률 (%)

```
Host OS 서비스 응답 성공률(%) = 장애 후 응답 성공 횟수 / 장애 후 요청 횟수 × 100
```

---

## QS-006: pVM 단일 장애 시 타 pVM 무중단 유지

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-006 |
| 품질 속성 | 가용성 (Availability) |
| 관련 요구사항 | QA-A-02 |
| 관련 UC | UC-11 |

### 환경

**시스템 상태**: 2개 이상의 pVM이 동시에 실행 중

**초기 조건**
- 모든 pVM에서 서비스 정상 운영 중

**부하 조건**: 각 pVM 일반 운영 부하

**관련 컴포넌트**
- pKVM Hypervisor (EL2)
- 장애 발생 pVM
- 나머지 pVM

### 동작

1. 실행 중인 pVM 중 하나에 크래시 강제 발생
2. pKVM이 장애 pVM을 격리 처리
3. 나머지 pVM의 서비스 응답 지속 여부 확인

### 측정

- **측정 항목**: pVM 장애 발생 전후 타 pVM 서비스 응답 성공률 (%)

```
타 pVM 서비스 응답 성공률(%) = 장애 후 타 pVM 응답 성공 횟수 / 장애 후 타 pVM 요청 횟수 × 100
```

---

## QS-007: Host OS의 pVM 메모리 영역 직접 접근 차단

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-007 |
| 품질 속성 | 보안 (Security) |
| 관련 요구사항 | QA-S-01 |
| 관련 UC | UC-10 |

### 환경

**시스템 상태**: pKVM이 Stage-2 Page Table 설정 완료, pVM 실행 중

**초기 조건**
- Host OS가 EL1에서 실행 중
- pVM 전용 물리 메모리 영역 할당 및 Stage-2 매핑 완료

**부하 조건**: 없음

**관련 컴포넌트**
- pKVM Hypervisor (EL2)
- Stage-2 Page Table
- Host Linux Kernel (EL1)

### 동작

1. Host OS(EL1)가 pVM 전용 물리 메모리 주소에 직접 read/write 접근 시도
2. Stage-2 Page Table이 해당 접근을 인터셉트
3. 접근 허용 또는 차단 결과 확인

### 측정

- **측정 항목**: Host OS의 pVM 메모리 접근 차단 비율 (%)

```
차단 비율(%) = 차단된 접근 횟수 / 전체 접근 시도 횟수 × 100
```

---

## QS-008: pVM 간 메모리 영역 상호 접근 차단

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-008 |
| 품질 속성 | 보안 (Security) |
| 관련 요구사항 | QA-S-02 |
| 관련 UC | UC-10 |

### 환경

**시스템 상태**: 2개 이상의 pVM이 각자 전용 물리 메모리 영역을 보유하고 실행 중

**초기 조건**
- 각 pVM의 Stage-2 Page Table 설정 완료
- 각 pVM의 물리 메모리 영역이 상호 분리되어 있음

**부하 조건**: 없음

**관련 컴포넌트**
- pKVM Hypervisor (EL2)
- Stage-2 Page Table
- 복수 Guest VM (EL1)

### 동작

1. pVM-A가 pVM-B의 전용 물리 메모리 주소에 read/write 접근 시도
2. Stage-2 Page Table이 해당 접근을 인터셉트
3. 접근 허용 또는 차단 결과 확인

### 측정

- **측정 항목**: pVM 간 메모리 접근 차단 비율 (%)

```
차단 비율(%) = 차단된 접근 횟수 / 전체 접근 시도 횟수 × 100
```

---

## QS-009: Host OS 침해 시 EL2 신뢰 경계 및 pVM 메모리 격리 유지

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-009 |
| 품질 속성 | 보안 (Security) |
| 관련 요구사항 | QA-S-03 |
| 관련 UC | UC-10 |

### 환경

**시스템 상태**: pKVM nVHE 모드 실행 중, pVM 실행 중

**초기 조건**
- Host OS(EL1)가 공격자에 의해 완전히 장악된 상태로 가정 (루트 권한 탈취 포함)
- pVM이 정상 실행 중

**부하 조건**: 없음

**관련 컴포넌트**
- pKVM Hypervisor (EL2)
- Stage-2 Page Table
- Host Linux Kernel (EL1)

### 동작

1. 침해된 Host OS가 EL2 신뢰 경계 우회를 시도 (예: 악성 Hypercall, EL1→EL2 권한 상승 시도)
2. nVHE 구조가 EL1→EL2 비인가 접근을 차단
3. Stage-2 Page Table이 pVM 메모리 접근 시도를 차단
4. EL2 신뢰 경계 및 pVM 메모리 격리 상태 확인

### 측정

- **측정 항목 1**: EL2 신뢰 경계 침해 성공 횟수
- **측정 항목 2**: pVM 메모리 유출 발생 여부 (이진값: 발생 / 미발생)

```
EL2 침해 성공률(%) = EL2 침해 성공 횟수 / EL2 침해 시도 횟수 × 100
pVM 메모리 유출 여부 = 침해 시도 후 pVM 전용 메모리 데이터 외부 노출 발생 여부
```

---

## QS-010: Framework 무수정 신규 보안 시나리오 확장

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-010 |
| 품질 속성 | 변경 용이성 (Modifiability) |
| 관련 요구사항 | QA-M-01 |
| 관련 UC | UC-02, UC-05 |

### 환경

**시스템 상태**: 기존 pVM Framework 및 1개 이상의 보안 시나리오 pVM 실행 중

**초기 조건**
- Framework 핵심 코드베이스 고정 상태
- 기존 보안 시나리오 pVM(예: Secure Camera) 정상 운영 중

**부하 조건**: 없음

**관련 컴포넌트**
- pVM Framework API
- pVM 생명주기 관리 모듈
- 신규 pVM Payload

### 동작

1. 신규 보안 시나리오(예: Secure AI) pVM 추가 요청
2. Framework 핵심 코드 수정 없이 신규 pVM Payload 및 설정만으로 배포 시도
3. 신규 pVM 정상 실행 및 기존 pVM 영향 여부 확인

### 측정

- **측정 항목**: 신규 pVM 추가를 위해 수정된 Framework 핵심 코드 규모

```
수정 코드 라인 수(LOC) = 신규 pVM 추가를 위해 변경된 Framework 핵심 모듈의 코드 라인 수
수정 파일 수 = 신규 pVM 추가를 위해 변경된 Framework 핵심 모듈 파일 수
```

---

## QS-011: Linux 비종속 독자 확장

### 개요

| 항목 | 내용 |
|------|------|
| ID | QS-011 |
| 품질 속성 | 변경 용이성 (Modifiability) |
| 관련 요구사항 | QA-M-02 |
| 관련 UC | — |

### 환경

**시스템 상태**: Android 없이 Linux 기반 Host OS에서 pVM Framework 실행 중

**초기 조건**
- Android AVF 미설치, 순수 Linux 커널 기반 환경
- pVM Framework 빌드 완료

**부하 조건**: 없음

**관련 컴포넌트**
- pVM Framework
- Host Linux Kernel (EL1)
- pKVM Hypervisor (EL2)

### 동작

1. Android 생태계 없이 Linux 환경에서 pVM 생성·실행 요청
2. pVM Framework가 Android 종속 없이 빌드 및 동작
3. pVM 정상 실행 확인

### 측정

- **측정 항목**: Framework 코드베이스 내 Android 종속 컴포넌트 수

```
Android 종속 수 = Framework 빌드 시 Android API / 라이브러리 의존성 항목 수
```
