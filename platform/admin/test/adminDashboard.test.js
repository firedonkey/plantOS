const { readFile } = require("node:fs/promises");
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { join } = require("node:path");

const root = join(__dirname, "..");

test("admin dashboard is separate from the user web app and calls admin diagnostics", async () => {
  const source = await readFile(join(root, "src/main.js"), "utf8");

  assert.match(source, /\/api\/admin\/diagnostics/);
  assert.match(source, /user\?\.is_admin/);
  assert.match(source, /PLANTLAB_ADMIN_CONFIG/);
  assert.doesNotMatch(source, /devices\/add/);
});

test("admin static server injects runtime API base URL without rebuilding", async () => {
  const source = await readFile(join(root, "server.js"), "utf8");

  assert.match(source, /\/config\.js/);
  assert.match(source, /PLANTLAB_ADMIN_API_BASE_URL/);
  assert.match(source, /VITE_API_BASE_URL/);
});
