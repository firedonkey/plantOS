import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testDir = dirname(fileURLToPath(import.meta.url));
const readText = (path: string) => readFile(join(testDir, path), "utf8");

function escaped(text: string) {
  return new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
}

test("mobile API maps backend water sensor fields into dashboard readings", async () => {
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

test("mobile surfaces water readings in list, dashboard, history, trends, and mocks", async () => {
  const listSource = await readText("../src/screens/DeviceListScreen.tsx");
  const dashboardSource = await readText("../src/screens/DeviceDashboardScreen.tsx");
  const historySource = await readText("../src/screens/HistoryScreen.tsx");
  const trendSource = await readText("../src/components/ReadingTrendSection.tsx");
  const mockSource = await readText("../src/mock/data.ts");

  for (const requiredText of [
    'DeviceMetric label="Water" value={formatMetric(latestReading?.waterTemperatureC, "C")}',
    'label="Water temp"',
    'label="Water level"',
    "Water {reading.waterTemperatureC?.toFixed(1) ?? \"--\"} C",
    "Water level {reading.waterLevelState ?? \"unknown\"}",
    "waterTemperatureC",
    "waterLevelRaw",
    "waterTemperatureC: 20.4",
    "waterLevelRaw: 35200",
    'waterLevelState: "ok"',
  ]) {
    assert.match(`${listSource}\n${dashboardSource}\n${historySource}\n${trendSource}\n${mockSource}`, escaped(requiredText));
  }

  assert.doesNotMatch(`${listSource}\n${dashboardSource}\n${historySource}`, /soilMoisturePercent/);
});
