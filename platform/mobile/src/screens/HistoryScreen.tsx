import { StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { ReadingTrendSection } from "@/components/ReadingTrendSection";
import { Screen } from "@/components/Screen";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { theme } from "@/styles/theme";

type HistoryScreenProps = {
  deviceId: string;
};

export function HistoryScreen({ deviceId }: HistoryScreenProps) {
  const { dashboard, usedMock, isLoading, error, refresh, lastUpdatedAt } = useDeviceDashboard(deviceId);

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

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {isLoading && !dashboard ? <Text style={styles.meta}>Loading readings…</Text> : null}
      {!isLoading && !dashboard?.history.length ? (
        <Card>
          <Text style={styles.timestamp}>No readings yet</Text>
          <Text style={styles.row}>Once the device reports sensor data, the recent history will appear here.</Text>
        </Card>
      ) : null}

      {dashboard?.history.length ? (
        <ReadingTrendSection
          history={dashboard.history}
          title="Trend charts"
          subtitle="The backend currently returns the latest 50 readings, so longer ranges reflect the data available in that window."
        />
      ) : null}

      {dashboard?.history.map((reading) => (
        <Card key={reading.timestamp}>
          <Text style={styles.timestamp}>{new Date(reading.timestamp).toLocaleString()}</Text>
          <Text style={styles.row}>
            {reading.temperatureC?.toFixed(1) ?? "--"} C • {reading.humidityPercent?.toFixed(1) ?? "--"}% • {reading.soilMoisturePercent?.toFixed(1) ?? "--"}%
          </Text>
          <Text style={styles.meta}>Light {reading.lightOn ? "on" : "off"} • Pump {reading.pumpOn ? "on" : "off"}</Text>
        </Card>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: 8 },
  eyebrow: { fontSize: 13, fontWeight: "700", color: theme.colors.accent },
  title: { fontSize: 30, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: 16, color: theme.colors.textSecondary },
  meta: { fontSize: 14, color: theme.colors.textSecondary },
  timestamp: { fontSize: 14, fontWeight: "700", color: theme.colors.textPrimary },
  row: { fontSize: 15, color: theme.colors.textSecondary },
  error: { color: "#b42318" },
});
