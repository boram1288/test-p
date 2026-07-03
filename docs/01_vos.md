# VOS (Voice of Stakeholder) 요약

> 본 문서는 `01_requirements_collection.md` 3절의 VOS 목록을 Stakeholder, VOS 요약, 요구 유형(예상) 기준으로 재정리한 것이다.

| Stakeholder | VOS 요약 | 요구 유형(예상) |
|---|---|---|
| 로봇 제조사 | Host OS가 해킹되어도 카메라 영상 원본/AI 모델/추론 데이터는 노출되면 안 됨 | QA(보안) |
| 로봇 제조사 | Camera/AI HW 하드웨어 가속을 그대로 사용해야 하며, Host의 일반 기능과 동시 사용 필요 | FR + QA(성능) |
| 로봇 제조사 | Yocto/Ubuntu 기반 Linux 제품이며 Android 종속 솔루션은 채택 불가 | CONST |
| 로봇 제조사 | 보안 기능의 전력/메모리 오버헤드가 과도하면 탑재 불가 | QA(성능/자원 효율) |
| 상품 기획 | Secure Vision AI 외 향후 시나리오도 Framework 수정 없이 수용해야 사업 경쟁력 확보 | QA(확장성) |
| 과제 PM | 2026-10-30까지 E2E 데모 완료 필요, 인력은 Security/Hypervisor/SOC 설계 인력으로 한정 | CONST |
| 내부 Security 개발자 | Secure Camera/Secure AI 도메인은 독립 운용되어야 하며, 한쪽 침해가 다른 쪽에 영향 없어야 함 | FR + QA(보안) |
| SOC 설계 부서 | Camera/AI HW는 다중 Context 미지원 HW라 DMA 경로(S2MPU) 통제 및 잔류 데이터 삭제 필요 | QA(보안) + CONST |
| 내부 Security 개발자 | 도메인 간, pVM-Host 간 데이터 전달은 노출 없이 빠르게 이뤄져야 함 | FR + QA(성능/보안) |
| 내부 Hypervisor 개발자 | pKVM 커널(EL2)은 기 포팅된 그대로 사용, EL2 수정 불가, 제공 hypercall 범위 내 설계 | CONST |
| 내부 Security 개발자 | 기존 Secure OS의 pVM 이식 인터페이스가 명확해야 함 | QA(변경 용이성/이식성) |
| 내부 Security 개발자 | 기존 TrustZone TEE(키 관리/인증) 기능은 무중단 유지, 기존 SMC 경로 보존 | FR + CONST |
| 검증 부서 | Host 침해 시에도 격리 유지 주장을 객관적으로 검증할 수 있어야 함 | QA(시험 용이성) |
| 로봇 앱 개발자 | pVM 생성/실행/통신 API가 단순/문서화되어 비보안 전문가도 사용 가능해야 함 | QA(사용성) |
| 상품 기획 | 시장의 프라이버시/규제(GDPR 등) 요구를 반영한 기술적 격리 증빙 필요 | CONST + QA(보안) |
| 내부 Security 개발자 | pVM 비정상 종료/오동작 시에도 Host/다른 pVM/로봇 기본 동작은 영향받지 않아야 함 | QA(가용성) |
