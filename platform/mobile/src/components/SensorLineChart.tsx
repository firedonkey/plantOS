import { useMemo, useState } from "react";
import { LayoutChangeEvent, StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";

export type SensorChartPoint = {
  timestamp: string;
  value?: number;
};

type SensorLineChartProps = {
  points: SensorChartPoint[];
  color: string;
  height?: number;
};

type RenderPoint = {
  index: number;
  runId?: number;
  timestamp: number | undefined;
  value: number | undefined;
};

type ScaledPoint = RenderPoint & {
  x: number;
  y: number;
};

const DEFAULT_HEIGHT = 132;
const MAX_RENDER_POINTS = 240;
const PADDING = {
  top: 10,
  right: 8,
  bottom: 28,
  left: 36,
};

export function SensorLineChart({ points, color, height = DEFAULT_HEIGHT }: SensorLineChartProps) {
  const [width, setWidth] = useState(0);

  const chart = useMemo(() => {
    if (width <= 0) {
      return null;
    }
    return buildChart(points, width, height);
  }, [height, points, width]);

  const handleLayout = (event: LayoutChangeEvent) => {
    const nextWidth = event.nativeEvent.layout.width;
    if (Math.abs(nextWidth - width) > 1) {
      setWidth(nextWidth);
    }
  };

  return (
    <View style={[styles.container, { height }]} onLayout={handleLayout}>
      {width <= 0 ? null : chart && chart.validPoints.length ? (
        <View style={StyleSheet.absoluteFill}>
          {chart.horizontalGrid.map((y, index) => (
            <View
              key={`horizontal-${index}`}
              style={[
                styles.horizontalGridLine,
                {
                  top: y,
                  left: PADDING.left,
                  right: PADDING.right,
                  backgroundColor: hexToRgba(theme.colors.chartGrid, 0.42),
                },
              ]}
            />
          ))}
          {chart.yAxisLabels.map((label, index) => (
            <Text key={`y-axis-${index}-${label.text}`} style={[styles.yAxisLabel, { top: label.y - 7 }]}>
              {label.text}
            </Text>
          ))}
          {chart.verticalGrid.map((x, index) => (
            <View
              key={`vertical-${index}`}
              style={[
                styles.verticalGridLine,
                {
                  left: x,
                  top: PADDING.top,
                  bottom: PADDING.bottom,
                  backgroundColor: hexToRgba(theme.colors.chartGrid, 0.22),
                },
              ]}
            />
          ))}
          {chart.xAxisLabels.map((label, index) => (
            <Text key={`x-axis-${index}-${label.text}`} style={[styles.xAxisLabel, { left: label.x - label.offset }]}>
              {label.text}
            </Text>
          ))}
          {chart.validPoints.length === 1 ? (
            <View
              style={[
                styles.referenceLine,
                {
                  top: chart.validPoints[0].y,
                  left: PADDING.left,
                  right: PADDING.right,
                  backgroundColor: hexToRgba(color, 0.25),
                },
              ]}
            />
          ) : null}
          {chart.segments.map((segment, index) => {
            if (segment.length === 1) {
              return (
                <View
                  key={`point-${index}`}
                  style={[
                    styles.pointMarker,
                    {
                      left: segment[0].x - 2,
                      top: segment[0].y - 2,
                      backgroundColor: hexToRgba(color, 0.72),
                    },
                  ]}
                />
              );
            }

            return (
              <View key={`segment-${index}`} style={StyleSheet.absoluteFill}>
                {segment.slice(0, -1).map((point, pointIndex) => (
                  <LineSegment key={`${point.index}-${segment[pointIndex + 1].index}`} color={color} from={point} to={segment[pointIndex + 1]} />
                ))}
              </View>
            );
          })}
          {chart.latestPoint ? (
            <View
              style={[
                styles.latestMarker,
                {
                  left: chart.latestPoint.x - 4,
                  top: chart.latestPoint.y - 4,
                  borderColor: color,
                },
              ]}
            />
          ) : null}
        </View>
      ) : (
        <View style={styles.noData}>
          <Text style={styles.noDataText}>No data</Text>
        </View>
      )}
    </View>
  );
}

function LineSegment({ from, to, color }: { from: ScaledPoint; to: ScaledPoint; color: string }) {
  const deltaX = to.x - from.x;
  const deltaY = to.y - from.y;
  const length = Math.hypot(deltaX, deltaY);

  if (length < 1) {
    return null;
  }

  return (
    <View
      style={[
        styles.lineSegment,
        {
          backgroundColor: color,
          left: from.x + deltaX / 2 - length / 2,
          top: from.y + deltaY / 2 - 1,
          transform: [{ rotateZ: `${Math.atan2(deltaY, deltaX)}rad` }],
          width: length,
        },
      ]}
    />
  );
}

function buildChart(points: SensorChartPoint[], width: number, height: number) {
  const sanitized = downsamplePoints(
    points.map((point, index) => ({
      index,
      timestamp: parseTimestamp(point.timestamp),
      value: typeof point.value === "number" && Number.isFinite(point.value) ? point.value : undefined,
    })),
    MAX_RENDER_POINTS,
  );

  const validValues = sanitized.map((point) => point.value).filter((value): value is number => value !== undefined);
  const validTimestamps = sanitized.map((point) => point.timestamp).filter((timestamp): timestamp is number => timestamp !== undefined);
  const xMin = validTimestamps.length >= 2 ? Math.min(...validTimestamps) : undefined;
  const xMax = validTimestamps.length >= 2 ? Math.max(...validTimestamps) : undefined;
  const yDomain = getYDomain(validValues);
  const plotWidth = Math.max(width - PADDING.left - PADDING.right, 1);
  const plotHeight = Math.max(height - PADDING.top - PADDING.bottom, 1);

  const scaled = sanitized.map((point, position) => {
    const xRatio = getXRatio(point, position, sanitized.length, xMin, xMax);
    const yRatio = point.value === undefined ? 0.5 : (point.value - yDomain.min) / (yDomain.max - yDomain.min);

    return {
      ...point,
      x: PADDING.left + xRatio * plotWidth,
      y: PADDING.top + (1 - yRatio) * plotHeight,
    };
  });

  const validPoints = scaled.filter((point) => point.value !== undefined);
  const latestPoint = validPoints.at(-1);

  return {
    horizontalGrid: [0, 0.5, 1].map((ratio) => PADDING.top + ratio * plotHeight),
    verticalGrid: [0.25, 0.5, 0.75].map((ratio) => PADDING.left + ratio * plotWidth),
    xAxisLabels: getXAxisLabels(xMin, xMax, plotWidth),
    yAxisLabels: getYAxisLabels(yDomain, plotHeight),
    latestPoint,
    segments: splitSegments(scaled),
    validPoints,
  };
}

function getYAxisLabels(yDomain: { min: number; max: number }, plotHeight: number) {
  return [0, 0.5, 1].map((ratio) => ({
    text: formatAxisNumber(yDomain.max - ratio * (yDomain.max - yDomain.min), yDomain),
    y: PADDING.top + ratio * plotHeight,
  }));
}

function getXAxisLabels(xMin: number | undefined, xMax: number | undefined, plotWidth: number) {
  if (xMin === undefined || xMax === undefined || xMax <= xMin) {
    return [];
  }

  return [0, 0.5, 1].map((ratio, index) => ({
    offset: index === 0 ? 0 : index === 1 ? 18 : 36,
    text: formatTimeLabel(xMin + ratio * (xMax - xMin), xMax - xMin),
    x: PADDING.left + ratio * plotWidth,
  }));
}

function formatAxisNumber(value: number, yDomain?: { min: number; max: number }) {
  if (Math.abs(value) >= 100) {
    return value.toFixed(0);
  }

  const range = yDomain ? Math.abs(yDomain.max - yDomain.min) : undefined;
  return value.toFixed(range !== undefined && range < 1 ? 2 : 1);
}

function formatTimeLabel(timestamp: number, spanMs: number) {
  const date = new Date(timestamp);

  if (spanMs > 36 * 60 * 60 * 1000) {
    return `${date.getMonth() + 1}/${date.getDate()}`;
  }

  return `${date.getHours()}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function getYDomain(values: number[]) {
  if (!values.length) {
    return { min: 0, max: 1 };
  }

  const minimum = Math.min(...values);
  const maximum = Math.max(...values);

  if (minimum === maximum) {
    const padding = Math.max(Math.abs(minimum) * 0.01, 0.5);
    return { min: minimum - padding, max: maximum + padding };
  }

  const padding = Math.max((maximum - minimum) * 0.18, 0.05);
  return { min: minimum - padding, max: maximum + padding };
}

function getXRatio(point: RenderPoint, position: number, pointCount: number, xMin: number | undefined, xMax: number | undefined) {
  if (point.timestamp !== undefined && xMin !== undefined && xMax !== undefined && xMax > xMin) {
    return (point.timestamp - xMin) / (xMax - xMin);
  }

  if (pointCount <= 1) {
    return 0.5;
  }

  return position / (pointCount - 1);
}

function splitSegments(points: ScaledPoint[]) {
  const segments: ScaledPoint[][] = [];
  let current: ScaledPoint[] = [];

  points.forEach((point) => {
    if (point.value === undefined) {
      if (current.length) {
        segments.push(current);
        current = [];
      }
      return;
    }

    if (current.length && current[current.length - 1].runId !== point.runId) {
      segments.push(current);
      current = [];
    }

    current.push(point);
  });

  if (current.length) {
    segments.push(current);
  }

  return segments;
}

function downsamplePoints(points: RenderPoint[], targetCount: number) {
  if (points.length <= targetCount) {
    return points;
  }

  const runs = buildRuns(points);
  const selectedRuns = selectRunsForBudget(runs, targetCount);
  const budgets = allocateRunBudgets(selectedRuns, targetCount);

  const sampled = selectedRuns.flatMap(({ run, runIndex }) => {
    if (run[0]?.value === undefined) {
      return [{ ...run[0], runId: runIndex }];
    }

    const anchor = runIndex === 0 ? "start" : runIndex === runs.length - 1 ? "end" : undefined;
    return downsampleValidRun(run, budgets.get(runIndex) ?? 1, anchor).map((point) => ({ ...point, runId: runIndex }));
  });

  return sampled.sort((left, right) => left.index - right.index);
}

function buildRuns(points: RenderPoint[]) {
  const runs: RenderPoint[][] = [];
  let currentRun: RenderPoint[] = [];
  let currentRunIsValid: boolean | undefined;

  points.forEach((point) => {
    const pointIsValid = point.value !== undefined;
    if (currentRunIsValid === undefined || currentRunIsValid === pointIsValid) {
      currentRun.push(point);
      currentRunIsValid = pointIsValid;
      return;
    }

    runs.push(currentRun);
    currentRun = [point];
    currentRunIsValid = pointIsValid;
  });

  if (currentRun.length) {
    runs.push(currentRun);
  }

  return runs;
}

function selectRunsForBudget(runs: RenderPoint[][], targetCount: number) {
  if (runs.length <= targetCount) {
    return runs.map((run, runIndex) => ({ run, runIndex }));
  }

  const selectedIndexes = new Set<number>([0, runs.length - 1]);
  const interiorBudget = Math.max(targetCount - selectedIndexes.size, 0);
  const interiorRunCount = Math.max(runs.length - 2, 0);

  for (let bucketIndex = 0; bucketIndex < interiorBudget; bucketIndex += 1) {
    const start = Math.floor((bucketIndex / interiorBudget) * interiorRunCount) + 1;
    const end = Math.floor(((bucketIndex + 1) / interiorBudget) * interiorRunCount) + 1;
    selectedIndexes.add(Math.floor((start + Math.max(start, end - 1)) / 2));
  }

  return Array.from(selectedIndexes)
    .sort((left, right) => left - right)
    .map((runIndex) => ({ run: runs[runIndex], runIndex }));
}

function allocateRunBudgets(selectedRuns: { run: RenderPoint[]; runIndex: number }[], targetCount: number) {
  const budgets = new Map<number, number>();
  selectedRuns.forEach(({ runIndex }) => budgets.set(runIndex, 1));

  let remainingBudget = Math.max(targetCount - selectedRuns.length, 0);
  const validRuns = selectedRuns.filter(({ run }) => run[0]?.value !== undefined);

  for (const { run, runIndex } of validRuns) {
    if (remainingBudget <= 0) {
      break;
    }
    if (run.length > (budgets.get(runIndex) ?? 1)) {
      budgets.set(runIndex, (budgets.get(runIndex) ?? 1) + 1);
      remainingBudget -= 1;
    }
  }

  while (remainingBudget > 0) {
    const eligibleRuns = validRuns.filter(({ run, runIndex }) => run.length > (budgets.get(runIndex) ?? 1));
    if (!eligibleRuns.length) {
      break;
    }

    const capacity = eligibleRuns.reduce((total, { run, runIndex }) => total + run.length - (budgets.get(runIndex) ?? 1), 0);
    let allocatedThisPass = 0;

    for (const { run, runIndex } of eligibleRuns) {
      const currentBudget = budgets.get(runIndex) ?? 1;
      const available = run.length - currentBudget;
      const share = Math.min(available, Math.max(1, Math.floor((available / capacity) * remainingBudget)));
      budgets.set(runIndex, currentBudget + share);
      remainingBudget -= share;
      allocatedThisPass += share;

      if (remainingBudget <= 0) {
        break;
      }
    }

    if (allocatedThisPass === 0) {
      break;
    }
  }

  return budgets;
}

function downsampleValidRun(points: RenderPoint[], targetCount: number, anchor?: "start" | "end") {
  if (points.length <= targetCount) {
    return points;
  }

  if (targetCount <= 1) {
    if (anchor === "end") {
      return [points[points.length - 1]];
    }
    if (anchor === "start") {
      return [points[0]];
    }
    return [points[Math.floor(points.length / 2)]];
  }

  if (targetCount <= 2) {
    return [points[0], points[points.length - 1]];
  }

  if (targetCount === 3) {
    return [points[0], points[Math.floor(points.length / 2)], points[points.length - 1]]
      .filter((point, index, all) => all.findIndex((candidate) => candidate.index === point.index) === index)
      .sort((left, right) => left.index - right.index);
  }

  const sampled = [points[0]];
  const interiorPoints = points.slice(1, -1);
  const bucketCount = Math.max(1, Math.floor((targetCount - 2) / 2));

  for (let bucketIndex = 0; bucketIndex < bucketCount; bucketIndex += 1) {
    const start = Math.floor((bucketIndex / bucketCount) * interiorPoints.length);
    const end = Math.floor(((bucketIndex + 1) / bucketCount) * interiorPoints.length);
    const bucket = interiorPoints.slice(start, Math.max(start + 1, end));
    const extrema = getBucketExtrema(bucket);

    sampled.push(...extrema);
  }

  sampled.push(points[points.length - 1]);

  return sampled
    .filter((point, index, all) => all.findIndex((candidate) => candidate.index === point.index) === index)
    .sort((left, right) => left.index - right.index);
}

function getBucketExtrema(points: RenderPoint[]) {
  if (!points.length) {
    return [];
  }

  let minimum = points[0];
  let maximum = points[0];

  points.forEach((point) => {
    if ((point.value ?? 0) < (minimum.value ?? 0)) {
      minimum = point;
    }
    if ((point.value ?? 0) > (maximum.value ?? 0)) {
      maximum = point;
    }
  });

  if (minimum.index === maximum.index) {
    return [minimum];
  }

  return [minimum, maximum].sort((left, right) => left.index - right.index);
}

function parseTimestamp(timestamp: string) {
  const parsed = new Date(timestamp).getTime();
  return Number.isFinite(parsed) ? parsed : undefined;
}

function hexToRgba(hex: string, alpha: number) {
  const normalized = hex.replace("#", "");
  const value = Number.parseInt(normalized, 16);
  const red = (value >> 16) & 255;
  const green = (value >> 8) & 255;
  const blue = value & 255;

  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

const styles = StyleSheet.create({
  container: {
    overflow: "hidden",
    borderWidth: 1,
    borderColor: hexToRgba(theme.colors.borderSoft, 0.92),
    borderRadius: theme.radii.md,
    backgroundColor: theme.colors.surface,
  },
  noData: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  noDataText: {
    color: theme.colors.chartAxis,
    fontSize: 13,
    fontWeight: "600",
  },
  horizontalGridLine: {
    height: 1,
    position: "absolute",
  },
  verticalGridLine: {
    position: "absolute",
    width: 1,
  },
  xAxisLabel: {
    bottom: 6,
    color: theme.colors.chartAxis,
    fontSize: 10,
    fontWeight: "600",
    position: "absolute",
    width: 40,
  },
  yAxisLabel: {
    color: theme.colors.chartAxis,
    fontSize: 10,
    fontWeight: "600",
    left: 4,
    position: "absolute",
    textAlign: "right",
    width: 28,
  },
  referenceLine: {
    height: 1,
    position: "absolute",
  },
  lineSegment: {
    borderRadius: theme.radii.pill,
    height: 2,
    position: "absolute",
  },
  latestMarker: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.pill,
    borderWidth: 2,
    height: 8,
    position: "absolute",
    width: 8,
  },
  pointMarker: {
    borderRadius: theme.radii.pill,
    height: 4,
    position: "absolute",
    width: 4,
  },
});
