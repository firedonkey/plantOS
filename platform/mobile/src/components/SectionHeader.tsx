import { StyleSheet, Text, View } from "react-native";

import { theme } from "@/styles/theme";

type SectionHeaderProps = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
};

export function SectionHeader({ eyebrow, title, subtitle }: SectionHeaderProps) {
  return (
    <View style={styles.container}>
      {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: theme.spacing.xs,
  },
  eyebrow: {
    color: theme.colors.accent,
    fontSize: theme.typography.eyebrow,
    fontWeight: "800",
  },
  title: {
    color: theme.colors.textPrimary,
    fontSize: theme.typography.sectionTitle,
    fontWeight: "800",
  },
  subtitle: {
    color: theme.colors.textSecondary,
    fontSize: theme.typography.body,
    lineHeight: 20,
  },
});
