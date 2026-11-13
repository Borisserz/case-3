# When to add charts / figures

`{{MAX_CHARTS}}` / `{{MAX_IMAGES}}` / `{{MAX_DIAGRAMS}}` are **ceilings**. Do **not** invent numbers to fill the budget.
But if the chart ceiling is **≥ 1** and Source **has usable numbers**, you **should** add charts — **aim for up to {{MAX_CHARTS}}** (UI/env budget), not a soft 1–2. Prefer **variety of types** when adding 2+.
**Token priority:** finish `charts` + `diagrams` in JSON before spending the rest of the budget on `figures`. Shorten prose / fewer photos rather than under-shooting the chart budget.

## Charts — add when **all** hold

1. Source has **explicit numbers** (≥2 comparable points, shares, time series, or one clear KPI).
2. A chart helps the reader more than (or alongside) a table.
3. Every plotted value is from Source (only simple % / differences allowed).
4. Place `%CASE3_CHART:id%` **alone on its line** next to the prose it explains. **Forbidden:** trailing dump sections — «Визуализация данных» / «Иллюстрации» / «Графики» / «Приложение: … для визуализации» / any appendix that only lists charts/photos — scatter slots through the report body instead. Never wrap slots in `\begin{figure}` (pipeline wraps PNGs).
5. `caption`: Russian, specific («Клиенты по годам», not «График 1»).
6. Optional chat card meta (numbers **only from Source**): `insight` (1 short Russian sentence) and `highlights: [{label, value, pct?}]` for the top categories — never invent figures.

If Intent **forbids** charts → `"charts": []`, no slots.  
If Intent **asks** for a chart / names types → honor (map wishes to whitelist).  
If Intent is auto/silent but Source has numbers and ceiling ≥ 1 → **add 1…ceiling charts**, pick types by playbook, prefer **different** types.

## `charts[].type` whitelist (strict)

Only: `bar`, `grouped_bar`, `stacked_bar`, `line`, `horizontal_bar`, `donut`, `kpi`, `area`, `scatter`.

Synonyms: pie/круговая/doughnut → `donut`; column/столбцы → `bar`; тренд → `line`; топ-N → `horizontal_bar`; одна цифра → `kpi`.  
Never emit non-catalog `type`.

## Image API `figures` (photos / illustrations) — **opt-in only**

`{{MAX_IMAGES}}` is a **ceiling** for generated `fig_*` (Image API). **Default OFF.**
Do **not** invent stock photos just because Source mentions a place, office, product, or scene.

### When to emit generated `fig_*` ({{MAX_IMAGES}} ≥ 1)

Emit only if Intent **or** Source **explicitly** asks for a picture / illustration / appearance visual, e.g.:

- фото / фотка / иллюстрация / рисунок / картинка / изображение;
- «внешний вид…», «покажи здание/офис/продукт…»;
- photo / photograph / illustration / picture of / image of / visual of / show the appearance.

If the budget is ≥ 1, that already means the desk detected opt-in — **prefer filling up to {{MAX_IMAGES}} strong photos** with rich English prompts (do not soft-skip to empty).

Skip generated photos (`"figures": []` for `fig_*`) when budget is 0, Intent says «без фото», or there is no explicit picture ask (user uploads `usr_*` are separate — always place those when attached).

- If Intent says «сгенерируй фото…» → emit up to {{MAX_IMAGES}} with rich English prompts matching that request.
- `caption`: Russian, what the reader sees.
- `prompt`: **English only**, photographic subject + setting + lighting + lens feel; no Cyrillic; no tiny text overlays; no charts/tables of numbers; no logos unless Source requires.
- Photo prompts **MUST**: print-editorial / matte / natural light / documentary object or place; one clear subject; suitable for A4 print.
- Photo prompts **MUST NOT**: handshake, stock smiling team in glass office, purple/violet/magenta neon glow, hologram UI, watermark / Shutterstock look, plastic 3D people, confetti/trophy slam energy.
- Prefer photorealistic clarity; avoid readable faces of real people when possible. Server also hardens brand-safe + pack style-lock.
- Never use figures for KPI/number comparisons — those are `charts`.
- Place each `%CASE3_FIG:id%` slot near the prose it illustrates. **Never** gather photos into a final `\section{Иллюстрации}` (or similar) — one slot beside the matching paragraph.
- If {{MAX_IMAGES}} is 0 → `"figures": []`, no `%CASE3_FIG:%` slots.

## Пользовательские фото (`usr_01`, `usr_02`, ...) — Vision-анализ и логичное встраивание

Когда к запросу прикреплены фотографии пользователя (`usr_XX`):
1. **Визуальный осмотр:** Внимательно посмотри на прикреплённое изображение (интерфейс, экран, схема, чертёж, оборудование, объект, документ, рабочее место и т.д.).
2. **Точный `caption`:** В JSON `figures[]` для каждого `usr_XX` укажи подробную и конкретную подпись на русском языке, точно описывающую содержание снимка (например: «Интерфейс панели управления Liber с графиками нагрузки», а не просто «Фото 1»).
3. **Логичное место в отчёте:** Слот `%CASE3_FIG:usr_XX%` должен стоять **строго в том разделе и рядом с тем абзацем**, который смыслово относится к данному изображению (например, скриншот интерфейса — в разделе об архитектуре/системе, фото устройства — в разделе спецификаций). Ни в коем случае не сваливай фото в конец отчёта!
4. **Текстовое описание в отчёте:** Абзац текста рядом с фотографией должен ссылаться на неё и описывать ключевые элементы, видимые на снимке («На фотографии показан...», «Как видно на скриншоте интерфейса...»).
5. Не подменяй идентификаторы: используй ровно `usr_01`, `usr_02` и т.д.
