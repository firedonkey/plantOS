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
  const latestReading = history.length ? history[history.length - 1] : undefined;

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
            values={history.map((reading) => reading.temperatureC)}
            latest={latestReading?.temperatureC}
          />
          <TrendCard
            label="Humidity"
            unit="%"
            values={history.map((reading) => reading.humidityPercent)}
            latest={latestReading?.humidityPercent}
          />
          <TrendCard
            label="Water temp"
            unit="C"
            values={history.map((reading) => reading.waterTemperatureC)}
            latest={latestReading?.waterTemperatureC}
          />
        </div>
      )}
    </div>
  );
}

function TrendCard({
  label,
  unit,
  values,
  latest,
}: {
  label: string;
  unit: string;
  values: Array<number | undefined>;
  latest?: number;
}) {
  const numericValues = values.filter((value): value is number => typeof value === "number");
  const minimum = numericValues.length ? Math.min(...numericValues) : undefined;
  const maximum = numericValues.length ? Math.max(...numericValues) : undefined;

  return (
    <div className="trend-card">
      <div className="trend-card-header">
        <span>{label}</span>
        <strong>{latest !== undefined ? `${latest.toFixed(1)} ${unit}` : "--"}</strong>
      </div>
      <div className="trend-bars" aria-hidden="true">
        {values.map((value, index) => {
          const height = normalizeValue(value, minimum, maximum);
          return <span key={`${label}-${index}`} className="trend-bar" style={{ height: `${height}%` }} />;
        })}
      </div>
      <p className="meta-text">
        Min {minimum !== undefined ? `${minimum.toFixed(1)} ${unit}` : "--"} • Max {maximum !== undefined ? `${maximum.toFixed(1)} ${unit}` : "--"}
      </p>
    </div>
  );
}

function normalizeValue(value: number | undefined, minimum: number | undefined, maximum: number | undefined): number {
  if (value === undefined || minimum === undefined || maximum === undefined) {
    return 20;
  }
  if (maximum === minimum) {
    return 60;
  }
  return 20 + ((value - minimum) / (maximum - minimum)) * 80;
}
