const assert = require("assert");
const { test } = require("node:test");
const { cloneConfig } = require("../src/config.js");

test("shallow copy", () => {
  assert.strictEqual(cloneConfig({ env: "prod" }).env, "prod");
});
