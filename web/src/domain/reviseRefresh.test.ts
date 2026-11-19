import assert from "node:assert/strict";
import test from "node:test";
import {
  chatToReopen,
  historyRailRun,
  offersNewChat,
  revisedRailPlan,
  reviseSurface,
} from "./reviseRefresh";

test("only a full chat offers a new-chat button", () => {
  assert.equal(offersNewChat("full"), true);
  assert.equal(offersNewChat("ask"), false);
  assert.equal(offersNewChat("rewrite"), false);
});

test("a renamed section and a new slide open the right rail", () => {
  assert.equal(reviseSurface("rename_heading"), "report");
  assert.equal(reviseSurface("retype_chart"), "report");
  assert.equal(reviseSurface("add_slide"), "deck");
  assert.equal(reviseSurface("slide_text"), "deck");
  assert.equal(reviseSurface("slide_bullets"), "deck");
  assert.equal(reviseSurface("replace_cell"), "report");
  assert.equal(reviseSurface("add_item"), "report");
  assert.equal(reviseSurface("refine_diagram"), "report");
});

test("a deck edit refreshes the presentation rail", () => {
  assert.equal(reviseSurface("reorder_slide"), "deck");
  assert.equal(reviseSurface("recolor_deck"), "deck");
  assert.equal(reviseSurface("delete_slide"), "deck");
  assert.equal(reviseSurface("retitle", "deck"), "deck");
});

test("a report edit refreshes the report rail and a question does not", () => {
  assert.equal(reviseSurface("rewrite"), "report");
  assert.equal(reviseSurface("retype_charts"), "report");
  assert.equal(reviseSurface("retitle", "report"), "report");
  assert.equal(reviseSurface("ask"), null);
  assert.equal(reviseSurface(""), null);
});

test("a later chat edit opens the file and keeps the next message on the head", () => {
  const plan = revisedRailPlan("chat_head", "report_run", "report");
  assert.equal(plan.fetchId, "report_run");
  assert.equal(plan.chainHead, "chat_head");
  assert.equal(plan.tab, "preview");
  assert.equal(revisedRailPlan("deck_run", "", "deck").tab, "presentation");
});

test("reopening a chat with only later answers still shows the report", () => {
  assert.equal(
    historyRailRun({ run_id: "chat_head", output_mode: "chat" }, "report_run"),
    "report_run",
  );
  assert.equal(
    historyRailRun(
      { run_id: "report_run", preview: { blocks: [{ kind: "p" }] } },
      "report_run",
    ),
    "report_run",
  );
});

test("reload reopens only the chat that was open", () => {
  const items = [{ runId: "a" }, { runId: "b" }];
  assert.equal(chatToReopen(items, "b", false), "b");
  assert.equal(chatToReopen(items, "b", true), "");
  assert.equal(chatToReopen(items, "missing", false), "");
  assert.equal(chatToReopen(items, "", false), "");
});
