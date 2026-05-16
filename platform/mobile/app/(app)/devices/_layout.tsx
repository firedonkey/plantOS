import { Stack } from "expo-router";

import { theme } from "@/styles/theme";

export default function DevicesLayout() {
  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: theme.colors.background },
        headerShadowVisible: false,
        headerTitleStyle: { color: theme.colors.textPrimary, fontSize: 17, fontWeight: "800" },
        headerTintColor: theme.colors.textPrimary,
        contentStyle: { backgroundColor: theme.colors.background },
      }}
    >
      <Stack.Screen name="index" options={{ title: "Devices" }} />
      <Stack.Screen name="add" options={{ title: "Add device" }} />
      <Stack.Screen name="[deviceId]/index" options={{ title: "Device" }} />
      <Stack.Screen name="[deviceId]/history" options={{ title: "History" }} />
      <Stack.Screen name="[deviceId]/settings" options={{ title: "Device settings" }} />
    </Stack>
  );
}
