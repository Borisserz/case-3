/** Node smoke for pure Liber helpers (run: npx tsx --test if available). */

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { modeSurfaces } from "./liberModes";
import {
  formatRunStatusError,
  provisionalSessionTitle,
  reportReadyText,
  reportTitle,
  stageLabel,
} from "./liberRunHelpers";

describe("liberRunHelpers", () => {
  it("stageLabel charts detail", () => {
    assert.equal(stageLabel("charts", "cht_01"), "Рисую cht_01…");
    assert.equal(stageLabel("latex"), "Собираю PDF…");
  });

  it("stageLabel scales by thinking mode", () => {
    assert.match(stageLabel("llm", null, "diagram"), /схем/i);
    assert.match(stageLabel("llm", null, "presentation"), /слайд/i);
    assert.match(stageLabel("slides_render", null, "presentation"), /twin|превью/i);
  });

  it("reportReadyText prefers chat_summary", () => {
    assert.equal(
      reportReadyText({ chat_summary: "  Итог  " } as never, "stream"),
      "Итог",
    );
    assert.equal(reportReadyText(undefined, " streamed "), "streamed");
    assert.equal(reportReadyText(), "Отчёт готов");
  });

  it("reportTitle prefers preview.title", () => {
    assert.equal(
      reportTitle({
        run_id: "r1",
        preview: { title: "  Board Update  " },
      } as never),
      "Board Update",
    );
    assert.equal(
      reportTitle({ run_id: "r2", output_mode: "diagram" } as never),
      "Схема · r2",
    );
  });

  it("provisionalSessionTitle by mode", () => {
    assert.equal(provisionalSessionTitle("report"), "Новый отчёт");
    assert.equal(provisionalSessionTitle("diagram"), "Новая схема");
    assert.equal(provisionalSessionTitle("presentation"), "Новая презентация");
  });

  it("modeSurfaces gates artifacts by Liber mode", () => {
    const report = modeSurfaces("report");
    assert.equal(report.showReportPreview, true);
    assert.equal(report.showDiagram, true);
    assert.equal(report.showPresentation, false);
    assert.equal(report.showDeckMake, false);

    const diagram = modeSurfaces("diagram");
    assert.equal(diagram.showReportPreview, false);
    assert.equal(diagram.showReportPdf, false);
    assert.equal(diagram.showDiagram, true);
    assert.equal(diagram.showPresentation, false);

    const deck = modeSurfaces("presentation");
    assert.equal(deck.showReportPreview, false);
    assert.equal(deck.showDiagram, false);
    assert.equal(deck.showPresentation, true);
  });

  it("formatRunStatusError includes chart + TeX tail", () => {
    const msg = formatRunStatusError(
      {
        error: "latexmk failed",
        failed_charts: ["cht_02"],
        failed_figures: [],
        latex_log_tail: "a\n! Misplaced &\nend",
      },
      "run_x",
    );
    assert.match(msg, /latexmk failed/);
    assert.match(msg, /график cht_02/);
    assert.match(msg, /TeX:/);
    assert.match(msg, /Misplaced/);
    assert.match(msg, /run run_x/);
  });
});
