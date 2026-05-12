import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { AddDeviceScreen } from "./screens/AddDeviceScreen";
import { DeviceDashboardScreen } from "./screens/DeviceDashboardScreen";
import { DeviceListScreen } from "./screens/DeviceListScreen";
import { HistoryScreen } from "./screens/HistoryScreen";
import { LoginScreen } from "./screens/LoginScreen";
import { RemoveDeviceScreen } from "./screens/RemoveDeviceScreen";
import { SettingsScreen } from "./screens/SettingsScreen";
import { SetupFinishingScreen } from "./screens/SetupFinishingScreen";
import { useSession } from "./hooks/useSession";

function ProtectedRoutes() {
  const { token } = useSession();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <AppLayout />;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginScreen />} />
      <Route path="/" element={<ProtectedRoutes />}>
        <Route index element={<Navigate to="/devices" replace />} />
        <Route path="devices" element={<DeviceListScreen />} />
        <Route path="devices/add" element={<AddDeviceScreen />} />
        <Route path="devices/setup-finishing" element={<SetupFinishingScreen />} />
        <Route path="devices/:deviceId" element={<DeviceDashboardScreen />} />
        <Route path="devices/:deviceId/history" element={<HistoryScreen />} />
        <Route path="devices/:deviceId/remove" element={<RemoveDeviceScreen />} />
        <Route path="settings" element={<SettingsScreen />} />
      </Route>
    </Routes>
  );
}
