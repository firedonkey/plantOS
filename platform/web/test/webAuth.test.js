import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testDir = dirname(fileURLToPath(import.meta.url));
const readText = (path) => readFile(join(testDir, path), "utf8");

function escaped(text) {
  return new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
}

test("web login exposes backend-owned Apple and Google auth starts", async () => {
  const authSource = await readText("../src/api/auth.ts");
  const loginSource = await readText("../src/screens/LoginScreen.tsx");
  const styleSource = await readText("../src/styles/app.css");

  for (const requiredText of [
    "getAppleAuthStartUrl",
    "/api/auth/apple/start?",
    "Continue with Apple",
    "startAppleAuth",
    "apple-auth-button",
    "Continue with Google",
    "getGoogleAuthStartUrl",
    "loginWithDemoAccount",
    "/api/auth/demo",
    "Try PlantLab Demo",
    "startDemoAuth",
    "is_demo_user",
  ]) {
    assert.match(`${authSource}\n${loginSource}\n${styleSource}`, escaped(requiredText));
  }
});
