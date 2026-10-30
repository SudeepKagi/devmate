const assert = require("assert");
const { test } = require("node:test");
const { getUserCity } = require("../src/address.js");

test("missing address returns undefined", () => {
  assert.strictEqual(getUserCity({}), undefined);
});
