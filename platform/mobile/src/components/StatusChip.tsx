import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";
import { DeviceConnectionState } from "@/types";

type StatusChipProps = {
  label: string;
  tone?: DeviceConnectionState | "mock";
  compact?: boolean;
};

export function StatusChip({ label, tone = "unknown", compact = false }: StatusChipProps) {
  return (
    <View style={[styles.chip, compact ? styles.compactChip : null, toneStyles[tone]]}>
      <Text style={[styles.label, compact ? styles.compactLabel : null, textStyles[tone]]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: theme.radii.pill,
    alignSelf: "flex-start",
  },
  compactChip: {
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  label: {
    fontSize: theme.typography.caption,
    fontWeight: "600",
  },
  compactLabel: {
    fontSize: 11,
  },
});

const toneStyles = StyleSheet.create({
  online: { backgroundColor: theme.colors.successSoft },
  offline: { backgroundColor: theme.colors.dangerSoft },
  unknown: { backgroundColor: theme.colors.surfaceInset },
  degraded: { backgroundColor: theme.colors.warningSoft },
  stale: { backgroundColor: theme.colors.warningSoft },
  warning: { backgroundColor: theme.colors.warningSoft },
  waiting: { backgroundColor: theme.colors.infoSoft },
  mock: { backgroundColor: theme.colors.mockSoft },
});

const textStyles = StyleSheet.create({
  online: { color: theme.colors.success },
  offline: { color: theme.colors.danger },
  unknown: { color: theme.colors.textSecondary },
  degraded: { color: theme.colors.warning },
  stale: { color: theme.colors.warning },
  warning: { color: theme.colors.warning },
  waiting: { color: theme.colors.info },
  mock: { color: theme.colors.mock },
});
