import { PropsWithChildren } from "react";
import { StyleSheet, View, ViewStyle } from "react-native";

import { theme } from "@/styles/theme";

type CardProps = PropsWithChildren<{
  variant?: "default" | "inset" | "elevated" | "hero";
  style?: ViewStyle;
}>;

export function Card({ children, variant = "default", style }: CardProps) {
  return <View style={[styles.card, variantStyles[variant], style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: theme.spacing.lg,
    gap: theme.spacing.md,
  },
});

const variantStyles = StyleSheet.create({
  default: {},
  inset: {
    ...theme.surfaces.muted,
  },
  elevated: {
    borderColor: theme.surfaces.hero.borderColor,
    ...theme.elevation.card,
  },
  hero: {
    ...theme.surfaces.hero,
    ...theme.elevation.hero,
    padding: theme.spacing.xl,
  },
});
