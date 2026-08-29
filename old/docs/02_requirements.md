# 요구사항 도출

> 본 문서는 `01_vos_collection.md`와 유즈케이스 명세를 입력으로 하여 Secure Vision AI Platform의 기능 요구사항(FR)과 제약사항(CONST)을 도출한다.
>
> 진행 순서: 요구사항 수집 → **요구사항 도출(본 문서)** → 품질 속성 명세 → Architectural Driver 선정

관련 문서: [`01_use_case_spec.md`](01_use_case_spec.md)

---

## 1. 도출 원칙

- **FR (Functional Requirement)**: 시스템이 제공해야 하는 기능. 유즈케이스의 Main/Alternative/Exception Flow에서 도출한다.
- **CONST (Constraint)**: 설계 선택지를 제한하는 제약. 과제 전제, 기존 포팅 상태, 표준/호환성 요구에서 도출한다.
- **명명**: FR-nn / CS-nn.

---

## 2. FR (기능 요구사항)

| ID | 요구사항 | 설명 | 관련 UC | 출처 VOS |
|----|---------|------|--------|---------|
| FR-01 | **pVM 생성/시작/정지/종료** | pVM의 생성/시작/정지/종료와 자원 할당/회수를 관리하는 기능을 제공한다. | UC-01 | VOS-01, VOS-07 |
| FR-02 | **다중 pVM 동시 운용** | Secure Camera, Secure AI 등 복수 pVM을 독립적으로 동시 운용하는 기능을 제공한다. | UC-02 | VOS-07 |
| FR-03 | **보안 Workload 동적 탑재** | 보안 Workload 이미지의 서명을 검증하고, 검증에 성공한 Workload를 실행 중인 플랫폼의 pVM에 동적으로 탑재하는 기능을 제공한다. | UC-03 | VOS-05 |
| FR-04 | **Camera/AI HW 공유 사용** | Camera/AI HW를 Host와 pVM이 공유하되 한 번에 하나의 주체에만 접근 권한을 부여하고, 사용 주체 전환 시 DMA 접근 권한 회수와 잔류 데이터 격리를 보장한다. | UC-04 | VOS-02, VOS-08 |
| FR-05 | **도메인 간 보안 데이터 전송** | pVM↔pVM 및 pVM↔Host 간 DMABUF를 송신·수신 도메인에만 매핑하여 비신뢰 주체에 노출하지 않고 전달하는 기능을 제공한다. | UC-05 | VOS-01, VOS-09 |
| FR-06 | **Secure OS ENC/DEC 명령 전송** | pVM의 Workload가 Secure OS에 암호화/복호화 명령을 전송하고 처리 결과를 안전하게 반환받는 기능을 제공한다. | UC-06 | VOS-11, VOS-12 |

---

## 3. CONST (제약사항)

| ID | 제약사항 | 설명 | 출처 VOS |
|----|---------|------|---------|
| CS-01 | **Linux 네이티브** | Android 스택에 의존하지 않고 Linux에서 네이티브로 동작한다. | VOS-03 |
| CS-02 | **GP 표준 규격 준수** | GlobalPlatform 표준 규격을 준수해야 한다. | VOS-12 |

---

## 다음 단계

VOS를 입력으로, **품질 속성 명세** 단계에서 품질 속성 시나리오를 구체화(자극/환경/응답/응답 측정치)하고 `03_utility_tree.md`에서 우선순위를 확정한다.
