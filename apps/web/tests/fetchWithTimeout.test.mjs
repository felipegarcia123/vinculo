import assert from "node:assert/strict";
import test from "node:test";
import { fetchWithTimeout } from "../lib/fetchWithTimeout.mjs";

test("a stalled API request is aborted and returns a clear error", async () => {
  const fetchImplementation = (_input, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
  });

  await assert.rejects(
    fetchWithTimeout("/api/v1/auth/me", {}, 10, fetchImplementation),
    /El servicio tardó demasiado en responder/,
  );
});
