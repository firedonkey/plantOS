import { SensorReading } from "@/types";

export type RangeKey = "24h" | "7d" | "30d" | "all";

type ReadingTrendSectionProps = {
  history: SensorReading[];
  title?: string;
  subtitle?: string;
  selectedRange: RangeKey;
  onRangeChange: (range: RangeKey) => void;
  loading?: boolean;
};

const RANGE_OPTIONS: Array<{ key: RangeKey; label: string }> = [
  { key: "24h", label: "24h" },
  { key: "7d", label: "7d" },
  { key: "30d", label: "30d" },
  { key: "all", label: "All" },
];

const MAX_RENDER_POINTS = 240;

const SENSOR_SERIES = [
  {
    key: "air-temperature",
    label: "Air temp",
    unit: "C",
    color: "#b76a35",
    minDomainSpan: 5,
    isValidValue: (value: number) => value >= -20 && value <= 60,
    getValue: (reading: SensorReading) => reading.temperatureC,
  },
  {
    key: "humidity",
    label: "Humidity",
    unit: "%",
    color: "#2f75b5",
    minDomainSpan: 10,
    isValidValue: (value: number) => value >= 0 && value <= 100,
    getValue: (reading: SensorReading) => reading.humidityPercent,
  },
  {
    key: "water-temperature",
    label: "Water temp",
    unit: "C",
    color: "#2f855a",
    minDomainSpan: 5,
    isValidValue: (value: number) => value >= 0 && value <= 50 && Math.abs(value - 85) > 0.01,
    getValue: (reading: SensorReading) => reading.waterTemperatureC,
  },
];

export function ReadingTrendSection({
  history,
  title = "Trends",
  subtitle,
  selectedRange,
  onRangeChange,
  loading = false,
}: ReadingTrendSectionProps) {
  return (
    <div className="card stack-form">
      <div className="section-header">
        <div>
          <h3>{title}</h3>
          {subtitle ? <p className="subtitle">{subtitle}</p> : null}
        </div>
        <div className="range-tabs">
          {RANGE_OPTIONS.map((option) => (
            <button
              key={option.key}
              className={`range-tab ${selectedRange === option.key ? "range-tab-active" : ""}`}
              disabled={loading}
              onClick={() => onRangeChange(option.key)}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {!history.length ? (
        <p className="subtitle">No readings are available in this range yet.</p>
      ) : (
        <div className="trend-grid">
          {SENSOR_SERIES.map((series) => (
            <TrendCard
              key={series.key}
              color={series.color}
              label={series.label}
              unit={series.unit}
              history={history}
              minDomainSpan={series.minDomainSpan}
              getValue={series.getValue}
              isValidValue={series.isValidValue}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function TrendCard({
  label,
  unit,
  color,
  history,
  minDomainSpan,
  getValue,
  isValidValue,
}: {
  label: string;
  unit: string;
  color: string;
  history: SensorReading[];
  minDomainSpan: number;
  getValue: (reading: SensorReading) => number | undefined;
  isValidValue: (value: number) => boolean;
}) {
  const chartPoints = downsamplePoints(
    history.map((reading, index) => {
      const value = getValue(reading);
      const hasNumericValue = typeof value === "number" && Number.isFinite(value);
      return {
        index,
        timestamp: reading.timestamp,
        timestampMs: parseTimestamp(reading.timestamp),
        value: hasNumericValue && isValidValue(value) ? value : undefined,
        ignored: hasNumericValue && !isValidValue(value),
      };
    }),
    MAX_RENDER_POINTS,
  );
  const points = chartPoints.filter((point): point is TrendPoint & { value: number } => point.value !== undefined);
  const ignoredCount = chartPoints.filter((point) => point.ignored).length;
  const numericValues = points.map((point) => point.value);
  const latestPoint = points.length ? points[points.length - 1] : undefined;
  const minimum = numericValues.length ? Math.min(...numericValues) : undefined;
  const maximum = numericValues.length ? Math.max(...numericValues) : undefined;
  const domain = buildValueDomain(numericValues, minDomainSpan);
  const yTicks = domain ? buildYTicks(domain) : [];
  const xDomain = buildXDomain(points);
  const xLabels = buildXLabels(xDomain);
  const scaledPoints = domain ? scalePoints(chartPoints, domain, xDomain) : [];
  const segments = splitSegments(scaledPoints);
  const scaledValidPoints = scaledPoints.filter((point) => point.value !== undefined);
  const latestPointCoordinates = scaledValidPoints.length ? scaledValidPoints[scaledValidPoints.length - 1] : undefined;

  return (
    <div className="trend-card">
      <div className="trend-card-header">
        <div className="trend-card-title">
          <span className="series-dot" style={{ backgroundColor: color }} />
          <span>{label}</span>
        </div>
        <strong>{latestPoint ? `${formatAxisValue(latestPoint.value, minimum, maximum)} ${unit}` : "--"}</strong>
      </div>
      {points.length ? (
        <div className="trend-chart-frame">
          <div className="trend-y-axis" aria-hidden="true">
            {yTicks.map((tick, index) => (
              <span key={`${label}-y-${index}`} style={{ bottom: `${tick.position}%` }}>
                {formatAxisValue(tick.value, minimum, maximum)}
              </span>
            ))}
          </div>
          <div className="trend-plot">
            <svg className="trend-line-chart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={`${label} sensor trend`}>
              {yTicks.map((tick, index) => (
                <line key={`${label}-grid-${index}`} className="trend-grid-line" x1="0" x2="100" y1={100 - tick.position} y2={100 - tick.position} />
              ))}
              {segments.map((segment, index) => (
                <polyline key={`${label}-segment-${index}`} className="trend-line" points={formatPolyline(segment)} stroke={color} />
              ))}
              {points.length <= 80
                ? scaledPoints
                    .filter((point) => point.value !== undefined)
                    .map((point) => <circle key={`${label}-point-${point.index}`} className="trend-point" cx={point.x} cy={point.y} r="1.4" stroke={color} />)
                : null}
              {latestPointCoordinates ? (
                <circle
                  className="trend-latest-point"
                  cx={latestPointCoordinates.x}
                  cy={latestPointCoordinates.y}
                  r="2.4"
                  stroke={color}
                />
              ) : null}
            </svg>
            <div className="trend-x-axis" aria-hidden="true">
              {xLabels.map((entry, index) => (
                <span key={`${label}-x-${index}`}>{entry}</span>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <p className="subtitle">No sensor readings for this metric yet.</p>
      )}
      <p className="meta-text">
        {points.length} readings • Min {minimum !== undefined ? `${formatAxisValue(minimum, minimum, maximum)} ${unit}` : "--"} • Max{" "}
        {maximum !== undefined ? `${formatAxisValue(maximum, minimum, maximum)} ${unit}` : "--"}
        {ignoredCount > 0 ? ` • ${ignoredCount} outlier${ignoredCount === 1 ? "" : "s"} ignored` : ""}
      </p>
    </div>
  );
}

type ValueDomain = {
  min: number;
  max: number;
};

type TrendPoint = {
  index: number;
  ignored: boolean;
  timestamp: string;
  timestampMs: number | undefined;
  value: number | undefined;
};

type ScaledTrendPoint = TrendPoint & {
  x: number;
  y: number;
};

function buildValueDomain(values: number[], minDomainSpan: number): ValueDomain | undefined {
  if (!values.length) {
    return undefined;
  }
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = maximum - minimum;
  const domainSpan = Math.max(range, minDomainSpan);
  const midpoint = (minimum + maximum) / 2;
  const halfSpan = domainSpan / 2;
  const padding = Math.max(domainSpan * 0.08, 0.05);
  return {
    min: midpoint - halfSpan - padding,
    max: midpoint + halfSpan + padding,
  };
}

function buildYTicks(domain: ValueDomain): Array<{ value: number; position: number }> {
  return [0, 0.5, 1].map((ratio) => ({
    value: domain.min + (domain.max - domain.min) * ratio,
    position: ratio * 100,
  }));
}

function buildXDomain(points: Array<TrendPoint & { value: number }>): { min: number; max: number } | undefined {
  const timestamps = points.map((point) => point.timestampMs).filter((timestamp): timestamp is number => timestamp !== undefined);
  if (timestamps.length < 2) {
    return undefined;
  }
  const min = Math.min(...timestamps);
  const max = Math.max(...timestamps);
  return max > min ? { min, max } : undefined;
}

function scalePoints(points: TrendPoint[], domain: ValueDomain, xDomain?: { min: number; max: number }): ScaledTrendPoint[] {
  return points.map((point, position) => {
    const xRatio = getXRatio(point, position, points.length, xDomain);
    const y = point.value === undefined ? 50 : 100 - valueToY(point.value, domain);
    return {
      ...point,
      x: xRatio * 100,
      y,
    };
  });
}

function splitSegments(points: ScaledTrendPoint[]): ScaledTrendPoint[][] {
  const segments: ScaledTrendPoint[][] = [];
  let current: ScaledTrendPoint[] = [];

  for (const point of points) {
    if (point.value === undefined) {
      if (current.length) {
        segments.push(current);
        current = [];
      }
      continue;
    }
    current.push(point);
  }

  if (current.length) {
    segments.push(current);
  }

  return segments;
}

function formatPolyline(points: ScaledTrendPoint[]): string {
  return points.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(" ");
}

function valueToY(value: number, domain: ValueDomain): number {
  if (domain.max === domain.min) {
    return 50;
  }
  return ((value - domain.min) / (domain.max - domain.min)) * 100;
}

function getXRatio(point: TrendPoint, position: number, total: number, xDomain?: { min: number; max: number }): number {
  if (xDomain && point.timestampMs !== undefined) {
    return Math.min(Math.max((point.timestampMs - xDomain.min) / (xDomain.max - xDomain.min), 0), 1);
  }
  if (total <= 1) {
    return 0.5;
  }
  return position / (total - 1);
}

function buildXLabels(xDomain?: { min: number; max: number }): string[] {
  if (!xDomain) {
    return [];
  }
  return [0, 0.5, 1].map((ratio) => formatTimeLabel(xDomain.min + (xDomain.max - xDomain.min) * ratio, xDomain.max - xDomain.min));
}

function formatTimeLabel(timestamp: string | number, spanMs = 0): string {
  const date = new Date(timestamp);
  if (spanMs > 36 * 60 * 60 * 1000) {
    return `${date.getMonth() + 1}/${date.getDate()}`;
  }
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function formatAxisValue(value: number, minimum?: number, maximum?: number): string {
  if (minimum === undefined || maximum === undefined) {
    return value.toFixed(1);
  }
  const range = Math.abs(maximum - minimum);
  return value.toFixed(range > 0 && range < 1 ? 2 : 1);
}

function parseTimestamp(timestamp: string): number | undefined {
  const parsed = Date.parse(timestamp);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function downsamplePoints<T>(points: T[], maxPoints: number): T[] {
  if (points.length <= maxPoints) {
    return points;
  }
  const step = Math.ceil(points.length / maxPoints);
  return points.filter((_, index) => index % step === 0 || index === points.length - 1);
}
