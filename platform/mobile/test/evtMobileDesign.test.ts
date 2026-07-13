import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testDir = dirname(fileURLToPath(import.meta.url));
const readText = (path: string) => readFile(join(testDir, path), "utf8");
const escaped = (text: string) => new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));

test("EVT mobile routes map to the supplied seven reference screens", async () => {
  const [tabsSource, indexSource, registerRoute, caseRoute, dashboardRoute, supportRoute] = await Promise.all([
    readText("../app/(app)/_layout.tsx"),
    readText("../app/index.tsx"),
    readText("../app/register.tsx"),
    readText("../app/(app)/case.tsx"),
    readText("../app/(app)/dashboard.tsx"),
    readText("../app/(app)/support.tsx"),
  ]);

  for (const requiredText of [
    'title: "Home"',
    'title: "Case"',
    'title: "Data"',
    'name="settings" options={{ href: null',
    'name="support" options={{ href: null',
  ]) {
    assert.match(tabsSource, escaped(requiredText));
  }

  assert.match(indexSource, /<Redirect href="\/login" \/>/);
  assert.match(registerRoute, /RegisterScreen/);
  assert.match(caseRoute, /CaseScreen/);
  assert.match(dashboardRoute, /DashboardTabScreen/);
  assert.match(supportRoute, /SupportScreen/);
});

test("EVT assets are curated and renamed from Figma exports", async () => {
  const assetSource = await readText("../src/assets/evtAssets.ts");

  for (const requiredText of [
    '["image 93.png", "auth-leaf-frame.png"]',
    '["Group 117.png", "plantlab-leaf-logo.png"]',
    '["Group 144.png", "plantlab-wordmark.png"]',
    '["pngsucai_1395069_3c5c6c 1.png", "google-icon.png"]',
    '["Vector.png", "apple-icon.png"]',
    "evtAssetMapping",
  ]) {
    assert.match(assetSource, escaped(requiredText));
  }

  assert.doesNotMatch(assetSource, /Login\.png|Register\.png|Landing Page\.png|Dashboard\.png|Setting\.png|Support\.png/);
});

test("EVT register and support screens avoid fake account creation and secret exposure", async () => {
  const [registerSource, supportSource] = await Promise.all([
    readText("../src/screens/RegisterScreen.tsx"),
    readText("../src/screens/SupportScreen.tsx"),
  ]);

  for (const requiredText of [
    "Registration unavailable",
    "Account registration is not enabled in this EVT mobile build.",
    "Enter your mobile phone number",
    "Enter the verification code",
  ]) {
    assert.match(registerSource, escaped(requiredText));
  }

  for (const requiredText of [
    '<EvtInfoRow label="Device ID"',
    '<EvtInfoRow label="Plant type"',
    '<EvtInfoRow label="uptime"',
    '<EvtInfoRow label="firmware"',
    '<EvtInfoRow label="Application version"',
  ]) {
    assert.match(supportSource, escaped(requiredText));
  }

  assert.doesNotMatch(`${registerSource}\n${supportSource}`, /refreshToken|api_token|password|secret/i);
});
