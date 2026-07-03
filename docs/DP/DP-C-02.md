# DP-C-02 결정 과정: 접근 통제 일관성을 위한 보안 정책 및 권한 집행 모델 설계

> 관련 문서: `05_decision_points.md` DP-C-02, `DP/DP-C-01.md`
> 상태: 확정

---

## 1. 보안 정책 및 권한 집행 모델의 중요성

보안 정책 및 권한 집행 모델은 pVM 생성, Workload 로딩, HW IP 사용, 채널 수립 같은 동작을 누가 요청할 수 있고 어떤 범위까지 허용할지를 정한다. 이 모델이 불명확하면 Host app, Framework, Workload, pVM 리소스가 서로 다른 권한 가정으로 동작하게 되어 접근 통제 일관성이 깨진다.

본 결정의 핵심 전제는 다음과 같다.

- Camera/AI HW IP 사용 정책은 SoC BSP 제공 업체가 일괄 결정할 문제가 아니라, 최종 제품 제조사인 고객사가 제품 요구에 맞게 정해야 하는 문제다.
- 기존 Host 리소스와 HW IP 접근은 이미 SELinux 정책으로 통제되고 있으므로, 기존 방식과의 정합성을 유지해야 한다.
- 본 과제에서 새로 추가되는 권한 통제 대상은 pVM 생성, pVM 생명주기 제어, Workload 로딩, pVM 리소스 접근이다.
- 따라서 새 pVM 리소스 권한도 별도 정책 엔진을 새로 만들기보다 SELinux 정책 체계에 통합한다.

결론적으로 DP-C-02는 "새로운 독립 권한 체계"를 정의하는 결정이 아니라, **pVM 리소스를 기존 SELinux 기반 접근 통제 모델에 어떻게 편입할 것인가**를 결정하는 항목이다.

단, SELinux는 정상 Host 정책 집행 수단이다. Host 커널 침해 상황에서 pVM 자산의 기밀성/무결성을 보호하는 보장은 DP-C-01의 EL2/SMMU 격리 메커니즘에 의존한다.

---

## 2. Host 보안정책 및 권한집행 모델 (SELinux)

Host 영역의 권한 통제는 기존 SELinux 정책을 그대로 사용한다.

| 대상 | 정책 주체 | 집행 지점 |
|------|----------|----------|
| Host app의 Framework API 호출 | 고객사 SELinux 정책 | Linux SELinux |
| Camera/AI HW IP의 Host 측 접근 | 고객사 SELinux 정책 | Linux SELinux + 기존 드라이버 권한 |
| pVM 생성/시작/정지/종료 요청 | 고객사 SELinux 정책 | pVM Framework API 진입부 |
| Workload 패키지 전달 요청 | 고객사 SELinux 정책 | pVM Framework API 진입부 |

Host app은 SELinux domain에 따라 pVM Framework API 사용 권한을 얻는다. 예를 들어 어떤 app은 pVM 생성 요청이 가능하고, 다른 app은 상태 조회만 가능하도록 고객사가 정책을 작성할 수 있어야 한다.

중요한 점은 Host app의 SELinux 권한이 곧 Workload의 권한을 의미하지 않는다는 것이다. Host app은 pVM 생명주기 요청자이자 Workload 전달자일 수 있지만, pVM 안에서 실행될 Workload의 권한은 별도로 통제되어야 한다.

### 결정

- Host app 권한은 기존 SELinux domain 정책으로 통제한다.
- Camera/AI HW IP의 Host 측 사용 정책도 기존 SELinux 정책으로 통제한다.
- SoC BSP는 SELinux label, device node, Framework hook 등 정책을 적용할 수 있는 메커니즘을 제공하고, 최종 허용 정책은 고객사가 작성한다.

---

## 3. pVM 보안정책 및 권한집행 모델

pVM 리소스는 기존 Host 리소스와 달리 본 과제에서 새로 추가되는 접근 통제 대상이다. 따라서 SELinux 정책에 pVM 관련 object class/type을 추가하고, Host app 권한과 Workload 권한을 분리해서 표현할 수 있어야 한다.

### 3.1 권한 통제 대상

| 대상 | 설명 |
|------|------|
| pVM 생명주기 | 생성, 시작, 정지, 종료, 재시작 |
| Workload 로딩 | 특정 Workload 패키지를 특정 pVM 프로파일로 실행 |
| pVM 리소스 | 메모리, vCPU, 채널, device binding 등 |
| pVM 간 채널 | 송신자/수신자 Workload 조합별 채널 수립 |
| pVM의 HW IP 사용 요청 | pVM Workload가 Camera/AI HW IP 사용을 요청하는 경우 |

### 3.2 후보 구조

#### 후보 A: Host app 권한과 Workload 권한을 동일하게 취급

Host app이 가진 SELinux 권한을 Workload 실행 권한으로 그대로 승계한다. Host app이 pVM 생성과 Workload 전달을 허용받으면, 전달된 Workload도 같은 권한 범위 안에서 실행된다.

| 항목 | 평가 |
|------|------|
| 장점 | 정책 모델이 단순하다. Host app 중심으로 기존 SELinux 정책을 재사용하기 쉽다. |
| 단점 | Host app과 Workload의 책임 경계가 흐려진다. 하나의 Host app이 여러 Workload를 전달할 때 Workload별 최소 권한 분리가 어렵다. app 권한이 과도하면 Workload도 과도한 권한을 얻게 된다. 감사 로그에서 app 권한 위반인지 Workload 권한 위반인지 구분하기 어렵다. |

#### 후보 B: Host app 권한과 Workload 권한을 분리

Host app 권한과 Workload 권한을 별도 SELinux Context로 관리한다. Host app은 pVM 생성과 Workload 전달 권한을 검사받고, 전달된 Workload는 별도의 Workload label/type에 따라 pVM 리소스 사용 권한을 검사받는다.

| 항목 | 평가 |
|------|------|
| 장점 | Host app과 Workload의 책임이 분리된다. 고객사가 Workload별로 pVM 리소스, 채널, HW IP 사용 권한을 세밀하게 통제할 수 있다. 최소 권한 원칙과 감사 추적성이 좋아진다. |
| 단점 | Workload label, 패키지 메타데이터, SELinux policy 매핑이 추가로 필요하다. pVM Framework가 Host app Context와 Workload Context를 함께 검사해야 한다. |

### 3.3 결정

**후보 B를 채택한다. Host app 권한과 Workload 권한은 분리한다.**

Host app은 "pVM 생성 요청자"와 "Workload 전달자"로서 권한을 검사받는다. Workload는 "pVM 안에서 실행되는 보안 작업 단위"로서 별도의 SELinux label/type을 갖고, 이 label/type에 따라 pVM 리소스와 채널, HW IP 사용 권한을 검사받는다.

권한 검사는 다음 두 단계로 수행한다.

1. **Host app 권한 검사**: 해당 app이 pVM Framework API를 호출하고 특정 Workload를 전달할 수 있는지 SELinux로 검사한다.
2. **Workload 권한 검사**: 전달된 Workload label/type이 요청한 pVM 리소스, 채널, HW IP 사용 권한을 갖는지 SELinux로 검사한다.

둘 중 하나라도 실패하면 pVM 생성 또는 Workload 로딩은 거부한다.

### 3.4 정책 표현 원칙

- Workload 패키지는 SELinux policy에서 식별 가능한 Workload label/type을 가져야 한다.
- Host app의 domain과 Workload의 label/type은 독립적으로 정책화한다.
- Workload가 사용할 수 있는 pVM 리소스는 SELinux allow rule로 표현한다.
- Workload가 사용할 수 있는 Camera/AI HW IP 권한도 SELinux policy에 표현한다.
- HW IP 사용 정책의 최종 결정권은 고객사에 있으며, Framework는 정책 적용 지점을 제공한다.

예시 개념은 다음과 같다.

```text
Host app domain:
  camera_app_t -> pVM 생성 요청 가능
  normal_app_t -> pVM 생성 요청 불가

Workload type:
  secure_camera_workload_t -> Camera pVM 리소스 사용 가능
  secure_ai_workload_t -> AI/NPU pVM 리소스 사용 가능
  unknown_workload_t -> pVM 리소스 사용 불가
```

---

## 4. 후속 DP에 주는 전제

| 후속 DP | 전제 |
|---------|------|
| DP-C-03 (pVM 관리 골격) | pVM Framework API 진입부에서 Host app SELinux 권한과 Workload SELinux 권한을 모두 확인할 수 있어야 한다. |
| DP-C-04 (보안 Workload 실행 방식) | Workload 패키지는 SELinux policy와 연결 가능한 Workload label/type 또는 동등한 식별자를 포함해야 한다. |
| DP-C-06 (zero-copy 보안 채널) | 채널 수립 권한은 Workload label/type 조합에 따라 검사한다. |
| DP-C-07 (HW IP 중재) | Camera/AI HW IP 사용 권한은 고객사 SELinux 정책으로 표현하고, 중재자는 해당 정책을 적용할 수 있는 집행 지점을 제공해야 한다. |

---

## 5. 결정 요약

| 항목 | 결정 |
|------|------|
| Host 권한 모델 | 기존 SELinux 정책을 사용한다. |
| HW IP Host 측 사용 정책 | 고객사가 기존 SELinux 정책으로 결정한다. |
| pVM 리소스 권한 모델 | pVM 리소스를 SELinux 정책 체계에 추가한다. |
| Host app과 Workload 권한 관계 | 분리한다. |
| Workload 권한 표현 | Workload label/type을 통해 SELinux 정책으로 표현한다. |
| 최종 결정 | SELinux 기반 Host/pVM 통합 권한 모델을 채택한다. |
