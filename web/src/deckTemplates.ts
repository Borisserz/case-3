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

/** Eight unique DNA pairs — each pack + structure is distinct. */
export const DECK_TEMPLATE_CARDS: DeckTemplateCard[] = [
  {
    id: "board-update",
    structureId: "board_update",
    packId: "board",
    title: "Northstar — совет",
    blurb: "Split-титул с цифрами → scorecard → таблицы моста",
    arc: "Callout → scorecard → tables → board ask",
    starterPrompt:
      "Собери board update в духе Northstar: thesis + hero KPI, scorecard actual vs plan, ARR trajectory и bridge, GTM constraint, NRR/cash, Q+1 plan с owners и явный board ask. Цифры только из Source или брифа.",
  },
  {
    id: "performance",
    structureId: "performance",
    packId: "signal",
    title: "Bold Signal — каналы",
    blurb: "Chart-first → tables → realloc → 90-day roadmap",
    arc: "Charts → tables → card_row → close",
    starterPrompt:
      "Собери marketing performance в духе Bold Signal: scorecard spend/revenue/ROAS, spend vs return, channel/region/campaign tables, realloc как тест (±pp), 3 recommendations + 90-day roadmap. Только Source/бриф.",
  },
  {
    id: "qbr",
    structureId: "qbr",
    packId: "relay",
    title: "Split Pastel — QBR",
    blurb: "2× section chapters → pastel scorecards → Q ask",
    arc: "Section → scorecard → charts → decisions",
    starterPrompt:
      "Собери QBR в духе Split Pastel: hero KPI на титуле, тезис квартала, scorecard, 2–3 графика, wins/misses, testable decisions, план Q+1 и goals с gates. Без выдуманных метрик.",
  },
  {
    id: "survey",
    structureId: "survey",
    packId: "voltage",
    title: "Voltage — feedback",
    blurb: "Method callout → % meters → quotes → NOW/NEXT",
    arc: "Callouts + % cards · almost no charts",
    starterPrompt:
      "Собери product-feedback readout в духе Creative Voltage: punchy thesis, n/CSAT/NPS, method caveats, loves vs friction, quotes из Source, NOW/NEXT/LATER bets с gates. % только из Source/брифа.",
  },
  {
    id: "investor",
    structureId: "investor",
    packId: "ink",
    title: "Relay Ink — инвесторы",
    blurb: "Одна большая цифра → график → ask → риски",
    arc: "Sparse ink · chart · ask · risks",
    starterPrompt:
      "Собери investor update в духе Relay Ink: one-sentence quarter, compounding ARR, engines, quality, GTM/CAC, cash/runway, Q+1 bets и risks. Числа строго из Source/брифа.",
  },
  {
    id: "launch",
    structureId: "launch",
    packId: "botanical",
    title: "Vesper — запуск",
    blurb: "Bleed photo → story callout → media → roadmap",
    arc: "Photo · story · table · soft foil",
    starterPrompt:
      "Собери product launch в духе Dark Botanical / Vesper: soft thesis, story/tension, product callout, audience triad, GTM, roadmap table, investment scorecard, learning gates и closing ask. KPI только из Source/брифа.",
  },
  {
    id: "campaign",
    structureId: "campaign",
    packId: "atelier",
    title: "Atelier — кампания",
    blurb: "Масштаб против паузы → статусы в таблице → пятница",
    arc: "Short ops · table + bullets",
    starterPrompt:
      "Собери weekly campaign status в духе Atelier: KPI недели, creative scale/pause table, channel chart, next-week bets, flat-total realloc и Friday review. Метрики только из Source/брифа.",
  },
  {
    id: "workshop",
    structureId: "workshop",
    packId: "studio",
    title: "Studio — воркшоп",
    blurb: "Таймлайн повестки → упражнения → владельцы",
    arc: "Agenda · exercises · owners table",
    starterPrompt:
      "Собери facilitation deck в духе Workshop Studio: goals, timeboxed agenda, framing + force-rank exercises, outputs/norms и follow-ups с owners. Детали только из Source/брифа.",
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
