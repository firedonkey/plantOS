import { Link, Navigate } from "react-router-dom";

import { useSession } from "@/hooks/useSession";

export function LandingScreen() {
  const { token } = useSession();

  if (token) {
    return <Navigate to="/devices" replace />;
  }

  return (
    <div className="landing-page">
      <section className="landing-hero">
        <div className="landing-copy">
          <div className="eyebrow">PLANTLAB</div>
          <h1>Grow with a calmer control room.</h1>
          <p className="landing-lede">
            PlantLab keeps your sensors, photos, and device controls in one place so you can check plant health quickly and act with confidence.
          </p>
          <div className="button-row">
            <Link className="primary-button" to="/login">
              Get started
            </Link>
            <a className="secondary-button" href="http://localhost:8000/login">
              Open legacy web
            </a>
          </div>
          <p className="meta-text">
            The standalone web app currently uses dev-only local auth. Production auth migration is documented before we retire the old Google sign-in flow.
          </p>
        </div>

        <div className="landing-panel">
          <div className="landing-card">
            <span className="chip chip-online">Live status</span>
            <h2>See readings, recent images, and controls together.</h2>
            <p className="subtitle">
              Devices list and dashboard now run through the shared backend API, with onboarding and setup-finishing in the standalone flow too.
            </p>
          </div>
          <div className="landing-metrics">
            <div className="metric-card">
              <span>Devices</span>
              <strong>Web + mobile</strong>
            </div>
            <div className="metric-card">
              <span>Onboarding</span>
              <strong>Standalone flow</strong>
            </div>
            <div className="metric-card">
              <span>Auth</span>
              <strong>Prod plan documented</strong>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
