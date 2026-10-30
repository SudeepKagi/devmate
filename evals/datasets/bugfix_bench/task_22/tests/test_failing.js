const assert = require("assert");
const { test } = require("node:test");
const { getUserDisplayName } = require("../src/user.js");

test("displayName resolves value", async () => {
  const res = await getUserDisplayName(1);
  assert.strictEqual(res, "User: Alice");
});
