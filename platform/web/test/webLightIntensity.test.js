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

test("web dashboard gates grow LED intensity controls on hardware capability support", async () => {
  const source = await readText("../src/screens/DeviceDashboardScreen.tsx");

  for (const requiredText of [
    "const lightIntensitySupported = hasLightIntensitySupport(dashboard?.hardwareHealth?.primary?.capabilities);",
    "lightIntensitySupported ? (",
    'aria-label="Grow LED brightness"',
    'type="range"',
    "function formatAge",
    "const commitLightIntensity = () => {",
    'runCommand("light_intensity", { intensityPercent: nextValue })',
    "dashboard?.device.currentLightOn ?? latestReading?.lightOn",
    "dashboard?.device.currentLightIntensityPercent ?? latestReading?.lightIntensityPercent",
    "capabilities.light_intensity_control === true",
    "capabilities.light_dimming === true",
    "capabilities.light_pwm === true",
    '["intensity", "dimming", "pwm"].includes(String(mode).toLowerCase())',
  ]) {
    assert.match(source, escaped(requiredText));
  }
});

test("web dashboard hides legacy pump actions from user-facing dashboard controls", async () => {
  const dashboardSource = await readText("../src/screens/DeviceDashboardScreen.tsx");
  const hookSource = await readText("../src/hooks/useDeviceDashboard.ts");
  const apiSource = await readText("../src/api/devices.ts");

  assert.doesNotMatch(dashboardSource, /pump|Pump/);
  assert.match(apiSource, escaped('.filter((command) => command.action !== "pump_run").slice(0, 6)'));
  assert.match(hookSource, escaped('return "Legacy command";'));
});

test("web device API sends grow LED intensity as backend light command payload", async () => {
  const source = await readText("../src/api/devices.ts");

  for (const requiredText of [
    'case "light_intensity":',
    "path: (deviceId: string) => `/api/devices/${deviceId}/commands/light`,",
    "method: \"POST\"",
    "body: JSON.stringify({ intensity_percent: options?.intensityPercent ?? 0 })",
  ]) {
    assert.match(source, escaped(requiredText));
  }
});
