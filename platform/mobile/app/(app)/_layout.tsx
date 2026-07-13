import { Tabs } from "expo-router";
import { Image, ImageSourcePropType } from "react-native";

import { evtAssets } from "@/assets/evtAssets";
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
          backgroundColor: "rgba(246, 249, 247, 0.96)",
          borderTopColor: theme.colors.borderSoft,
          height: 76,
          paddingTop: 8,
          paddingBottom: 14,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: "500" },
        tabBarActiveTintColor: theme.colors.accent,
        tabBarInactiveTintColor: theme.colors.textMuted,
      }}
    >
      <Tabs.Screen
        name="devices"
        options={{
          title: "Home",
          headerShown: false,
          tabBarIcon: ({ color }) => <TabIcon color={color} source={evtAssets.homeIcon} />,
        }}
      />
      <Tabs.Screen
        name="case"
        options={{
          title: "Case",
          headerShown: false,
          tabBarIcon: ({ color }) => <TabIcon color={color} source={evtAssets.caseIcon} />,
        }}
      />
      <Tabs.Screen
        name="dashboard"
        options={{
          title: "Data",
          headerShown: false,
          tabBarIcon: ({ color }) => <TabIcon color={color} source={evtAssets.dataIcon} />,
        }}
      />
      <Tabs.Screen name="settings" options={{ href: null, headerShown: false, tabBarStyle: { display: "none" } }} />
      <Tabs.Screen name="support" options={{ href: null, headerShown: false, tabBarStyle: { display: "none" } }} />
    </Tabs>
  );
}

function TabIcon({ color, source }: { color: string; source: ImageSourcePropType }) {
  return <Image source={source} style={{ height: 19, tintColor: color, width: 19 }} resizeMode="contain" />;
}
