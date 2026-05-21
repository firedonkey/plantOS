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
          <TrendCard
            label="Air temp"
            unit="C"
            history={history}
            getValue={(reading) => reading.temperatureC}
          />
          <TrendCard
            label="Humidity"
            unit="%"
            history={history}
            getValue={(reading) => reading.humidityPercent}
          />
          <TrendCard
            label="Water temp"
            unit="C"
            history={history}
            getValue={(reading) => reading.waterTemperatureC}
          />
        </div>
      )}
    </div>
  );
}

function TrendCard({
  label,
  unit,
  history,
  getValue,
}: {
  label: string;
  unit: string;
  history: SensorReading[];
  getValue: (reading: SensorReading) => number | undefined;
}) {
  const points = history
    .map((reading) => ({
      timestamp: reading.timestamp,
      value: getValue(reading),
    }))
    .filter((point): point is { timestamp: string; value: number } => typeof point.value === "number");
  const numericValues = points.map((point) => point.value);
  const latestPoint = points.length ? points[points.length - 1] : undefined;
  const minimum = numericValues.length ? Math.min(...numericValues) : undefined;
  const maximum = numericValues.length ? Math.max(...numericValues) : undefined;
  const domain = buildValueDomain(numericValues);
  const yTicks = domain ? buildYTicks(domain) : [];
  const xLabels = buildXLabels(points);
  const linePoints = domain ? buildLinePoints(points, domain) : "";

  return (
    <div className="trend-card">
      <div className="trend-card-header">
        <span>{label}</span>
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
              <polyline className="trend-line" points={linePoints} />
              {points.length <= 80
                ? points.map((point, index) => {
                    const x = points.length === 1 ? 50 : (index / (points.length - 1)) * 100;
                    const y = valueToY(point.value, domain!);
                    return <circle key={`${label}-point-${index}`} className="trend-point" cx={x} cy={100 - y} r="1.4" />;
                  })
                : null}
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
      </p>
    </div>
  );
}

type ValueDomain = {
  min: number;
  max: number;
};

function buildValueDomain(values: number[]): ValueDomain | undefined {
  if (!values.length) {
    return undefined;
  }
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const range = maximum - minimum;
  const padding = range === 0 ? Math.max(Math.abs(maximum) * 0.01, 0.5) : Math.max(range * 0.18, 0.05);
  return {
    min: minimum - padding,
    max: maximum + padding,
  };
}

function buildYTicks(domain: ValueDomain): Array<{ value: number; position: number }> {
  return [0, 0.5, 1].map((ratio) => ({
    value: domain.min + (domain.max - domain.min) * ratio,
    position: ratio * 100,
  }));
}

function buildLinePoints(points: Array<{ timestamp: string; value: number }>, domain: ValueDomain): string {
  if (points.length === 1) {
    return `50,${100 - valueToY(points[0].value, domain)}`;
  }
  return points
    .map((point, index) => {
      const x = (index / (points.length - 1)) * 100;
      const y = valueToY(point.value, domain);
      return `${x.toFixed(2)},${(100 - y).toFixed(2)}`;
    })
    .join(" ");
}

function valueToY(value: number, domain: ValueDomain): number {
  if (domain.max === domain.min) {
    return 50;
  }
  return ((value - domain.min) / (domain.max - domain.min)) * 100;
}

function buildXLabels(points: Array<{ timestamp: string; value: number }>): string[] {
  if (!points.length) {
    return [];
  }
  const first = points[0];
  const last = points[points.length - 1];
  const middle = points[Math.floor((points.length - 1) / 2)];
  return [first, middle, last].map((point) => formatTimeLabel(point.timestamp));
}

function formatTimeLabel(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const sameYear = date.getFullYear() === now.getFullYear();
  return date.toLocaleString(undefined, {
    month: sameYear ? undefined : "short",
    day: sameYear ? undefined : "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatAxisValue(value: number, minimum?: number, maximum?: number): string {
  if (minimum === undefined || maximum === undefined) {
    return value.toFixed(1);
  }
  const range = Math.abs(maximum - minimum);
  return value.toFixed(range > 0 && range < 1 ? 2 : 1);
}
