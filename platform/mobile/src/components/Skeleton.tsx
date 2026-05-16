import { StyleSheet, View } from "react-native";

import { theme } from "@/styles/theme";

type SkeletonBlockProps = {
  height?: number;
  width?: number | `${number}%`;
};

export function SkeletonBlock({ height = 16, width = "100%" }: SkeletonBlockProps) {
  return <View style={[styles.block, { height, width }]} />;
}

export function SkeletonCard() {
  return (
    <View style={styles.card}>
      <SkeletonBlock width="44%" height={14} />
      <SkeletonBlock height={28} />
      <SkeletonBlock width="68%" height={14} />
    </View>
  );
}

const styles = StyleSheet.create({
  block: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radii.sm,
  },
  card: {
    backgroundColor: theme.colors.surface,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    gap: theme.spacing.md,
    padding: theme.spacing.lg,
  },
});
