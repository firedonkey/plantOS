import { useLocalSearchParams } from "expo-router";

import { HistoryScreen } from "@/screens/HistoryScreen";

export default function HistoryRoute() {
  const params = useLocalSearchParams<{ deviceId?: string }>();
  return <HistoryScreen deviceId={params.deviceId ?? ""} />;
}
