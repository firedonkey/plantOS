import { StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { FeedbackBanner } from "@/components/FeedbackBanner";
import { ReadingTrendSection } from "@/components/ReadingTrendSection";
import { Screen } from "@/components/Screen";
import { SkeletonCard } from "@/components/Skeleton";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { theme } from "@/styles/theme";

type HistoryScreenProps = {
  deviceId: string;
};

export function HistoryScreen({ deviceId }: HistoryScreenProps) {
  const { dashboard, usedMock, isLoading, error, refresh, lastUpdatedAt, selectedRange, setSelectedRange } = useDeviceDashboard(deviceId);
  const displayHistory = dashboard?.history ? [...dashboard.history].reverse() : [];

  return (
    <Screen onRefresh={refresh} refreshing={isLoading}>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>HISTORY</Text>
        <Text style={styles.title}>Recent sensor history</Text>
        <Text style={styles.subtitle}>
          {usedMock ? "Mock history data is shown because the backend is unavailable." : "Recent readings from the local PlantLab backend."}
        </Text>
        <Text style={styles.meta}>
          {lastUpdatedAt ? `Last updated ${new Date(lastUpdatedAt).toLocaleTimeString()}` : "Pull to refresh for the latest readings."}
        </Text>
      </View>

      {error ? <FeedbackBanner tone="error" message={error} /> : null}
      {isLoading && !dashboard ? <SkeletonCard /> : null}
      {!isLoading && !error && !dashboard?.history.length ? (
        <EmptyState title="No readings yet" message="Once the device reports sensor data, recent history and trend charts will appear here." />
      ) : null}

      {dashboard?.history.length ? (
        <ReadingTrendSection
          history={dashboard.history}
          title="Trend charts"
          subtitle="Range tabs now request matching backend history windows when the API is available."
          selectedRange={selectedRange}
          onRangeChange={setSelectedRange}
          loading={isLoading}
        />
      ) : null}

      {displayHistory.map((reading) => (
        <Card key={reading.timestamp} variant="inset">
          <Text style={styles.timestamp}>{new Date(reading.timestamp).toLocaleString()}</Text>
          <Text style={styles.row}>
            Air {reading.temperatureC?.toFixed(1) ?? "--"} C | Humidity {reading.humidityPercent?.toFixed(1) ?? "--"}% | Water {reading.waterTemperatureC?.toFixed(1) ?? "--"} C
          </Text>
          <Text style={styles.meta}>Grow LED {reading.lightOn ? "on" : "off"} | Water level {reading.waterLevelState ?? "unknown"} {reading.waterLevelRaw !== undefined ? `(${reading.waterLevelRaw})` : ""}</Text>
        </Card>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: 8 },
  eyebrow: { fontSize: theme.typography.eyebrow, fontWeight: "800", color: theme.colors.accent },
  title: { fontSize: theme.typography.screenTitle, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: theme.typography.bodyLarge, color: theme.colors.textSecondary, lineHeight: 22 },
  meta: { fontSize: theme.typography.body, color: theme.colors.textSecondary, lineHeight: 20 },
  timestamp: { fontSize: theme.typography.body, fontWeight: "800", color: theme.colors.textPrimary },
  row: { fontSize: 15, color: theme.colors.textSecondary, lineHeight: 21 },
});
