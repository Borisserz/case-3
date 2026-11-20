import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { splitDashboardBlocks } from "./dashboardTables.ts";

const wide = [
  "# Данные дашборда",
  "",
  "Числа скопированы из ячеек PDF.",
  "",
  "## Таблица PDF",
  "",
  "| Налог | Факт | План | Доля |",
  "| --- | --- | --- | --- |",
  "| НДС | 1 234,56 | 100,0 | 17,8% |",
  "| Акциз | 77 | 77 | -12,4% |",
  "| A\\|B |  | 3 |  |",
].join("\n");

describe("splitDashboardBlocks", () => {
  it("keeps every column, a repeated neighbour, and an escaped pipe", () => {
    const blocks = splitDashboardBlocks(wide);
    const table = blocks.find((block) => block.kind === "table");
    assert.ok(table && table.kind === "table");
    assert.deepEqual(table.header, ["Налог", "Факт", "План", "Доля"]);
    assert.equal(table.rows[0][1], "1 234,56");
    assert.equal(table.rows[1][1], "77");
    assert.equal(table.rows[1][2], "77");
    assert.equal(table.rows[2][0], "A|B");
    assert.equal(table.rows.length, 3);
    assert.deepEqual(table.numeric, [false, true, true, true]);
  });

  it("drops the machine intro and keeps the table title", () => {
    const blocks = splitDashboardBlocks(wide);
    const text = blocks
      .filter((block) => block.kind === "heading")
      .map((block) => block.text);
    assert.deepEqual(text, ["Таблица PDF"]);
    assert.equal(
      blocks.some(
        (block) => block.kind === "text" && block.text.includes("скопированы"),
      ),
      false,
    );
  });

  it("counts a wide grid without dropping the last column", () => {
    const header = ["Название", ...Array.from({ length: 20 }, (_, i) => `c${i}`)];
    const row = ["НДС", ...Array.from({ length: 20 }, (_, i) => String(i))];
    const md = [
      `| ${header.join(" | ")} |`,
      `| ${header.map(() => "---").join(" | ")} |`,
      `| ${row.join(" | ")} |`,
    ].join("\n");
    const table = splitDashboardBlocks(md).find((block) => block.kind === "table");
    assert.ok(table && table.kind === "table");
    assert.equal(table.header.length, 21);
    assert.equal(table.header[20], "c19");
    assert.equal(table.rows[0][20], "19");
    assert.equal(table.numeric[0], false);
    assert.equal(table.numeric[20], true);
  });
});
