import { PropsWithChildren, useEffect, useRef } from "react";
import { RefreshControl, ScrollView, StyleSheet } from "react-native";

import { theme } from "@/styles/theme";

type ScreenProps = PropsWithChildren<{
  onRefresh?: () => void;
  refreshing?: boolean;
  scrollToTopSignal?: string | number | boolean | null;
}>;

export function Screen({ children, onRefresh, refreshing = false, scrollToTopSignal }: ScreenProps) {
  const scrollRef = useRef<ScrollView>(null);

  useEffect(() => {
    if (scrollToTopSignal !== undefined) {
      scrollRef.current?.scrollTo({ y: 0, animated: true });
    }
  }, [scrollToTopSignal]);

  return (
    <ScrollView
      ref={scrollRef}
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
