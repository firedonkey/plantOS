import { Link } from "react-router-dom";

import appIcon from "@/assets/app-icon-512.png";
import { useSession } from "@/hooks/useSession";

const landingGrowthFrameModules = import.meta.glob<string>("../assets/demo/growth/*.jpg", {
  eager: true,
  import: "default",
});

const landingGrowthFrameUrls = Object.entries(landingGrowthFrameModules)
  .sort(([left], [right]) => left.localeCompare(right))
  .map(([, src]) => src);

const landingGrowthStart = landingGrowthFrameUrls[0] ?? "";
const landingGrowthMiddle = landingGrowthFrameUrls[Math.floor(landingGrowthFrameUrls.length / 2)] ?? landingGrowthStart;
const landingGrowthLatest = landingGrowthFrameUrls[landingGrowthFrameUrls.length - 1] ?? landingGrowthStart;
const landingCaptureStripFrames = [landingGrowthStart, landingGrowthMiddle, landingGrowthLatest].filter(Boolean);
const landingTimelineFrames = selectLandingTimelineFrames(landingGrowthFrameUrls, 6);

const proofPoints = [
  { label: "Camera timeline", detail: "Growth history" },
  { label: "Smart monitoring", detail: "Live plant state" },
  { label: "Device health", detail: "Readable reliability" },
];

type CapabilityVisual = "monitor" | "capture" | "track" | "control";

const featureCards: Array<{
  label: string;
  title: string;
  body: string;
  metric: string;
  state: string;
  visual: CapabilityVisual;
}> = [
  {
    label: "Monitor",
    title: "Know the growing environment.",
    body: "Track temperature, humidity, water state, and device runtime in one calm view.",
    metric: "26.4 C",
    state: "Stable air temp",
    visual: "monitor",
  },
  {
    label: "Capture",
    title: "See slow growth clearly.",
    body: "Review plant images and build a visual growth history without manual photo tracking.",
    metric: "12 captures",
    state: "Latest image today",
    visual: "capture",
  },
  {
    label: "Track",
    title: "Understand what changed.",
    body: "Readable activity and device health states help explain warnings, updates, and camera events.",
    metric: "3 events",
    state: "Camera recovered",
    visual: "track",
  },
  {
    label: "Control",
    title: "Adjust simple device actions.",
    body: "Use web or mobile controls for supported actions like grow-light state and image capture.",
    metric: "65%",
    state: "Grow light on",
    visual: "control",
  },
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
  const previewLabel = "View live demo";

  return (
    <div className="landing-page">
      <header className="landing-nav" aria-label="PlantLab">
        <Link className="landing-brand" to="/">
          <img src={appIcon} alt="" />
          <span>PlantLab</span>
        </Link>
        <nav className="landing-nav-links" aria-label="Landing navigation">
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
              <Link className="primary-button" to="/demo">
                {previewLabel}
              </Link>
              <Link className="secondary-button" to={dashboardHref}>
                {dashboardLabel}
              </Link>
            </div>
          </div>

          <ProductPreview />
        </section>

        <section className="landing-proof-strip" aria-label="PlantLab proof points">
          {proofPoints.map((point) => (
            <span key={point.label}>
              <strong>{point.label}</strong>
              <small>{point.detail}</small>
            </span>
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
          <div className="landing-capability-grid">
            {featureCards.map((feature) => (
              <article className="landing-capability-card" key={feature.label}>
                <CapabilityPreview
                  visual={feature.visual}
                  metric={feature.metric}
                  state={feature.state}
                />
                <div>
                  <span>{feature.label}</span>
                  <h3>{feature.title}</h3>
                  <p>{feature.body}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="landing-section landing-two-column landing-growth-section" aria-labelledby="growth-title">
          <GrowthShowcase />
          <div className="section-heading">
            <div className="eyebrow">Growth history</div>
            <h2 id="growth-title">A visual record of what is usually too slow to notice.</h2>
            <p>
              PlantLab's camera history and growth timelapse make it easier to compare days, weeks, and small changes
              without taking manual photos.
            </p>
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
            <p>Start with the public demo now, or sign in to manage your own PlantLab device.</p>
          </div>
          <div className="button-row">
            <Link className="primary-button" to="/demo">
              {previewLabel}
            </Link>
            <Link className="secondary-button" to={dashboardHref}>
              {dashboardLabel}
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}

function CapabilityPreview({ visual, metric, state }: { visual: CapabilityVisual; metric: string; state: string }) {
  return (
    <div className={`landing-capability-preview landing-capability-preview-${visual}`} aria-hidden="true">
      <div className="landing-capability-visual">
        {visual === "monitor" ? (
          <>
            <span />
            <span />
            <span />
          </>
        ) : null}
        {visual === "capture" ? (
          <div className="landing-mini-camera-strip">
            {landingCaptureStripFrames.map((src, index) => (
              <span key={src}>
                <img src={src} alt="" loading={index === landingCaptureStripFrames.length - 1 ? "eager" : "lazy"} />
              </span>
            ))}
          </div>
        ) : null}
        {visual === "track" ? (
          <div className="landing-mini-events">
            <span />
            <span />
            <span />
          </div>
        ) : null}
        {visual === "control" ? (
          <div className="landing-mini-slider">
            <span />
          </div>
        ) : null}
      </div>
      <div className="landing-capability-metric">
        <strong>{metric}</strong>
        <span>{state}</span>
      </div>
    </div>
  );
}

function GrowthShowcase() {
  return (
    <div className="landing-growth-showcase" aria-label="PlantLab growth history preview">
      <div className="landing-growth-before-after">
        <div>
          <img src={landingGrowthStart} alt="Early PlantLab demo capture showing a young basil plant." loading="lazy" />
          <span>Day 1</span>
        </div>
        <div>
          <img src={landingGrowthLatest} alt="Latest PlantLab demo capture showing mature basil leaves." loading="lazy" />
          <span>Day 7</span>
        </div>
      </div>
      <div className="landing-growth-timeline" aria-label="Camera capture progression">
        {landingTimelineFrames.map((src) => (
          <span key={src}>
            <img src={src} alt="" loading="lazy" />
          </span>
        ))}
      </div>
      <div className="landing-growth-caption">
        <strong>30s growth story</strong>
        <span>Camera captures become a fixed-length timelapse.</span>
      </div>
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
        <img src={landingGrowthLatest} alt="Latest PlantLab demo capture showing basil leaves." />
        <div>
          <span>Latest capture</span>
          <strong>New leaf visible</strong>
        </div>
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

function selectLandingTimelineFrames(frames: string[], count: number) {
  if (frames.length <= count) {
    return frames;
  }

  const lastIndex = frames.length - 1;
  return Array.from({ length: count }, (_, index) => {
    const frameIndex = Math.round((index / Math.max(count - 1, 1)) * lastIndex);
    return frames[frameIndex];
  }).filter((src): src is string => Boolean(src));
}
