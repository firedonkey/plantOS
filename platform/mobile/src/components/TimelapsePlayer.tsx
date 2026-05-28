import { useEffect, useState } from "react";
import { Image, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { PrimaryButton } from "@/components/PrimaryButton";
import { SectionHeader } from "@/components/SectionHeader";
import { DeviceTimelapse, TimelapseFrame } from "@/types";
import { theme } from "@/styles/theme";

type TimelapsePlayerProps = {
  timelapse?: DeviceTimelapse;
  imageHeaders?: Record<string, string>;
};

export function TimelapsePlayer({ timelapse, imageHeaders }: TimelapsePlayerProps) {
  const frames = timelapse?.frames ?? [];
  const [frameIndex, setFrameIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const currentFrame = frames[Math.min(frameIndex, Math.max(frames.length - 1, 0))];

  useEffect(() => {
    setFrameIndex(0);
    setPlaying(false);
  }, [timelapse?.windowStart, timelapse?.windowEnd, frames.length]);

  useEffect(() => {
    if (!playing || frames.length < 2) {
      return;
    }
    const intervalId = setInterval(() => {
      setFrameIndex((current) => (current + 1) % frames.length);
    }, timelapse?.playbackFrameMs ?? 450);
    return () => clearInterval(intervalId);
  }, [frames.length, playing, timelapse?.playbackFrameMs]);

  return (
    <Card variant="elevated">
      <View style={styles.header}>
        <SectionHeader title="Growth timelapse" subtitle={subtitleForTimelapse(timelapse)} />
        {frames.length >= 2 ? (
          <View style={styles.actions}>
            <View style={styles.actionButton}>
              <PrimaryButton label={playing ? "Pause" : "Play"} onPress={() => setPlaying((current) => !current)} />
            </View>
            <View style={styles.actionButton}>
              <PrimaryButton
                label="Restart"
                onPress={() => {
                  setFrameIndex(0);
                  setPlaying(false);
                }}
                tone="secondary"
              />
            </View>
          </View>
        ) : null}
      </View>

      {!currentFrame ? (
        <EmptyState title="No timelapse yet" message="PlantLab will build a timelapse after the camera has multiple captures over time." />
      ) : (
        <View style={styles.player}>
          <TimelapseImage frame={currentFrame} imageHeaders={imageHeaders} />
          <View style={styles.metaRow}>
            <Text style={styles.meta}>
              Frame {frameIndex + 1} of {frames.length}
            </Text>
            <Text style={styles.meta}>{formatTimestamp(currentFrame.capturedAt)}</Text>
          </View>
          {frames.length < 2 ? (
            <Text style={styles.helper}>One more capture is needed before playback is available.</Text>
          ) : null}
        </View>
      )}
    </Card>
  );
}

function TimelapseImage({ frame, imageHeaders }: { frame: TimelapseFrame; imageHeaders?: Record<string, string> }) {
  const source = shouldUseImageHeaders(frame.url) && imageHeaders ? { uri: frame.url, headers: imageHeaders } : { uri: frame.url };
  return <Image source={source} style={styles.image} />;
}

function subtitleForTimelapse(timelapse?: DeviceTimelapse): string {
  if (!timelapse || timelapse.frameCount === 0) {
    return "Sampled from the last week of camera captures.";
  }
  const imageWord = timelapse.totalImageCount === 1 ? "capture" : "captures";
  const frameWord = timelapse.frameCount === 1 ? "frame" : "frames";
  return `${timelapse.frameCount} ${frameWord} from ${timelapse.totalImageCount} ${imageWord}, sampled every ${formatInterval(timelapse.intervalMinutes)}.`;
}

function formatInterval(minutes: number): string {
  if (minutes < 60) {
    return `${minutes} min`;
  }
  const hours = minutes / 60;
  return Number.isInteger(hours) ? `${hours}h` : `${hours.toFixed(1)}h`;
}

function shouldUseImageHeaders(url: string): boolean {
  const path = url.replace(/^https?:\/\/[^/]+/i, "");
  return path.startsWith("/api/images/") && path.split("?")[0].endsWith("/content");
}

function formatTimestamp(timestamp: string) {
  return new Date(timestamp).toLocaleString();
}

const styles = StyleSheet.create({
  header: { gap: theme.spacing.md },
  actions: { flexDirection: "row", gap: theme.spacing.sm },
  actionButton: { flex: 1 },
  player: { gap: theme.spacing.sm },
  image: {
    width: "100%",
    aspectRatio: 4 / 3,
    borderRadius: theme.radii.md,
    backgroundColor: theme.colors.surfaceInset,
  },
  metaRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: theme.spacing.sm,
    justifyContent: "space-between",
  },
  meta: { color: theme.colors.textMuted, fontSize: theme.typography.meta },
  helper: { color: theme.colors.textSecondary, fontSize: theme.typography.body, lineHeight: 20 },
});
