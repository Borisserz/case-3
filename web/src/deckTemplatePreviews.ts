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
      kicker: "КВАРТАЛ · СОВЕТ",
      title: "Выручка 12,4 млн — рост год к году",
      subtitle: "Удержание 117% · запас 30 мес. · 268 клиентов",
    },
    {
      kind: "scorecard",
      kicker: "01 / СВОДКА",
      title: "План и факт",
      cells: [
        { label: "Выручка", value: "12,4 млн", delta: "+24%" },
        { label: "Удержание", value: "117%", delta: "+3 п.п." },
        { label: "Burn", value: "0,9×", delta: "−0,2" },
        { label: "Кэш", value: "21,3 млн", delta: "30 мес." },
      ],
    },
    {
      kind: "chart",
      kicker: "02 / РОСТ",
      title: "Мост выручки — новые клиенты",
      bars: [42, 58, 51, 72, 68, 88],
    },
    {
      kind: "table",
      kicker: "03 / ПРОДАЖИ",
      title: "Воронка по сегментам",
      rows: [
        ["Сегмент", "Воронка", "Win"],
        ["Средний", "4,2 млн", "28%"],
        ["Крупный", "6,1 млн", "19%"],
        ["Расширение", "2,8 млн", "41%"],
      ],
    },
    {
      kind: "cards",
      kicker: "04 / ПРИОРИТЕТЫ",
      title: "Три ставки на следующий квартал",
      cards: ["Автоматизация процессов", "Партнёрский mid-market", "Маржа до 78%"],
    },
    {
      kind: "closing",
      kicker: "05 / РЕШЕНИЕ",
      title: "Утвердить найм и нарратив раунда",
      subtitle: "Решения на этой встрече",
    },
  ],
  performance: [
    {
      kind: "signal",
      kicker: "СИГНАЛ",
      title: "Затраты и отдача — перераспределить за 90 дней",
      bars: [35, 62, 48, 80],
      dark: true,
    },
    {
      kind: "scorecard",
      kicker: "ЗАТРАТЫ / ОТДАЧА",
      title: "Эффективность каналов",
      cells: [
        { label: "Затраты", value: "420 тыс.", delta: "+8%" },
        { label: "ROAS", value: "3,4×", delta: "+0,4" },
        { label: "CAC", value: "182", delta: "−12%" },
        { label: "Воронка", value: "2,1 млн", delta: "+19%" },
      ],
      dark: true,
    },
    {
      kind: "chart",
      kicker: "ТРЕНД",
      title: "Отдача по неделям",
      bars: [30, 44, 52, 48, 70, 85],
      dark: true,
    },
    {
      kind: "table",
      kicker: "ПЕРЕНОС",
      title: "Тестовое перераспределение",
      rows: [
        ["Откуда", "Куда", "Δ"],
        ["Медиа", "Поиск", "+40 тыс."],
        ["Соцсети", "Партнёры", "+25 тыс."],
        ["Бренд", "Hold", "—"],
      ],
      dark: true,
    },
    {
      kind: "cards",
      kicker: "90 ДНЕЙ",
      title: "Дорожная карта",
      cards: ["Срезать слабые 20%", "Удвоить сильный регион", "Тест с партнёром"],
      dark: true,
    },
    {
      kind: "closing",
      kicker: "РЕШЕНИЕ",
      title: "Утвердить перераспределение на этой неделе",
      subtitle: "Ответственные назначены · обзор через 30 дней",
      dark: true,
    },
  ],
  qbr: [
    {
      kind: "title",
      kicker: "КВАРТАЛЬНЫЙ ОБЗОР",
      title: "Тезис → сдвиг, который усиливается",
      subtitle: "Победы · промахи · план на Q+1",
    },
    {
      kind: "scorecard",
      kicker: "СВОДКА",
      title: "Снимок квартала",
      cells: [
        { label: "Выручка", value: "4,8 млн", delta: "+11%" },
        { label: "Маржа", value: "62%", delta: "+2 п.п." },
        { label: "NPS", value: "54", delta: "+6" },
        { label: "Отток", value: "2,1%", delta: "−0,4" },
      ],
    },
    {
      kind: "chart",
      kicker: "ИСТОРИЯ",
      title: "Откуда пришёл рост",
      bars: [40, 55, 48, 66, 78],
    },
    {
      kind: "cards",
      kicker: "ПОБЕДЫ / ПРОМАХИ",
      title: "Оставить / убрать / выучить",
      cards: ["Оставить: расширение", "Убрать: мёртвый SKU", "Выучить: онбординг"],
    },
    {
      kind: "table",
      kicker: "Q+1",
      title: "План с ответственными",
      rows: [
        ["Ставка", "Владелец", "Цель"],
        ["Активация", "Продукт", "+8 п.п."],
        ["Enterprise", "Продажи", "1,2 млн"],
        ["Маржа", "Операции", "64%"],
      ],
    },
    {
      kind: "closing",
      kicker: "УТВЕРДИТЬ",
      title: "Сохранить цикл обучения",
      subtitle: "Сдвинуть бюджет · держать ритм тестов",
    },
  ],
  survey: [
    {
      kind: "title",
      kicker: "ОПРОС",
      title: "Находки → действия",
      subtitle: "n только из Source",
      dark: true,
    },
    {
      kind: "scorecard",
      kicker: "МЕТОД",
      title: "Кто ответил",
      cells: [
        { label: "n", value: "428", delta: "82%" },
        { label: "CSAT", value: "4,2", delta: "+0,3" },
        { label: "NPS", value: "41", delta: "+5" },
        { label: "Усилие", value: "2,1", delta: "−0,4" },
      ],
      dark: true,
    },
    {
      kind: "quote",
      kicker: "НАХОДКА",
      title: "«Старт всё ещё как домашняя работа.»",
      subtitle: "Тема · трение активации",
      dark: true,
    },
    {
      kind: "cards",
      kicker: "ТЕМЫ",
      title: "Три карточки из данных",
      cards: ["Время настройки", "Ожидание поддержки", "Ясность ценности"],
      dark: true,
    },
    {
      kind: "table",
      kicker: "ДЕЙСТВИЯ",
      title: "Приоритеты",
      rows: [
        ["Действие", "Владелец", "Когда"],
        ["Упростить день 1", "Продукт", "Спринт 12"],
        ["SLA до 4 ч", "Поддержка", "Нояб."],
        ["Тур по ценности", "CS", "Пилот"],
      ],
      dark: true,
    },
    {
      kind: "closing",
      kicker: "ДАЛЬШЕ",
      title: "Два фикса до следующего пульса",
      subtitle: "Повтор через 60 дней",
      dark: true,
    },
  ],
  investor: [
    {
      kind: "title",
      kicker: "ОБНОВЛЕНИЕ ИНВЕСТОРАМ",
      title: "Рост — с большим сигналом.",
      subtitle: "Одна строка → двигатели → кэш → запрос",
      dark: true,
    },
    {
      kind: "scorecard",
      kicker: "ОДНО ПРЕДЛОЖЕНИЕ",
      title: "Маркетинг усилил двигатель",
      cells: [
        { label: "Выручка", value: "2,08 млн", delta: "+21% QoQ" },
        { label: "ARR", value: "12,0 млн", delta: "+25%" },
        { label: "Из маркетинга", value: "70%" },
        { label: "NRR", value: "112%", delta: "+3 п.п." },
      ],
      dark: true,
    },
    {
      kind: "chart",
      kicker: "НАКОПЛЕНИЕ",
      title: "Выручка растёт ровно, без всплесков",
      bars: [40, 48, 55, 68, 82],
      dark: true,
    },
    {
      kind: "table",
      kicker: "КОНВЕРСИЯ",
      title: "Лучше конверсия. Ниже CAC.",
      rows: [
        ["Метрика", "Было", "Сейчас"],
        ["Сделки", "180", "240"],
        ["Клиенты", "36", "48"],
        ["CAC", "29 тыс.", "26 тыс."],
      ],
      dark: true,
    },
    {
      kind: "cards",
      kicker: "Q+1",
      title: "Три ставки",
      cards: ["Расти эффективно", "Углубить продукт", "Беречь runway"],
      dark: true,
    },
    {
      kind: "closing",
      kicker: "ЗАПРОС",
      title: "Утвердить операционные ворота",
      subtitle: "Определения ⊆ Source на живых прогонах",
      dark: true,
    },
  ],
  launch: [
    {
      kind: "title",
      kicker: "ЗАПУСК ПРОДУКТА",
      title: "История в ритуале команды",
      subtitle: "Аудитория · каналы · решение",
      dark: true,
    },
    {
      kind: "cards",
      kicker: "АУДИТОРИИ",
      title: "Три, кому больно",
      cards: ["Операции", "Финансы", "Линейные лиды"],
      dark: true,
    },
    {
      kind: "table",
      kicker: "КАНАЛЫ",
      title: "Где появляемся",
      rows: [
        ["Канал", "Роль", "Ставка"],
        ["Продукт", "Aha", "Высокая"],
        ["Почта", "Nurture", "Средняя"],
        ["Партнёр", "Доверие", "Высокая"],
      ],
      dark: true,
    },
    {
      kind: "scorecard",
      kicker: "ЦЕЛИ",
      title: "Только цифры из Source",
      cells: [
        { label: "Лист ожидания", value: "—", delta: "Source" },
        { label: "Пилот", value: "—", delta: "Source" },
        { label: "NPS", value: "—", delta: "Source" },
        { label: "Затраты", value: "—", delta: "Source" },
      ],
      dark: true,
    },
    {
      kind: "agenda",
      kicker: "ОБУЧЕНИЕ",
      title: "Что узнать за 30 дней",
      cards: ["Время активации", "Готовность платить", "Нагрузка поддержки"],
      dark: true,
    },
    {
      kind: "closing",
      kicker: "РЕШЕНИЕ",
      title: "Идём / ждём — владельцы названы",
      subtitle: "Таблица инвестиций — если есть в Source",
      dark: true,
    },
  ],
  campaign: [
    {
      kind: "title",
      kicker: "СТАТУС КАМПАНИИ",
      title: "Победители и паузы",
      subtitle: "Затраты · ROAS · следующая неделя",
    },
    {
      kind: "scorecard",
      kicker: "ЭТА НЕДЕЛЯ",
      title: "Снимок эффективности",
      cells: [
        { label: "Затраты", value: "86 тыс.", delta: "+5%" },
        { label: "ROAS", value: "4,1×", delta: "+0,3" },
        { label: "CPA", value: "64", delta: "−8%" },
        { label: "Воронка", value: "410 тыс.", delta: "+12%" },
      ],
    },
    {
      kind: "chart",
      kicker: "ТРЕНД",
      title: "Отдача по дням",
      bars: [38, 45, 42, 55, 60, 72],
    },
    {
      kind: "table",
      kicker: "КРЕАТИВЫ",
      title: "Масштаб / пауза",
      rows: [
        ["Креатив", "ROAS", "Действие"],
        ["Хук A", "5,2×", "Масштаб"],
        ["Хук B", "1,1×", "Пауза"],
        ["UGC C", "3,8×", "Hold"],
      ],
    },
    {
      kind: "cards",
      kicker: "СЛЕД. НЕДЕЛЯ",
      title: "Три ставки",
      cards: ["Удвоить Хук A", "Новый оффер", "Срезать Хук B"],
    },
    {
      kind: "closing",
      kicker: "ЗАПРОС",
      title: "Утвердить сдвиг бюджета и заморозку",
      subtitle: "Обзор в пятницу",
    },
  ],
  workshop: [
    {
      kind: "agenda",
      kicker: "ВОРКШОП",
      title: "Цели → упражнения → результаты",
      subtitle: "Пакет фасилитатора",
    },
    {
      kind: "cards",
      kicker: "ЦЕЛИ",
      title: "Как выглядит успех сегодня",
      cards: ["Общая рамка проблемы", "Приоритетные ставки", "Владельцы + даты"],
    },
    {
      kind: "table",
      kicker: "ПОВЕСТКА",
      title: "Блоки",
      rows: [
        ["Блок", "Мин", "Выход"],
        ["Рамка", "20", "Проблема"],
        ["Дивергенция", "35", "Идеи"],
        ["Сходимость", "30", "Ставки"],
      ],
    },
    {
      kind: "cards",
      kicker: "УПРАЖНЕНИЕ A",
      title: "Карта трения",
      cards: ["Соло-заметки", "Пары", "Кластеры"],
    },
    {
      kind: "cards",
      kicker: "УПРАЖНЕНИЕ B",
      title: "Ранжирование ставок",
      cards: ["Влияние", "Усилие", "Владелец"],
    },
    {
      kind: "closing",
      kicker: "ДАЛЬШЕ",
      title: "Парковка → следующий ритуал",
      subtitle: "Заметки в течение 24 ч",
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
  hire: 6,
};

/** Bust browser cache when Liber twins are re-rendered. */
const PREVIEW_CACHE_BUST = "20261105-open";

/** Real rendered frames (Liber smoke or Julius-ref raster). Prefer over CSS mocks. */
export function previewPngUrls(structureId: string): string[] {
  const id = PREMIUM_PREVIEW_COUNTS[structureId]
    ? structureId
    : TEMPLATE_PREVIEW_SLIDES[structureId]
      ? structureId
      : "board_update";
  const n = PREMIUM_PREVIEW_COUNTS[id] ?? 6;
  return Array.from({ length: n }, (_, i) => i + 1).map(
    (k) =>
      `/deck/previews/${id}/${String(k).padStart(2, "0")}.png?v=${PREVIEW_CACHE_BUST}`,
  );
}

export function hasPreviewPngs(structureId: string): boolean {
  const id = structureId in PREMIUM_PREVIEW_COUNTS ? structureId : "";
  return Boolean(id && (PREMIUM_PREVIEW_COUNTS[id] ?? 0) >= 6);
}
