import { useLocalSearchParams } from "expo-router";

import { DeviceDashboardScreen } from "@/screens/DeviceDashboardScreen";

export default function DeviceDashboardRoute() {
  const params = useLocalSearchParams<{ deviceId?: string }>();
  return <DeviceDashboardScreen deviceId={params.deviceId ?? ""} />;
}
