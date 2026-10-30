const assert = require("assert");
const { test } = require("node:test");
const { getUserCity } = require("../src/address.js");

test("hidden null address", () => {
  assert.strictEqual(getUserCity({ address: null }), undefined);
});
