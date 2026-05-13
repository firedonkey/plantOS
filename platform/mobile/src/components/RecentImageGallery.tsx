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
          {images.map((image) => (
            <View key={image.id} style={styles.item}>
              <Image source={{ uri: image.url, headers: imageHeaders }} style={styles.image} />
              <Text style={styles.meta}>Captured {new Date(image.capturedAt).toLocaleString()}</Text>
            </View>
          ))}
        </View>
      )}
    </Card>
  );
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
  meta: { fontSize: 13, color: theme.colors.textSecondary },
});
