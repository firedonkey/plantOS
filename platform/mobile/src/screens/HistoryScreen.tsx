import { StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { Screen } from "@/components/Screen";
import { useDeviceDashboard } from "@/hooks/useDeviceDashboard";
import { theme } from "@/styles/theme";

type HistoryScreenProps = {
  deviceId: string;
};

export function HistoryScreen({ deviceId }: HistoryScreenProps) {
  const { dashboard, usedMock, isLoading, error, refresh } = useDeviceDashboard(deviceId);

  return (
    <Screen onRefresh={refresh} refreshing={isLoading}>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>HISTORY</Text>
        <Text style={styles.title}>Recent sensor history</Text>
        <Text style={styles.subtitle}>
          {usedMock ? "Mock data shown. TODO: replace with charted API history." : "Chart-ready structure placeholder."}
        </Text>
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {dashboard?.history.map((reading) => (
        <Card key={reading.timestamp}>
          <Text style={styles.timestamp}>{new Date(reading.timestamp).toLocaleString()}</Text>
          <Text style={styles.row}>
            {reading.temperatureC?.toFixed(1) ?? "--"} C • {reading.humidityPercent?.toFixed(1) ?? "--"}% • {reading.soilMoisturePercent?.toFixed(1) ?? "--"}%
          </Text>
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
  timestamp: { fontSize: 14, fontWeight: "700", color: theme.colors.textPrimary },
  row: { fontSize: 15, color: theme.colors.textSecondary },
  error: { color: "#b42318" },
});
