import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  craftParentId,
  craftProgress,
  formatCraftRecap,
  formatEtaSuffix,
  upsertCraftFilm,
  upsertCraftSubstep,
} from "./craftSteps.ts";

describe("craftSteps phase 2A", () => {
  it("maps SSE parents to craft ids", () => {
    assert.equal(craftParentId("charts"), "charts");
    assert.equal(craftParentId("images"), "photos");
    assert.equal(craftParentId("photos"), "photos");
    assert.equal(craftParentId("unknown"), null);
  });

  it("upserts nested chart beats", () => {
    let list = upsertCraftSubstep([], {
      parent: "charts",
      id: "cht_01",
      status: "active",
      label: "cht_01",
    });
    assert.equal(list.length, 1);
    assert.equal(list[0].status, "active");
    list = upsertCraftSubstep(list, {
      parent: "charts",
      id: "cht_01",
      status: "done",
    });
    assert.equal(list[0].status, "done");
  });

  it("nests substeps under charts and marks photos skipped", () => {
    const rows = craftProgress("charts", "report", {
      live: true,
      substeps: [
        { id: "cht_01", label: "cht_01", status: "done" },
        { id: "cht_02", label: "cht_02", status: "active" },
      ],
      skipped: { photos: "IMAGE_API_BASE_URL empty" },
    });
    const charts = rows.find((r) => r.id === "charts");
    const photos = rows.find((r) => r.id === "photos");
    assert.ok(charts);
    assert.equal(charts.state, "active");
    assert.equal(charts.substeps?.length, 2);
    assert.equal(photos?.state, "skipped");
    assert.match(photos?.reason || "", /IMAGE/);
  });

  it("formats ETA only when confident", () => {
    assert.equal(formatEtaSuffix(null), "");
    assert.equal(formatEtaSuffix(3), "");
    assert.equal(formatEtaSuffix(42), " · ещё ~42 с");
  });

  it("keeps mid-step active when cancel-frozen", () => {
    const rows = craftProgress("latex", "report", {
      live: false,
      frozen: true,
    });
    const pdf = rows.find((r) => r.id === "pdf");
    assert.equal(pdf?.state, "active");
  });

  it("formats success recap without plaques", () => {
    const line = formatCraftRecap({
      elapsed_s: 134,
      charts: 3,
      figures: 1,
      formats: ["pdf", "docx"],
    });
    assert.match(line, /Собрано за 2:14/);
    assert.match(line, /PDF/);
    assert.match(line, /3 графика/);
    assert.doesNotMatch(line, /готов/i);
  });

  it("upserts film frames", () => {
    let film = upsertCraftFilm([], {
      id: "cht_01",
      kind: "chart",
      url: "/api/runs/r/figures/cht_01.png",
    });
    film = upsertCraftFilm(film, {
      id: "cht_01",
      kind: "chart",
      url: "/api/runs/r/figures/cht_01.png?v=2",
    });
    assert.equal(film.length, 1);
    assert.match(film[0].url, /v=2/);
  });
});
