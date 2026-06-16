# 요구사항 분석

## 과제명: Linux pKVM 기반 가상화 보안 플랫폼 개발

---

## 1. Stakeholder 목록 및 관심사

| ID | Actor | 주요 관심사 |
|----|-------|-------------|
| A1 | Legacy CA/TA 앱 개발자 | 기존 GP API 기반 TA/CA 자산을 코드 수정 없이 신규 플랫폼에서 동작시키는 것 |
| A2 | 보안 시나리오 앱 개발자 | pVM 생명주기 제어, Host-pVM 통신, HW IP 접근, 보안 워크로드 격리 개발 편의성 |
| A3 | 검증팀 | 메모리 격리·장애 격리·성능 목표 수치의 객관적 측정 및 증거 확보 |

## 2. Use Case 목록

| UC ID | 이름 | 액터 | 설명 |
|-------|------|------|------|
| UC-01 | GP API를 통한 Host-TEE간 통신 | A1 | CA 앱이 GP Client API를 통해 Host OS에서 Secure OS(TEE)로 통신 |
| UC-02 | pVM 생성/실행/중단/삭제 | A2 | pVM Framework API로 pVM의 전체 생명주기를 관리 |
| UC-03 | pVM 상태 변경 확인 | A2 | 실행 중인 pVM의 상태(실행·중단·오류 등)를 조회 |
| UC-04 | pVM으로 RPC 통신 | A2 | Host OS 앱에서 pVM 내부 서비스를 RPC로 호출 |
| UC-05 | Payload, Memory, CPU 정보 설정 | A2 | pVM 생성 시 워크로드 Payload, 메모리 크기, vCPU 수를 설정 |
| UC-06 | pVM으로 보안 File System 마운트 | A2 | Host OS에서 pVM으로 보안 파일 시스템을 마운트하여 격리된 저장소 제공 |
| UC-07 | pVM내 HW IP 사용 | A2 | pVM 내 워크로드가 카메라·NPU 등 HW IP에 직접 접근 |
| UC-08 | Host으로 RPC 통신 | A2 | pVM 내부 서비스가 Host OS 앱으로 RPC 응답을 전달 |
| UC-09 | GP API를 통한 pVM-TEE간 통신 | A2 | pVM 내 앱이 GP Client API를 통해 Secure OS(TEE)와 통신 |
| UC-10 | 메모리 격리 검증 | A3 | Stage-2 Page Table 기반으로 Host OS가 pVM 메모리에 접근 불가함을 검증 |
| UC-11 | pVM 장애 격리 검증 | A3 | 단일 pVM 장애 발생 시 Host OS 및 타 pVM이 무중단 유지됨을 검증 |
| UC-12 | 성능 벤치마크 측정 | A3 | 네이티브 Linux 대비 CPU·메모리·I/O·부팅 시간 오버헤드 측정 |

---

## 3. 기능 요구사항 (Functional Requirements)

| ID | 요구사항 | 관련 UC | 관련 Actor |
|----|----------|---------|------------|
| FR-01 | 시스템은 pVM Framework API를 통해 pVM을 생성·실행·중단·삭제하는 생명주기 관리 기능을 제공해야 한다 | UC-02 | A2 |
| FR-02 | 시스템은 실행 중인 pVM의 상태(실행·중단·오류·종료)를 조회하는 기능을 제공해야 한다 | UC-03 | A2 |
| FR-03 | 시스템은 pVM 생성 시 Payload 경로, 메모리 크기, vCPU 수를 설정하는 기능을 제공해야 한다 | UC-05 | A2 |
| FR-04 | 시스템은 Host OS 앱에서 pVM 내부 서비스를 RPC로 호출하는 통신 채널을 제공해야 한다 | UC-04 | A2 |
| FR-05 | 시스템은 pVM 내부 서비스가 Host OS 앱으로 RPC 응답을 전달하는 통신 채널을 제공해야 한다 | UC-08 | A2 |
| FR-06 | 시스템은 Host OS에서 pVM으로 보안 파일 시스템을 마운트하여 격리된 저장소를 제공해야 한다 | UC-06 | A2 |
| FR-07 | 시스템은 pVM 내 워크로드가 HW IP(카메라·NPU 등)에 직접 접근할 수 있어야 하며, Host OS 및 타 pVM의 해당 HW IP 접근을 차단해야 한다 | UC-07 | A2 |
| FR-08 | 시스템은 Host OS에서 기존 GP Client API를 코드 수정 없이 그대로 사용하여 Secure OS(TEE)와 통신하는 기능을 제공해야 한다 | UC-01 | A1 |
| FR-09 | 시스템은 pVM 내 앱이 GP Client API를 통해 Secure OS(TEE)와 통신하는 기능을 제공해야 한다 | UC-09 | A2 |
| FR-10 | 시스템은 Framework 코드 수정 없이 신규 보안 워크로드 pVM을 추가·배포할 수 있는 확장 구조를 제공해야 한다 | UC-02 | A2 |

---

## 4. 품질 속성 (Quality Attributes)

### 4.1 성능 (Performance)

| ID | 요구사항 | 목표 수치 | 비교 기준 | 관련 UC | 출처 |
|----|----------|----------|----------|---------|------|
| QA-P-01 | CPU/메모리 집약 워크로드 실행 오버헤드 | 네이티브 Linux 대비 **5% 이내** | Android AVF 동등 | UC-12 | ACM SAC 2024 |
| QA-P-02 | I/O 집약 워크로드 실행 오버헤드 | 네이티브 Linux 대비 **10% 이내** | Android AVF 대비 우세 | UC-12 | ACM SAC 2024 |
| QA-P-03 | pVM 부팅 시간 | **1초 이내** | Android AVF 대비 우세 | UC-12 | Android Blog 2022 |
| QA-P-04 | Host-pVM RPC 레이턴시 | **100μs 이내** | Android AVF 동등 | UC-04, UC-08, UC-12 | Linux vsock IPC 기준 |

### 4.2 가용성 (Availability)

| ID | 요구사항 | 목표 | 관련 UC |
|----|----------|------|---------|
| QA-A-01 | pVM 단일 장애 시 Host OS 무중단 유지 | 장애 전파 없음 | UC-11 |
| QA-A-02 | pVM 단일 장애 시 타 pVM 무중단 유지 | 장애 전파 없음 | UC-11 |

### 4.3 보안 (Security)

| ID | 요구사항 | 목표 | 관련 UC |
|----|----------|------|---------|
| QA-S-01 | Host OS의 pVM 메모리 영역 직접 접근 차단 | Stage-2 Page Table 기반 완전 차단 | UC-10 |
| QA-S-02 | pVM 간 메모리 영역 상호 접근 차단 | Stage-2 Page Table 기반 완전 차단 | UC-10 |
| QA-S-03 | Host OS 침해 시에도 EL2 신뢰 경계 및 pVM 메모리 격리 유지 | nVHE 구조적 보장 | UC-10 |

### 4.4 변경 용이성 (Modifiability)

| ID | 요구사항 | 목표 | 관련 UC |
|----|----------|------|---------|
| QA-M-01 | 신규 보안 시나리오(pVM) 추가 시 Framework 핵심 코드 무수정 | Android AVF 대비 우세 | UC-02 |
| QA-M-02 | Linux 종속성 유지로 Android 생태계 비종속 | 독자적 확장 가능 | — |

---

## 5. 제약사항 (Constraints)

| ID | 제약사항 |
|----|----------|
| CON-01 | 대상 아키텍처는 ARM Cortex-A이며, EL2 nVHE 모드를 지원해야 한다 (ARMv8.0 이상) |
| CON-02 | Hypervisor는 ARM EL2 nVHE(Non-VHE) 모드에서만 동작한다. Host OS는 EL1에서 실행된다 |
| CON-03 | Host OS는 Linux Kernel 기반이어야 한다 (Android 제외) |
| CON-04 | 가상화 기반은 pKVM(protected KVM)이어야 한다 |
| CON-05 | Android AVF 코드의 직접 포팅이 아닌, Linux에 최적화된 독자 Framework를 설계·구현한다 |
| CON-06 | EL2 pKVM 도입 이후에도 REE↔TEE 간 SMC 경로(S-EL3 Secure Monitor 경유)가 기존과 동일하게 동작해야 한다 |
| CON-07 | 기존 TA/CA 바이너리 또는 소스 코드를 최소 수정으로 신규 플랫폼에서 동작시킬 수 있어야 한다 |

---

## 6. 품질 속성 × UC 추적 매트릭스

| 품질 속성 | UC-01 | UC-02 | UC-03 | UC-04 | UC-05 | UC-06 | UC-07 | UC-08 | UC-09 | UC-10 | UC-11 | UC-12 |
|----------|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|
| QA-P-01 CPU/메모리 오버헤드 5% | O | O | O | | O | | | | O | | | O |
| QA-P-02 I/O 오버헤드 10% | O | | O | | | O | O | | O | | | O |
| QA-P-03 pVM 부팅 1초 | | O | | | | | | | | | | O |
| QA-P-04 RPC 레이턴시 100μs | | | | O | | | | O | | | | O |
| QA-A-01 Host OS 무중단 | | O | | | | | | | | | O | |
| QA-A-02 타 pVM 무중단 | | O | | | | | | | | | O | |
| QA-S-01 Host→pVM 메모리 차단 | | O | | | | | | | | O | | |
| QA-S-02 pVM간 메모리 차단 | | O | | | | | | | | O | | |
| QA-S-03 EL2 신뢰 경계 유지 | | O | | | | | | | | O | | |
| QA-M-01 Framework 무수정 확장 | | O | | | O | | | | | | | |
| QA-M-02 Linux 비종속 | | O | | | | | | | | | | |
