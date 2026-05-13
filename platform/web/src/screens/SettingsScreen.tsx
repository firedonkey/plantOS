import { getApiBaseUrl } from "@/api/config";
import { useSession } from "@/hooks/useSession";

export function SettingsScreen() {
  const { authMode, session, signOut } = useSession();

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
        <p className="subtitle">{session?.mode ?? "Signed out"} ({authMode})</p>
      </div>

      <div className="card">
        <h3>Notes</h3>
        <p className="subtitle">Production standalone auth uses backend Google sign-in, an HTTP-only refresh cookie, and an in-memory access token. Dev bearer auth is shown only in explicit dev mode.</p>
      </div>

      <div className="card">
        <h3>Device settings</h3>
        <p className="subtitle">Operational device details such as labels, masked token summaries, hardware identifiers, and provisioning status now live on each device dashboard.</p>
      </div>

      <button className="primary-button" onClick={() => void signOut()}>
        Log out
      </button>
    </section>
  );
}
