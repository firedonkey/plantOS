import { getApiBaseUrl } from "@/api/config";
import { useSession } from "@/hooks/useSession";

export function SettingsScreen() {
  const { session, signOut } = useSession();

  return (
    <section className="page-section">
      <div className="page-header">
        <div>
          <div className="eyebrow">SETTINGS</div>
          <h2>App settings</h2>
        </div>
      </div>

      <div className="card">
        <h3>API URL</h3>
        <p className="subtitle">{getApiBaseUrl() || "Not configured"}</p>
      </div>

      <div className="card">
        <h3>Session mode</h3>
        <p className="subtitle">{session?.mode ?? "Signed out"}</p>
      </div>

      <div className="card">
        <h3>Notes</h3>
        <p className="subtitle">TODO: replace dev-only placeholder login before standalone web replaces backend-rendered auth.</p>
      </div>

      <button className="primary-button" onClick={signOut}>
        Log out
      </button>
    </section>
  );
}
