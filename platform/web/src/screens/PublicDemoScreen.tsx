import { useEffect } from "react";
import { Link } from "react-router-dom";

import appIcon from "@/assets/app-icon-512.png";
import { useSession } from "@/hooks/useSession";

const demoGrowthFrameModules = import.meta.glob<string>("../assets/demo/growth/*.jpg", {
  eager: true,
  import: "default",
});

const demoGrowthFrameUrls = Object.entries(demoGrowthFrameModules)
  .sort(([left], [right]) => left.localeCompare(right))
  .map(([, src]) => src);

const demoGrowthImages = demoGrowthFrameUrls.map((src, index) => {
  const totalFrames = demoGrowthFrameUrls.length;
  const finalIndex = Math.max(totalFrames - 1, 1);
  const progress = index / finalIndex;
  const day = Math.round(progress * 20) + 1;
  const label = index === totalFrames - 1 ? "Today" : `Day ${day}`;
  const captureTime = index === totalFrames - 1 ? "Today, 9:15 AM" : `May ${String(day).padStart(2, "0")}, 9:15 AM`;
  const note = getGrowthObservation(progress, index === totalFrames - 1);

  return {
    src,
    label,
    capturedAt: `${captureTime} · Capture ${index + 1}/${totalFrames}`,
    note,
    alt: `Overhead PlantLab demo growth capture, frame ${index + 1} of ${totalFrames}.`,
  };
});

const latestCapture = demoGrowthImages[demoGrowthImages.length - 1];

const overviewStats = [
  { label: "Device health", value: "Healthy", detail: "Main controller online" },
  { label: "Wi-Fi", value: "-58 dBm", detail: "Signal stable" },
  { label: "Camera node", value: "Connected", detail: "Latest capture today" },
  { label: "Capture interval", value: "4 hours", detail: "Daylight schedule" },
  { label: "Grow light", value: "68%", detail: "Evening support active" },
];

const sensorReadings = [
  { label: "Air temp", value: "23.9 C" },
  { label: "Humidity", value: "46%" },
  { label: "Water state", value: "Stable" },
];

const demoEvents = [
  {
    tone: "online",
    time: "9:15 AM",
    title: "Growth image uploaded",
    body: "A new overhead capture was added to the plant history.",
  },
  {
    tone: "online",
    time: "9:12 AM",
    title: "Device check-in healthy",
    body: "PlantLab reported stable Wi-Fi, camera, and light state.",
  },
  {
    tone: "online",
    time: "8:00 AM",
    title: "Lighting schedule updated",
    body: "Grow light support adjusted to 68% for the morning cycle.",
  },
  {
    tone: "warning",
    time: "Yesterday",
    title: "Wi-Fi recovered",
    body: "Signal returned to a stable range after a short drop.",
  },
  {
    tone: "online",
    time: "2 days ago",
    title: "Software up to date",
    body: "The device is running the current stable release.",
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
            <p className="demo-sample-note">Demo uses sample PlantLab data for illustration.</p>
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
            <h2>Mars Basil Lab</h2>
            <p>Demo basil planter - Local sample device</p>
            <div className="demo-live-grid">
              <div>
                <span>Last capture</span>
                <strong>Today 9:15</strong>
              </div>
              <div>
                <span>Light</span>
                <strong>68%</strong>
              </div>
              <div>
                <span>Wi-Fi</span>
                <strong>-58 dBm</strong>
              </div>
            </div>
          </article>
        </section>

        <section className="demo-section demo-overview-grid" aria-labelledby="demo-overview-title">
          <div className="section-heading">
            <div className="eyebrow">Device overview</div>
            <h2 id="demo-overview-title">A calm snapshot of the plant and the device.</h2>
            <p>
              The demo mirrors the information PlantLab keeps visible: whether the plant was captured, whether the
              device is healthy, and whether the supporting hardware is online.
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
              These sample captures show the same plant from a consistent overhead angle, making slow growth easier to
              compare at a glance.
            </p>
          </div>
          <div className="demo-growth-grid">
            {demoGrowthImages.map((image) => (
              <article className="demo-growth-card" key={`${image.label}-${image.capturedAt}`}>
                <img src={image.src} alt={image.alt} loading="lazy" />
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

function getGrowthObservation(progress: number, isLatest: boolean) {
  if (isLatest) {
    return "Canopy fills more of the view, with broader leaves visible near the center.";
  }
  if (progress < 0.18) {
    return "First new leaves are visible under the camera.";
  }
  if (progress < 0.42) {
    return "Leaf area expands as the plant settles into the light cycle.";
  }
  if (progress < 0.68) {
    return "Growth accelerates and the canopy begins to fill the planter.";
  }
  return "New leaves widen and overlap, making the progression easy to see.";
}
