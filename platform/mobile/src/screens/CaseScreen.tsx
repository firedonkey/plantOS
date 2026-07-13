import { router } from "expo-router";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import { evtAssets } from "@/assets/evtAssets";
import { evtCaseStats, evtUseCaseCards, type EvtUseCaseCard } from "@/config/evtContent";
import { Dot, EvtCard, EvtImageCard, EvtSectionHeader, MetricTile, PlantLabHeader } from "@/components/evt/EvtComponents";
import { Screen } from "@/components/Screen";
import { useDevices } from "@/hooks/useDevices";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";
import { formatHumidity, formatLightState, formatTemperature, formatWaterLevel } from "@/utils/formatting";

export function CaseScreen() {
  const { devices, isLoading, refresh } = useDevices();
  const { token } = useSession();
  const device = devices[0];
  const latestReading = device?.latestReading;
  const latestImage = device?.latestImage;
  const imageHeaders = latestImage?.url ? imageHeadersFor(latestImage.url, token) : undefined;

  return (
    <Screen onRefresh={refresh} refreshing={isLoading}>
      <PlantLabHeader
        right={
          <View style={styles.headerActions}>
            <Pressable accessibilityLabel="Open dashboard" accessibilityRole="button" onPress={() => router.push("/(app)/dashboard" as never)}>
              <Image source={evtAssets.dataIcon} style={styles.headerIcon} resizeMode="contain" />
            </Pressable>
            <Image source={evtAssets.notificationIcon} style={styles.notificationIcon} resizeMode="contain" />
          </View>
        }
      />

      <View style={styles.hero}>
        <EvtImageCard
          accessibilityLabel="PlantLab Mars Lab case image"
          imageHeaders={imageHeaders}
          imageUrl={latestImage?.url}
          style={styles.heroImage}
        >
          <View style={styles.heroOverlay} />
          <Text style={styles.heroTitle}>Mars Lab</Text>
          <View style={styles.liveBadge}>
            <Dot color="#33f24d" />
            <Text style={styles.liveText}>Live</Text>
          </View>
          <View style={styles.playButton}>
            <Text style={styles.playIcon}>&gt;</Text>
          </View>
        </EvtImageCard>
      </View>

      <View style={styles.metricRow}>
        <MetricTile label="Temperature" value={formatTemperature(latestReading?.temperatureC)} meta="Temperature" tone="green" />
        <MetricTile label="Humidity" value={formatHumidity(latestReading?.humidityPercent)} meta="Humidity" tone="green" />
        <MetricTile label="Water Level" value={formatWaterLevel(latestReading)} meta="Water Level" tone="green" />
      </View>

      <EvtCard>
        <EvtSectionHeader title="Latest Capture" actionLabel={latestImage ? "Today" : "Waiting"} />
        <EvtImageCard
          accessibilityLabel="Latest PlantLab case capture"
          imageHeaders={imageHeaders}
          imageUrl={latestImage?.url}
        />
        <View style={styles.identificationRow}>
          <Image source={evtAssets.plantIdentificationIcon} style={styles.plantIcon} resizeMode="contain" />
          <View style={styles.identificationCopy}>
            <Text style={styles.identificationLabel}>Plant Identification</Text>
            <Text style={styles.identificationTitle}>{device?.plantType ?? "Plant profile not set"}</Text>
            <Text style={styles.identificationMeta}>{device?.plantType ? "Profile data from device settings" : "Add plant type in settings"}</Text>
          </View>
        </View>
      </EvtCard>

      <View style={styles.sectionSpacer}>
        <EvtSectionHeader title="Environment Overview" actionLabel="View All" onActionPress={() => router.push("/(app)/dashboard" as never)} />
        <View style={styles.metricRow}>
          <MetricTile label="Temperature" value={formatTemperature(latestReading?.temperatureC)} meta="Optimal" tone="green" />
          <MetricTile label="Humidity" value={formatHumidity(latestReading?.humidityPercent)} meta="Optimal" tone="green" />
          <MetricTile label="Water Level" value={formatWaterLevel(latestReading)} meta="Reported" tone="blue" />
          <MetricTile label="Light" value={device ? formatLightState(device) : "--"} meta="Reported" tone="orange" />
        </View>
      </View>

      <EvtCard>
        <EvtSectionHeader title="Growth Story" subtitle="From Day 1 to Day 7" actionLabel="View All" />
        <GrowthPreview />
        <View style={styles.caseStatsRow}>
          {evtCaseStats.map((stat) => (
            <View key={stat.id} style={styles.caseStat}>
              <Text style={styles.caseStatValue}>{stat.value}</Text>
              <Text style={styles.caseStatLabel}>{stat.label}</Text>
            </View>
          ))}
        </View>
        <PrimaryOutlineButton label="Watch Growth Video" onPress={() => router.push("/(app)/dashboard" as never)} />
      </EvtCard>

      <EvtCard>
        <EvtSectionHeader title="Designed For" />
        <View style={styles.useCaseList}>
          {evtUseCaseCards.map((card) => (
            <UseCaseRow card={card} key={card.id} />
          ))}
        </View>
      </EvtCard>
    </Screen>
  );
}

function GrowthPreview() {
  return (
    <View style={styles.growthStrip}>
      {Array.from({ length: 7 }, (_, index) => (
        <View key={index} style={styles.growthItem}>
          <View style={styles.growthPlaceholder}>
            <Image source={evtAssets.plantIdentificationIcon} style={styles.growthPlantIcon} resizeMode="contain" />
          </View>
          <Text style={styles.growthDay}>Day {index + 1}</Text>
          <Text style={styles.growthDate}>May {10 + index}</Text>
        </View>
      ))}
    </View>
  );
}

function UseCaseRow({ card }: { card: EvtUseCaseCard }) {
  return (
    <View style={styles.useCaseRow}>
      <View style={styles.useCaseIcon}>
        <Text style={styles.useCaseGlyph}>{iconGlyph(card.icon)}</Text>
      </View>
      <View style={styles.useCaseCopy}>
        <Text style={styles.useCaseTitle}>{card.title}</Text>
        <Text style={styles.useCaseDescription}>{card.description}</Text>
      </View>
    </View>
  );
}

function PrimaryOutlineButton({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.outlineButton}>
      <Text style={styles.outlineButtonText}>{label}</Text>
    </Pressable>
  );
}

function iconGlyph(icon: EvtUseCaseCard["icon"]): string {
  switch (icon) {
    case "enthusiasts":
      return "P";
    case "smart-home":
      return "H";
    case "education":
      return "E";
    case "manufacturing":
      return "M";
  }
}

function imageHeadersFor(url: string, token: string | null): Record<string, string> | undefined {
  if (!token) {
    return undefined;
  }
  const path = url.replace(/^https?:\/\/[^/]+/i, "");
  return path.startsWith("/api/images/") && path.split("?")[0].endsWith("/content") ? { Authorization: `Bearer ${token}` } : undefined;
}

const styles = StyleSheet.create({
  headerActions: {
    alignItems: "center",
    flexDirection: "row",
    gap: 18,
  },
  headerIcon: {
    height: 25,
    tintColor: theme.colors.textPrimary,
    width: 25,
  },
  notificationIcon: {
    height: 30,
    width: 30,
  },
  hero: {
    gap: theme.spacing.md,
  },
  heroImage: {
    aspectRatio: 343 / 210,
  },
  heroOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.22)",
  },
  heroTitle: {
    color: theme.colors.white,
    fontSize: 24,
    fontWeight: "900",
    left: 20,
    position: "absolute",
    top: 20,
  },
  liveBadge: {
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,0.52)",
    borderRadius: theme.radii.sm,
    flexDirection: "row",
    gap: 6,
    paddingHorizontal: 9,
    paddingVertical: 7,
    position: "absolute",
    right: 16,
    top: 16,
  },
  liveText: {
    color: theme.colors.white,
    fontSize: theme.evtTypography.body,
    fontWeight: "800",
  },
  playButton: {
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.78)",
    borderRadius: 24,
    height: 48,
    justifyContent: "center",
    left: "50%",
    marginLeft: -24,
    marginTop: -24,
    position: "absolute",
    top: "50%",
    width: 48,
  },
  playIcon: {
    color: theme.colors.white,
    fontSize: 22,
    marginLeft: 3,
  },
  metricRow: {
    flexDirection: "row",
    gap: 10,
  },
  identificationRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
  },
  plantIcon: {
    height: 48,
    width: 48,
  },
  identificationCopy: {
    flex: 1,
    gap: 2,
  },
  identificationLabel: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.caption,
    fontWeight: "800",
  },
  identificationTitle: {
    color: theme.colors.textPrimary,
    fontSize: 17,
    fontWeight: "900",
  },
  identificationMeta: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
  },
  sectionSpacer: {
    gap: theme.spacing.sm,
  },
  growthStrip: {
    flexDirection: "row",
    gap: 8,
  },
  growthItem: {
    alignItems: "center",
    flex: 1,
    gap: 2,
  },
  growthPlaceholder: {
    alignItems: "center",
    aspectRatio: 1,
    backgroundColor: theme.colors.accentSoft,
    borderRadius: 4,
    justifyContent: "center",
    width: "100%",
  },
  growthPlantIcon: {
    height: 24,
    width: 24,
  },
  growthDay: {
    color: theme.colors.textPrimary,
    fontSize: 9,
    fontWeight: "800",
  },
  growthDate: {
    color: theme.colors.textMuted,
    fontSize: 8,
  },
  caseStatsRow: {
    flexDirection: "row",
    gap: 10,
    justifyContent: "space-between",
  },
  caseStat: {
    alignItems: "center",
    flex: 1,
    gap: 2,
  },
  caseStatValue: {
    color: theme.colors.textSecondary,
    fontSize: theme.evtTypography.body,
    fontWeight: "800",
  },
  caseStatLabel: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
    textAlign: "center",
  },
  outlineButton: {
    alignItems: "center",
    borderColor: theme.colors.primaryGreen,
    borderRadius: theme.radii.sm,
    borderWidth: 1,
    minHeight: 34,
    justifyContent: "center",
  },
  outlineButtonText: {
    color: theme.colors.primaryGreen,
    fontSize: theme.evtTypography.caption,
    fontWeight: "800",
  },
  useCaseList: {
    gap: 8,
  },
  useCaseRow: {
    alignItems: "center",
    borderColor: theme.colors.borderSoft,
    borderRadius: theme.radii.sm,
    borderWidth: 1,
    flexDirection: "row",
    gap: 12,
    minHeight: 42,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  useCaseIcon: {
    alignItems: "center",
    height: 26,
    justifyContent: "center",
    width: 26,
  },
  useCaseGlyph: {
    color: theme.colors.primaryGreen,
    fontSize: theme.evtTypography.bodyLarge,
    fontWeight: "900",
  },
  useCaseCopy: {
    flex: 1,
  },
  useCaseTitle: {
    color: theme.colors.textPrimary,
    fontSize: theme.evtTypography.body,
    fontWeight: "900",
  },
  useCaseDescription: {
    color: theme.colors.textMuted,
    fontSize: theme.evtTypography.caption,
  },
});
