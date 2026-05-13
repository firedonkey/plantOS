import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";
import { DeviceConnectionState } from "@/types";

type StatusChipProps = {
  label: string;
  tone?: DeviceConnectionState | "mock";
};

export function StatusChip({ label, tone = "unknown" }: StatusChipProps) {
  return (
    <View style={[styles.chip, toneStyles[tone]]}>
      <Text style={[styles.label, textStyles[tone]]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    alignSelf: "flex-start",
  },
  label: {
    fontSize: 12,
    fontWeight: "600",
  },
});

const toneStyles = StyleSheet.create({
  online: { backgroundColor: "#dff7e8" },
  offline: { backgroundColor: "#fde4e4" },
  unknown: { backgroundColor: "#eceff3" },
  degraded: { backgroundColor: "#fff1d6" },
  mock: { backgroundColor: "#efe7ff" },
});

const textStyles = StyleSheet.create({
  online: { color: "#157347" },
  offline: { color: "#b42318" },
  unknown: { color: theme.colors.textSecondary },
  degraded: { color: "#9a6700" },
  mock: { color: "#6941c6" },
});
