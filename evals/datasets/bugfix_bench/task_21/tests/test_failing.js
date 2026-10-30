const assert = require("assert");
const { test } = require("node:test");
const { sortNumbers } = require("../src/sorter.js");

test("numerical sort order", () => {
  assert.deepStrictEqual(sortNumbers([10, 2, 5]), [2, 5, 10]);
});
