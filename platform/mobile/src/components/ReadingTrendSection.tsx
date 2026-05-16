import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { SectionHeader } from "@/components/SectionHeader";
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
    label: "Air temp",
    unit: "C",
    color: "#b76a35",
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
    key: "water-temperature",
    label: "Water temp",
    unit: "C",
    color: theme.colors.accent,
    getValue: (reading: SensorReading) => reading.waterTemperatureC,
  },
  {
    key: "water-level",
    label: "Water level raw",
    unit: "",
    color: "#6f7d45",
    getValue: (reading: SensorReading) => reading.waterLevelRaw,
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
    <Card variant="elevated">
      <View style={styles.header}>
        <SectionHeader title={title} subtitle={subtitle} />
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
        <EmptyState title="No readings in range" message="Sensor trends will appear after the device reports data for this window." />
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
      <View style={styles.trendHeader}>
        <View style={[styles.seriesDot, { backgroundColor: color }]} />
        <Text style={styles.cardLabel}>{label}</Text>
      </View>
      <Text style={styles.cardValue}>{latest !== undefined ? `Current ${latest.toFixed(1)} ${unit}` : "Current --"}</Text>
      <SensorLineChart points={chartPoints} color={color} />
      <View style={styles.metaRow}>
        <Text style={styles.meta}>Min {minimum !== undefined ? `${minimum.toFixed(1)} ${unit}` : "--"}</Text>
        <Text style={styles.meta}>Max {maximum !== undefined ? `${maximum.toFixed(1)} ${unit}` : "--"}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: theme.spacing.md },
  tabs: { flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm },
  tab: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: theme.radii.pill,
    borderWidth: 1,
    borderColor: theme.colors.borderSoft,
    backgroundColor: theme.colors.surfaceMuted,
  },
  tabActive: {
    borderColor: theme.colors.accent,
    backgroundColor: theme.colors.accentSoft,
  },
  tabLabel: { color: theme.colors.textSecondary, fontWeight: "600" },
  tabLabelActive: { color: theme.colors.accent },
  grid: { gap: theme.spacing.md },
  trendCard: {
    borderWidth: 1,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.md,
    backgroundColor: theme.colors.surfaceMuted,
    padding: theme.spacing.md,
    gap: theme.spacing.md,
  },
  trendHeader: { flexDirection: "row", alignItems: "center", gap: theme.spacing.sm },
  seriesDot: { width: 8, height: 8, borderRadius: theme.radii.pill },
  cardLabel: { color: theme.colors.textSecondary, fontSize: theme.typography.meta, fontWeight: "700" },
  cardValue: { fontSize: 22, fontWeight: "800", color: theme.colors.textPrimary },
  metaRow: { flexDirection: "row", justifyContent: "space-between", gap: theme.spacing.md },
  meta: { fontSize: theme.typography.meta, color: theme.colors.textSecondary },
});
