import assert from "node:assert/strict";
import test from "node:test";
import { homeForRole } from "../lib/auth-routing.mjs";

test("sends every authenticated role to its Vínculo panel", () => {
  assert.equal(homeForRole("owner"), "/loyalty/owner");
  assert.equal(homeForRole("cashier"), "/loyalty/cashier");
  assert.equal(homeForRole("customer"), "/loyalty");
});

test("unknown roles fail closed to login", () => {
  assert.equal(homeForRole("unexpected"), "/login");
});
