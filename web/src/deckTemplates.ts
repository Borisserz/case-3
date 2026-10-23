/** Liber presentation starters — structure (arc) + visual pack. */

export type DeckTemplateCard = {
  id: string;
  /** Narrative arc — different slide sequence, not just colors. */
  structureId: string;
  packId: string;
  title: string;
  blurb: string;
  /** Short arc label for modal (not dumped into chat). */
  arc: string;
};

export const DECK_TEMPLATE_CARDS: DeckTemplateCard[] = [
  {
    id: "board-update",
    structureId: "board_update",
    packId: "board",
    title: "Обновление для совета",
    blurb: "Scorecard → рост → cash → план → решения",
    arc: "Scorecard → ARR → cash → Q+1 → решения",
  },
  {
    id: "performance",
    structureId: "performance",
    packId: "signal",
    title: "Маркетинг и каналы",
    blurb: "Spend/return → каналы → перераспределение → 90 дней",
    arc: "Сигнал → эффективность → realloc → roadmap",
  },
  {
    id: "qbr",
    structureId: "qbr",
    packId: "relay",
    title: "Квартальный обзор",
    blurb: "Тезис → графики → wins/misses → план Q+1",
    arc: "Тезис → scorecard → истории → план",
  },
  {
    id: "survey",
    structureId: "survey",
    packId: "relay",
    title: "Результаты опроса",
    blurb: "Метод → findings → темы → действия",
    arc: "Метод → findings → actions",
  },
  {
    id: "investor",
    structureId: "investor",
    packId: "botanical",
    title: "Инвесторский апдейт",
    blurb: "Тезис → драйверы → качество → риски → ask",
    arc: "Тезис → engines → quality → ask",
  },
  {
    id: "launch",
    structureId: "launch",
    packId: "botanical",
    title: "Запуск продукта",
    blurb: "История → аудитория → каналы → инвестиции → решение",
    arc: "Story → audience → channels → decision",
  },
  {
    id: "campaign",
    structureId: "campaign",
    packId: "atelier",
    title: "Статус кампании",
    blurb: "KPI → winners/pauses → ставки на неделю",
    arc: "KPI → winners → next week",
  },
  {
    id: "workshop",
    structureId: "workshop",
    packId: "relay",
    title: "Воркшоп",
    blurb: "Цели → упражнения → outputs → follow-ups",
    arc: "Goals → exercises → follow-ups",
  },
];
