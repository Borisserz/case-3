/** Liber composer work modes. */

export type LiberWorkMode = "report" | "diagram" | "presentation" | null;

export const LIBER_MODE_PILLS: {
  id: Exclude<LiberWorkMode, null>;
  label: string;
  hint: string;
}[] = [
  { id: "report", label: "Отчёт", hint: "PDF и DOCX из Source" },
  { id: "diagram", label: "Схема", hint: "Только Mermaid + краткое описание" },
  {
    id: "presentation",
    label: "Презентация",
    hint: "Только дек PPTX — без PDF/превью отчёта",
  },
];

/** Visible nudge under pills on empty desk. */
export function modeNudge(mode: LiberWorkMode): string {
  if (mode === "presentation") {
    return "Шаблон подставит бриф в чат — правьте и отправляйте; Source по желанию.";
  }
  if (mode === "diagram") {
    return "Короткий или длинный запрос — без PDF, только схема.";
  }
  if (mode === "report") {
    return "Вставьте Source или опишите задачу — соберём PDF/DOCX.";
  }
  return "Сначала выберите режим: Отчёт · Схема · Презентация.";
}

export function modeToOutputMode(mode: LiberWorkMode): string {
  return mode ?? "auto";
}
