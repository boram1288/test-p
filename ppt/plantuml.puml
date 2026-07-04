@startuml
skinparam rectangleBorderColor #555555
skinparam rectangleBackgroundColor #FAFAFA
skinparam noteBackgroundColor #FFFDE7

title ARM Exception Level 배치 제약

rectangle "Normal World (REE)" as REE {
  rectangle "EL0\nHost App (보안 시나리오 앱 / Legacy CA 앱)\n[A1, A2 진입점]" as EL0 #D6EAF8
  rectangle "EL1\nLinux Kernel (Host OS)" as EL1 #D5F5E3
  rectangle "EL2\npKVM (Hypervisor)\n[CON-T-02 기술 제약]" as EL2 #FADBD8
}

rectangle "Secure World (TEE)" as TEE {
  rectangle "S-EL0\nSecure OS Internal Library" as SEL0 #FDF2D0
  rectangle "S-EL1\nSecure OS Firmware\n[CON-T-06 SMC 경로 유지]" as SEL1 #FDF2D0
  rectangle "S-EL3\nSecure Monitor" as SEL3 #F9E79F
}

rectangle "pVM (격리 실행 환경)" as PVM #E8DAEF {
  rectangle "pVM-1\nSecure AI\n[HW IP 독점 접근: FR-07]" as PVM1
  rectangle "pVM-2\nSecure Camera\n[HW IP 독점 접근: FR-07]" as PVM2
  rectangle "pVM-N\n신규 시나리오\n(Framework 무수정 추가: QA-M-01)" as PVMN
}

EL0 -down-> EL1 : GP Client API (UC-01)\nRPC 채널 (UC-04, UC-08)
EL1 -down-> EL2 : Hypercall\n(pVM 생명주기 관리: FR-01)
EL2 -right-> PVM : Stage-2 Page Table\n메모리 격리 (QA-S-01, QA-S-02)
EL1 <-right-> SEL1 : SMC (UC-01, CON-T-06)
PVM -right-> SEL1 : GP API via pVM-TEE 채널 (UC-09, CON-T-08)
SEL1 -down-> SEL3 : Secure Monitor Call

note bottom of EL2
  nVHE 모드: Host OS(EL1)는 EL2 직접 접근 불가
  Host OS 침해 시에도 pVM 격리 유지 (QA-S-03)
end note
@enduml