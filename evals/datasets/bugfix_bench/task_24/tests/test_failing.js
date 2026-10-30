const assert = require("assert");
const { test } = require("node:test");
const { createCallbacks } = require("../src/callbacks.js");

test("closure values", () => {
  const cbs = createCallbacks(3);
  assert.strictEqual(cbs[0](), 0);
  assert.strictEqual(cbs[1](), 1);
  assert.strictEqual(cbs[2](), 2);
});
