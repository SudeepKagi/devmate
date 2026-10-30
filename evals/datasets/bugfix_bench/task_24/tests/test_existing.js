const assert = require("assert");
const { test } = require("node:test");
const { createCallbacks } = require("../src/callbacks.js");

test("length", () => {
  assert.strictEqual(createCallbacks(3).length, 3);
});
