import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { SensorLineChart } from "@/components/SensorLineChart";
import { SensorReading } from "@/types";
import { theme } from "@/styles/theme";

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

const SENSOR_SERIES = [
  {
    key: "temperature",
    label: "Temperature",
    unit: "C",
    color: "#c96f2d",
    getValue: (reading: SensorReading) => reading.temperatureC,
  },
  {
    key: "humidity",
    label: "Humidity",
    unit: "%",
    color: "#2f75b5",
    getValue: (reading: SensorReading) => reading.humidityPercent,
  },
  {
    key: "soil-moisture",
    label: "Soil moisture",
    unit: "%",
    color: theme.colors.accent,
    getValue: (reading: SensorReading) => reading.soilMoisturePercent,
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
    <Card>
      <View style={styles.header}>
        <View style={{ flex: 1, gap: 4 }}>
          <Text style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        <View style={styles.tabs}>
          {RANGE_OPTIONS.map((option) => (
            <Pressable
              key={option.key}
              disabled={loading}
              onPress={() => onRangeChange(option.key)}
              style={[styles.tab, selectedRange === option.key ? styles.tabActive : null]}
            >
              <Text style={[styles.tabLabel, selectedRange === option.key ? styles.tabLabelActive : null]}>{option.label}</Text>
            </Pressable>
          ))}
        </View>
      </View>

      {!history.length ? (
        <Text style={styles.subtitle}>No readings are available in this range yet.</Text>
      ) : (
        <View style={styles.grid}>
          {SENSOR_SERIES.map((series) => (
            <TrendCard
              key={series.key}
              color={series.color}
              label={series.label}
              readings={history}
              unit={series.unit}
              getValue={series.getValue}
            />
          ))}
          <StateCard readings={history} />
        </View>
      )}
    </Card>
  );
}

function TrendCard({
  label,
  unit,
  color,
  readings,
  getValue,
}: {
  label: string;
  unit: string;
  color: string;
  readings: SensorReading[];
  getValue: (reading: SensorReading) => number | undefined;
}) {
  const values = readings.map(getValue);
  const numericValues = values.filter((value): value is number => typeof value === "number");
  const minimum = numericValues.length ? Math.min(...numericValues) : undefined;
  const maximum = numericValues.length ? Math.max(...numericValues) : undefined;
  const latestReading = readings.at(-1);
  const latest = latestReading ? getValue(latestReading) : undefined;
  const chartPoints = readings.map((reading) => ({
    timestamp: reading.timestamp,
    value: getValue(reading),
  }));

  return (
    <View style={styles.trendCard}>
      <Text style={styles.cardLabel}>{label}</Text>
      <Text style={styles.cardValue}>{latest !== undefined ? `Current ${latest.toFixed(1)} ${unit}` : "Current --"}</Text>
      <SensorLineChart points={chartPoints} color={color} />
      <Text style={styles.meta}>
        Min {minimum !== undefined ? `${minimum.toFixed(1)} ${unit}` : "--"} • Max {maximum !== undefined ? `${maximum.toFixed(1)} ${unit}` : "--"}
      </Text>
    </View>
  );
}

function StateCard({ readings }: { readings: SensorReading[] }) {
  const lightOnCount = readings.filter((reading) => reading.lightOn).length;
  const pumpOnCount = readings.filter((reading) => reading.pumpOn).length;
  const latest = readings.at(-1);

  return (
    <View style={styles.trendCard}>
      <Text style={styles.cardLabel}>Light / pump state</Text>
      <Text style={styles.cardValue}>{latest ? `${latest.lightOn ? "Light on" : "Light off"} • ${latest.pumpOn ? "Pump on" : "Pump off"}` : "--"}</Text>
      <View style={styles.stateMetrics}>
        <View>
          <Text style={styles.meta}>Light on</Text>
          <Text style={styles.metricStrong}>{lightOnCount}</Text>
        </View>
        <View>
          <Text style={styles.meta}>Pump on</Text>
          <Text style={styles.metricStrong}>{pumpOnCount}</Text>
        </View>
      </View>
      <Text style={styles.meta}>Counts are based on the readings currently loaded in this range.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: 10 },
  title: { fontSize: 18, fontWeight: "700", color: theme.colors.textPrimary },
  subtitle: { fontSize: 14, color: theme.colors.textSecondary },
  tabs: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  tab: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
  },
  tabActive: {
    borderColor: theme.colors.accent,
    backgroundColor: "#e7f3ec",
  },
  tabLabel: { color: theme.colors.textSecondary, fontWeight: "600" },
  tabLabelActive: { color: theme.colors.accent },
  grid: { gap: 12 },
  trendCard: {
    borderWidth: 1,
    borderColor: "#dfe6ea",
    borderRadius: 8,
    backgroundColor: "#fbfcfd",
    padding: 14,
    gap: 10,
  },
  cardLabel: { color: theme.colors.textSecondary, fontWeight: "600" },
  cardValue: { fontSize: 22, fontWeight: "800", color: theme.colors.textPrimary },
  stateMetrics: { flexDirection: "row", gap: 16 },
  metricStrong: { fontSize: 22, fontWeight: "800", color: theme.colors.textPrimary },
  meta: { fontSize: 13, color: theme.colors.textSecondary },
});
