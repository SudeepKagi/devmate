const assert = require("assert");
const { test } = require("node:test");
const { cloneConfig } = require("../src/config.js");

test("hidden multi level", () => {
  const orig = { db: { host: "localhost" } };
  const cl = cloneConfig(orig, { db: { host: "remote" } });
  assert.strictEqual(orig.db.host, "localhost");
});
