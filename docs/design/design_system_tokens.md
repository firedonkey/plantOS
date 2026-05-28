# PlantLab Design System Tokens

## Purpose

PlantLab uses a small shared token layer so web and mobile can move toward the
same product language without adopting a large UI framework.

The tokens support the current polish sequence:

- calm smart-device surfaces
- consistent status and severity colors
- shared spacing, radius, typography, and elevation decisions
- reusable web surface classes
- React Native-friendly mobile theme values

## Source Files

Web:

- `platform/web/src/styles/app.css`

Mobile:

- `platform/mobile/src/styles/theme.ts`

The web implementation exposes CSS custom properties under the `--pl-*`
namespace. The mobile implementation exposes equivalent values through the
`theme` object.

## Color Families

Core colors:

- `background`
- `backgroundElevated`
- `surface`
- `surfaceMuted`
- `surfaceInset`
- `border`
- `borderSoft`
- `textPrimary`
- `textSecondary`
- `textMuted`

Brand and action:

- `accent`
- `accentSoft`

Semantic colors:

- `success`
- `warning`
- `danger`
- `info`
- `mock`

Sensor colors:

- `sensorAir`
- `sensorHumidity`
- `sensorWater`

Guidance:

- Use PlantLab green for primary action, healthy state, and living-device cues.
- Use blue for system or water/humidity information.
- Use copper sparingly for air temperature.
- Use red only for errors or critical states.
- Use purple only for mock/developer states.

## Status, Severity, And Health Tokens

Status tokens describe runtime state:

- `online`
- `degraded`
- `offline`
- `provisioning`
- `updating`
- `error`
- `mock`

Severity tokens describe timeline or diagnostics importance:

- `info`
- `warning`
- `critical`

Health tokens describe product-facing device confidence:

- `healthy`
- `attention`
- `offline`
- `updating`
- `critical`

Guidance:

- Prefer health tokens for user-facing summaries.
- Prefer severity tokens for events.
- Prefer status tokens for node/device runtime state.

## Spacing

Spacing is intentionally compact:

- `xs`: 4
- `sm`: 8
- `md`: 12
- `lg`: 16
- `xl`: 20
- `xxl`: 24

Web additionally exposes larger layout spacing variables:

- `--pl-space-8`: 32px
- `--pl-space-10`: 40px
- `--pl-space-12`: 48px

## Typography

Shared type roles:

- `eyebrow`
- `caption`
- `meta`
- `body`
- `bodyLarge`
- `sectionTitle`
- `cardTitle`
- `screenTitle`

Guidance:

- Use fewer all-caps labels on product surfaces.
- Keep hardware identifiers and timestamps in `meta`.
- Use concise status language rather than backend terms.

## Radius

Shared radius roles:

- `sm`: 6px
- `md`: 8px
- `pill`: 999px

Guidance:

- Use `md` for cards and controls.
- Use `pill` only for chips, tabs, and compact status badges.

## Elevation

Mobile exposes:

- `none`
- `card`
- `hero`

Web exposes:

- `--pl-shadow-card`
- `--pl-shadow-card-hover`
- `--pl-shadow-hero`

Guidance:

- Use elevation to communicate hierarchy, not decoration.
- Keep default surfaces quiet.
- Reserve hero elevation for the top device overview composition.

## Web Surface Classes

Reusable web classes:

- `.surface`
- `.surface-muted`
- `.surface-inset`
- `.surface-hero`
- `.surface-debug`

Status/severity helpers:

- `.status-token`
- `.status-token-online`
- `.status-token-degraded`
- `.status-token-offline`
- `.status-token-updating`
- `.status-token-error`
- `.severity-token-info`
- `.severity-token-warning`
- `.severity-token-critical`
- `.health-token-healthy`
- `.health-token-attention`
- `.health-token-offline`
- `.health-token-updating`
- `.health-token-critical`

These classes are foundations for later screen redesigns. Step 1 does not
require broad screen adoption.

## Adoption Rules

- Preserve existing APIs and behavior while adopting tokens.
- Do not redesign screens only to use tokens.
- Replace hardcoded values opportunistically when a component is touched.
- Keep web and mobile token names aligned unless platform constraints require
  different names.
- Avoid adding new color families unless a real product state needs them.

## Next Slice

The next implementation slice should use these tokens to redesign the top of
the web/mobile device dashboard around a clear product-facing device overview.
