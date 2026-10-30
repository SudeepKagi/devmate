const assert = require("assert");
const { test } = require("node:test");
const { cloneConfig } = require("../src/config.js");

test("isolated nested db", () => {
  const original = { db: { port: 5432 } };
  const cloned = cloneConfig(original, { db: { port: 5433 } });
  assert.strictEqual(original.db.port, 5432, "Original was modified!");
  assert.strictEqual(cloned.db.port, 5433);
});
