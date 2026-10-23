/** Liber presentation starters — structure (arc) + visual pack + Julius-style prompt. */

export type DeckTemplateCard = {
  id: string;
  /** Narrative arc — different slide sequence, not just colors. */
  structureId: string;
  packId: string;
  title: string;
  blurb: string;
  /** Short arc label for modal. */
  arc: string;
  /** Fills composer on «Взять шаблон» (editable). */
  starterPrompt: string;
};

export const DECK_TEMPLATE_CARDS: DeckTemplateCard[] = [
  {
    id: "board-update",
    structureId: "board_update",
    packId: "board",
    title: "Обновление для совета",
    blurb: "Scorecard → рост → cash → план → решения",
    arc: "Scorecard → ARR → cash → Q+1 → решения",
    starterPrompt:
      "Собери презентацию для совета директоров: scorecard KPI, рост и выручка, cash/runway, план на следующий период и слайд решений. Цифры и факты только из Source или из этого брифа — ничего не выдумывай.",
  },
  {
    id: "performance",
    structureId: "performance",
    packId: "signal",
    title: "Маркетинг и каналы",
    blurb: "Spend/return → каналы → перераспределение → 90 дней",
    arc: "Сигнал → эффективность → realloc → roadmap",
    starterPrompt:
      "Собери маркетинговую презентацию: spend vs return, разрез по каналам, что усилить/паузить, перераспределение бюджета и план на 90 дней. Только числа из Source или брифа.",
  },
  {
    id: "qbr",
    structureId: "qbr",
    packId: "relay",
    title: "Квартальный обзор",
    blurb: "Тезис → графики → wins/misses → план Q+1",
    arc: "Тезис → scorecard → истории → план",
    starterPrompt:
      "Собери квартальный обзор (QBR): главный тезис квартала, scorecard, wins и misses, истории с цифрами и план на Q+1. Без выдуманных метрик — только Source/бриф.",
  },
  {
    id: "survey",
    structureId: "survey",
    packId: "relay",
    title: "Результаты опроса",
    blurb: "Метод → findings → темы → действия",
    arc: "Метод → findings → actions",
    starterPrompt:
      "Собери презентацию по результатам опроса: метод и выборка, ключевые findings, темы/кластеры и конкретные действия. Цитаты и % только из Source или брифа.",
  },
  {
    id: "investor",
    structureId: "investor",
    packId: "botanical",
    title: "Инвесторский апдейт",
    blurb: "Тезис → драйверы → качество → риски → ask",
    arc: "Тезис → engines → quality → ask",
    starterPrompt:
      "Собери инвесторский апдейт: тезис, драйверы роста, качество метрик, риски и явный ask. Числа строго из Source или этого брифа.",
  },
  {
    id: "launch",
    structureId: "launch",
    packId: "botanical",
    title: "Запуск продукта",
    blurb: "История → аудитория → каналы → инвестиции → решение",
    arc: "Story → audience → channels → decision",
    starterPrompt:
      "Собери презентацию запуска продукта: история/проблема, аудитория, каналы go-to-market, инвестиции и решение к действию. Без выдуманных KPI — только Source/бриф.",
  },
  {
    id: "campaign",
    structureId: "campaign",
    packId: "atelier",
    title: "Статус кампании",
    blurb: "KPI → winners/pauses → ставки на неделю",
    arc: "KPI → winners → next week",
    starterPrompt:
      "Собери статус кампании: KPI недели, winners и pauses, ставки/бюджет на следующую неделю. Метрики только из Source или брифа.",
  },
  {
    id: "workshop",
    structureId: "workshop",
    packId: "relay",
    title: "Воркшоп",
    blurb: "Цели → упражнения → outputs → follow-ups",
    arc: "Goals → exercises → follow-ups",
    starterPrompt:
      "Собери deck для воркшопа: цели, повестка/упражнения, ожидаемые outputs и follow-ups. Детали только из Source или этого брифа.",
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
