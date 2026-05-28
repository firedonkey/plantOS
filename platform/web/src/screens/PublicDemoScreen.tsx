import { useEffect } from "react";
import { Link } from "react-router-dom";

import appIcon from "@/assets/app-icon-512.png";
import roseSeedling from "@/assets/demo/rose-01-seedling.jpg";
import roseLeaves from "@/assets/demo/rose-02-young-leaves.jpg";
import roseBud from "@/assets/demo/rose-03-bud.jpg";
import roseBloom from "@/assets/demo/rose-04-bloom.jpg";
import roseCloseup from "@/assets/demo/rose-05-bloom.jpg";
import { useSession } from "@/hooks/useSession";

const demoGrowthImages = [
  {
    src: roseSeedling,
    label: "Day 1",
    capturedAt: "May 1, 8:12 AM",
    note: "New rose seedling settled into the planter.",
    alt: "Young rose seedling in soil inside a planter.",
  },
  {
    src: roseLeaves,
    label: "Day 3",
    capturedAt: "May 3, 8:10 AM",
    note: "Leaf surface and moisture visibility improved.",
    alt: "Close view of rose plant leaves with dew.",
  },
  {
    src: roseBud,
    label: "Day 7",
    capturedAt: "May 7, 8:09 AM",
    note: "Bud formation became visible in the camera history.",
    alt: "Rose bud beginning to open.",
  },
  {
    src: roseBloom,
    label: "Day 14",
    capturedAt: "May 14, 8:11 AM",
    note: "Bloom opened while device health stayed stable.",
    alt: "Red rose bloom in outdoor light.",
  },
  {
    src: roseCloseup,
    label: "Today",
    capturedAt: "May 28, 2:20 PM",
    note: "Latest close-up capture is ready for the growth timeline.",
    alt: "Close-up image of a fully opened red rose.",
  },
];

const latestCapture = demoGrowthImages[demoGrowthImages.length - 1];

const overviewStats = [
  { label: "Device health", value: "Healthy", detail: "Main controller online" },
  { label: "Wi-Fi", value: "-61 dBm", detail: "Signal stable" },
  { label: "Camera node", value: "Connected", detail: "Latest capture just now" },
  { label: "Grow light", value: "65%", detail: "Scheduled evening support" },
];

const sensorReadings = [
  { label: "Air temp", value: "24.8 C" },
  { label: "Humidity", value: "43%" },
  { label: "Water state", value: "Ready" },
];

const demoEvents = [
  {
    tone: "online",
    time: "Just now",
    title: "Image captured",
    body: "The camera node saved a new rose close-up for the growth timeline.",
  },
  {
    tone: "online",
    time: "2m ago",
    title: "Heartbeat received",
    body: "Device health, Wi-Fi, light state, and runtime state were updated.",
  },
  {
    tone: "warning",
    time: "18m ago",
    title: "Wi-Fi recovered",
    body: "Signal returned to a stable range after a brief dip.",
  },
  {
    tone: "online",
    time: "1h ago",
    title: "Firmware up to date",
    body: "PlantLab is running the current stable release.",
  },
];

const featureNotes = [
  {
    title: "Camera history",
    body: "Capture slow changes automatically and compare growth over time.",
  },
  {
    title: "Health visibility",
    body: "Know whether the planter, camera, Wi-Fi, and firmware are behaving normally.",
  },
  {
    title: "Lighting control",
    body: "Adjust supported lighting actions from a calm product interface.",
  },
  {
    title: "Remote monitoring",
    body: "Check plant state from web or mobile without opening a debug dashboard.",
  },
];

export function PublicDemoScreen() {
  const { token } = useSession();
  const dashboardHref = token ? "/devices" : "/login";
  const dashboardLabel = token ? "Dashboard" : "Sign in";

  useEffect(() => {
    const previousTitle = document.title;
    const description = "Explore a public PlantLab demo with sample plant images, growth history, device health, and activity timeline.";
    document.title = "PlantLab Demo - Growth History and Device Health";
    const restoreMeta = setMeta("description", description);
    const restoreOgTitle = setMeta("og:title", "PlantLab Demo - Growth History and Device Health", "property");
    const restoreOgDescription = setMeta("og:description", description, "property");

    return () => {
      document.title = previousTitle;
      restoreMeta();
      restoreOgTitle();
      restoreOgDescription();
    };
  }, []);

  return (
    <div className="demo-page">
      <header className="landing-nav demo-nav" aria-label="PlantLab demo">
        <Link className="landing-brand" to="/">
          <img src={appIcon} alt="" />
          <span>PlantLab</span>
        </Link>
        <nav className="landing-nav-links" aria-label="Demo navigation">
          <Link to="/">Home</Link>
          <Link className="landing-signin-link" to={dashboardHref}>
            {dashboardLabel}
          </Link>
        </nav>
      </header>

      <main>
        <section className="demo-hero" aria-labelledby="demo-title">
          <div className="demo-hero-copy">
            <div className="eyebrow">Public sample data</div>
            <h1 id="demo-title">Live PlantLab demo</h1>
            <p>
              Explore a sample PlantLab device with realistic plant imagery, growth history, lighting state, camera
              status, and readable device activity. No sign-in or hardware is required.
            </p>
            <div className="button-row">
              <a className="primary-button" href="#demo-growth">
                View growth timeline
              </a>
              <Link className="secondary-button" to={dashboardHref}>
                {dashboardLabel}
              </Link>
            </div>
          </div>

          <article className="demo-live-card" aria-label="Demo PlantLab current status">
            <div className="demo-live-photo">
              <img src={latestCapture.src} alt={latestCapture.alt} />
            </div>
            <span className="chip chip-online">Healthy</span>
            <h2>Mars Rose Lab</h2>
            <p>Demo rose planter - Local sample device</p>
            <div className="demo-live-grid">
              <div>
                <span>Last capture</span>
                <strong>Just now</strong>
              </div>
              <div>
                <span>Light</span>
                <strong>65%</strong>
              </div>
              <div>
                <span>Wi-Fi</span>
                <strong>-61 dBm</strong>
              </div>
            </div>
          </article>
        </section>

        <section className="demo-section demo-overview-grid" aria-labelledby="demo-overview-title">
          <div className="section-heading">
            <div className="eyebrow">Device overview</div>
            <h2 id="demo-overview-title">A calm snapshot of the plant and the device.</h2>
            <p>
              The demo mirrors the kind of information PlantLab keeps visible: whether the plant was captured, whether
              the device is healthy, and whether the supporting hardware is online.
            </p>
          </div>
          <div className="demo-stat-grid" aria-label="Demo device state">
            {overviewStats.map((item) => (
              <article className="demo-stat-card" key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value}</strong>
                <small>{item.detail}</small>
              </article>
            ))}
          </div>
        </section>

        <section className="demo-section demo-capture-layout" aria-labelledby="demo-capture-title">
          <div className="demo-capture-image">
            <img src={latestCapture.src} alt={latestCapture.alt} />
            <div>
              <strong>{latestCapture.label}</strong>
              <span>{latestCapture.capturedAt}</span>
            </div>
          </div>
          <div className="demo-capture-copy">
            <div className="eyebrow">Latest capture</div>
            <h2 id="demo-capture-title">A realistic image becomes part of the plant history.</h2>
            <p>{latestCapture.note}</p>
            <div className="demo-sensor-row" aria-label="Sample sensor readings">
              {sensorReadings.map((reading) => (
                <div key={reading.label}>
                  <span>{reading.label}</span>
                  <strong>{reading.value}</strong>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="demo-growth" className="demo-section" aria-labelledby="demo-growth-title">
          <div className="section-heading landing-section-centered">
            <div className="eyebrow">Growth timeline</div>
            <h2 id="demo-growth-title">PlantLab makes slow changes visible.</h2>
            <p>
              These local demo images show how a sequence of captures can become a clear growth story without manual
              photo tracking.
            </p>
          </div>
          <div className="demo-growth-grid">
            {demoGrowthImages.map((image) => (
              <article className="demo-growth-card" key={image.label}>
                <img src={image.src} alt={image.alt} />
                <div>
                  <strong>{image.label}</strong>
                  <span>{image.capturedAt}</span>
                  <p>{image.note}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="demo-section demo-two-column" aria-labelledby="demo-activity-title">
          <div>
            <div className="section-heading">
              <div className="eyebrow">Recent activity</div>
              <h2 id="demo-activity-title">Readable events explain what happened.</h2>
              <p>
                PlantLab keeps diagnostics understandable by turning device activity into concise, ordered summaries.
              </p>
            </div>
            <div className="demo-timeline" aria-label="Sample PlantLab activity timeline">
              {demoEvents.map((event) => (
                <article className="demo-event" key={`${event.title}-${event.time}`}>
                  <span className={`demo-event-dot demo-event-dot-${event.tone}`} />
                  <div>
                    <small>{event.time}</small>
                    <strong>{event.title}</strong>
                    <p>{event.body}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="demo-feature-stack" aria-label="PlantLab demo feature explanation">
            {featureNotes.map((feature) => (
              <article key={feature.title}>
                <h3>{feature.title}</h3>
                <p>{feature.body}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function setMeta(name: string, content: string, attribute: "name" | "property" = "name") {
  const selector = `meta[${attribute}="${name}"]`;
  let element = document.querySelector<HTMLMetaElement>(selector);
  const created = !element;
  const previousContent = element?.getAttribute("content") ?? null;

  if (!element) {
    element = document.createElement("meta");
    element.setAttribute(attribute, name);
    document.head.appendChild(element);
  }

  element.setAttribute("content", content);

  return () => {
    if (!element) {
      return;
    }
    if (created) {
      element.remove();
      return;
    }
    if (previousContent === null) {
      element.removeAttribute("content");
    } else {
      element.setAttribute("content", previousContent);
    }
  };
}
