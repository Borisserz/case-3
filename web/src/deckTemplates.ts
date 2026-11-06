/** Liber presentation starters — structure (arc) + visual pack + Julius-style prompt. */

export type DeckTemplateCard = {
  id: string;
  /** Narrative arc — different slide sequence, not just colors. */
  structureId: string;
  /** Gallery film. Defaults to structureId. Old row keeps the previous frames. */
  previewId?: string;
  packId: string;
  title: string;
  blurb: string;
  /** Short arc label for modal. */
  arc: string;
  /** Fills composer on «Взять шаблон» (editable). */
  starterPrompt: string;
};

/** Narrative starters — each card is an arc, not only a recolor. */
export const DECK_TEMPLATE_CARDS: DeckTemplateCard[] = [
  {
    id: "survey-classic",
    structureId: "survey",
    previewId: "survey_classic",
    packId: "voltage",
    title: "Creative Voltage — Продукт и UX-исследования",
    blurb: "14 форматов: Кибер-постер → Bento 2×2 → реверс-сплиты → боли vs драйверы → UX-петля",
    arc: "Poster Title → Ch.1 → Method → Bento 2×2 → Drivers → Reversed Chart → Stat → Compare → Matrix → 2×2 Sprints → Close",
    starterPrompt:
      "Собери продуктовый и исследовательский обзор в стиле Creative Voltage: постер-титул с выборкой, методология, матрица метрик 2×2 (CSAT/NPS), факторы удержания и точки трения, горизонтальный рейтинг запросов, матрица ставок и спринтов. Цифры и цитаты только из Source или брифа.",
  },
  {
    id: "campaign",
    structureId: "campaign",
    previewId: "campaign_css",
    packId: "atelier",
    title: "Atelier Olive — Операции и маркетинг",
    blurb: "14 форматов: Оливковый лонгрид → матрица связок → реверс-графики → чеклист 2×2 → схема",
    arc: "Title → Ch.1 → Scorecard → Compare → Matrix → Reversed Chart Hero → Bets → Checklist 2×2 → Close",
    starterPrompt:
      "Собери презентацию статуса кампаний и маркетинговых операций в стиле Atelier Olive: снимок эффективности недели, сравнение лидеров и аутсайдеров, матрица креативов (масштаб/пауза), графики отдачи, три ставки с владельцами, предрелизный чеклист 2×2 и пятничный обзор. Цифры только из Source или брифа.",
  },
  {
    id: "quarter",
    structureId: "quarter",
    packId: "botanical",
    title: "Dark Botanical — Квартальный и клубный обзор",
    blurb: "15 форматов: Изумруд и латунь → 2 главы → Bento 2×2 → когорты → матрица Q+1 → схема",
    arc: "Poster Title → Ch.1 (Вышло) → Thesis → Bento 2×2 → Channels → Stat → Ch.2 (Q+1) → Compare → Matrix → Close",
    starterPrompt:
      "Собери двухглавный квартальный обзор в стиле Dark Botanical: тёмная изумрудная подача с латунными акцентами, глава «Что вышло» (метрики удержания и маржи в сетке Bento 2×2, каналы, ключевой мультипликатор), глава «План Q+1» (что удваиваем и что останавливаем, инвестиционная матрица с гейтами и дорожная карта). Цифры только из Source.",
  },
  {
    id: "qbr-classic",
    structureId: "qbr",
    previewId: "qbr_classic",
    packId: "relay",
    title: "Split Pastel — Квартальный и продуктовый обзор",
    blurb: "15 форматов: Две пастельные главы → Bento-карточки → каналы → план Q+1 → схема",
    arc: "Title → Ch.1 → Scorecard → Charts → Wins/Misses → Ch.2 → Compare → Matrix → Stat → Roadmap → Close",
    starterPrompt:
      "Собери презентацию в стиле Split Pastel (Rose Quartz & Garnet): двухчастная структура (Итоги периода + План следующего этапа), мягкие пастельные карточки KPI, графики и таблицы каналов, блок побед и точек роста, дорожная карта с владельцами и гейтами. Цифры только из Source или брифа.",
  },
  {
    id: "board-classic",
    structureId: "board_update",
    previewId: "board_classic",
    packId: "board",
    title: "Northstar — Архитектура и стратегия",
    blurb: "15 форматов: Split-титул → Bento KPI → графики → таблицы → таймлайн → цитата",
    arc: "Title → Section → Callout → Scorecard → Charts → Matrix → Compare → Timeline → Close",
    starterPrompt:
      "Собери презентацию в стиле Northstar Sapphire: сильный титул с ключевыми метриками, тезис главы, scorecard с прогрессом, графики и таблицы из данных, сравнение подходов, дорожная карта и финальные решения. Используй разнообразные макеты под контент. Цифры только из Source или брифа.",
  },
  {
    id: "investor",
    structureId: "investor",
    previewId: "investor_css",
    packId: "ink",
    title: "Relay Ink — Меморандум для инвесторов",
    blurb: "14 форматов: Обсидиан и золото → Stat-first → панорамные графики → кодекс 2×2 → риски",
    arc: "Title → Ch.1 → Big Stat → Scorecard → Widescreen Chart → GTM Split → Matrix → Risks → Capital Gates 2×2 → Close",
    starterPrompt:
      "Собери инвесторский меморандум в стиле Relay Ink: главный тезис квартала, крупная якорная метрика (ARR/выручка), табло эффективности, панорамный график накопления, конверсия и CAC, матрица рисков с триггерами и кодекс капитальной дисциплины 2×2 на следующий квартал. Числа строго из Source или брифа.",
  },
  {
    id: "council",
    structureId: "council",
    packId: "studio",
    title: "Workshop Studio — Архитектурный совет и сессия",
    blurb: "15 форматов: Баухаус-студия → панорамные графики → 2 главы → доска правил 2×2 → схема",
    arc: "Title → Ch.1 → Thesis → Scorecard → Widescreen Chart → Tracks → Stat → Ch.2 → Compare → Action Board 2×2 → Close",
    starterPrompt:
      "Собери презентацию архитектурного совета или стратегической сессии в стиле Workshop Studio: формулировка ключевого вопроса, баланс ресурсов, панорамный график приоритизации, три фокусных трека с владельцами, операционный кодекс 2×2 и протокол закрепленных решений. Цифры только из Source.",
  },
  {
    id: "performance-classic",
    structureId: "performance",
    previewId: "performance_classic",
    packId: "signal",
    title: "Bold Signal — Эффективность и рост",
    blurb: "15 форматов: Dark Luxury · Chart-first → ROAS матрица → юнит-экономика → спринты",
    arc: "Title → Section → Chart Hero → Scorecard → Split Charts → Matrix → Stat → Compare → Close",
    starterPrompt:
      "Собери презентацию эффективности и роста в стиле Bold Signal: тёмная контрастная подача, графики на первом плане, scorecard ключевых метрик, глубокая таблица каналов и сегментов, сравнение сценариев перераспределения бюджета и 90-дневная дорожная карта. Цифры только из Source или брифа.",
  },
];

export function starterPromptForStructure(structureId?: string | null): string {
  const id = (structureId || "").trim();
  const card = DECK_TEMPLATE_CARDS.find((c) => c.structureId === id);
  return (
    card?.starterPrompt ||
    "Собери презентацию 16:9 по брифу ниже. Структура ясная, цифры только из Source или текста запроса — ничего не выдумывай."
  );
}
