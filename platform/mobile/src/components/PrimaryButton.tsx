import { Pressable, StyleSheet, Text } from "react-native";

import { theme } from "@/styles/theme";

type PrimaryButtonProps = {
  label: string;
  onPress: () => void;
};

export function PrimaryButton({ label, onPress }: PrimaryButtonProps) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.button, pressed && styles.pressed]}>
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: theme.colors.accent,
    borderRadius: 8,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: "center",
  },
  pressed: {
    opacity: 0.85,
  },
  label: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "700",
  },
});
