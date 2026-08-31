# Slide 1 localized technical-clarity edit

Edit the supplied PowerPoint slide image in place while preserving its current 16:9 composition, white background, navy/cobalt palette, typography, icons, column widths, spacing, and all text not explicitly changed below. This is a localized text-and-flow correction, not a redesign.

Make only these exact changes:

1. In the EL1 layer, replace the actor line
   `Linux Kernel · Driver`
   with
   `Host / pVM Kernel · Driver`

2. In the EL0 layer, replace the actor line
   `Application · pVM Workload`
   with
   `Host App · pVM Userspace Workload`

3. Replace the orange section heading
   `보호된 상향 요청`
   with
   `보호된 상향 요청 · 대표 경로`

4. Keep the teal heading `하향 비동기 알림`, but replace its three-box flow with these exact labels:
   - first box: `Event Queue 기록`
   - second box: `IRQ / vIRQ Pending`
   - third box: `대상 EL Handler`

5. Replace the blue ERET line and the small explanatory line below it with two clearly separate statements. The blue return arrow must not look connected to the teal asynchronous flow.

   Blue return arrow label, render exactly:
   `실행 복귀: ERET → 같은 EL 또는 유효한 하위 EL`

   Small black explanatory line below, render exactly:
   `IRQ / vIRQ는 Pending 후 대상 EL 실행 시 Handler 진입`

6. Replace the right-column slim emphasis strip text
   `Interrupt는 알림만, Data는 Queue로`
   with
   `설계 원칙 | Interrupt는 알림만, Data는 Queue로`

Preserve the existing title, core message, EL labels and role descriptions, SVC/HVC/SMC rows, security and performance cards, conclusion bar, and all other visual elements exactly. Keep all Korean and English text crisp, correctly spelled, untruncated, and readable. Do not add any logo, watermark, slide number, new icon, new section, or decorative element.
