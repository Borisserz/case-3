import assert from "node:assert/strict";
import test from "node:test";
import { messagesFromMemory, priorRunIdFromMessages } from "./priorRun";

test("priorRunIdFromMessages uses the latest bot run, skipping an empty pending bubble", () => {
  const id = priorRunIdFromMessages([
    { role: "user", text: "первый" },
    { role: "bot", text: "готово", result: { run_id: "run_a" } },
    { role: "user", text: "короче" },
    { role: "bot", text: "жду", pending: true },
  ]);
  assert.equal(id, "run_a");
});

test("priorRunIdFromMessages stays on the chat head after the rail shows an older file", () => {
  const id = priorRunIdFromMessages([
    {
      role: "bot",
      result: { run_id: "report_run", chain_head: "chat_head" },
    },
  ]);
  assert.equal(id, "chat_head");
});

test("priorRunIdFromMessages is empty on a fresh chat", () => {
  assert.equal(priorRunIdFromMessages([]), null);
  assert.equal(
    priorRunIdFromMessages([{ role: "user", text: "только вопрос" }]),
    null,
  );
});

test("messagesFromMemory keeps the chat in order, including a later edit", () => {
  let n = 0;
  const lines = messagesFromMemory(
    [
      {
        run_id: "a",
        chat_prompt: "первый",
        chat_summary: "ответ 1",
      },
      {
        run_id: "b",
        chat_prompt: "переделай введение",
        chat_summary: "Переписал",
        dialogue: [
          { user: "ещё точнее", assistant: "Переписал раздел «Введение»" },
        ],
      },
    ],
    () => `id${(n += 1)}`,
  );
  assert.deepEqual(
    lines.map((line) => line.text),
    [
      "первый",
      "ответ 1",
      "переделай введение",
      "Переписал",
      "ещё точнее",
      "Переписал раздел «Введение»",
    ],
  );
  assert.equal(lines[0].role, "user");
  assert.equal(lines.at(-1)?.role, "bot");
});

test("messagesFromMemory keeps uploaded photos on the user line", () => {
  let n = 0;
  const lines = messagesFromMemory(
    [
      {
        chat_prompt: "смотри",
        chat_summary: "вижу",
        photos: [{ name: "usr_01", url: "/api/runs/a/figures/usr_01.png" }],
      },
    ],
    () => `id${(n += 1)}`,
  );
  assert.equal(lines[0].role, "user");
  assert.deepEqual(lines[0].photos, [
    { name: "usr_01", url: "/api/runs/a/figures/usr_01.png" },
  ]);
  assert.equal(lines[1].photos, undefined);
});
