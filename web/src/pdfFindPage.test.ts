import { describe, expect, it } from "vitest";
import { pageTextMatchesNeedle, pdfSearchNeedles } from "./pdfFindPage";

describe("pdfSearchNeedles", () => {
  it("prefers full caption then bare title", () => {
    const n = pdfSearchNeedles("Рис. 2: Распределение продаж по каналам", "cht_02");
    expect(n[0]).toBe("Рис. 2: Распределение продаж по каналам");
    expect(n).toContain("Распределение продаж по каналам");
    expect(n).toContain("cht_02");
  });

  it("skips empty / tiny", () => {
    expect(pdfSearchNeedles("  ", null)).toEqual([]);
    expect(pdfSearchNeedles("ab", "xy")).toEqual([]);
  });
});

describe("pageTextMatchesNeedle", () => {
  it("matches spaced and compact caption text", () => {
    const page = "Рис. 2 Распределение продаж по каналам Таблица 2";
    expect(
      pageTextMatchesNeedle(page, "Распределение продаж по каналам"),
    ).toBe(true);
    expect(pageTextMatchesNeedle("Рис.2:Foo", "Рис. 2")).toBe(true);
    expect(pageTextMatchesNeedle(page, "несуществующий текст xyz")).toBe(false);
  });
});
