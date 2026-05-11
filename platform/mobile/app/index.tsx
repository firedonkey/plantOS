import { Redirect } from "expo-router";

import { useSession } from "@/hooks/useSession";

export default function IndexRoute() {
  const { isHydrated, token } = useSession();

  if (!isHydrated) {
    return null;
  }

  if (!token) {
    return <Redirect href="/login" />;
  }

  return <Redirect href="/(app)/devices" />;
}
