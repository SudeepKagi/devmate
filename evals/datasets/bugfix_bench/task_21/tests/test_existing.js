const assert = require("assert");
const { test } = require("node:test");
const { sortNumbers } = require("../src/sorter.js");

test("single element", () => {
  assert.deepStrictEqual(sortNumbers([1]), [1]);
});
