const assert = require("assert");
const { test } = require("node:test");
const { sortNumbers } = require("../src/sorter.js");

test("hidden negatives and large numbers", () => {
  assert.deepStrictEqual(sortNumbers([100, -5, 20, 0]), [-5, 0, 20, 100]);
});
