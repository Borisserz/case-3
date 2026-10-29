# Julius live generation run (2026-10-22)

**Chat:** https://julius.ai/chat?id=7f4b020f-4bb0-400b-a7a3-c0ca2547e4a4  
**Prompt:** Board Update template (Series B SaaS sample)  
**Model:** Julius 1.5 Lite · ~1:30 wall clock

## Observed pipeline

1. Empty Slides → Use prompt fills composer → **blue Send**
2. Instant ack: honest «no attachment → labeled sample data»
3. Composer: **Working · 0:MM** + Send→**Stop**
4. Steps collapse: Ran Command → Generating Code → **Created 12 slides** + `.pptx` + `.xlsx`
5. Artifacts in chat: **PPTX (Export · Edit)** · **PDF (Export · View)** · **Excel sample**
6. Mid-stream upsell: «Add your styles»
7. Title bar renames to «Series B Board Update Deck»
8. Preview pane: Data Explorer | Files | **Preview** with insert Text/Image/Table/Shapes + filmstrip 12
9. Export modal: Publish | Export · Download PPTX · branding upsell
10. Slide craft: **takeaway titles** («ARR grew 50% YoY; execution must close the plan gap»), KPI row, footer disclaimer

## Liber follow-ups from this run

| Julius | Liber action |
|--------|----------------|
| Working timer | ✅ `PresentationPane` Working · m:ss |
| PPTX Export/Edit in chat | ✅ `ArtifactCard` deck file rows |
| Takeaway titles | ✅ `system_slides.md` rule |
| Stop cancel mid-job | P2 (API cancel) |
| Insert Text/Image/Table/Shapes | NON-goal freeform; Liber = IR text edit |
| Sample xlsx companion | Skip — Liber = Source truth |
| Publish link | Out of scope |
