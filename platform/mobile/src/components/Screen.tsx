import { PropsWithChildren, useEffect, useRef } from "react";
import { KeyboardAvoidingView, Platform, RefreshControl, ScrollView, StyleSheet } from "react-native";

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
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={24}
      style={styles.container}
    >
      <ScrollView
        ref={scrollRef}
        keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "none"}
        keyboardShouldPersistTaps="handled"
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
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scroll: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  content: {
    padding: theme.spacing.xl,
    paddingBottom: 72,
    gap: theme.spacing.lg,
  },
});
