import { PropsWithChildren } from "react";
import { StyleSheet, View } from "react-native";

import { theme } from "@/styles/theme";

export function Card({ children }: PropsWithChildren) {
  return <View style={styles.card}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: 16,
    gap: 10,
  },
});
