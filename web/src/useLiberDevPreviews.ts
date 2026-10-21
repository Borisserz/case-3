/**
 * Visual QA bootstraps (?preview=artifact|flow).
 * No-ops unless the matching query string is present.
 */

import { useEffect, type Dispatch, type SetStateAction } from "react";
import type { ActiveArtifact } from "./ArtifactRail";
import type { ThinkingLine } from "./pipelinePhrases";
import type { Msg, RunResult, SourceDraft } from "./liberTypes";
import {
  appendBotThinking,
  reportTitle,
  stageLabel,
} from "./liberRunHelpers";

type SetMsgs = Dispatch<SetStateAction<Msg[]>>;

export function useLiberDevPreviews({
  setMsgs,
  setBusy,
  setSourceDraft,
  setActiveArtifact,
}: {
  setMsgs: SetMsgs;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setSourceDraft: Dispatch<SetStateAction<SourceDraft | null>>;
  setActiveArtifact: Dispatch<SetStateAction<ActiveArtifact | null>>;
}): void {
  // Visual QA: http://127.0.0.1:5173/?preview=artifact
  useEffect(() => {
    if (!/preview=artifact/.test(window.location.search)) return;
    const id = "preview-artifact";
    const result: RunResult = {
      run_id: "source_20261021T082640Z",
      status: "ok",
      downloads: {
        pdf: "/api/runs/source_20261021T082640Z/files/source.pdf",
        docx: "/api/runs/source_20261021T082640Z/files/source.docx",
      },
      preview: {
        title: "Northstar Labs — демо",
        blocks: [
          { type: "heading", level: 1, text: "Итоги квартала" },
          {
            type: "paragraph",
            text: "Рост ускоряется, качество растёт вместе с ним. Это демо Artifact rail.",
          },
          { type: "heading", level: 2, text: "Ключевые метрики" },
          {
            type: "table",
            caption: "KPI",
            headers: ["Метрика", "Q2", "Q3"],
            rows: [
              ["Выручка", "12.4", "14.1"],
              ["NPS", "42", "51"],
            ],
          },
          { type: "heading", level: 2, text: "График" },
          {
            type: "figure",
            id: "cht_01",
            kind: "chart",
            caption: "Распределение бюджета по категориям, %",
            url: "/api/runs/source_20261021T082640Z/figures/cht_01.png",
            chartType: "donut",
            pdfPage: 1,
          },
          { type: "heading", level: 2, text: "Выводы" },
          {
            type: "paragraph",
            text: "Качество растёт вместе с объёмом — смотрите TOC и кнопку PDF на рисунке.",
          },
        ],
      },
      charts_ok: 1,
      figures_ok: 0,
      charts_planned: ["cht_01"],
      figures_planned: [],
      warnings: [],
    };
    setMsgs([
      {
        id: "preview-user",
        role: "user",
        text:
          "Собери отчёт по демо: таблица KPI, один line-график, спокойная палитра atelier, без лишней воды и без выдуманных цифр — только Source.",
        chips: ["демо", "палитра: atelier", "графики: ≤2"],
        attachment: {
          title: "northstar_demo.md",
          text: "# Source\n\nДемонстрационный файл для вкладки Source.\n",
          fileName: "northstar_demo.md",
        },
      },
      {
        id,
        role: "bot",
        text:
          "Собрал демо-отчёт: структура, таблица и график по числам из Source.\n\nПодробности — в полном документе справа.",
        result,
      },
    ]);
    setSourceDraft({
      title: "northstar_demo.md",
      text: "# Source\n\nДемонстрационный файл для вкладки Source.\n",
      fileName: "northstar_demo.md",
    });
    setActiveArtifact({
      kind: "report",
      msgId: id,
      tab: "preview",
      title: reportTitle(result),
    });
  }, [setMsgs, setSourceDraft, setActiveArtifact]);

  // Visual QA: http://127.0.0.1:5173/?preview=flow
  useEffect(() => {
    if (!/preview=flow/.test(window.location.search)) return;
    const stages = [
      "queued",
      "llm",
      "charts",
      "inject",
      "latex",
      "docx",
      "ok",
    ] as const;
    const id = "preview-flow";
    let i = 0;
    let thinking: ThinkingLine[] = [];
    let thinkingStartedAt = Date.now();
    let thinkingStageKey: string | undefined;
    let thinkingStageAt = Date.now();
    const tick = () => {
      const idx = i % stages.length;
      if (idx === 0 && i > 0) {
        thinking = [];
        thinkingStartedAt = Date.now();
        thinkingStageKey = undefined;
        thinkingStageAt = Date.now();
      }
      const stage = stages[idx];
      const detail = stage === "charts" ? "cht_01" : null;
      setBusy(stage !== "ok");
      if (stage === "ok") {
        setMsgs([
          {
            id: "preview-user",
            role: "user",
            text: "Intent · preview flow",
          },
          {
            id,
            role: "bot",
            text: "Готово · preview — структура ясна, отчёт собран.",
            pending: false,
            thinking,
            thinkingStartedAt,
            thinkingElapsedSec: Math.max(
              0,
              Math.round((Date.now() - thinkingStartedAt) / 1000),
            ),
            result: {
              run_id: "preview-flow",
              status: "ok",
              downloads: {},
              charts_ok: 0,
              figures_ok: 0,
              charts_planned: [],
              figures_planned: [],
              warnings: [],
            },
          },
        ]);
      } else {
        const draft = appendBotThinking(
          {
            id,
            role: "bot",
            text: stageLabel(stage, detail),
            pending: true,
            pendingStage: stage,
            pendingDetail: detail,
            thinking,
            thinkingStartedAt,
            thinkingStageKey,
            thinkingStageAt,
          },
          stage,
          detail,
        );
        thinking = draft.thinking || [];
        thinkingStartedAt = draft.thinkingStartedAt || thinkingStartedAt;
        thinkingStageKey = draft.thinkingStageKey;
        thinkingStageAt = draft.thinkingStageAt || thinkingStageAt;
        setMsgs([
          {
            id: "preview-user",
            role: "user",
            text: "Intent · preview flow",
          },
          draft,
        ]);
      }
      i += 1;
    };
    tick();
    const t = window.setInterval(tick, 1400);
    return () => window.clearInterval(t);
  }, [setMsgs, setBusy]);
}
