import { Pressable, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
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
          <TrendCard label="Temperature" unit="C" values={history.map((reading) => reading.temperatureC)} latest={history.at(-1)?.temperatureC} />
          <TrendCard label="Humidity" unit="%" values={history.map((reading) => reading.humidityPercent)} latest={history.at(-1)?.humidityPercent} />
          <TrendCard label="Soil moisture" unit="%" values={history.map((reading) => reading.soilMoisturePercent)} latest={history.at(-1)?.soilMoisturePercent} />
          <StateCard readings={history} />
        </View>
      )}
    </Card>
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
    <View style={styles.trendCard}>
      <Text style={styles.cardLabel}>{label}</Text>
      <Text style={styles.cardValue}>{latest !== undefined ? `${latest.toFixed(1)} ${unit}` : "--"}</Text>
      <View style={styles.bars}>
        {values.map((value, index) => {
          const height = normalizeValue(value, minimum, maximum);
          return <View key={`${label}-${index}`} style={[styles.bar, { height: `${height}%` }]} />;
        })}
      </View>
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

function normalizeValue(value: number | undefined, minimum: number | undefined, maximum: number | undefined): number {
  if (value === undefined || minimum === undefined || maximum === undefined) {
    return 20;
  }
  if (maximum === minimum) {
    return 60;
  }
  return 20 + ((value - minimum) / (maximum - minimum)) * 80;
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
    borderColor: theme.colors.border,
    borderRadius: 8,
    backgroundColor: "#f8fafb",
    padding: 14,
    gap: 10,
  },
  cardLabel: { color: theme.colors.textSecondary, fontWeight: "600" },
  cardValue: { fontSize: 22, fontWeight: "800", color: theme.colors.textPrimary },
  bars: { flexDirection: "row", alignItems: "flex-end", gap: 4, minHeight: 92 },
  bar: { flex: 1, minWidth: 6, backgroundColor: theme.colors.accent, borderTopLeftRadius: 4, borderTopRightRadius: 4 },
  stateMetrics: { flexDirection: "row", gap: 16 },
  metricStrong: { fontSize: 22, fontWeight: "800", color: theme.colors.textPrimary },
  meta: { fontSize: 13, color: theme.colors.textSecondary },
});
