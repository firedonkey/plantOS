import { PropsWithChildren, useEffect, useRef } from "react";
import { KeyboardAvoidingView, Platform, RefreshControl, ScrollView, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { theme } from "@/styles/theme";

type ScreenProps = PropsWithChildren<{
  onRefresh?: () => void;
  refreshing?: boolean;
  scrollEnabled?: boolean;
  scrollToTopSignal?: string | number | boolean | null;
  transparentBackground?: boolean;
}>;

export function Screen({
  children,
  onRefresh,
  refreshing = false,
  scrollEnabled = true,
  scrollToTopSignal,
  transparentBackground = false,
}: ScreenProps) {
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
      style={[styles.container, transparentBackground ? styles.transparent : null]}
    >
      <SafeAreaView edges={["top", "left", "right"]} style={[styles.safeArea, transparentBackground ? styles.transparent : null]}>
        <ScrollView
          ref={scrollRef}
          keyboardDismissMode={Platform.OS === "ios" ? "interactive" : "none"}
          keyboardShouldPersistTaps="handled"
          scrollEnabled={scrollEnabled}
          style={[styles.scroll, transparentBackground ? styles.transparent : null]}
          contentContainerStyle={styles.content}
          refreshControl={
            onRefresh ? (
              <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.accent} />
            ) : undefined
          }
        >
          {children}
        </ScrollView>
      </SafeAreaView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  safeArea: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scroll: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  content: {
    padding: theme.spacing.page,
    paddingBottom: 72,
    gap: theme.spacing.lg,
  },
  transparent: {
    backgroundColor: "transparent",
  },
});
