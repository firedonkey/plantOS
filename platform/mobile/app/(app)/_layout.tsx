import { Tabs } from "expo-router";

import { theme } from "@/styles/theme";

export default function AppLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: theme.colors.background },
        headerShadowVisible: false,
        headerTitleStyle: { color: theme.colors.textPrimary, fontSize: 17, fontWeight: "800" },
        headerTintColor: theme.colors.textPrimary,
        tabBarStyle: {
          backgroundColor: theme.colors.surface,
          borderTopColor: theme.colors.border,
        },
        tabBarLabelStyle: { fontSize: 12, fontWeight: "700" },
        tabBarActiveTintColor: theme.colors.accent,
        tabBarInactiveTintColor: theme.colors.textMuted,
      }}
    >
      <Tabs.Screen name="devices" options={{ title: "Devices", headerShown: false }} />
      <Tabs.Screen name="settings" options={{ title: "Settings" }} />
    </Tabs>
  );
}
