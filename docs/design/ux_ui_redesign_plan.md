# PlantLab UX/UI Audit And Redesign Plan

## Purpose

This document is a planning artifact for moving PlantLab web and mobile from a
working prototype into a calmer, more premium smart-device product experience.

No UI implementation is included in this pass.

## Scope Reviewed

Web:

- Landing, login, app shell, device list, device dashboard, device settings
- Sensor trends, recent image gallery, timelapse player, diagnostics timeline
- Support diagnostics and admin diagnostics screens
- Global web styling in `platform/web/src/styles/app.css`

Mobile:

- Landing, login, device list, device dashboard, add-device/provisioning flow
- Shared mobile components, theme tokens, timeline, gallery, trends, health
- Mobile styling in screen-local `StyleSheet` files plus `theme.ts`

Product capabilities considered:

- Contract-first device data
- Simulator-driven live states
- Command lifecycle
- Image uploads and timelapse
- Diagnostics timeline
- OTA status and staged rollout
- State-change events

## Executive Summary

PlantLab now has enough backend and simulator maturity to stop designing around
raw telemetry and start designing around product confidence.

The current UI is functional and mostly coherent, but it still reads as an
engineering dashboard in several places:

- Too many sections compete at equal visual weight.
- Debug concepts are visible too early in the user journey.
- Web and mobile share product intent, but not a unified design system.
- Device status is fragmented across readings, command banners, hardware health,
  timeline events, and settings.
- Diagnostics are powerful, but the default presentation should be more
  narrative and less raw-event focused.

The recommended direction is an incremental redesign centered on one clear
product promise:

> "At a glance, the user should know whether the plant and device are okay,
> what changed recently, and what action is available now."

## Current Strengths

- The main app routes are now product-shaped rather than only developer-shaped:
  landing page, login, device list, device detail, settings, support, and admin.
- Web no longer exposes "Add device" as a primary flow, matching the current
  mobile-owned provisioning model.
- Mobile has a native landing page and a stronger sign-in screen than earlier
  prototype versions.
- Device detail already includes the right product ingredients:
  readings, light control, images, timelapse, trends, activity, and settings.
- Diagnostics timeline exists on web and mobile components exist for mobile use.
- Hardware health and command activity have been moved away from the main web
  dashboard as advanced/support concepts.
- Simulator can generate realistic state, image, OTA, command, and failure
  activity. This is a major asset for UX iteration.

## UX Issues Found

### 1. Dashboard Hierarchy Is Still Too Flat

The web device dashboard stacks these sections:

- Header
- Status banners
- Primary readings
- Grow LED
- Camera
- Timelapse
- Sensor trends
- Diagnostics timeline
- Device settings button

Most sections use similar card weight, borders, spacing, and type scale. This
makes the user scan the whole page instead of understanding the device state
from the first screen.

Recommended change:

- Create a dominant "Device overview" hero area.
- Group readings, light, camera, and update state into a single product summary.
- Move heavy charts, timeline filters, and advanced details lower or behind
  progressive disclosure.

### 2. User And Support Concepts Are Mixed

The product has both user-facing and support-facing needs:

- User: "Is my planter okay?"
- Support: "Which node posted this command result?"
- Developer: "What was the raw JSON payload?"

The UI sometimes surfaces support language too early:

- hardware identifiers
- node roles
- mock mode
- command lifecycle wording
- backend diagnostics
- raw JSON details

Recommended change:

- Rename the default timeline surface to "Activity" or "Recent activity".
- Keep "Diagnostics timeline" inside Device Settings, Support, or Admin.
- Use support/debug terminology only inside advanced surfaces.

### 3. Visual Identity Is Functional But Not Premium Yet

The current palette is calm and appropriate, but the web app still feels like
a set of standard cards:

- soft gray background
- white cards
- green accent
- simple chips
- technical charts

This is a good foundation, but not yet a distinctive smart-home product.

Recommended change:

- Keep the matte white and soft gray base.
- Use PlantLab green as the primary accent.
- Add restrained secondary accents for sensor categories only.
- Introduce richer visual structure through layout, scale, imagery, and
  device-state composition rather than decorative gradients or heavy effects.

### 4. Web And Mobile Are Not Sharing Enough Design Infrastructure

Mobile has a clear `theme.ts` with colors, spacing, radii, and typography.
Web has a large global CSS file with many screen and component concerns mixed
together.

Recommended change:

- Create a web token layer that mirrors mobile theme concepts.
- Keep implementation lightweight: CSS variables and component classes first,
  no large design-system framework.
- Align names across web/mobile: background, surface, surfaceMuted, border,
  accent, success, warning, danger, info, textPrimary, textSecondary.

### 5. Charts Are Useful But Still Read As Telemetry

Sensor trends are improved, but the chart panels still emphasize:

- exact reading count
- min/max
- chart axes
- range tabs

This is valid for debugging, but the default user story should be:

- "Stable"
- "Warming"
- "Humidity trending down"
- "Water temperature normal"

Recommended change:

- Keep detailed charts available.
- Add higher-level trend summaries above or inside each chart.
- De-emphasize raw counts in the default view.

### 6. Image And Timelapse Can Become The Emotional Center

PlantLab is a visual plant product. The latest image and growth timelapse should
feel more central than the current card treatment.

Recommended change:

- Make the latest plant image a primary visual region on both web and mobile.
- Treat timelapse as "Growth story" rather than a utility widget.
- Keep capture controls clear, but avoid making the image area feel like a file
  browser.

### 7. Mobile Dashboard Is Better Focused Than Web But Missing Activity

Mobile has a clear single-column flow and shared components. However, the
device dashboard does not yet surface timeline/activity by default, even though
the component exists.

Recommended change:

- Add a compact "Recent activity" preview on mobile after primary actions.
- Keep full diagnostics collapsed or under an advanced view.

### 8. Onboarding Is A Product Risk Area

The mobile add-device flow is large and complex. It handles BLE discovery,
serial fallback, Wi-Fi provisioning, recovery mode, QR scanning, and online
confirmation.

Recommended change:

- Do not redesign this first.
- Later, split the UX into clearer steps with one primary action per screen.
- Preserve all existing BLE and recovery behavior during redesign.

### 9. Admin And Support Screens Are Correctly Separate But Visually Dense

Admin diagnostics and support diagnostics are expected to be denser than the
consumer dashboard. The current structure is acceptable for internal tooling,
but it still benefits from clearer rollups, severity grouping, and fewer large
lists on first load.

Recommended change:

- Keep admin separate.
- Do not force admin visuals to match the consumer dashboard exactly.
- Use the same tokens and typography so it still feels like PlantLab.

## Product Design Direction

### Product Personality

PlantLab should feel:

- calm
- intelligent
- precise
- alive
- reliable
- modern
- quietly futuristic

It should not feel:

- like Grafana
- like a hacker console
- like an enterprise admin panel
- like a gaming UI
- like a generic Bootstrap dashboard

### Visual Direction

Base:

- matte white and soft mist-gray background
- low-contrast borders
- restrained shadows
- generous whitespace
- rounded controls at 6px to 8px, with pill shapes only for chips/tabs

Accent system:

- PlantLab green for primary action and healthy state
- cool blue for humidity/water/system info
- warm copper only for air temperature or plant warmth
- red only for true errors
- amber only for caution
- purple only for mock/developer state, and never as a main brand color

Layout:

- fewer full-width stacked cards
- clearer section ownership
- one dominant product summary at top
- media and live state get stronger hierarchy than debug details

### Typography

Recommended hierarchy:

- Display: device name, landing hero, major state
- Title: screen and card titles
- Body: product explanation and status
- Meta: timestamps, hardware details, technical identifiers
- Label: controls, filters, chips

Guidance:

- Use fewer all-caps labels.
- Keep technical identifiers in meta style.
- Use short human labels: "Healthy", "Needs attention", "Updating",
  "Camera offline", "Light on".

### Card System

Recommended card types:

- `Surface`: neutral section container
- `HeroSurface`: top device summary
- `ControlSurface`: interactive controls
- `MediaSurface`: image or timelapse region
- `InsightSurface`: trend or summary
- `DebugSurface`: advanced support details

Avoid:

- cards inside cards unless the inner card is a repeated item
- equal card weight for every concept
- debug JSON as the visual center

### Iconography

Use simple, line-based icons only where they improve scan speed:

- device
- plant/image
- light
- camera
- Wi-Fi
- update
- warning
- check

Avoid:

- cartoon plant graphics
- overloaded icon badges
- novelty sci-fi symbols

### Motion And Interaction

Motion should be subtle and purposeful:

- control state transitions
- loading skeletons
- timeline expand/collapse
- OTA progress
- image capture feedback

Avoid:

- decorative motion
- pulsing backgrounds
- animations that imply device state changed before the backend confirms it

## Information Architecture Proposal

### Web IA

Public:

- Landing
- Sign in

Authenticated user:

- Devices
  - device cards with health, latest image, and last seen
- Device overview
  - hero state
  - primary readings
  - light control
  - latest image
  - recent activity preview
  - trend summary
- Device media
  - image history
  - timelapse
  - capture history
- Device trends
  - environmental charts
  - range controls
  - detailed min/max/counts
- Device settings
  - name/location/plant type
  - hardware health
  - recovery actions
  - technical identifiers
- Activity and diagnostics
  - user-friendly recent activity by default
  - advanced timeline filters and raw JSON behind expand

Internal:

- Support diagnostics
- Admin diagnostics
- OTA/release management if kept internal

### Mobile IA

Public:

- Landing
- Sign in

Authenticated:

- Home / devices
  - glanceable device cards
  - latest image thumbnail
  - health and last seen
- Device overview
  - live state hero
  - primary actions
  - latest image
  - readings
  - recent activity
- Device media
  - gallery
  - timelapse
  - manual capture
- Device trends
  - simplified chart cards
- Device settings
  - device labels
  - hardware health
  - advanced diagnostics
- Add device
  - mobile-only provisioning and recovery flow

### Progressive Disclosure Rules

Always visible:

- device name
- overall health
- latest image or clear empty state
- most recent readings
- light control
- last updated / online confidence
- latest meaningful activity

Visible when relevant:

- OTA update state
- camera disconnected
- Wi-Fi degraded
- low water alert
- failed command
- image upload failure

Advanced only:

- hardware IDs
- node roles
- device tokens
- raw JSON
- command queue details
- backend endpoint concepts
- mock mode details

## Dashboard Redesign Proposal

### Top Structure

1. Device hero
   - device name, plant type, location
   - health state
   - last seen
   - latest image thumbnail or ambient visual
   - one concise status sentence

2. Live controls and state
   - grow light toggle and brightness
   - camera capture
   - OTA/update state only if active or available

3. Plant environment
   - air temp
   - humidity
   - water temp
   - water level alert only when relevant
   - short trend summary

4. Growth media
   - latest image
   - recent captures
   - timelapse preview

5. Recent activity
   - concise timeline rows
   - "View diagnostics" link for advanced timeline

6. Detailed trends
   - full charts and range controls

7. Device settings / advanced
   - hardware health
   - recovery
   - identifiers

### Better Device Status Communication

Current state is spread across multiple surfaces. Redesign should consolidate it
into a single status sentence and supporting chips.

Examples:

- "Everything looks steady. Last update 18 seconds ago."
- "Camera is offline. Sensor readings are still updating."
- "Wi-Fi signal is weak, but commands are still reaching the device."
- "Update is installing. Keep the device powered."

## Diagnostics UX Strategy

### Default User Surface: Activity

Use simple summaries:

- "Light changed to 65%"
- "Image captured"
- "Camera reconnected"
- "Update completed"
- "Wi-Fi signal recovered"

Limit default filters. Show only:

- All
- Alerts
- Updates
- Images
- Commands

### Advanced Surface: Diagnostics Timeline

Keep advanced controls:

- event type
- severity
- node role
- correlation id
- raw JSON
- load older

Make this available from:

- Device settings
- Support diagnostics
- Admin diagnostics

### Correlation Display

For related events, show a small correlation thread:

- Command sent
- Acknowledged
- Running
- Completed

Do this visually in a lightweight way before building complex grouping.

## Mobile-First Guidance

Mobile should optimize for:

- fast glance
- one-handed actions
- confidence that commands landed
- latest image first
- clear offline/update states
- short event summaries

Mobile should avoid:

- desktop-style debug panels
- long raw payloads by default
- dense chart controls on the first screen
- making provisioning copy sound like backend internals

Recommended mobile default order:

1. Device state hero
2. Quick actions
3. Latest image
4. Primary readings
5. Recent activity
6. Trends
7. Settings and diagnostics

## Simulator-Driven UX Workflow

Use the simulator as the primary live-data source during redesign.

Recommended scenario set:

- `normal`: steady readings, light changes, image captures
- `unstable_wifi`: degraded/recovered signal states
- `camera_disconnect`: camera state and image failure UX
- `ota_failure`: update trust and error copy
- `command_failure`: command feedback and recovery copy
- `reboot_loop`: health and timeline readability
- `low_memory`: support diagnostics behavior

Designer/developer validation loop:

1. Start local Docker backend.
2. Start simulator with a real local device token.
3. Open web dashboard and mobile dev build.
4. Run one scenario at a time.
5. Confirm the UI remains calm, readable, and actionable.

## Redesign Roadmap

### Phase 1: Product Foundation And Dashboard Polish

Targets:

- web design tokens
- mobile token alignment
- shared product copy rules
- web/mobile dashboard top hierarchy
- loading, empty, and error states
- primary cards and controls

Expected improvement:

- app feels more cohesive immediately
- first screen communicates device confidence
- engineering details move down or behind advanced controls

Dependencies:

- existing APIs only
- simulator for visual testing

Risk areas:

- changing dashboard structure without breaking command interactions
- preserving slider command behavior
- keeping mobile dashboard scroll performance clean

### Phase 2: Device Detail, Media, Timeline, And OTA Polish

Targets:

- recent image gallery
- timelapse player
- trend cards
- user-facing activity timeline
- advanced diagnostics timeline
- OTA state and update messaging

Expected improvement:

- growth media becomes emotionally central
- timeline becomes understandable to non-engineers
- OTA feels trustworthy and safe

Dependencies:

- current timeline API
- current image/timelapse APIs
- current OTA events

Risk areas:

- over-compressing diagnostics and hiding useful support data
- making OTA look complete before backend/device confirms it

### Phase 3: Onboarding, Provisioning, And Mobile Refinement

Targets:

- mobile add-device flow
- BLE discovery
- Wi-Fi selection
- recovery/re-provisioning
- mobile activity panel
- subtle transitions
- permission copy

Expected improvement:

- setup feels like a consumer device flow
- fewer scary technical states
- better recovery when provisioning is slow

Dependencies:

- existing BLE provisioning logic
- current setup status APIs

Risk areas:

- onboarding is already complex and must be refactored carefully
- BLE edge cases must remain intact

### Phase 4: Landing, AI Insights, And Advanced Product Layers

Targets:

- public landing polish
- marketing narrative
- AI/growth insight placeholders
- automation UX
- admin/support refinement

Expected improvement:

- stronger first impression before sign-in
- product story is clear outside the dashboard
- future intelligence has a proper UI home

Dependencies:

- product messaging decisions
- future AI/analytics scope

Risk areas:

- adding speculative features before the core dashboard feels finished

## Suggested Component Priorities

Build these in order:

1. Design tokens
   - web CSS variables aligned with mobile `theme.ts`
   - documented semantic colors and spacing

2. Product shell components
   - `PageHeader`
   - `DeviceHero`
   - `StatusSummary`
   - `SectionSurface`

3. Device data components
   - `ReadingTile`
   - `LightControl`
   - `ConnectionQuality`
   - `UpdateStatus`

4. Media components
   - `LatestImagePanel`
   - `CaptureAction`
   - `GrowthTimelinePreview`

5. Activity components
   - `RecentActivity`
   - `ActivityRow`
   - `DiagnosticsDetails`

6. State components
   - loading skeletons
   - empty states
   - inline error states
   - command pending/success/failure states

## Implementation Plan By Phase

### Phase 1 Implementation Plan

Screens/components:

- Web: `AppLayout`, device dashboard, device list, card/button/chip styles
- Mobile: dashboard hero, device list card, shared `theme.ts` additions

Work:

- Add design tokens.
- Normalize card, chip, button, and section spacing.
- Create a device overview hero using existing data.
- Reduce debug copy on dashboard.
- Keep existing command and API hooks unchanged.

Backend/API needs:

- none expected

Validation:

- web typecheck/build
- mobile typecheck
- simulator visual pass with normal and unstable Wi-Fi scenarios

### Phase 2 Implementation Plan

Screens/components:

- Web/mobile image gallery
- Timelapse player
- Trends
- Timeline/activity
- OTA status surfaces

Work:

- Redesign media presentation.
- Split user activity from advanced diagnostics.
- Make OTA status more narrative and less raw.
- Add useful empty states for no images, no events, and no readings.

Backend/API needs:

- none expected, unless an activity-summary endpoint is later desired

Validation:

- web/mobile typecheck
- simulator scenarios: image capture, camera disconnect, OTA success/failure

### Phase 3 Implementation Plan

Screens/components:

- Mobile add-device/provisioning
- Device recovery
- Mobile diagnostics entry
- Permission and error states

Work:

- Split onboarding into smaller visual steps.
- Reduce technical copy.
- Preserve BLE, QR, serial fallback, recovery, and waiting-online logic.

Backend/API needs:

- none expected

Validation:

- mobile typecheck
- manual BLE/provisioning test
- local simulator for post-provision device activity

### Phase 4 Implementation Plan

Screens/components:

- Web landing page
- Admin/support diagnostics
- Future AI insights area
- Automation concepts

Work:

- Make public product story more concrete.
- Keep landing page available for signed-in and signed-out users.
- Improve internal tools without making user UI feel like admin UI.

Backend/API needs:

- none for landing
- possible future insight endpoints

Validation:

- web typecheck/build
- landing route regression test
- admin/support smoke test

## Web Vs Mobile Guidance

Web should be:

- spacious
- comparative
- good for reviewing trends, images, and timeline history
- able to expose advanced diagnostics, but not as the default story

Mobile should be:

- glanceable
- action-oriented
- image-forward
- clear about command feedback
- careful with long technical details

Shared behavior:

- same status language
- same severity meanings
- same visual hierarchy for healthy, warning, critical, updating, offline
- same command feedback model

Different behavior:

- web can show side-by-side trends and activity
- mobile should show one primary decision per section
- web can host support/admin entry points
- mobile should keep support/debug features secondary

## Recommended Single Next Implementation Step

Start with Phase 1A:

> Create a shared product design token layer and redesign only the top of the
> device dashboard into a calm "Device overview" composition on web and mobile,
> using existing data and existing APIs.

Why this step first:

- It improves the highest-traffic product surface.
- It does not require backend changes.
- It does not touch risky provisioning logic.
- It gives web and mobile a shared visual direction.
- It can be validated immediately with the simulator.

Definition of done for Phase 1A:

- Web and mobile dashboard top sections have the same information hierarchy.
- Device status, readings, light control, latest image, and recent activity are
  visible in a clearer priority order.
- Advanced diagnostics remain available but are not visually dominant.
- Existing command, image capture, trend, and timeline behavior still works.
- Web build, mobile typecheck, and simulator smoke pass.

## Open Decisions

- Whether "Activity" should fully replace "Diagnostics timeline" on user
  surfaces, or whether both labels remain visible in different sections.
- Whether media should move above readings on mobile after real user testing.
- Whether OTA management belongs on normal device detail or only settings/admin
  unless an update is available.
- Whether public landing should include real product photography before App Store
  release.

## Non-Goals For The Next Slice

- No new backend contracts.
- No new animation framework.
- No admin dashboard rewrite.
- No provisioning refactor.
- No charting library replacement unless current charts block the design.
- No visual overhaul of every screen in one commit.
