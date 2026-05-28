import { Link } from "react-router-dom";

import appIcon from "@/assets/app-icon-512.png";
import { useSession } from "@/hooks/useSession";

const proofPoints = ["Camera timeline", "Smart monitoring", "OTA updates", "Mobile + web", "Device health"];

const featureCards = [
  {
    label: "Monitor",
    title: "Know the growing environment.",
    body: "Track temperature, humidity, water state, and device runtime in one calm view.",
  },
  {
    label: "Capture",
    title: "See slow growth clearly.",
    body: "Review plant images and build a visual growth history without manual photo tracking.",
  },
  {
    label: "Track",
    title: "Understand what changed.",
    body: "Readable activity and device health states help explain warnings, updates, and camera events.",
  },
  {
    label: "Control",
    title: "Adjust simple device actions.",
    body: "Use web or mobile controls for supported actions like grow-light state and image capture.",
  },
];

const reliabilityItems = [
  "Device health monitoring",
  "Diagnostics timeline",
  "OTA update readiness",
  "Camera and Wi-Fi visibility",
];

const useCases = [
  {
    title: "Plant hobbyists",
    body: "Watch growth, environment changes, and recent captures without building a spreadsheet.",
  },
  {
    title: "Smart home users",
    body: "Keep an indoor planter visible from the same kind of calm product surface as other connected devices.",
  },
  {
    title: "STEM education",
    body: "Demonstrate sensors, firmware, cloud services, and product UX through one tangible system.",
  },
  {
    title: "Makers",
    body: "Use PlantLab as a practical connected-device platform with OTA and diagnostics already designed in.",
  },
];

export function LandingScreen() {
  const { token } = useSession();
  const dashboardHref = token ? "/devices" : "/login";
  const dashboardLabel = token ? "Dashboard" : "Sign in";

  return (
    <div className="landing-page">
      <header className="landing-nav" aria-label="PlantLab">
        <Link className="landing-brand" to="/">
          <img src={appIcon} alt="" />
          <span>PlantLab</span>
        </Link>
        <nav className="landing-nav-links" aria-label="Landing navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#use-cases">Use cases</a>
          <Link className="landing-signin-link" to={dashboardHref}>
            {dashboardLabel}
          </Link>
        </nav>
      </header>

      <main>
        <section className="landing-hero" aria-labelledby="landing-hero-title">
          <div className="landing-copy">
            <div className="eyebrow">PlantLab by Mars Potato Lab</div>
            <h1 id="landing-hero-title">Grow smarter. See every change.</h1>
            <p className="landing-lede">
              PlantLab is a smart indoor plant monitoring system that combines sensors, camera history, grow-light control,
              and device health visibility across mobile and web.
            </p>
            <div className="button-row">
              <a className="primary-button" href="#product-showcase">
                View live demo
              </a>
              <Link className="secondary-button" to={dashboardHref}>
                {dashboardLabel}
              </Link>
            </div>
          </div>

          <ProductPreview />
        </section>

        <section className="landing-proof-strip" aria-label="PlantLab proof points">
          {proofPoints.map((point) => (
            <span key={point}>{point}</span>
          ))}
        </section>

        <section className="landing-section landing-two-column" aria-labelledby="problem-title">
          <div className="section-heading">
            <div className="eyebrow">The problem</div>
            <h2 id="problem-title">Plant changes happen slowly. Device issues happen quietly.</h2>
          </div>
          <div className="landing-copy-stack">
            <p>
              Indoor growing setups can hide the information people need most. Gradual plant changes are easy to miss,
              camera history is often manual, and device warnings can stay invisible until something already feels wrong.
            </p>
            <p>
              PlantLab gives plant owners, educators, and makers a clearer way to understand both the plant and the
              connected device supporting it.
            </p>
          </div>
        </section>

        <section id="product-showcase" className="landing-section" aria-labelledby="showcase-title">
          <div className="section-heading landing-section-centered">
            <div className="eyebrow">The solution</div>
            <h2 id="showcase-title">One calm view for plant state, images, controls, and device health.</h2>
            <p>
              PlantLab turns an indoor planter into a visible, updateable smart device without making the experience feel
              like a hardware console.
            </p>
          </div>
          <div className="landing-feature-grid landing-feature-grid-four">
            {featureCards.map((feature) => (
              <article className="landing-feature-card" key={feature.label}>
                <span>{feature.label}</span>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="how-it-works" className="landing-band" aria-labelledby="how-title">
          <div>
            <div className="eyebrow">How it works</div>
            <h2 id="how-title">Pair once. Watch continuously. Understand changes over time.</h2>
          </div>
          <div className="landing-steps">
            <StepItem number="1" title="Connect PlantLab" body="Use the mobile app to provision and link the device." />
            <StepItem number="2" title="Watch your plant grow" body="Camera captures and readings build a history automatically." />
            <StepItem number="3" title="Understand what changed" body="Health states, updates, and events stay readable from web or mobile." />
          </div>
        </section>

        <section className="landing-section landing-two-column landing-growth-section" aria-labelledby="growth-title">
          <div className="landing-camera-preview" aria-label="PlantLab camera history preview">
            <div className="landing-camera-main">
              <span>Latest capture</span>
              <strong>Monstera cutting</strong>
              <small>Today, 2:20 PM</small>
            </div>
            <div className="landing-camera-strip" aria-label="Recent capture timeline">
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
          </div>
          <div className="section-heading">
            <div className="eyebrow">Growth history</div>
            <h2 id="growth-title">A visual record of what is usually too slow to notice.</h2>
            <p>
              PlantLab's camera history and growth timelapse make it easier to compare days, weeks, and small changes
              without taking manual photos.
            </p>
          </div>
        </section>

        <section className="landing-section landing-two-column" aria-labelledby="reliability-title">
          <div className="section-heading">
            <div className="eyebrow">Diagnostics and reliability</div>
            <h2 id="reliability-title">Know when your device is healthy, connected, and up to date.</h2>
            <p>
              PlantLab keeps reliability visible with device health, OTA update status, and a readable activity timeline
              when something needs attention.
            </p>
          </div>
          <div className="landing-reliability-list">
            {reliabilityItems.map((item) => (
              <div key={item}>
                <span />
                <strong>{item}</strong>
              </div>
            ))}
          </div>
        </section>

        <section id="use-cases" className="landing-section" aria-labelledby="use-cases-title">
          <div className="section-heading landing-section-centered">
            <div className="eyebrow">Use cases</div>
            <h2 id="use-cases-title">Built for curious growers and practical connected-device work.</h2>
          </div>
          <div className="landing-feature-grid landing-feature-grid-four">
            {useCases.map((useCase) => (
              <article className="landing-feature-card" key={useCase.title}>
                <h3>{useCase.title}</h3>
                <p>{useCase.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section landing-final" aria-labelledby="final-title">
          <div>
            <div className="eyebrow">Ready to look closer?</div>
            <h2 id="final-title">See PlantLab as a product, not a prototype.</h2>
            <p>Start with the product preview now, or sign in to manage your own PlantLab device.</p>
          </div>
          <div className="button-row">
            <a className="primary-button" href="#product-showcase">
              View live demo
            </a>
            <Link className="secondary-button" to={dashboardHref}>
              {dashboardLabel}
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}

function ProductPreview() {
  return (
    <div className="landing-product" aria-label="PlantLab product preview">
      <div className="landing-product-topline">
        <img src={appIcon} alt="PlantLab app icon" />
        <div>
          <span>Demo PlantLab</span>
          <strong>Healthy</strong>
        </div>
      </div>
      <div className="landing-product-photo">
        <span>Latest capture</span>
        <strong>New leaf visible</strong>
      </div>
      <div className="landing-product-panel">
        <div>
          <span>Air</span>
          <strong>26.4 C</strong>
        </div>
        <div>
          <span>Humidity</span>
          <strong>41%</strong>
        </div>
        <div>
          <span>Light</span>
          <strong>65%</strong>
        </div>
      </div>
      <div className="landing-product-timeline">
        <span>Camera connected</span>
        <span>OTA ready</span>
        <span>Image captured</span>
      </div>
    </div>
  );
}

function StepItem({ number, title, body }: { number: string; title: string; body: string }) {
  return (
    <article className="landing-step">
      <span>{number}</span>
      <div>
        <h3>{title}</h3>
        <p>{body}</p>
      </div>
    </article>
  );
}
