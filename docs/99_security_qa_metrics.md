# 보안 QA 정량 측정 방법 조사

> 본 문서는 `02_requirements.md`의 보안 관련 QA(QA-01 기밀성, QA-02 도메인 간 격리, QA-03 DMA 경로 격리, QA-10 시험 용이성)에 대해, 품질 달성 여부를 숫자로 측정하거나 공인 등급으로 판정할 수 있는 방법을 논문/신뢰 가능한 출처에서 조사한 결과를 기록한다.
> 조사 일자: 2026-07-02

---

## 1. 조사 배경

보안 요구사항은 "노출되지 않는다"와 같이 부정형(negative)으로 기술되어 직접 측정이 어렵다. 그러나 Hypervisor/TEE 격리 분야에서는 아래와 같이 정량화된 검증 체계가 확립되어 있으며, 특히 본 과제와 동일한 기술 기반인 pKVM이 이미 이 체계로 인증을 획득한 선례가 있다.

---

## 2. QA별 정량 측정 방법

### 2.1 QA-01 보안 (기밀성: Host 침해 시 데이터 비노출)

#### (1) 형식 검증 (Formal Verification) — 증명 커버리지로 측정

- **측정치**: 기계 검증(machine-checked proof)이 커버하는 코드 라인 수 / 전체 TCB 라인 수 (%)
- Google은 pKVM에 대해 "Hypervisor의 격리 속성을 형식적으로 검증"하는 접근을 사용 중임을 Android 공식 문서에 명시.
- 학술 선례:
  - **SeKVM** (Columbia, IEEE S&P 2021): KVM 핵심 3.8K LOC에 대해 VM 기밀성/무결성을 기계 검증.
  - **seL4 비간섭 증명** (IEEE S&P 2013): 실제 C 코드 8,830라인 전체에 대한 정보흐름 보안의 기계 검증 최초 사례. 증명 커버리지 100%라는 명시적 수치 제시.

#### (2) SESIP / Common Criteria 인증 등급 — 공인 서수 척도

- **측정치**: SESIP Level 1~5, CC AVA_VAN.1~5 등급
- **pKVM은 2025년 8월 SESIP Level 5 인증 획득** (평가기관 Dekra, TrustCB 스킴, EN-17927 준거). 소비자 기기 대상 대규모 배포 SW 최초.
- SESIP Level 5는 ISO/IEC 15408(Common Criteria)의 최고 취약성 분석 등급인 **AVA_VAN.5**(고숙련/충분한 자금/내부자 지식을 가진 공격자에 대한 저항)를 포함.
- CC AVA_VAN은 공격 잠재력(attack potential)을 시간/전문성/장비/접근성 점수표로 수치화하여 등급(Basic / Enhanced-Basic / Moderate / High / Beyond-High)을 판정.
- 본 과제가 pKVM 기반이므로 동일 인증 체계를 목표 지표로 삼을 수 있음.

#### (3) 정량적 정보흐름 (QIF) — 누출량을 비트(bit)로 측정

- **측정치**: min-entropy leakage (bit). 누출 0 bit = 완전 기밀성.
- Smith의 min-entropy leakage 이론: "공격자가 한 번의 시도로 비밀을 맞힐 취약도(vulnerability)"를 기반으로 누출을 비트 단위로 계산. 단일 추측 공격 모델에서 Shannon 상호정보량보다 적합하다는 것이 학계 정설.

### 2.2 QA-02 보안 (도메인 간 격리)

#### (1) 비간섭(Noninterference) 증명

- **측정치**: 증명 통과 여부(이진 판정) + 증명 범위(LOC)
- seL4의 intransitive noninterference 증명이 직접 선례: "파티션 A의 어떤 행위도 파티션 B의 관측에 영향을 주지 않는다"를 기계 증명.

#### (2) GlobalPlatform TEE Protection Profile — 표준 공격 카탈로그

- **측정치**: EAL2+ (AVA_TEE.2 증강) 등급, 공격 카탈로그(Annex A) 항목별 차단율 (%)
- Common Criteria 공식 인증된 TEE 보호 프로파일(ANSSI PP-2014_01). TEE 도메인 격리에 대한 대표 공격 집합을 정의.
- 본 과제처럼 기존 TrustZone TEE와 공존하는 구조에서는 이 공격 카탈로그를 시험 항목 체크리스트로 활용 가능.

### 2.3 QA-03 보안 (DMA 경로 격리)

#### (1) Thunderclap형 악성 주변장치 모사 시험

- **측정치**: 시도한 DMA 공격 벡터 수 대비 차단된 수 (차단율 100% 목표)
- **Thunderclap** (NDSS 2019, Cambridge/SRI): FPGA로 악성 주변장치를 모사해 IOMMU 보호를 실공격으로 시험하는 평가 플랫폼. macOS/FreeBSD/Linux/Windows에서 IOMMU 우회 취약점을 실증하여, "IOMMU를 켰다"만으로는 격리가 증명되지 않음을 보임.
- 본 과제 적용: 악성 Host(또는 비할당 pVM)가 Camera/AI HW의 DMA 경로로 pVM 격리 메모리 접근을 시도하는 시나리오를 SMMU 설정별로 시험.

#### (2) 잔류 데이터 스캔

- **측정치**: HW IP 사용 주체 전환 후 이전 도메인 잔류 바이트 수 = 0
- 주체 전환(pVM→Host, pVM→pVM) 직후 HW IP 접근 가능 메모리/레지스터/내부 버퍼를 스캔하여 직접 수치 판정.

### 2.4 QA-10 시험 용이성 (격리 검증의 객관성)

#### (1) TVLA (Test Vector Leakage Assessment) — ISO/IEC 17825

- **측정치**: Welch's t-통계량. **|t| >= 4.5 (유의수준 alpha = 0.00001)** 초과 시 통계적으로 유의한 부채널 누출로 판정.
- ISO/IEC 17825:2024로 개정되어 고차 누출 탐지/비대칭키/PQC 지침 포함.
- "통계적으로 유의한 누출이 검출되지 않음"을 숫자로 증빙 가능하여 규제 증빙(CONST-04)에 특히 유용.

#### (2) 실증적 공격 저항 지표 — 침투시험/버그바운티

- **측정치**: 일정 기간/보상금 조건 하 경계 돌파 성공 건수 (0건 목표)
- Google Android VRP는 **"pKVM Boundary Defeat"**(pKVM 경계를 넘는 코드 실행/정보 노출)를 명시적 보상 카테고리로 운영. Host 침해 모사 시험(QA-10)을 상시화한 형태의 실증 지표.

---

## 3. 요약: 본 과제 적용 가능 측정 체계

| QA | 방법 | 측정치 형태 |
|----|------|------------|
| QA-01 | 형식 검증 + SESIP/CC 인증 | 검증 커버리지(LOC %), 인증 등급(SESIP L1~5, AVA_VAN.1~5) |
| QA-01 | QIF (min-entropy leakage) | 누출량 (bit) |
| QA-02 | 비간섭 증명, GP TEE PP 공격 카탈로그 | 증명 통과 여부, 공격 항목 차단율 (%) |
| QA-03 | Thunderclap형 DMA 공격 시험 + 잔류 메모리 스캔 | 공격 벡터 차단율 (%), 잔류 바이트 수 |
| QA-10 | TVLA (ISO/IEC 17825) | t-통계량 (임계 4.5), 침투시험 성공 건수 |

---

## 4. 출처

1. [Android pKVM SESIP Level 5 인증 (Google Security Blog, 2025-08)](https://security.googleblog.com/2025/08/Android-pKVM-Certified-SESIP-Level-5.html)
2. [Android Virtualization 보안 공식 문서 (AOSP)](https://source.android.com/docs/core/virtualization/security)
3. [A Secure and Formally Verified Linux KVM Hypervisor (Li, Li, Gu, Nieh, Hui — IEEE S&P 2021)](https://www.cs.columbia.edu/~nieh/pubs/ieeesp2021_kvm.pdf)
4. [seL4: From General Purpose to a Proof of Information Flow Enforcement (Murray et al. — IEEE S&P 2013)](https://ieeexplore.ieee.org/document/6547124/)
5. [Quantifying Information Flow Using Min-Entropy (Smith — IEEE)](https://ieeexplore.ieee.org/document/6041599/)
6. [GlobalPlatform TEE Protection Profile (Common Criteria 인증본, ANSSI PP-2014_01)](https://www.commoncriteriaportal.org/files/ppfiles/anssi-profil_PP-2014_01.pdf)
7. [A Critical Analysis of ISO 17825 (Whitnall, Oswald — IACR ePrint 2019/1013)](https://eprint.iacr.org/2019/1013.pdf)
8. [Thunderclap: Exploring Vulnerabilities in OS IOMMU Protection via DMA from Untrustworthy Peripherals (Markettos et al. — NDSS 2019)](https://thunderclap.io/wp-content/uploads/2024/01/thunderclap-paper-ndss2019.pdf)
9. [Android and Google Devices Security Reward Program Rules (Google Bug Hunters)](https://bughunters.google.com/about/rules/android-friends/android-and-google-devices-security-reward-program-rules)
10. [Secure System Virtualization: End-to-End Verification of Memory Isolation (arXiv:2005.02605)](https://arxiv.org/pdf/2005.02605)
