# Glossary

| Term | Meaning |
|------|---------|
| **Liber / Atelier** | Chat UI brand (olive/cream desk) |
| **Source** | User text/file with numbers — only factual base |
| **Intent** | UI+chat requirements (types, palette, caps) |
| **Qwen / Vision** | LLM behind `VISION_API_BASE_URL` |
| **Chart slot** | `%CASE3_CHART:cht_01%` → includegraphics after PNG |
| **Figure slot** | `%CASE3_FIG:fig_01%` / `usr_XX` uploads |
| **Coerce** | Force chart type HTML to match preferred type |
| **Polish** | Palette remap + geometry harden after coerce |
| **Harden (TeX)** | Repair preamble/tables before latexmk |
| **Dry-run** | Skip LLM media / or skip heavy path per flags |
| **Gold** | Few-shot TeX examples in `prompt/gold/` |
| **Image API** | Office `/generate` + `/edit` for photos |
| **case-3:tex** | Docker image with XeLaTeX + pandoc |
