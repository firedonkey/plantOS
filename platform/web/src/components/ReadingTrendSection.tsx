import { useMemo, useState } from "react";

import { SensorReading } from "@/types";

type RangeKey = "24h" | "7d" | "30d" | "all";

type ReadingTrendSectionProps = {
  history: SensorReading[];
  title?: string;
  subtitle?: string;
};

const RANGE_OPTIONS: Array<{ key: RangeKey; label: string }> = [
  { key: "24h", label: "24h" },
  { key: "7d", label: "7d" },
  { key: "30d", label: "30d" },
  { key: "all", label: "All" },
];

export function ReadingTrendSection({ history, title = "Trends", subtitle }: ReadingTrendSectionProps) {
  const [selectedRange, setSelectedRange] = useState<RangeKey>("24h");

  const filtered = useMemo(() => filterReadingsByRange(history, selectedRange), [history, selectedRange]);
  const latestReading = filtered.length ? filtered[filtered.length - 1] : undefined;

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
              onClick={() => setSelectedRange(option.key)}
              type="button"
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {!filtered.length ? (
        <p className="subtitle">No readings are available in this range yet.</p>
      ) : (
        <div className="trend-grid">
          <TrendCard
            label="Temperature"
            unit="C"
            values={filtered.map((reading) => reading.temperatureC)}
            latest={latestReading?.temperatureC}
          />
          <TrendCard
            label="Humidity"
            unit="%"
            values={filtered.map((reading) => reading.humidityPercent)}
            latest={latestReading?.humidityPercent}
          />
          <TrendCard
            label="Soil moisture"
            unit="%"
            values={filtered.map((reading) => reading.soilMoisturePercent)}
            latest={latestReading?.soilMoisturePercent}
          />
          <StateCard label="Light / pump state" readings={filtered} />
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

function StateCard({ label, readings }: { label: string; readings: SensorReading[] }) {
  const lightOnCount = readings.filter((reading) => reading.lightOn).length;
  const pumpOnCount = readings.filter((reading) => reading.pumpOn).length;
  const latest = readings.length ? readings[readings.length - 1] : undefined;

  return (
    <div className="trend-card">
      <div className="trend-card-header">
        <span>{label}</span>
        <strong>{latest ? `${latest.lightOn ? "Light on" : "Light off"} • ${latest.pumpOn ? "Pump on" : "Pump off"}` : "--"}</strong>
      </div>
      <div className="state-metrics">
        <div>
          <span className="meta-text">Light on</span>
          <strong>{lightOnCount}</strong>
        </div>
        <div>
          <span className="meta-text">Pump on</span>
          <strong>{pumpOnCount}</strong>
        </div>
      </div>
      <p className="meta-text">Counts are based on the readings currently loaded in this range.</p>
    </div>
  );
}

function filterReadingsByRange(readings: SensorReading[], range: RangeKey): SensorReading[] {
  if (range === "all" || !readings.length) {
    return readings;
  }

  const latestTimestamp = new Date(readings[readings.length - 1].timestamp).getTime();
  const cutoff = latestTimestamp - rangeToMilliseconds(range);
  return readings.filter((reading) => new Date(reading.timestamp).getTime() >= cutoff);
}

function rangeToMilliseconds(range: Exclude<RangeKey, "all">): number {
  switch (range) {
    case "24h":
      return 24 * 60 * 60 * 1000;
    case "7d":
      return 7 * 24 * 60 * 60 * 1000;
    case "30d":
      return 30 * 24 * 60 * 60 * 1000;
  }
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
