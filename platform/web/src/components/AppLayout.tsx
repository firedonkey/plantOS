import { NavLink, Outlet } from "react-router-dom";

import { useSession } from "@/hooks/useSession";

export function AppLayout() {
  const { signOut } = useSession();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="eyebrow">PLANTLAB</div>
          <h1>Dashboard</h1>
        </div>
        <nav className="nav">
          <NavLink to="/devices" className="nav-link">
            Devices
          </NavLink>
          <NavLink to="/devices/add" className="nav-link">
            Add device
          </NavLink>
          <NavLink to="/settings" className="nav-link">
            Settings
          </NavLink>
        </nav>
        <button className="secondary-button" onClick={signOut}>
          Log out
        </button>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
