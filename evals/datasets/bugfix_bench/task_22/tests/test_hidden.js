const assert = require("assert");
const { test } = require("node:test");
const { getUserDisplayName } = require("../src/user.js");

test("hidden check not containing promise", async () => {
  const res = await getUserDisplayName(99);
  assert.ok(!res.includes("[object Promise]"));
});
