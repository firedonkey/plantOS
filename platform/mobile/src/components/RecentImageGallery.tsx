import { Dispatch, SetStateAction, useState } from "react";
import { Image, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { PrimaryButton } from "@/components/PrimaryButton";
import { SectionHeader } from "@/components/SectionHeader";
import { LatestImage } from "@/types";
import { theme } from "@/styles/theme";

type RecentImageGalleryProps = {
  images: LatestImage[];
  imageHeaders?: Record<string, string>;
  captureDisabled?: boolean;
  captureLabel?: string;
  onCapture?: () => void;
};

export function RecentImageGallery({
  images,
  imageHeaders,
  captureDisabled = false,
  captureLabel = "Capture image",
  onCapture,
}: RecentImageGalleryProps) {
  const [failedImageKeys, setFailedImageKeys] = useState<Record<string, true>>({});
  const latestImage = images[0];
  const olderImages = images.slice(1, 4);

  return (
    <Card variant="elevated">
      <View style={styles.header}>
        <SectionHeader
          title="Camera"
          subtitle={latestImage ? `${formatCameraRole(latestImage.cameraRole)} capture ${formatImageAge(latestImage.capturedAt)}` : "Latest device captures appear here."}
        />
        {onCapture ? (
          <View style={styles.captureButton}>
            <PrimaryButton label={captureLabel} onPress={onCapture} disabled={captureDisabled} />
          </View>
        ) : null}
      </View>

      {!images.length ? (
        <EmptyState title="No image yet" message="The gallery will populate after the device uploads its next capture." />
      ) : (
        <View style={styles.gallery}>
          <GalleryImage
            failedImageKeys={failedImageKeys}
            image={latestImage}
            imageHeaders={imageHeaders}
            setFailedImageKeys={setFailedImageKeys}
            primary
          />
          {olderImages.length ? (
            <View style={styles.thumbnailRow}>
              {olderImages.map((image) => (
                <GalleryImage
                  key={image.id}
                  failedImageKeys={failedImageKeys}
                  image={image}
                  imageHeaders={imageHeaders}
                  setFailedImageKeys={setFailedImageKeys}
                />
              ))}
            </View>
          ) : null}
        </View>
      )}
    </Card>
  );
}

function GalleryImage({
  failedImageKeys,
  image,
  imageHeaders,
  setFailedImageKeys,
  primary = false,
}: {
  failedImageKeys: Record<string, true>;
  image: LatestImage;
  imageHeaders?: Record<string, string>;
  setFailedImageKeys: Dispatch<SetStateAction<Record<string, true>>>;
  primary?: boolean;
}) {
  const imageKey = `${image.id}:${image.url}`;
  const source = shouldUseImageHeaders(image.url) && imageHeaders ? { uri: image.url, headers: imageHeaders } : { uri: image.url };

  return (
    <View style={primary ? styles.item : styles.thumbnailItem}>
      {failedImageKeys[imageKey] ? (
        <View style={[primary ? styles.image : styles.thumbnailImage, styles.imageFallback]}>
          <Text style={styles.fallbackText}>Image unavailable</Text>
        </View>
      ) : (
        <Image
          source={source}
          style={primary ? styles.image : styles.thumbnailImage}
          onError={() => setFailedImageKeys((current) => ({ ...current, [imageKey]: true }))}
        />
      )}
      <Text style={styles.meta}>{formatCameraRole(image.cameraRole)} camera - {formatTimestamp(image.capturedAt)}</Text>
    </View>
  );
}

function formatCameraRole(role: LatestImage["cameraRole"]) {
  if (role === "side") {
    return "Side";
  }
  return "Top";
}

function shouldUseImageHeaders(url: string): boolean {
  const path = url.replace(/^https?:\/\/[^/]+/i, "");
  return path.startsWith("/api/images/") && path.split("?")[0].endsWith("/content");
}

function formatImageAge(timestamp: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 1000));
  if (seconds < 60) {
    return "just now";
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.round(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function formatTimestamp(timestamp: string) {
  return new Date(timestamp).toLocaleString();
}

const styles = StyleSheet.create({
  header: { gap: theme.spacing.md },
  captureButton: { alignSelf: "flex-start", minWidth: 160 },
  gallery: { gap: theme.spacing.md },
  item: { gap: theme.spacing.sm },
  thumbnailRow: { flexDirection: "row", gap: theme.spacing.sm },
  thumbnailItem: { flex: 1, gap: theme.spacing.xs },
  image: { width: "100%", aspectRatio: 4 / 3, borderRadius: theme.radii.md, backgroundColor: theme.colors.surfaceInset },
  thumbnailImage: { width: "100%", aspectRatio: 1, borderRadius: theme.radii.sm, backgroundColor: theme.colors.surfaceInset },
  imageFallback: { alignItems: "center", justifyContent: "center" },
  fallbackText: { fontSize: 14, fontWeight: "600", color: theme.colors.textSecondary },
  meta: { fontSize: theme.typography.meta, color: theme.colors.textMuted },
});
