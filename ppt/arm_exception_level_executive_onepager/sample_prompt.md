# Slide 1 sample generation prompt

Create one polished 16:9 landscape PowerPoint slide image for a Korean executive audience. Render the full slide edge to edge with no outer frame. The slide must look like a refined extension of the two supplied reference slides, using them strictly as visual-style references only. Do not copy any source content, logos, navigation tabs, diagrams, tables, annotations, or page structure from the references.

## Visual identity

- Bright white background, deep navy `#0B1F35`, cobalt blue `#1677C8`, pale blue-gray `#EEF3F8`.
- Orange `#F59E0B` only for upward protected calls; teal `#0F9D91` only for downward asynchronous notification.
- Bold, crisp Korean sans-serif typography; strong black title; thin navy rules; flat vector architecture graphics.
- Match the existing deck's practical corporate tone, but reduce information density and increase whitespace for executives.
- No gradients except a very subtle tonal progression across the four EL layers. No stock photos or decorative illustrations.

## Layout

Top 17%: title and one-sentence message. Add a short deep-navy vertical bar to the left of the title.

Title, render exactly:
`ARM Exception Level — CPU 권한과 격리를 나누는 4단계 실행 계층`

Core message, render exactly:
`높은 Level일수록 통제 권한과 장애 영향이 커지므로, 상위 EL의 코드와 호출 빈도를 최소화`

Main area: a disciplined three-column grid with clear alignment and generous internal spacing.

### Left column, 40% — four-layer architecture stack

Small header, render exactly: `권한 ↑  ·  통제 범위 ↑  ·  장애 영향 ↑`

Create four broad stacked horizontal layers. Each layer must contain exactly these labels, with the EL number visually dominant:

1. `EL3  Platform 보안 통제`
   `Secure Monitor · Firmware`
   `Secure / Non-secure 전환`
2. `EL2  VM 격리 통제`
   `Hypervisor · pKVM`
   `VM Memory · CPU · Interrupt 격리`
3. `EL1  OS 자원 통제`
   `Linux Kernel · Driver`
   `Process · Memory · Device 관리`
4. `EL0  Service 실행`
   `Application · pVM Workload`
   `Business Logic 실행`

Use deep navy for EL3, dark cobalt for EL2, medium blue for EL1, and very pale blue for EL0. Ensure white or near-black text has sufficient contrast.

### Middle column, 32% — controlled transitions

Section heading, render exactly: `EL 간 전환`

Show an orange upward path labeled `보호된 상향 요청` with these exact rows:

- `EL0 → EL1   SVC`
- `EL1 → EL2   HVC / Trap`
- `EL1·EL2 → EL3   SMC`
- `HW Event → 설정된 EL   IRQ / FIQ / SError`

Below it, show a teal downward asynchronous path labeled `하향 비동기 알림` with this compact flow:

`Event Queue 기록 → IRQ / vIRQ Pending → Lower EL Handler`

Add a separate thin return arrow with this exact label:

`실제 실행 복귀: ERET`

Add one small explanatory line, render exactly:

`낮은 EL이 실행 중이 아니면 Event는 Pending 후 처리`

Do not imply a direct function call from a higher EL to a lower EL.

### Right column, 28% — executive insights

Create two clean insight cards with simple line icons.

Card 1 title: `보안 · 신뢰`

- `Hardware 권한 분리로 침해 범위 제한`
- `EL2·EL3은 작은 신뢰 코드(TCB)로 유지`

Card 2 title: `성능 · 확장성`

- `Exception과 VM exit / entry 비용 발생`
- `Batching · Queue로 EL 전환 최소화`

Below the cards, add a slim emphasis strip, render exactly:

`Interrupt는 알림만, Data는 Queue로`

Bottom 9%: full-width deep-navy decision bar with white text. Render exactly:

`결론  |  상위 EL에는 격리·정책 집행만 두고 코드 크기와 호출 빈도를 최소화`

## Rendering constraints

- All Korean and English text above must be spelled exactly and remain readable at normal presentation size.
- Use at least 24 px equivalent for body text and stronger hierarchy for titles and EL labels.
- Do not add any text beyond what is explicitly provided.
- Do not truncate, overlap, distort, or garble text.
- No logo, watermark, slide number, page number, photo, 3D object, or unrelated icon.
- Preserve a clean 16:9 PowerPoint composition suitable for a boardroom presentation.
