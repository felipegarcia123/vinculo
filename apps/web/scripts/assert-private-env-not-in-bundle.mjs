import { access, readFile, readdir } from "node:fs/promises";
import { extname, join } from "node:path";

const testRoot = process.env.VINCULO_CLIENT_BUNDLE_DIR;
const publicRoots = testRoot
  ? [{ path: testRoot, required: true }]
  : [
      { path: ".next/static", required: true },
      { path: "public", required: false },
      {
        path: ".next/server/app",
        required: false,
        extensions: new Set([".html", ".rsc", ".body", ".meta", ".json", ".txt"]),
      },
      {
        path: ".next/server/pages",
        required: false,
        extensions: new Set([".html", ".json", ".txt"]),
      },
    ];
const canaries = [
  ["DATABASE_URL", process.env.VINCULO_CI_DATABASE_CANARY],
  ["AUTH_RATE_LIMIT_SECRET", process.env.VINCULO_CI_AUTH_CANARY],
  ["NEON_API_KEY", process.env.VINCULO_CI_NEON_CANARY],
].filter(([, value]) => typeof value === "string" && value.length > 0);

if (canaries.length !== 3) {
  throw new Error("Expected all three CI-only private-value canaries.");
}

async function listFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? listFiles(path) : [path];
  }));
  return nested.flat();
}

const fileGroups = await Promise.all(publicRoots.map(async (root) => {
  try {
    await access(root.path);
  } catch {
    if (root.required) throw new Error(`Expected public build output at ${root.path}.`);
    return [];
  }
  const files = await listFiles(root.path);
  return root.extensions ? files.filter((file) => root.extensions.has(extname(file))) : files;
}));
const files = fileGroups.flat();
const leakedNames = new Set();
for (const file of files) {
  const content = await readFile(file);
  for (const [name, value] of canaries) {
    if (content.includes(Buffer.from(value))) leakedNames.add(name);
  }
}

if (leakedNames.size > 0) {
  throw new Error(`Private CI canary found in browser bundle: ${[...leakedNames].join(", ")}`);
}

console.log("Private environment canaries are absent from browser assets.");
