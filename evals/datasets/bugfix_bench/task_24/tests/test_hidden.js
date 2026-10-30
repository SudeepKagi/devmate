const assert = require("assert");
const { test } = require("node:test");
const { createCallbacks } = require("../src/callbacks.js");

test("hidden single", () => {
  const cbs = createCallbacks(1);
  assert.strictEqual(cbs[0](), 0);
});
