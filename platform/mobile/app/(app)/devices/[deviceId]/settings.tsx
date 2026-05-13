import { useLocalSearchParams } from "expo-router";

import { DeviceSettingsScreen } from "@/screens/DeviceSettingsScreen";

export default function DeviceSettingsRoute() {
  const params = useLocalSearchParams<{ deviceId?: string }>();
  return <DeviceSettingsScreen deviceId={params.deviceId ?? ""} />;
}
