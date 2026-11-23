import assert from "node:assert/strict";
import test from "node:test";
import { stripChatgptUtmSource } from "../lib/cleanChatgptUtm.mjs";

test("removes exact ChatGPT source tags and preserves all other query parameters", () => {
  const url = new URL(
    "https://vinculo.test/login?utm_source=chatgpt.com&utm_campaign=summer&keep=a%2Fb&utm_source=chatgpt.com",
  );

  assert.equal(stripChatgptUtmSource(url), true);
  assert.deepEqual([...url.searchParams.entries()], [
    ["utm_campaign", "summer"],
    ["keep", "a/b"],
  ]);
});

test("does not remove another source, casing, or a value that only contains the target", () => {
  const url = new URL(
    "https://vinculo.test/login?utm_source=other&utm_source=ChatGPT.com&utm_source=xchatgpt.com&next=%2Floyalty",
  );
  const before = url.search;

  assert.equal(stripChatgptUtmSource(url), false);
  assert.equal(url.search, before);
});

test("removes only the matching source while keeping blank and repeated unrelated values", () => {
  const url = new URL(
    "https://vinculo.test/login?utm_source=chatgpt.com&empty=&tag=one&tag=two&utm_medium=email",
  );

  assert.equal(stripChatgptUtmSource(url), true);
  assert.deepEqual([...url.searchParams.entries()], [
    ["empty", ""],
    ["tag", "one"],
    ["tag", "two"],
    ["utm_medium", "email"],
  ]);
});
