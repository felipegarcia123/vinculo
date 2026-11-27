import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import test from "node:test";

const checker = resolve("scripts/assert-private-env-not-in-bundle.mjs");
const canaries = {
  VINCULO_CI_DATABASE_CANARY: "db-canary-test-only-981f",
  VINCULO_CI_AUTH_CANARY: "auth-canary-test-only-47ad",
  VINCULO_CI_NEON_CANARY: "neon-canary-test-only-530c",
};

async function withFixture(run) {
  const directory = await mkdtemp(join(tmpdir(), "vinculo-private-bundle-"));
  const publicFiles = join(directory, ".next", "static");
  await mkdir(publicFiles, { recursive: true });
  try {
    await run(directory, publicFiles);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
}

function runChecker(publicFiles) {
  return spawnSync(process.execPath, [checker], {
    cwd: process.cwd(),
    encoding: "utf8",
    env: {
      ...process.env,
      ...canaries,
      VINCULO_CLIENT_BUNDLE_DIR: publicFiles,
    },
  });
}

test("private bundle scan passes when public files contain no canaries", async () => {
  await withFixture(async (directory, staticFiles) => {
    await writeFile(join(staticFiles, "client.js"), "window.demo = true;");
    const html = join(directory, ".next", "server", "app");
    await mkdir(html, { recursive: true });
    await writeFile(join(html, "login.html"), "<main>Vínculo</main>");
    const result = runChecker(directory);

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /absent from browser assets/);
  });
});

test("private bundle scan fails and names the variable when a canary leaks", async () => {
  await withFixture(async (directory, _staticFiles) => {
    const publicHtml = join(directory, "public");
    await mkdir(publicHtml, { recursive: true });
    await writeFile(join(publicHtml, "leaked.html"), `<main>${canaries.VINCULO_CI_DATABASE_CANARY}</main>`);
    const result = runChecker(directory);
    const output = `${result.stdout}\n${result.stderr}`;

    assert.notEqual(result.status, 0);
    assert.match(output, /DATABASE_URL/);
    assert.doesNotMatch(output, new RegExp(canaries.VINCULO_CI_DATABASE_CANARY));
  });
});
