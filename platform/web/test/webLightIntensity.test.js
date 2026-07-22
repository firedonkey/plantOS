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

test("web dashboard queues ambient LED belt color commands separately from grow LED controls", async () => {
  const dashboardSource = await readText("../src/screens/DeviceDashboardScreen.tsx");
  const hookSource = await readText("../src/hooks/useDeviceDashboard.ts");
  const apiSource = await readText("../src/api/devices.ts");
  const typeSource = await readText("../src/types/api.ts");

  for (const requiredText of [
    "Ambient LED belt",
    "AMBIENT_LED_BELT_COLORS",
    'runCommand("ambient_belt_color", { ambientColor: option.color, ambientBrightness: ambientBeltBrightness })',
    'runCommand("ambient_belt_off")',
    'aria-label="Ambient LED belt brightness"',
  ]) {
    assert.match(dashboardSource, escaped(requiredText));
  }

  for (const requiredText of [
    'case "ambient_belt_color":',
    'case "ambient_belt_off":',
    'target: "ambient_led_belt"',
    'action: "set"',
    "path: (deviceId: string) => `/api/devices/${deviceId}/commands`,",
    "clampAmbientLedBeltBrightness(options?.ambientBrightness ?? AMBIENT_LED_BELT_DEFAULT_BRIGHTNESS)",
  ]) {
    assert.match(apiSource, escaped(requiredText));
  }

  assert.match(typeSource, escaped('"ambient_belt_color"'));
  assert.match(typeSource, escaped('"ambient_belt_off"'));
  assert.match(hookSource, escaped('return "Ambient LED belt color";'));
  assert.match(hookSource, escaped('return "Ambient LED belt off";'));
});
