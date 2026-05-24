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

test("web API maps backend water sensor fields into dashboard readings", async () => {
  const source = await readText("../src/api/devices.ts");

  for (const requiredText of [
    "water_temperature_c?: number | null;",
    "water_level_raw?: number | null;",
    "water_level_state?: string | null;",
    "waterTemperatureC: reading.water_temperature_c ?? undefined,",
    "waterLevelRaw: reading.water_level_raw ?? undefined,",
    "waterLevelState: reading.water_level_state ?? undefined,",
    "function mergeLatestReadingIntoHistory",
    "READING_LIMIT_BY_RANGE",
    '"24h": 5000',
    '"7d": 25000',
    '"30d": 50000',
    'new URLSearchParams({ limit: String(READING_LIMIT_BY_RANGE[range]), order: "newest" })',
    ".sort((left, right) => new Date(left.timestamp).getTime() - new Date(right.timestamp).getTime())",
    "history: mergeLatestReadingIntoHistory(mappedHistory, latestReading),",
  ]) {
    assert.match(source, escaped(requiredText));
  }
});

test("web dashboards summarize water readings instead of stale soil moisture", async () => {
  const listSource = await readText("../src/screens/DeviceListScreen.tsx");
  const historySource = await readText("../src/screens/HistoryScreen.tsx");
  const mockSource = await readText("../src/mock/data.ts");

  for (const requiredText of [
    "Water ${device.latestReading.waterTemperatureC?.toFixed(1) ?? \"--\"} C",
    "Level ${device.latestReading.waterLevelState ?? \"--\"}",
    "Water {reading.waterTemperatureC?.toFixed(1) ?? \"--\"} C",
    "Water level {reading.waterLevelState ?? \"unknown\"}",
    "waterTemperatureC: 20.4",
    "waterLevelRaw: 35200",
    'waterLevelState: "ok"',
  ]) {
    assert.match(`${listSource}\n${historySource}\n${mockSource}`, escaped(requiredText));
  }

  assert.doesNotMatch(listSource, /soilMoisturePercent/);
  assert.doesNotMatch(historySource, /soilMoisturePercent/);
  assert.doesNotMatch(mockSource, /waterLevelPercent/);
});

test("web sensor trends render water temperature without a water level chart", async () => {
  const trendSource = await readText("../src/components/ReadingTrendSection.tsx");

  for (const requiredText of [
    "Water temp",
    "waterTemperatureC",
    "trend-line-chart",
    "trend-y-axis",
    "buildValueDomain",
    "formatAxisValue",
    "readings • Min",
    "minDomainSpan: 5",
    "outlier",
    "Math.abs(value - 85) > 0.01",
  ]) {
    assert.match(trendSource, escaped(requiredText));
  }

  assert.doesNotMatch(trendSource, /Water level raw|waterLevelRaw/);
  assert.doesNotMatch(trendSource, /trend-bars|trend-bar/);
});

test("web hardware health expands needs attention into visible reasons", async () => {
  const panelSource = await readText("../src/components/HardwareHealthPanel.tsx");
  const styleSource = await readText("../src/styles/app.css");
  const dashboardSource = await readText("../src/screens/DeviceDashboardScreen.tsx");
  const settingsSource = await readText("../src/screens/DeviceSettingsScreen.tsx");

  for (const requiredText of [
    "function getAttentionItems",
    "attention-panel",
    "attention-dismiss",
    "Dismiss",
    "Reviewed",
    "Backend reported an issue but did not include a specific reason.",
    "attentionItems.length ? attentionItems.join",
    "HardwareHealthPanel",
    "health={details?.hardwareHealth}",
  ]) {
    assert.match(`${panelSource}\n${styleSource}\n${settingsSource}`, escaped(requiredText));
  }

  assert.doesNotMatch(dashboardSource, /HardwareHealthPanel|CommandActivityPanel/);
});
