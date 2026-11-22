/** One name for the attached document. The screen note is only for a capture. */

export const SOURCE_LABEL = "Документ";

export const SCREEN_READ_NOTE = "Числа с экрана модель могла прочитать";

export const ATTACHED_TOAST = "Данные прикреплены";

export function screenReadNote(fromScreen: boolean): string {
  return fromScreen ? SCREEN_READ_NOTE : "";
}
