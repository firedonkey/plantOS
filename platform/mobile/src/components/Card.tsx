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
    backgroundColor: theme.colors.surfaceMuted,
    borderColor: theme.colors.borderSoft,
  },
  elevated: {
    borderColor: theme.colors.borderSoft,
    shadowColor: "#000000",
    shadowOpacity: 0.05,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 2,
  },
  hero: {
    backgroundColor: theme.colors.surface,
    borderColor: theme.colors.borderSoft,
    padding: theme.spacing.xl,
  },
});
