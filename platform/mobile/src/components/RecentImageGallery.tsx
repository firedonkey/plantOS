import { useState } from "react";
import { Image, StyleSheet, Text, View } from "react-native";

import { Card } from "@/components/Card";
import { PrimaryButton } from "@/components/PrimaryButton";
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

  return (
    <Card>
      <View style={styles.header}>
        <View style={styles.headerText}>
          <Text style={styles.title}>Recent image gallery</Text>
          <Text style={styles.subtitle}>Recent uploads from the device appear here newest first.</Text>
        </View>
        {onCapture ? (
          <View style={styles.captureButton}>
            <PrimaryButton label={captureLabel} onPress={onCapture} disabled={captureDisabled} />
          </View>
        ) : null}
      </View>

      {!images.length ? (
        <Text style={styles.subtitle}>No image available yet. The gallery will populate after the device uploads its next image.</Text>
      ) : (
        <View style={styles.grid}>
          {images.map((image) => {
            const imageKey = `${image.id}:${image.url}`;
            const source = shouldUseImageHeaders(image.url) && imageHeaders ? { uri: image.url, headers: imageHeaders } : { uri: image.url };
            return (
              <View key={image.id} style={styles.item}>
                {failedImageKeys[imageKey] ? (
                  <View style={[styles.image, styles.imageFallback]}>
                    <Text style={styles.fallbackText}>Image unavailable</Text>
                  </View>
                ) : (
                  <Image
                    source={source}
                    style={styles.image}
                    onError={() => setFailedImageKeys((current) => ({ ...current, [imageKey]: true }))}
                  />
                )}
                <Text style={styles.meta}>Captured {new Date(image.capturedAt).toLocaleString()}</Text>
              </View>
            );
          })}
        </View>
      )}
    </Card>
  );
}

function shouldUseImageHeaders(url: string): boolean {
  const path = url.replace(/^https?:\/\/[^/]+/i, "");
  return path.startsWith("/api/images/") && path.split("?")[0].endsWith("/content");
}

const styles = StyleSheet.create({
  header: { gap: 12 },
  headerText: { gap: 4 },
  captureButton: { alignSelf: "flex-start", minWidth: 160 },
  title: { fontSize: 18, fontWeight: "700", color: theme.colors.textPrimary },
  subtitle: { fontSize: 14, color: theme.colors.textSecondary },
  grid: { gap: 12 },
  item: { gap: 8 },
  image: { width: "100%", height: 220, borderRadius: 8, backgroundColor: "#dfe5e9" },
  imageFallback: { alignItems: "center", justifyContent: "center" },
  fallbackText: { fontSize: 14, fontWeight: "600", color: theme.colors.textSecondary },
  meta: { fontSize: 13, color: theme.colors.textSecondary },
});
