# PlantLab Marketing Landing Plan

## Purpose

This document defines the strategy for turning the public PlantLab website from
a prototype/project page into a polished product landing site for Mars Potato
Lab.

This is a planning artifact only. It does not include UI implementation.

## Scope Reviewed

Current public website:

- Web landing route: `platform/web/src/screens/LandingScreen.tsx`
- Landing styles: `platform/web/src/styles/app.css`
- Existing design direction: `docs/design/ux_ui_redesign_plan.md`
- Existing visual token system: `docs/design/design_system_tokens.md`

Current product capabilities considered:

- Plant/device monitoring
- Camera image history
- Growth timelapse
- Diagnostics timeline
- OTA updates
- Device command system
- Mobile app and web dashboard
- Simulator-generated demo data
- Contract-first backend/device protocol

Target audiences:

- Plant hobbyists
- Smart home users
- Educators and STEM users
- Early adopters
- Potential investors and collaborators

## Current Website Audit

### What Works

- The page is calm, visually simple, and aligned with PlantLab's current
  matte-white and green-accent direction.
- The headline is approachable: "A calmer way to care for your plants."
- The page correctly keeps `/` as a real landing page for signed-in and
  signed-out users.
- The page explains the current product boundary: device setup happens in the
  mobile app and monitoring can happen on the web.
- The product preview already hints at readings and live device state.

### Main Gaps

#### 1. Product Category Is Not Clear Enough

The current page says PlantLab is a calmer way to care for plants, but it does
not immediately say what PlantLab is.

The first screen should answer:

- Is this hardware, software, or both?
- Is it for indoor plants?
- Does it monitor, automate, photograph, or diagnose?
- What does Mars Potato Lab make here?

Recommended fix:

- Make the hero subheadline explicitly describe PlantLab as a smart indoor
  planter monitoring system with app, camera, and device health visibility.

#### 2. Hero Section Is Too Close To An App Login Page

The current primary CTA is "Sign in" or "Open dashboard". That is useful for
existing users, but weak for first-time visitors.

Recommended fix:

- Keep "Sign in" in the nav.
- Make the hero CTA product-oriented:
  - "View live demo"
  - "Join early access"
  - "See how PlantLab works"
- Existing users can still access the dashboard from a secondary nav/action.

#### 3. Feature Messaging Is Correct But Too Functional

Current feature cards:

- Live readings
- Plant photos
- Remote control

These are accurate, but they read like a feature checklist. They do not explain
the emotional/product outcome:

- Confidence that the plant and device are okay
- A visual record of growth
- Fewer mystery failures
- Better trust in connected hardware

Recommended fix:

- Reframe features around outcomes first, technical capability second.

#### 4. Missing Trust Signals

The current page does not show why a visitor should believe the product is real
or reliable.

Trust signals PlantLab can honestly use now:

- Mobile app plus web dashboard
- Real camera captures and image history
- OTA update path
- Diagnostics timeline
- Simulator-powered demo data
- Contract-first backend/device protocol
- Built by Mars Potato Lab

Avoid:

- Claims like "fully autonomous plant care"
- AI insight claims before an AI pipeline is real
- Enterprise reliability claims before long-running production evidence exists

#### 5. Missing Product Story

The landing page does not yet explain the flow:

1. Add the device from mobile.
2. PlantLab monitors readings and camera captures.
3. Web/mobile show health, trends, and images.
4. Diagnostics and OTA keep the device supportable.

Recommended fix:

- Add a short "How it works" section with three to four visual steps.

#### 6. Weak Visual Proof

The current product preview is an icon plus three readings. It does not show
the most differentiating parts of PlantLab:

- Plant image history
- Growth timelapse
- Device health confidence
- Diagnostics timeline
- OTA/update state

Recommended fix:

- Use real or simulator-generated product screenshots.
- Use the latest image/growth story as a central visual.
- Keep raw diagnostics behind a polished "reliability" story.

#### 7. Public And Existing-User CTAs Are Blended

New visitors need product education. Existing users need sign-in.

Recommended fix:

- Nav: "Sign in" or "Dashboard"
- Hero primary: "View demo" or "Join early access"
- Hero secondary: "How it works"
- Final CTA: "Request a demo" or "Join early access"

## Messaging Framework

### One-Sentence Product Pitch

PlantLab is a smart indoor plant monitoring system that combines sensors,
camera history, and device health tools so you can understand your plant and
planter from your phone or web dashboard.

Shorter version:

PlantLab helps you see, understand, and maintain your indoor growing setup from
one calm app.

### Hero Headline Options

Recommended:

1. "A smarter window into your indoor plant."

Other viable options:

2. "See what your plant and planter are doing."
3. "Plant care, with a live view."
4. "A calmer way to understand your indoor garden."
5. "Know how your plant is growing, even when you are away."

Avoid:

- "Autonomous plant care"
- "AI plant brain"
- "Never kill a plant again"

### Hero Subheadline Options

Recommended:

PlantLab combines sensor readings, camera history, grow-light control, and
device diagnostics in one mobile and web experience.

Alternatives:

- Follow your plant's environment, image history, and device health without
  digging through hardware logs.
- Built by Mars Potato Lab, PlantLab turns an indoor planter into a visible,
  updateable smart device.
- Monitor readings, capture plant images, and keep firmware health visible from
  one product dashboard.

### CTA Options

Primary CTAs:

- View live demo
- Join early access
- Request a demo

Secondary CTAs:

- See how it works
- Open dashboard
- Sign in

Recommended first implementation:

- Hero primary: "View live demo"
- Hero secondary: "See how it works"
- Nav action: "Sign in" or "Dashboard"
- Final CTA: "Join early access"

If a waitlist backend does not exist yet:

- Use a mailto link or placeholder form only if clearly labeled.
- Prefer "Request a demo" linking to contact until a waitlist flow is real.

### Problem Statement

Indoor growing setups often hide the information people need most. Readings are
scattered, plant changes are slow, camera history is manual, and device issues
only become obvious after something has already gone wrong.

### Solution Statement

PlantLab brings the plant view, environment readings, device controls, and
support diagnostics into a single product experience. The result is a calmer,
more trustworthy way to monitor an indoor plant system.

### Feature Messaging

#### Plant And Environment Monitoring

Outcome:

- Know whether the growing environment is stable.

Supporting capability:

- Air temperature, humidity, water temperature, water level, and runtime state.

Suggested copy:

Track the signals that matter without turning plant care into a spreadsheet.

#### Camera History And Growth Timelapse

Outcome:

- See growth and change over time.

Supporting capability:

- Camera captures, image history, and fixed-duration growth timelapse.

Suggested copy:

Build a visual growth story from regular plant captures.

#### Calm Device Control

Outcome:

- Make simple adjustments without touching hardware.

Supporting capability:

- Grow-light state, brightness, capture commands, and future command actions.

Suggested copy:

Control the planter when it helps, without exposing every internal command.

#### Diagnostics And Reliability

Outcome:

- Understand what happened when a device needs attention.

Supporting capability:

- Diagnostics timeline, command lifecycle, OTA status, state-change events, and
  device health.

Suggested copy:

When something changes, PlantLab keeps the story readable.

#### OTA Updates

Outcome:

- Improve firmware after the product is installed.

Supporting capability:

- OTA release flow, compatibility checks, status reporting, and staged rollout
  foundation.

Suggested copy:

Designed for field updates, not one-time prototypes.

### Why Now / Why This Matters

Smart indoor growing is becoming more accessible, but many hobby projects still
break down at the same point: the hardware works, but the product experience is
hard to trust.

PlantLab matters because it treats the planter as a real connected product:

- visible state
- visual history
- updateable firmware
- supportable diagnostics
- web and mobile access

This makes it useful not only for plant hobbyists, but also for educators,
makers, and collaborators who need a reliable demonstration platform.

### Tone Of Voice

Use:

- calm
- precise
- human
- product-forward
- quietly technical only after the first impression

Avoid:

- hype
- enterprise jargon
- raw backend terms
- excessive "AI" language
- support/debug wording in hero copy

Example tone:

- "See how your plant is doing."
- "Review the latest capture."
- "The camera node needs attention."
- "Firmware update in progress."

Avoid:

- "Contract-native command lifecycle active."
- "Canonical event stream emitted."
- "Backend-owned diagnostics payloads."

## Recommended Homepage Information Architecture

The user suggested these possible sections:

1. Hero
2. Problem
3. Solution
4. Product showcase
5. How it works
6. App/dashboard preview
7. Growth history / camera timeline
8. Diagnostics / reliability
9. Use cases
10. Waitlist or demo CTA

Recommended final structure:

### 1. Hero

Purpose:

- Explain what PlantLab is in one screen.
- Show a premium product preview.
- Offer clear public and existing-user actions.

Content:

- Brand: PlantLab by Mars Potato Lab
- Headline: "A smarter window into your indoor plant."
- Subheadline: sensors, camera history, device health, mobile/web dashboard
- CTA: "View live demo"
- Secondary CTA: "See how it works"
- Nav: "Sign in" or "Dashboard"

Visual:

- Large plant image/dashboard composite, not just an app icon.
- Show one calm health state and one recent capture.

### 2. Product Proof Strip

Purpose:

- Quickly establish that the product is real.

Possible items:

- Mobile app
- Web dashboard
- Camera history
- OTA-ready firmware
- Diagnostics timeline

Keep it short. This is not a specs table.

### 3. Problem

Purpose:

- Make the pain concrete for non-technical users.

Message:

- Indoor plant systems change slowly and fail quietly.
- It is hard to know what happened without scattered logs, manual photos, or
  hardware access.

### 4. Solution / Product Showcase

Purpose:

- Show the PlantLab product experience.

Content:

- Device health summary
- Latest capture
- Readings
- Grow light state
- Growth timelapse

Visual:

- Polished screenshot/composite using simulator data.

### 5. How It Works

Recommended four steps:

1. Pair the device in the mobile app.
2. PlantLab collects readings and camera captures.
3. Monitor plant state from mobile or web.
4. Use diagnostics and OTA updates when the device needs attention.

### 6. Growth History / Camera Timeline

Purpose:

- Make the visual plant story emotionally central.

Content:

- Latest capture
- Recent capture strip
- 30-second growth timelapse concept

Message:

- PlantLab helps you see slow changes clearly.

### 7. Diagnostics And Reliability

Purpose:

- Build trust for early adopters, educators, and investors.

Content:

- Diagnostics timeline
- Command lifecycle
- OTA status
- Camera/Wi-Fi/device health states

Message:

- Reliability is designed into the product, not hidden behind logs.

### 8. Use Cases

Recommended cards:

- Plant hobbyists: watch growth and environment changes.
- Smart home users: keep a connected planter visible.
- STEM educators: demonstrate sensors, firmware, cloud, and app behavior.
- Collaborators/investors: review a real connected-product platform.

### 9. Demo / Waitlist CTA

Purpose:

- Give the visitor a next step.

Recommended:

- Primary: "View live demo"
- Secondary: "Request early access"

If no waitlist exists:

- Use "Request a demo" and route to a contact mechanism rather than a fake
  signup.

## Demo Mode Strategy

### Goal

Create a `/demo` route that lets visitors experience a polished fake-live
PlantLab device without owning hardware or creating an account.

This should be product demo mode, not developer mock mode.

### Demo Principles

- Use simulator-shaped data.
- Do not write to production user accounts.
- Do not expose raw mock/dev terminology.
- Make the device feel alive but not noisy.
- Keep the demo deterministic enough for screenshots and investor walkthroughs.

### Recommended Demo Route

Route:

- `/demo`

Page title:

- "PlantLab Live Demo"

Demo device:

- Name: "Demo PlantLab"
- State: healthy or mild needs-attention depending selected scenario
- Latest image: simulator-generated plant image
- Camera timeline: 6 to 12 captures
- Timelapse: fixed 30-second preview
- Readings: realistic sensor trends
- Health: Wi-Fi, camera node, firmware, OTA state
- Activity: readable recent events

### Demo Scenarios

Initial implementation should support one default scenario:

- Normal healthy device with recent captures and stable readings.

Later scenarios:

- Wi-Fi degraded
- Camera reconnect
- OTA in progress
- OTA failed and recovered
- Low memory warning
- Growth history available

### Demo Data Sources

Phase 1 demo can use static fixture data generated from simulator patterns.

Phase 2 demo can call a backend demo endpoint if useful:

- `GET /api/demo/device`
- `GET /api/demo/timeline`
- `GET /api/demo/images`

Do not require real device tokens for public demo mode.

### Demo UX

The demo should feel like a guided product walkthrough:

- "This is a simulated PlantLab device."
- "No hardware required."
- "Try viewing images, growth history, and diagnostics."

Keep this note quiet and transparent. Avoid "fake" language in the main visual
areas.

### What The Demo Should Show

- Hero device state
- Latest image preview
- 30-second growth timelapse
- Sensor trend cards
- Grow light state
- Camera node status
- OTA/update badge
- Recent activity timeline

### What The Demo Should Not Show First

- raw JSON
- device tokens
- database IDs
- command payloads
- backend contract names

## Visual Direction

### Layout Style

Use spacious, editorial product sections:

- full-width bands with constrained inner content
- one strong hero
- large product visuals
- alternating copy and screenshot sections
- clear CTA hierarchy

Avoid:

- dense dashboard grids on the public homepage
- card-heavy feature walls above the fold
- a login-form feel

### Typography Direction

Use the existing PlantLab typography hierarchy from the design token plan:

- Display for hero headline
- Title for section headings
- Body large for product explanation
- Meta for proof-strip labels and supporting notes

Guidance:

- Fewer all-caps labels.
- Keep hero copy short.
- Let the product visuals carry detail.

### Color Direction

Base:

- matte white
- soft mist gray
- low-contrast borders

Accent:

- PlantLab green for primary actions and healthy living state
- blue for system/water/camera details
- warm copper sparingly for plant warmth/light
- amber only for needs-attention states

Avoid:

- dark enterprise dashboard palettes
- purple/blue gradient branding
- neon sci-fi visuals
- beige/brown plant-store palette

### Imagery And Product Visuals

Use:

- real or simulator-generated plant captures
- dashboard screenshots/composites
- mobile app screenshots
- minimal product/device render if available

Avoid:

- cartoon plants
- generic stock plant photos as the main proof
- raw UI screenshots with debug/admin clutter

### Animation And Motion

Motion should be subtle:

- hero capture gently updates
- timelapse preview animates on interaction
- OTA progress uses calm progress motion
- section reveals only if they do not distract

Do not add:

- heavy parallax
- decorative blobs/orbs
- gaming-style motion

### Mobile Responsiveness

Mobile landing should prioritize:

- direct product explanation
- one clear screenshot/visual at a time
- CTA visibility
- compressed proof strip
- no horizontal dashboard squeeze

## Implementation Roadmap

### Phase 1: Core Marketing Copy And Homepage Structure

Goal:

- Replace project-page feel with a clear product landing structure.

Likely files affected:

- `platform/web/src/screens/LandingScreen.tsx`
- `platform/web/src/styles/app.css`
- possibly `platform/web/src/assets/*` if screenshot assets are added

Components to create:

- `MarketingHero`
- `ProductProofStrip`
- `LandingSection`
- `LandingCTA`

Work:

- Update hero headline and subheadline.
- Separate public CTA from sign-in/dashboard CTA.
- Add problem, solution, and how-it-works sections.
- Keep `/` public for signed-in and signed-out users.

Validation commands:

```bash
npm --prefix platform/web run build
git diff --check
```

Risks:

- Breaking the root landing behavior for authenticated users.
- Overloading the first screen with too many CTAs.
- Making claims beyond current product capability.

Pass criteria:

- Homepage clearly explains PlantLab in the first viewport.
- Existing sign-in/dashboard path remains available.
- Web build passes.
- No backend changes required.

### Phase 2: Product Sections And App Preview

Goal:

- Show the actual product experience, not just describe it.

Likely files affected:

- `platform/web/src/screens/LandingScreen.tsx`
- `platform/web/src/styles/app.css`
- `platform/web/src/components/*` for reusable preview components
- `platform/web/src/assets/*` for screenshots or generated demo visuals

Components to create:

- `ProductShowcase`
- `AppPreviewPanel`
- `GrowthStoryPreview`
- `ReliabilityPreview`
- `UseCaseGrid`

Work:

- Add dashboard/mobile preview.
- Add image history/growth timelapse section.
- Add diagnostics/reliability section.
- Add use-case cards.

Validation commands:

```bash
npm --prefix platform/web run build
git diff --check
```

Risks:

- Screenshots becoming stale.
- Product preview looking like a dense dashboard.
- Diagnostics copy becoming too technical.

Pass criteria:

- Product visuals support the copy.
- User-facing sections do not expose raw debug concepts.
- Responsive layout works at mobile and desktop widths.

### Phase 3: Simulator-Powered Demo Page

Goal:

- Add `/demo` as a polished product demo using fake-live PlantLab data.

Likely files affected:

- `platform/web/src/App.tsx` or route configuration
- `platform/web/src/screens/DemoScreen.tsx`
- `platform/web/src/api/demo.ts` if API-backed
- `platform/web/src/mock/*` or `platform/web/src/demo/*`
- Optional backend demo endpoints if static fixtures are not enough

Components to create:

- `DemoDeviceOverview`
- `DemoImageTimeline`
- `DemoGrowthTimelapse`
- `DemoActivityTimeline`
- `DemoScenarioSelector` if scenarios are included

Work:

- Create public demo route.
- Use simulator-style fake live data.
- Show images, timeline, OTA/status, Wi-Fi/camera state, and readings.
- Keep demo transparent but premium.

Validation commands:

```bash
npm --prefix platform/web run build
git diff --check
```

If backend demo endpoints are added:

```bash
.venv/bin/pytest platform/backend/tests -q
```

Risks:

- Accidentally depending on authenticated APIs.
- Confusing demo state with real user/device state.
- Demo becoming another dashboard instead of guided product proof.

Pass criteria:

- `/demo` works without sign-in.
- Demo does not require real hardware or device token.
- Demo clearly presents PlantLab's value.
- Build/tests pass.

### Phase 4: Polish, SEO, And Launch Readiness

Goal:

- Prepare the public page for real external traffic.

Likely files affected:

- `platform/web/index.html`
- `platform/web/src/screens/LandingScreen.tsx`
- `platform/web/src/styles/app.css`
- `platform/web/public/*` if social image/metadata assets are added

Work:

- Add SEO title and meta description.
- Add Open Graph/Twitter image.
- Tune mobile layout.
- Add final trust signals.
- Add analytics only if privacy/product decision is made.
- Add route regression check for `/`.

Validation commands:

```bash
npm --prefix platform/web run build
git diff --check
```

Risks:

- SEO/social images requiring stable public asset paths.
- Adding tracking before privacy expectations are clear.
- Landing route regression.

Pass criteria:

- Metadata is production-ready.
- Mobile and desktop first view are polished.
- `/` still renders landing page for signed-in and signed-out users.

## Recommended Next Implementation Step

Start with Phase 1 only:

> Rewrite the homepage structure and copy around one clear promise: PlantLab is
> a smart indoor plant monitoring system with sensors, camera history, and
> device health tools.

Do not start with `/demo`.

Reason:

- The homepage currently needs clearer messaging before a demo route can convert
  well.
- Phase 1 does not need backend changes.
- It can reuse existing design tokens and assets.
- It preserves momentum without touching risky device/dashboard behavior.

Definition of done for Phase 1:

- Hero explains what PlantLab is.
- CTA hierarchy supports new visitors and existing users.
- Problem, solution, and how-it-works sections exist.
- Copy avoids overpromising AI/autonomy.
- Web build passes.
- `git diff --check` passes.

## Open Decisions

- Primary CTA: "View live demo" vs "Join early access" vs "Request a demo".
- Whether the first release should use real product photography, simulator
  captures, or a polished screenshot composite.
- Whether `/demo` should be fully static at first or API-backed.
- Whether waitlist/contact should be email, form, or external tool.
- Whether Mars Potato Lab should be visible in the hero or footer only.

## Non-Goals

- No implementation in this planning pass.
- No new backend features.
- No speculative AI claims.
- No public demo requiring auth.
- No replacing the signed-in dashboard.
- No changing mobile app onboarding.
