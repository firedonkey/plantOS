import { Redirect } from "expo-router";

import { useSession } from "@/hooks/useSession";
import { LandingScreen } from "@/screens/LandingScreen";

export default function IndexRoute() {
  const { isHydrated, token } = useSession();

  if (!isHydrated) {
    return null;
  }

  if (token) {
    return <Redirect href="/(app)/devices" />;
  }

  return <LandingScreen />;
}
