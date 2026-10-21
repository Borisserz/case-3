# Design: PDF print polish (legend + D4 + D7 + D6)

**Date:** 2026-10-21  
**Status:** Implementing (user-approved)

## Scope

1. **Legend:** larger `.valued-legend` + Chart.js default legend in `chart_frame.html` / LiveChart
2. **D4:** title rule under `\maketitle` + float/caption spacing in `REPORT_STYLE_BLOCK`
3. **D7:** clamp chart `\includegraphics` width (≤0.92) + canvas height caps in harden
4. **D6:** prompt first-class `itemize`/`enumerate`/`emph`/`textbf`

## Out of scope

D5/D8 DOCX, D9 dual styles, D10 tokens.
