import { PropsWithChildren } from "react";
import { RefreshControl, ScrollView, StyleSheet } from "react-native";

import { theme } from "@/styles/theme";

type ScreenProps = PropsWithChildren<{
  onRefresh?: () => void;
  refreshing?: boolean;
}>;

export function Screen({ children, onRefresh, refreshing = false }: ScreenProps) {
  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      refreshControl={
        onRefresh ? (
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.accent} />
        ) : undefined
      }
    >
      {children}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  content: {
    padding: 20,
    gap: 16,
  },
});
