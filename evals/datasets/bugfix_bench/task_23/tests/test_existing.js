const assert = require("assert");
const { test } = require("node:test");
const { getUserCity } = require("../src/address.js");

test("valid user", () => {
  assert.strictEqual(getUserCity({ address: { city: "Paris" } }), "Paris");
});
