/** Six static preview slides per structure — Julius modal scroll DNA, Liber CSS. */

export type PreviewSlideKind =
  | "title"
  | "scorecard"
  | "chart"
  | "table"
  | "cards"
  | "closing"
  | "split"
  | "signal"
  | "quote"
  | "agenda";

export type PreviewSlide = {
  kind: PreviewSlideKind;
  kicker?: string;
  title: string;
  subtitle?: string;
  /** KPI chips / scorecard cells */
  cells?: { label: string; value: string; delta?: string }[];
  /** Fake bar heights 0–100 */
  bars?: number[];
  /** Table rows */
  rows?: string[][];
  /** Card titles */
  cards?: string[];
  dark?: boolean;
};

/** Exactly 6 frames for gallery modal scroll. */
export const TEMPLATE_PREVIEW_SLIDES: Record<string, PreviewSlide[]> = {
  board_update: [
    {
      kind: "title",
      kicker: "Q4 FY2025 · BOARD",
      title: "ARR $18.4M — two record quarters",
      subtitle: "NRR 117% · Burn 0.9x · 268 customers",
    },
    {
      kind: "scorecard",
      kicker: "01 / EXECUTIVE SCORECARD",
      title: "Plan vs actuals",
      cells: [
        { label: "ARR", value: "$18.4M", delta: "+24%" },
        { label: "NRR", value: "117%", delta: "+3pt" },
        { label: "Burn", value: "0.9x", delta: "−0.2" },
        { label: "Cash", value: "$21.3M", delta: "30 mo" },
      ],
    },
    {
      kind: "chart",
      kicker: "02 / GROWTH",
      title: "ARR bridge — new logo led",
      bars: [42, 58, 51, 72, 68, 88],
    },
    {
      kind: "table",
      kicker: "03 / GTM",
      title: "Pipeline by segment",
      rows: [
        ["Segment", "Pipe", "Win"],
        ["Mid-market", "$4.2M", "28%"],
        ["Enterprise", "$6.1M", "19%"],
        ["Expansion", "$2.8M", "41%"],
      ],
    },
    {
      kind: "cards",
      kicker: "04 / PRIORITIES",
      title: "Three owned bets for Q+1",
      cards: ["Workflow automation wedge", "Partner-led mid-market", "Gross margin to 78%"],
    },
    {
      kind: "closing",
      kicker: "05 / BOARD ASK",
      title: "Approve hiring plan + Series B narrative",
      subtitle: "Decisions needed this meeting",
    },
  ],
  performance: [
    {
      kind: "signal",
      kicker: "SIGNAL",
      title: "Spend vs return — reallocate in 90 days",
      bars: [35, 62, 48, 80],
      dark: true,
    },
    {
      kind: "scorecard",
      kicker: "SPEND / RETURN",
      title: "Channel efficiency this period",
      cells: [
        { label: "Spend", value: "$420k", delta: "+8%" },
        { label: "ROAS", value: "3.4x", delta: "+0.4" },
        { label: "CAC", value: "$182", delta: "−12%" },
        { label: "Pipe", value: "$2.1M", delta: "+19%" },
      ],
      dark: true,
    },
    {
      kind: "chart",
      kicker: "TREND",
      title: "Weekly return by channel",
      bars: [30, 44, 52, 48, 70, 85],
      dark: true,
    },
    {
      kind: "table",
      kicker: "REALLOCATION",
      title: "Move budget as a test",
      rows: [
        ["From", "To", "Δ"],
        ["Display", "Search", "+$40k"],
        ["Social", "Partner", "+$25k"],
        ["Brand", "Hold", "—"],
      ],
      dark: true,
    },
    {
      kind: "cards",
      kicker: "90 DAYS",
      title: "Roadmap bets",
      cards: ["Cut bottom 20% creatives", "Double winner geo", "Partner co-op test"],
      dark: true,
    },
    {
      kind: "closing",
      kicker: "DECISION",
      title: "Approve reallocation this week",
      subtitle: "Owners assigned · review in 30 days",
      dark: true,
    },
  ],
  qbr: [
    {
      kind: "title",
      kicker: "QUARTERLY BUSINESS REVIEW",
      title: "Thesis → the shift that compounds",
      subtitle: "Wins · misses · Q+1 plan",
    },
    {
      kind: "scorecard",
      kicker: "SCORECARD",
      title: "Quarter snapshot",
      cells: [
        { label: "Revenue", value: "$4.8M", delta: "+11%" },
        { label: "Margin", value: "62%", delta: "+2pt" },
        { label: "NPS", value: "54", delta: "+6" },
        { label: "Churn", value: "2.1%", delta: "−0.4" },
      ],
    },
    {
      kind: "chart",
      kicker: "STORY 1",
      title: "Where growth actually came from",
      bars: [40, 55, 48, 66, 78],
    },
    {
      kind: "cards",
      kicker: "WINS / MISSES",
      title: "Keep / kill / learn",
      cards: ["Keep: expansion motion", "Kill: unused SKU", "Learn: onboarding lag"],
    },
    {
      kind: "table",
      kicker: "Q+1",
      title: "Operating plan with owners",
      rows: [
        ["Bet", "Owner", "Target"],
        ["Activation", "Product", "+8pt"],
        ["Enterprise", "Sales", "$1.2M"],
        ["Margin", "Ops", "64%"],
      ],
    },
    {
      kind: "closing",
      kicker: "APPROVE",
      title: "Protect the learning loop",
      subtitle: "Shift budget · keep the test cadence",
    },
  ],
  survey: [
    {
      kind: "title",
      kicker: "SURVEY READOUT",
      title: "Findings → actions",
      subtitle: "n from Source only",
      dark: true,
    },
    {
      kind: "scorecard",
      kicker: "METHOD",
      title: "Who answered",
      cells: [
        { label: "n", value: "428", delta: "82%" },
        { label: "CSAT", value: "4.2", delta: "+0.3" },
        { label: "NPS", value: "41", delta: "+5" },
        { label: "Effort", value: "2.1", delta: "−0.4" },
      ],
      dark: true,
    },
    {
      kind: "quote",
      kicker: "FINDING 1",
      title: "“Onboarding still feels like homework.”",
      subtitle: "Theme · activation friction",
      dark: true,
    },
    {
      kind: "cards",
      kicker: "TOP THEMES",
      title: "Three cards from the data",
      cards: ["Setup time", "Support wait", "Value clarity"],
      dark: true,
    },
    {
      kind: "table",
      kicker: "ACTIONS",
      title: "Priority matrix",
      rows: [
        ["Action", "Owner", "When"],
        ["Simplify day-1", "Product", "Sprint 12"],
        ["SLA to 4h", "Support", "Nov"],
        ["Value tour", "CS", "Pilot"],
      ],
      dark: true,
    },
    {
      kind: "closing",
      kicker: "NEXT",
      title: "Ship two fixes before next pulse",
      subtitle: "Re-field in 60 days",
      dark: true,
    },
  ],
  investor: [
    {
      kind: "title",
      kicker: "RELAY / INVESTOR UPDATE",
      title: "Growth, with more signal.",
      subtitle: "One-liner → engines → cash → ask",
      dark: true,
    },
    {
      kind: "scorecard",
      kicker: "ONE SENTENCE",
      title: "Marketing scaled the engine",
      cells: [
        { label: "Revenue", value: "$2.08M", delta: "+21% QoQ" },
        { label: "ARR", value: "$12.0M", delta: "+25%" },
        { label: "Mkt-sourced", value: "70%" },
        { label: "NRR", value: "112%", delta: "+3pt" },
      ],
      dark: true,
    },
    {
      kind: "chart",
      kicker: "COMPOUNDING",
      title: "Revenue compounds — not spikes",
      bars: [40, 48, 55, 68, 82],
      dark: true,
    },
    {
      kind: "table",
      kicker: "CONVERSION",
      title: "Better conversion. Lower CAC.",
      rows: [
        ["Metric", "Prior", "Now"],
        ["Opps", "180", "240"],
        ["Customers", "36", "48"],
        ["CAC", "$29k", "$26k"],
      ],
      dark: true,
    },
    {
      kind: "cards",
      kicker: "Q+1",
      title: "Three owned bets",
      cards: ["Grow efficiently", "Deepen product", "Protect runway"],
      dark: true,
    },
    {
      kind: "closing",
      kicker: "ASK",
      title: "Approve operating plan gates",
      subtitle: "Definitions ⊆ Source on real runs",
      dark: true,
    },
  ],
  launch: [
    {
      kind: "title",
      kicker: "PRODUCT LAUNCH",
      title: "Story rooted in ritual",
      subtitle: "Audience · channels · decision",
      dark: true,
    },
    {
      kind: "cards",
      kicker: "AUDIENCES",
      title: "Three who feel the pain",
      cards: ["Ops leads", "Finance partners", "Frontline coaches"],
      dark: true,
    },
    {
      kind: "table",
      kicker: "CHANNELS",
      title: "Where we show up",
      rows: [
        ["Channel", "Role", "Bet"],
        ["Product", "Aha", "High"],
        ["Email", "Nurture", "Med"],
        ["Partner", "Trust", "High"],
      ],
      dark: true,
    },
    {
      kind: "scorecard",
      kicker: "TRACTION GOALS",
      title: "Only numbers from Source",
      cells: [
        { label: "Waitlist", value: "—", delta: "Source" },
        { label: "Pilot", value: "—", delta: "Source" },
        { label: "NPS", value: "—", delta: "Source" },
        { label: "Spend", value: "—", delta: "Source" },
      ],
      dark: true,
    },
    {
      kind: "agenda",
      kicker: "LEARNING",
      title: "What we must learn in 30 days",
      cards: ["Activation time", "Willingness to pay", "Support load"],
      dark: true,
    },
    {
      kind: "closing",
      kicker: "LAUNCH DECISION",
      title: "Go / hold — owners named",
      subtitle: "Investment table follows if Source has it",
      dark: true,
    },
  ],
  campaign: [
    {
      kind: "title",
      kicker: "CAMPAIGN STATUS",
      title: "Winners vs pauses",
      subtitle: "Spend · ROAS · next week",
    },
    {
      kind: "scorecard",
      kicker: "THIS WEEK",
      title: "Efficiency snapshot",
      cells: [
        { label: "Spend", value: "$86k", delta: "+5%" },
        { label: "ROAS", value: "4.1x", delta: "+0.3" },
        { label: "CPA", value: "$64", delta: "−8%" },
        { label: "Pipe", value: "$410k", delta: "+12%" },
      ],
    },
    {
      kind: "chart",
      kicker: "TREND",
      title: "Daily return",
      bars: [38, 45, 42, 55, 60, 72],
    },
    {
      kind: "table",
      kicker: "CREATIVES",
      title: "Scale / pause",
      rows: [
        ["Creative", "ROAS", "Action"],
        ["Hook A", "5.2x", "Scale"],
        ["Hook B", "1.1x", "Pause"],
        ["UGC C", "3.8x", "Hold"],
      ],
    },
    {
      kind: "cards",
      kicker: "NEXT WEEK",
      title: "Three bets",
      cards: ["Double Hook A geo", "New offer test", "Cut Hook B"],
    },
    {
      kind: "closing",
      kicker: "ASK",
      title: "Approve budget shift + creative freeze",
      subtitle: "Review Friday",
    },
  ],
  workshop: [
    {
      kind: "agenda",
      kicker: "WORKSHOP",
      title: "Goals → exercises → outputs",
      subtitle: "Facilitator pack",
    },
    {
      kind: "cards",
      kicker: "GOALS",
      title: "What success looks like today",
      cards: ["Shared problem frame", "Prioritized bets", "Owners + dates"],
    },
    {
      kind: "table",
      kicker: "AGENDA",
      title: "Blocks",
      rows: [
        ["Block", "Min", "Output"],
        ["Frame", "20", "Problem"],
        ["Diverge", "35", "Ideas"],
        ["Converge", "30", "Bets"],
      ],
    },
    {
      kind: "cards",
      kicker: "EXERCISE A",
      title: "Map the friction",
      cards: ["Solo notes", "Pair share", "Cluster"],
    },
    {
      kind: "cards",
      kicker: "EXERCISE B",
      title: "Force-rank bets",
      cards: ["Impact", "Effort", "Owner"],
    },
    {
      kind: "closing",
      kicker: "FOLLOW-UPS",
      title: "Parking lot → next ritual",
      subtitle: "Send notes within 24h",
    },
  ],
};

export function previewSlidesFor(structureId: string): PreviewSlide[] {
  return TEMPLATE_PREVIEW_SLIDES[structureId] || TEMPLATE_PREVIEW_SLIDES.board_update;
}

/** Must match PNG count under web/public/deck/previews/{id}/ (else broken ? thumbs). */
export const PREMIUM_PREVIEW_COUNTS: Record<string, number> = {
  board_update: 11,
  performance: 11,
  qbr: 12,
  survey: 9,
  investor: 9,
  launch: 9,
  campaign: 8,
  workshop: 11,
};

/** Bust browser cache when Liber twins are re-rendered. */
const PREVIEW_CACHE_BUST = "20261024v6";

/** Real rendered frames (Liber smoke or Julius-ref raster). Prefer over CSS mocks. */
export function previewPngUrls(structureId: string): string[] {
  const id = TEMPLATE_PREVIEW_SLIDES[structureId] ? structureId : "board_update";
  const n = PREMIUM_PREVIEW_COUNTS[id] ?? 6;
  return Array.from({ length: n }, (_, i) => i + 1).map(
    (k) =>
      `/deck/previews/${id}/${String(k).padStart(2, "0")}.png?v=${PREVIEW_CACHE_BUST}`,
  );
}

export function hasPreviewPngs(structureId: string): boolean {
  // All 8 structures seeded under web/public/deck/previews/
  return Boolean(TEMPLATE_PREVIEW_SLIDES[structureId]);
}
