/** Conversational pipeline phrases (templates — not LLM). Varied per run. */

export type ThinkingLine = {
  id: string;
  text: string;
  /** stage key that produced this line */
  stageKey: string;
};

const QUEUED = [
  "Ок, беру задачу…",
  "Сейчас гляну, что в запросе и Source…",
  "Принял — раскладываю на столе…",
  "Запрос понятен, захожу в Source…",
  "Стартую: сначала сверю входные данные…",
  "Беру в работу, без спешки…",
  "Открываю Source и Intent рядом…",
  "Поехали — сначала сверка фактов…",
];

const LLM = [
  "Читаю Source и Intent…",
  "Ловлю структуру документа…",
  "Структура ясна — собираю каркас отчёта…",
  "Пишу текст под печать, без лишней воды…",
  "Собираю LaTeX-код для вёрстки…",
  "Проверяю, чтобы числа остались из Source…",
  "Выстраиваю разделы так, чтобы читалось сверху вниз…",
  "Подбираю формулировки под тон отчёта…",
  "Сжимаю воду, оставляю суть и цифры…",
  "Сверяю заголовки с тем, что реально в Source…",
  "Держу факты жёстко: ничего от себя не дописываю…",
  "Набрасываю каркас: введение → данные → выводы…",
  "Чищу формулировки под спокойный печатный тон…",
  "Смотрю, где таблица уместнее абзаца…",
];

const IMAGES = [
  "Подбираю иллюстрацию к смыслу текста…",
  "Готовлю фото для разворота…",
  "Дожимаю картинку под макет…",
  "Прошу Image API сцену без текста на кадре…",
  "Ищу ракурс, который не спорит с графиком…",
  "Собираю иллюстрацию так, чтобы дышала страница…",
  "Генерирую кадр под подпись в документе…",
  "Проверяю, что на фото нет лишних надписей…",
  "Кладу иллюстрацию рядом с нужным абзацем…",
];

const CHARTS = [
  "Смотрю, какие числа можно показать графиком…",
  "Собираю диаграмму по данным Source…",
  "Рисую график, чтобы читалось с первого взгляда…",
  "Выбираю тип: сравнение, доли или тренд…",
  "Кладу подписи так, чтобы легенда не мешала…",
  "Сверяю шкалы с цифрами из Source…",
  "Палитра и тип — чтобы не спорили друг с другом…",
  "Готовлю PNG графика под печать…",
  "Убираю шум с оси, оставляю читаемые метки…",
  "Проверяю, что в чарте нет выдуманных процентов…",
];

const INJECT = [
  "Вставляю фигуры в текст…",
  "Связываю подписи и слоты в документе…",
  "Сверяю, что всё село в макет…",
  "Подставляю PNG в figure-слоты…",
  "Проверяю подписи: Рис. / Илл. на местах…",
  "Сшиваю текст и медиа в один TeX…",
  "Гляжу, не осталось ли пустых слотов…",
];

const LATEX = [
  "Отправляю в TeX — собираю PDF…",
  "Вёрстка на печать, ещё чуть-чуть…",
  "Дожимаю страницы и поля…",
  "XeLaTeX крутит макет в Docker…",
  "Сверяю поля и переносы под A4…",
  "Собираю печатную правду — PDF…",
  "Чищу предупреждения вёрстки на лету…",
  "Финишная сборка страниц…",
];

const DOCX = [
  "Параллельно собираю DOCX…",
  "Упаковываю Word-вариант…",
  "Готовлю DOCX рядом с PDF…",
  "Pandoc собирает редактируемую копию…",
  "Дублирую документ в Word без потери структуры…",
];

const CHART_DETAIL = [
  (d: string) => `Рисую график ${d}…`,
  (d: string) => `Собираю ${d} по числам Source…`,
  (d: string) => `Дожимаю диаграмму ${d}…`,
  (d: string) => `Рендерю ${d} в PNG…`,
  (d: string) => `Кладу ${d} на разворот…`,
];

const IMAGE_DETAIL = [
  (d: string) => `Готовлю иллюстрацию ${d}…`,
  (d: string) => `Генерирую кадр ${d}…`,
  (d: string) => `Дожимаю фото ${d}…`,
  (d: string) => `Прошу Image API: ${d}…`,
];

const BEATS: Record<string, string[]> = {
  queued: QUEUED,
  llm: LLM,
  images: IMAGES,
  charts: CHARTS,
  inject: INJECT,
  latex: LATEX,
  docx: DOCX,
};

function hashStr(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Mulberry32 — stable variety per run, not Math.random flicker. */
function mulberry32(seed: number): () => number {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function stageBucket(stage?: string | null): string {
  const s = (stage || "queued").toLowerCase();
  if (s in BEATS) return s;
  if (s === "ok" || s === "error") return s;
  return "queued";
}

export function stageKey(
  stage?: string | null,
  detail?: string | null,
): string {
  return `${stageBucket(stage)}:${detail || ""}`;
}

function detailPhrase(
  stage?: string | null,
  detail?: string | null,
  rand?: () => number,
): string | null {
  const d = (detail || "").trim();
  if (!d) return null;
  const bucket = stageBucket(stage);
  const roll = rand ? rand() : 0;
  if (bucket === "charts") {
    const fn = CHART_DETAIL[Math.floor(roll * CHART_DETAIL.length)]!;
    return fn(d);
  }
  if (bucket === "images") {
    const fn = IMAGE_DETAIL[Math.floor(roll * IMAGE_DETAIL.length)]!;
    return fn(d);
  }
  return null;
}

function nextFromPool(
  pool: string[],
  usedTexts: Set<string>,
  rand: () => number,
): string {
  const unused = pool.filter((p) => !usedTexts.has(p));
  const list = unused.length ? unused : pool;
  const i = Math.floor(rand() * list.length) % list.length;
  return list[i] || pool[0] || "Работаю над отчётом…";
}

/**
 * Append a line when stage/detail changes, or a micro-beat after dwell.
 * Returns same array reference if nothing new.
 *
 * Pass `seed` (e.g. thinkingStartedAt) so each run shuffles differently
 * but stays stable within the run.
 */
export function pushThinkingLine(
  prev: ThinkingLine[],
  opts: {
    stage?: string | null;
    detail?: string | null;
    /** seconds spent on current stageKey */
    dwellSec?: number;
    /** force a beat even if stage unchanged */
    beat?: boolean;
    /** run salt — Date.now() at thinking start */
    seed?: number;
  },
): ThinkingLine[] {
  const bucket = stageBucket(opts.stage);
  if (bucket === "ok" || bucket === "error") return prev;

  const key = stageKey(opts.stage, opts.detail);
  const used = new Set(prev.map((l) => l.text));
  const last = prev[prev.length - 1];
  const seed =
    (opts.seed ?? 1) ^
    (prev.length * 2654435761) ^
    (key.length * 1597334677) ^
    hashStr(key);
  const rand = mulberry32(seed >>> 0);

  // New stage or new detail → new line
  if (!last || last.stageKey !== key) {
    const specific = detailPhrase(opts.stage, opts.detail, rand);
    const pool = BEATS[bucket] || QUEUED;
    const text = specific || nextFromPool(pool, used, rand);
    const id = `${key}#${prev.length}`;
    return [...prev, { id, text, stageKey: key }];
  }

  // Same stage: optional micro-beats at dwell thresholds
  if (!opts.beat) return prev;
  const dwell = opts.dwellSec ?? 0;
  // Allow a beat every ~4s, max a few extras per stage
  const beatsOnStage = prev.filter((l) => l.stageKey === key).length;
  if (beatsOnStage >= 4) return prev;
  if (dwell < 4 * beatsOnStage) return prev;

  const pool = BEATS[bucket] || QUEUED;
  const text = nextFromPool(pool, used, rand);
  if (used.has(text) && beatsOnStage >= pool.length) return prev;
  const id = `${key}#beat${prev.length}`;
  return [...prev, { id, text, stageKey: key }];
}
