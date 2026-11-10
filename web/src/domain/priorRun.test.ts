import assert from "node:assert/strict";
import test from "node:test";
import { priorRunIdFromMessages } from "./priorRun";

test("priorRunIdFromMessages uses the latest bot run, skipping an empty pending bubble", () => {
  const id = priorRunIdFromMessages([
    { role: "user", text: "первый" },
    { role: "bot", text: "готово", result: { run_id: "run_a" } },
    { role: "user", text: "короче" },
    { role: "bot", text: "жду", pending: true },
  ]);
  assert.equal(id, "run_a");
});

test("priorRunIdFromMessages is empty on a fresh chat", () => {
  assert.equal(priorRunIdFromMessages([]), null);
  assert.equal(
    priorRunIdFromMessages([{ role: "user", text: "только вопрос" }]),
    null,
  );
});
