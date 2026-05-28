import { Link, NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";

import { fetchCurrentUserProfile } from "@/api/auth";
import { useSession } from "@/hooks/useSession";

export function AppLayout() {
  const { session, signOut, token } = useSession();
  const [isAdmin, setIsAdmin] = useState(Boolean(session?.isAdmin));

  useEffect(() => {
    if (!token) {
      setIsAdmin(false);
      return;
    }
    let cancelled = false;
    fetchCurrentUserProfile(token, session?.email)
      .then((result) => {
        if (!cancelled) {
          setIsAdmin(Boolean(result.profile.isAdmin));
        }
      })
      .catch(() => {
        if (!cancelled) {
          setIsAdmin(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [session?.email, token]);

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <Link to="/" className="eyebrow brand-home-link" aria-label="Open PlantLab landing page">
            PLANTLAB
          </Link>
          <h1>Dashboard</h1>
        </div>
        <nav className="nav">
          <NavLink to="/devices" className="nav-link">
            Devices
          </NavLink>
          <NavLink to="/settings" className="nav-link">
            Settings
          </NavLink>
          <NavLink to="/support/diagnostics" className="nav-link">
            Support
          </NavLink>
          {isAdmin ? (
            <NavLink to="/admin/diagnostics" className="nav-link">
              Admin
            </NavLink>
          ) : null}
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
