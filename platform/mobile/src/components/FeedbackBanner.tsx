import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";

type FeedbackBannerProps = {
  message: string;
  tone?: "success" | "error" | "info" | "warning";
};

export function FeedbackBanner({ message, tone = "info" }: FeedbackBannerProps) {
  return (
    <View style={[styles.banner, toneStyles[tone]]}>
      <Text style={[styles.text, textStyles[tone]]}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    borderRadius: theme.radii.md,
    borderWidth: 1,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.md,
  },
  text: {
    fontSize: theme.typography.body,
    fontWeight: "700",
    lineHeight: 20,
  },
});

const toneStyles = StyleSheet.create({
  success: {
    backgroundColor: theme.colors.successSoft,
    borderColor: theme.colors.successSoft,
  },
  error: {
    backgroundColor: theme.colors.dangerSoft,
    borderColor: theme.colors.dangerSoft,
  },
  info: {
    backgroundColor: theme.colors.infoSoft,
    borderColor: theme.colors.infoSoft,
  },
  warning: {
    backgroundColor: theme.colors.warningSoft,
    borderColor: theme.colors.warningSoft,
  },
});

const textStyles = StyleSheet.create({
  success: { color: theme.colors.success },
  error: { color: theme.colors.danger },
  info: { color: theme.colors.info },
  warning: { color: theme.colors.warning },
});
