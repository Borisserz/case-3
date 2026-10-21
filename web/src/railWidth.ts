/** Persistable Artifact rail width (% of desk-split). */

export const RAIL_WIDTH_KEY = "liber-rail-width";
export const RAIL_WIDTH_DEFAULT = 55;
export const RAIL_WIDTH_MIN = 34;
export const RAIL_WIDTH_MAX = 70;

export function clampRailWidth(n: number): number {
  return Math.min(RAIL_WIDTH_MAX, Math.max(RAIL_WIDTH_MIN, Math.round(n)));
}

export function loadRailWidth(): number {
  try {
    const raw = localStorage.getItem(RAIL_WIDTH_KEY);
    if (!raw) return RAIL_WIDTH_DEFAULT;
    const n = Number(raw);
    if (!Number.isFinite(n)) return RAIL_WIDTH_DEFAULT;
    return clampRailWidth(n);
  } catch {
    return RAIL_WIDTH_DEFAULT;
  }
}

export function saveRailWidth(n: number): void {
  try {
    localStorage.setItem(RAIL_WIDTH_KEY, String(clampRailWidth(n)));
  } catch {
    /* quota / private */
  }
}
