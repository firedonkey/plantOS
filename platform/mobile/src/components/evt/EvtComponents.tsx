import type { ReactNode } from "react";
import { Image, ImageSourcePropType, Pressable, StyleSheet, Text, View, ViewStyle } from "react-native";
import { router } from "expo-router";

import { evtAssets } from "@/assets/evtAssets";
import { theme } from "@/styles/theme";

type PlantLabHeaderProps = {
  right?: ReactNode;
  subtitle?: string;
};

export function PlantLabHeader({ right, subtitle = "SMART PLANT LABORATORY" }: PlantLabHeaderProps) {
  return (
    <View style={styles.header}>
      <View style={styles.wordmarkBlock}>
        <Image source={evtAssets.plantLabWordmark} style={styles.wordmark} resizeMode="contain" />
        {subtitle ? <Text style={styles.headerSubtitle}>{subtitle}</Text> : null}
      </View>
      {right ?? (
        <Pressable accessibilityLabel="Notifications" accessibilityRole="button" style={styles.headerIconButton}>
          <Image source={evtAssets.notificationIcon} style={styles.headerIcon} resizeMode="contain" />
        </Pressable>
      )}
    </View>
  );
}

type EvtCardProps = {
  children: ReactNode;
  compact?: boolean;
  style?: ViewStyle;
};

export function EvtCard({ children, compact = false, style }: EvtCardProps) {
  return <View style={[styles.card, compact ? styles.compactCard : null, style]}>{children}</View>;
}

type EvtSectionHeaderProps = {
  actionLabel?: string;
  icon?: ReactNode;
  onActionPress?: () => void;
  subtitle?: string;
  title: string;
};

export function EvtSectionHeader({ actionLabel, icon, onActionPress, subtitle, title }: EvtSectionHeaderProps) {
  return (
    <View style={styles.sectionHeader}>
      <View style={styles.sectionTitleGroup}>
        <View style={styles.sectionTitleRow}>
          {icon}
          <Text style={styles.sectionTitle}>{title}</Text>
        </View>
        {subtitle ? <Text style={styles.sectionSubtitle}>{subtitle}</Text> : null}
      </View>
      {actionLabel ? (
        <Pressable accessibilityRole="button" disabled={!onActionPress} onPress={onActionPress}>
          <Text style={styles.sectionAction}>{actionLabel}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

type MetricTileProps = {
  icon?: ImageSourcePropType;
  label: string;
  meta?: string;
  tone?: "green" | "blue" | "orange" | "gray" | "purple";
  value: string;
};

export function MetricTile({ icon, label, meta, tone = "green", value }: MetricTileProps) {
  return (
    <View style={styles.metricTile}>
      {icon ? <Image source={icon} style={styles.metricIcon} resizeMode="contain" /> : <View style={[styles.metricGlyph, metricToneStyles[tone]]} />}
      <Text style={styles.metricLabel} numberOfLines={2}>{label}</Text>
      <Text style={[styles.metricValue, metricValueToneStyles[tone]]} numberOfLines={1} adjustsFontSizeToFit>{value}</Text>
      {meta ? <Text style={styles.metricMeta} numberOfLines={1}>{meta}</Text> : null}
    </View>
  );
}

type ImageCardProps = {
  accessibilityLabel: string;
  children?: ReactNode;
  imageHeaders?: Record<string, string>;
  imageUrl?: string;
  style?: ViewStyle;
};

export function EvtImageCard({ accessibilityLabel, children, imageHeaders, imageUrl, style }: ImageCardProps) {
  const source = imageUrl ? (imageHeaders ? { uri: imageUrl, headers: imageHeaders } : { uri: imageUrl }) : null;
  return (
    <View style={[styles.imageFrame, style]}>
      {source ? (
        <Image accessibilityLabel={accessibilityLabel} source={source} style={styles.image} resizeMode="cover" />
      ) : (
        <View accessibilityLabel={accessibilityLabel} style={styles.imageFallback}>
          <Image source={evtAssets.plantOutlineIcon} style={styles.imageFallbackIcon} resizeMode="contain" />
          <Text style={styles.imageFallbackText}>Image unavailable</Text>
        </View>
      )}
      {children}
    </View>
  );
}

type DashboardTopNavProps = {
  active: "device" | "settings" | "support";
};

export function DashboardTopNav({ active }: DashboardTopNavProps) {
  return (
    <View style={styles.topNav}>
      <TopNavItem active={active === "device"} label="Device" onPress={() => router.push("/(app)/dashboard" as never)} />
      <TopNavItem active={active === "settings"} label="Settings" onPress={() => router.push("/(app)/settings")} />
      <TopNavItem active={active === "support"} label="Support" onPress={() => router.push("/(app)/support" as never)} />
    </View>
  );
}

function TopNavItem({ active, label, onPress }: { active: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={[styles.topNavItem, active ? styles.topNavItemActive : null]}
    >
      <Text style={[styles.topNavLabel, active ? styles.topNavLabelActive : null]}>{label}</Text>
    </Pressable>
  );
}

type InfoRowProps = {
  label: string;
  value: string;
  mono?: boolean;
};

export function EvtInfoRow({ label, value, mono = false }: InfoRowProps) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={[styles.infoValue, mono ? styles.mono : null]} numberOfLines={2}>{value}</Text>
    </View>
  );
}

type SmallActionCardProps = {
  body: string;
  icon: ReactNode;
  onPress: () => void;
  title: string;
};

export function SmallActionCard({ body, icon, onPress, title }: SmallActionCardProps) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.actionCard, pressed ? styles.pressed : null]}>
      <View style={styles.actionIcon}>{icon}</View>
      <View style={styles.actionCopy}>
        <Text style={styles.actionTitle}>{title}</Text>
        <Text style={styles.actionBody}>{body}</Text>
      </View>
      <Text style={styles.arrow}>→</Text>
    </Pressable>
  );
}

export function Dot({ color = theme.colors.primaryGreen, size = 8 }: { color?: string; size?: number }) {
  return <View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: color }} />;
}

const styles = StyleSheet.create({
  header: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    paddingTop: 4,
  },
  wordmarkBlock: {
    gap: 2,
  },
  wordmark: {
    height: 38,
    width: 136,
  },
  headerSubtitle: {
    color: theme.colors.textMuted,
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 0,
    marginLeft: 3,
  },
  headerIconButton: {
    alignItems: "center",
    height: 44,
    justifyContent: "center",
    width: 44,
  },
  headerIcon: {
    height: 30,
    width: 30,
  },
  card: {
    backgroundColor: theme.colors.cardBackground,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    gap: theme.spacing.md,
    padding: theme.spacing.md,
    ...theme.evtShadow,
  },
  compactCard: {
    gap: theme.spacing.sm,
    padding: theme.spacing.sm,
  },
  sectionHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    justifyContent: "space-between",
    gap: theme.spacing.md,
  },
  sectionTitleGroup: {
    flex: 1,
    gap: 3,
  },
  sectionTitleRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 5,
  },
  sectionTitle: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.sectionTitle,
    fontWeight: "800",
  },
  sectionSubtitle: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
  },
  sectionAction: {
    color: theme.colors.primaryGreen,
    fontSize: theme.evtTypography.caption,
    fontWeight: "800",
  },
  metricTile: {
    alignItems: "center",
    backgroundColor: theme.colors.cardBackground,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    flex: 1,
    gap: 4,
    minHeight: 104,
    minWidth: 74,
    paddingHorizontal: 6,
    paddingVertical: 12,
    ...theme.evtShadow,
  },
  metricIcon: {
    height: 22,
    width: 22,
  },
  metricGlyph: {
    borderRadius: 11,
    height: 22,
    width: 22,
  },
  metricLabel: {
    color: theme.colors.textSecondary,
    fontSize: theme.evtTypography.caption,
    textAlign: "center",
  },
  metricValue: {
    color: theme.colors.primaryGreen,
    fontSize: 17,
    fontWeight: "900",
    textAlign: "center",
  },
  metricMeta: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
    textAlign: "center",
  },
  imageFrame: {
    aspectRatio: 315 / 160,
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radii.md,
    overflow: "hidden",
  },
  image: {
    height: "100%",
    width: "100%",
  },
  imageFallback: {
    alignItems: "center",
    flex: 1,
    justifyContent: "center",
    gap: theme.spacing.sm,
  },
  imageFallbackIcon: {
    height: 54,
    opacity: 0.48,
    width: 54,
  },
  imageFallbackText: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.body,
    fontWeight: "700",
  },
  topNav: {
    backgroundColor: theme.colors.cardBackground,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.sm,
    borderWidth: 1,
    flexDirection: "row",
    overflow: "hidden",
  },
  topNavItem: {
    alignItems: "center",
    borderRightColor: theme.colors.borderSoft,
    borderRightWidth: 1,
    flex: 1,
    minHeight: 34,
    justifyContent: "center",
  },
  topNavItemActive: {
    backgroundColor: theme.colors.accentSoft,
    borderColor: theme.colors.primaryGreen,
    borderWidth: 1,
  },
  topNavLabel: {
    color: theme.colors.textSecondary,
    fontSize: theme.evtTypography.meta,
    fontWeight: "700",
  },
  topNavLabelActive: {
    color: theme.colors.darkGreen,
  },
  infoRow: {
    alignItems: "center",
    borderBottomColor: theme.colors.divider,
    borderBottomWidth: 1,
    flexDirection: "row",
    gap: theme.spacing.md,
    justifyContent: "space-between",
    minHeight: 45,
    paddingHorizontal: 10,
  },
  infoLabel: {
    color: theme.colors.textPrimary,
    flex: 1,
    fontSize: theme.evtTypography.body,
  },
  infoValue: {
    color: theme.colors.textMuted,
    flex: 1,
    fontSize: theme.evtTypography.body,
    textAlign: "right",
  },
  mono: {
    fontFamily: "Courier",
    fontSize: theme.evtTypography.meta,
  },
  actionCard: {
    alignItems: "center",
    backgroundColor: theme.colors.cardBackground,
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    flexDirection: "row",
    gap: theme.spacing.md,
    minHeight: 74,
    padding: theme.spacing.md,
    ...theme.evtShadow,
  },
  actionIcon: {
    alignItems: "center",
    backgroundColor: theme.colors.surfaceMuted,
    borderRadius: theme.radii.sm,
    height: 42,
    justifyContent: "center",
    width: 42,
  },
  actionCopy: {
    flex: 1,
    gap: 2,
  },
  actionTitle: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.bodyLarge,
    fontWeight: "800",
  },
  actionBody: {
    color: theme.colors.textSecondary,
    fontSize: theme.evtTypography.meta,
  },
  arrow: {
    color: theme.colors.textPrimary,
    fontSize: 26,
  },
  pressed: {
    opacity: 0.82,
  },
});

const metricToneStyles = StyleSheet.create({
  green: { backgroundColor: theme.colors.primaryGreen },
  blue: { backgroundColor: theme.colors.sensorWaterLevel },
  orange: { backgroundColor: theme.colors.sensorLight },
  gray: { backgroundColor: theme.colors.textMuted },
  purple: { backgroundColor: theme.colors.lavender },
});

const metricValueToneStyles = StyleSheet.create({
  green: { color: theme.colors.primaryGreen },
  blue: { color: theme.colors.sensorWaterLevel },
  orange: { color: theme.colors.sensorLight },
  gray: { color: theme.colors.textPrimary },
  purple: { color: theme.colors.lavender },
});
