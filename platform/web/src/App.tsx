import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { DeviceDashboardScreen } from "./screens/DeviceDashboardScreen";
import { DeviceListScreen } from "./screens/DeviceListScreen";
import { HistoryScreen } from "./screens/HistoryScreen";
import { LoginScreen } from "./screens/LoginScreen";
import { SettingsScreen } from "./screens/SettingsScreen";
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
        <Route path="devices/:deviceId" element={<DeviceDashboardScreen />} />
        <Route path="devices/:deviceId/history" element={<HistoryScreen />} />
        <Route path="settings" element={<SettingsScreen />} />
      </Route>
    </Routes>
  );
}
