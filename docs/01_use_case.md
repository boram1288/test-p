# Use Case 명세

> 본 문서는 기능 요구사항을 기반으로 Secure Vision AI Platform의 유스케이스를 도출하고 PlantUML 다이어그램으로 표현한 것이다.

---

## 1. 액터

| 액터 | 설명 |
|---|---|
| Host Application | pVM 생성/운용과 보안 Workload 탑재를 요청하는 Host 측 애플리케이션 |
| Workload(Camera/AI) | Camera HW/AI HW 사용, 도메인 간 데이터 전송, Secure OS 연동을 수행하는 보안 Workload |
| Normal Camera Application | Host의 일반 Camera 기능으로 Camera HW 사용을 요청하는 애플리케이션 |

---

## 2. Use Case 목록

| UC ID | Use Case | 설명 |
|---|---|---|
| UC-01 | pVM 생성/시작/정지/종료 | pVM의 전체 생명주기를 관리하고 자원을 할당/회수한다 |
| UC-02 | 다중 pVM 동시 운용 | Secure Camera, Secure AI 등 복수 pVM을 독립적으로 동시에 운용한다 |
| UC-03 | 보안 Workload 동적 탑재 | 보안 Workload를 서명 검증 후, pVM에 동적으로 탑재한다 |
| UC-04 | Camera/AI HW 공유 사용 | Camera/AI HW를 Host/pVM이 공유하고, 사용 주체 전환 시 격리를 보장한다 |
| UC-05 | 도메인 간 DMABUF 전송 | pVM↔pVM, pVM↔Host 간 DMABUF를 비신뢰 주체에 노출 없이 전달한다 |
| UC-06 | Secure OS ENC/DEC 명령 전송 | pVM에서 Secure OS에 암호화/복호화 명령을 전송한다 |

---

## 3. Use Case 다이어그램 (PlantUML)

```plantuml
@startuml
left to right direction
skinparam packageStyle rectangle
skinparam actorStyle awesome
skinparam usecase {
  BackgroundColor White
  BorderColor Black
}

actor "Host Application" as HostApp
actor "Workload(Camera/AI)" as Workload

rectangle "System" {
  usecase "UC-06. Secure OS\nENC/DEC 명령 전송" as UC06
  usecase "UC-05. 도메인 간\nDMABUF 전송" as UC05
  usecase "UC-04. Camera/AI HW 공유 사용" as UC04
  usecase "UC-03. 보안 Workload 동적 탑재" as UC03
  usecase "UC-02. 다중 pVM 동시 운용" as UC02
  usecase "UC-01. pVM 생성/시작/정지/종료" as UC01
}

actor "Normal Camera\nApplication" as NormalCameraApp

HostApp --> UC01
HostApp --> UC02
HostApp --> UC03
HostApp --> UC05

Workload --> UC04
Workload --> UC05
Workload --> UC06

UC04 <-- NormalCameraApp

@enduml
```

---

> 유즈케이스 명세는 [`01_use_case_spec.md`](01_use_case_spec.md) 참조
