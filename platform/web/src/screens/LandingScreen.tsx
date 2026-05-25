import { Link } from "react-router-dom";

import appIcon from "@/assets/app-icon-512.png";
import { useSession } from "@/hooks/useSession";

export function LandingScreen() {
  const { token } = useSession();
  const dashboardHref = token ? "/devices" : "/login";
  const dashboardLabel = token ? "Open dashboard" : "Sign in";

  return (
    <div className="landing-page">
      <header className="landing-nav" aria-label="PlantLab">
        <Link className="landing-brand" to="/">
          <img src={appIcon} alt="" />
          <span>PlantLab</span>
        </Link>
        <Link className="landing-signin-link" to={dashboardHref}>
          {dashboardLabel}
        </Link>
      </header>

      <section className="landing-hero">
        <div className="landing-copy">
          <div className="eyebrow">SMART GROWING AT HOME</div>
          <h1>A calmer way to care for your plants.</h1>
          <p className="landing-lede">
            PlantLab brings your planter readings, grow light, water temperature, and camera updates into one simple dashboard.
          </p>
          <div className="button-row">
            <Link className="primary-button" to={dashboardHref}>
              {dashboardLabel}
            </Link>
            <a className="secondary-button" href="#how-it-works">
              See how it works
            </a>
          </div>
        </div>

        <div className="landing-product" aria-label="PlantLab product preview">
          <div className="landing-product-glow" />
          <img className="landing-product-icon" src={appIcon} alt="PlantLab planter icon" />
          <div className="landing-product-panel">
            <div>
              <span>Air</span>
              <strong>26.4 C</strong>
            </div>
            <div>
              <span>Humidity</span>
              <strong>38%</strong>
            </div>
            <div>
              <span>Water</span>
              <strong>25.0 C</strong>
            </div>
          </div>
        </div>
      </section>

      <section id="how-it-works" className="landing-section" aria-labelledby="how-title">
        <div className="section-heading">
          <div className="eyebrow">HOW PLANTLAB HELPS</div>
          <h2 id="how-title">Understand the planter without digging through logs.</h2>
        </div>
        <div className="landing-feature-grid">
          <article className="landing-feature-card">
            <span className="feature-marker feature-marker-green" />
            <h3>Live readings</h3>
            <p>Track air temperature, humidity, and water temperature from the same place.</p>
          </article>
          <article className="landing-feature-card">
            <span className="feature-marker feature-marker-copper" />
            <h3>Plant photos</h3>
            <p>Review recent camera captures to see growth and spot problems earlier.</p>
          </article>
          <article className="landing-feature-card">
            <span className="feature-marker feature-marker-blue" />
            <h3>Remote control</h3>
            <p>Adjust grow light brightness and keep device status visible while you are away.</p>
          </article>
        </div>
      </section>

      <section className="landing-band" aria-label="PlantLab setup">
        <div>
          <div className="eyebrow">SETUP</div>
          <h2>Pair with the mobile app. Monitor from the web.</h2>
        </div>
        <p>
          Add your device from the PlantLab mobile app, then use this website to check status, readings, images, and device health on a larger screen.
        </p>
      </section>

      <section className="landing-section landing-final" aria-labelledby="final-title">
        <div>
          <div className="eyebrow">READY WHEN YOU ARE</div>
          <h2 id="final-title">Open your PlantLab dashboard.</h2>
          <p>Sign in to see your devices and continue caring for your plants.</p>
        </div>
        <Link className="primary-button" to={dashboardHref}>
          {token ? "Open dashboard" : "Sign in with Google"}
        </Link>
      </section>
    </div>
  );
}
