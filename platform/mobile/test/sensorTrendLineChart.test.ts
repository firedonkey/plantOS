import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testDir = dirname(fileURLToPath(import.meta.url));
const readText = (path: string) => readFile(join(testDir, path), "utf8");
const readJson = async (path: string) => JSON.parse(await readText(path));

test("mobile sensor trends use a native-module-free line chart", async () => {
  const packageConfig = await readJson("../package.json");
  const chartSource = await readText("../src/components/SensorLineChart.tsx");

  assert.equal(packageConfig.dependencies["react-native-svg"], undefined);
  assert.doesNotMatch(chartSource, /react-native-svg|RNSVGSvgView|<Svg\b|<Path\b|<Circle\b|<Line\b/);
  assert.match(chartSource, /function LineSegment/);
  assert.match(chartSource, /rotateZ/);
});

test("reading trend cards render line charts for the approved sensor series", async () => {
  const trendSource = await readText("../src/components/ReadingTrendSection.tsx");

  assert.match(trendSource, /import \{ SensorLineChart \}/);
  assert.match(trendSource, /<SensorLineChart points=\{chartPoints\} color=\{color\} \/>/);
  assert.match(trendSource, /Current \$\{latest\.toFixed\(1\)\}/);

  for (const requiredText of [
    "Temperature",
    "Humidity",
    "Soil moisture",
    "temperatureC",
    "humidityPercent",
    "soilMoisturePercent",
  ]) {
    assert.match(trendSource, new RegExp(requiredText));
  }

  assert.doesNotMatch(trendSource, /styles\.bars|styles\.bar\b|maxRange|barHeight/);
});

test("sensor line chart keeps safeguards for empty, sparse, missing, and dense histories", async () => {
  const chartSource = await readText("../src/components/SensorLineChart.tsx");

  for (const requiredText of [
    "No data",
    "getXAxisLabels",
    "getYAxisLabels",
    "formatTimeLabel",
    "formatAxisNumber",
    "validPoints.length === 1",
    "splitSegments",
    "downsamplePoints",
    "MAX_RENDER_POINTS = 240",
    "getYDomain",
    "parseTimestamp",
    "Number.isFinite",
  ]) {
    assert.match(chartSource, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});

test("dense missing-value histories are budgeted before valid runs are sampled", async () => {
  const chartSource = await readText("../src/components/SensorLineChart.tsx");

  assert.match(chartSource, /const selectedRuns = selectRunsForBudget\(runs, targetCount\);/);
  assert.match(chartSource, /const budgets = allocateRunBudgets\(selectedRuns, targetCount\);/);
  assert.match(chartSource, /Math\.max\(targetCount - selectedIndexes\.size, 0\)/);
  assert.match(chartSource, /Math\.max\(targetCount - selectedRuns\.length, 0\)/);
  assert.match(chartSource, /downsampleValidRun\(run, budgets\.get\(runIndex\) \?\? 1, anchor\)/);
  assert.match(chartSource, /runId: runIndex/);
  assert.match(chartSource, /current\[current\.length - 1\]\.runId !== point\.runId/);
});
