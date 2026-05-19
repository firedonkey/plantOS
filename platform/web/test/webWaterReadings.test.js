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
