import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const testDir = dirname(fileURLToPath(import.meta.url));
const readText = (path: string) => readFile(join(testDir, path), "utf8");

test("shared polish primitives use theme tokens and stable feedback surfaces", async () => {
  const [cardSource, emptyStateSource, feedbackSource, skeletonSource, statusChipSource, themeSource] = await Promise.all([
    readText("../src/components/Card.tsx"),
    readText("../src/components/EmptyState.tsx"),
    readText("../src/components/FeedbackBanner.tsx"),
    readText("../src/components/Skeleton.tsx"),
    readText("../src/components/StatusChip.tsx"),
    readText("../src/styles/theme.ts"),
  ]);

  for (const requiredText of [
    'variant?: "default" | "inset" | "elevated" | "hero"',
    "variantStyles[variant]",
    "theme.radii.md",
    "theme.spacing.lg",
  ]) {
    assert.match(cardSource, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }

  for (const source of [emptyStateSource, feedbackSource, skeletonSource, statusChipSource]) {
    assert.match(source, /theme\.colors\./);
    assert.match(source, /theme\.spacing\.|theme\.radii\.|theme\.typography\./);
  }

  for (const requiredToken of [
    "surfaceMuted",
    "surfaceInset",
    "borderSoft",
    "accentSoft",
    "successSoft",
    "warningSoft",
    "dangerSoft",
    "infoSoft",
    "mockSoft",
    "chartGrid",
    "chartAxis",
  ]) {
    assert.match(themeSource, new RegExp(requiredToken));
  }

  assert.match(feedbackSource, /tone\?: "success" \| "error" \| "info" \| "warning"/);
  assert.match(statusChipSource, /waiting: \{ backgroundColor: theme\.colors\.infoSoft \}/);
  assert.match(statusChipSource, /mock: \{ backgroundColor: theme\.colors\.mockSoft \}/);
});

test("device dashboard has polished loading, setup, controls, and empty states", async () => {
  const source = await readText("../src/screens/DeviceDashboardScreen.tsx");

  for (const requiredText of [
    "const setupComplete = params.setup === \"complete\";",
    "Setup complete. The dashboard is ready when the first live readings arrive.",
    '<FeedbackBanner tone="error" message={error} />',
    '<SkeletonCard />',
    '<EmptyState title="Waiting for first reading"',
    "Primary readings",
    "<Text style={styles.sectionTitle}>Grow LED</Text>",
    "Capture image",
    "Sensor trends",
    "formatDeviceContext",
  ]) {
    assert.match(source, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }

  assert.doesNotMatch(source, /runPump|label="Pump"|soilMoisturePercent/);
  assert.doesNotMatch(source, /FreshnessStrip|Operational controls stay disabled|>Controls<|MetricCard label="Grow LED"/);
  assert.doesNotMatch(source, /HardwareHealthPanel|CommandActivityPanel/);
  assert.doesNotMatch(source, /overviewImageFrame|overviewImageEmpty|No latest image yet/);
  assert.doesNotMatch(source, /Plant type not set|No location set/);
});

test("mobile login keeps local development sign-in available when dev auth is enabled", async () => {
  const source = await readText("../src/screens/LoginScreen.tsx");

  for (const requiredText of [
    'const showProductionAuth = authMode === "production";',
    "const showLocalLogin = isDevAuthEnabled();",
    "Local development sign-in",
    "dev@plantlab.local",
    "Continue locally",
    "keyboardType=\"email-address\"",
    "styles.localLoginPanel",
    "Continue with Google",
    "AppleAuthentication.AppleAuthenticationButton",
  ]) {
    assert.match(source, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }

  assert.doesNotMatch(source, /showLocalLogin = authMode === "dev"/);
  assert.doesNotMatch(source, /Google sign-in stays off while AUTH_MODE is dev/);
});

test("mobile settings surfaces the signed-in user name", async () => {
  const [settingsSource, authSource, typeSource] = await Promise.all([
    readText("../src/screens/SettingsScreen.tsx"),
    readText("../src/api/auth.ts"),
    readText("../src/types/api.ts"),
  ]);

  for (const requiredText of [
    "const userName = session?.name?.trim() || session?.email || \"Signed out\";",
    "<Text style={styles.label}>User name</Text>",
    "<Text style={styles.value}>{userName}</Text>",
    "{userEmail && userEmail !== userName ? <Text style={styles.note}>{userEmail}</Text> : null}",
  ]) {
    assert.match(settingsSource, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }

  assert.match(typeSource, /name\?: string/);
  assert.match(authSource, /name: session\.user\?\.name \?\? undefined/);
  assert.match(authSource, /name: payload\.user\.name \?\? undefined/);
});

test("device settings owns hardware health review", async () => {
  const source = await readText("../src/screens/DeviceSettingsScreen.tsx");

  for (const requiredText of [
    "HardwareHealthPanel",
    "health={details?.hardwareHealth}",
    "Operational details",
    "Recovery",
  ]) {
    assert.match(source, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});

test("device dashboard gates grow LED intensity controls on capability support", async () => {
  const source = await readText("../src/screens/DeviceDashboardScreen.tsx");

  for (const requiredText of [
    "const lightIntensitySupported = hasLightIntensitySupport(dashboard?.hardwareHealth?.primary?.capabilities);",
    "lightIntensitySupported ? (",
    "LightIntensitySlider",
    'onCommit={(value) => runCommand("light_intensity", { intensityPercent: value })}',
    "scrollEnabled={!sliderActive}",
    "onInteractionChange={setSliderActive}",
    "new Animated.Value(committedValue)",
    "measureInWindow",
    "event.nativeEvent.pageX",
    'accessibilityLabel="Grow LED intensity"',
    'accessibilityRole="adjustable"',
    "Brightness",
    "capabilities.light_intensity_control === true",
    "capabilities.light_dimming === true",
    "capabilities.light_pwm === true",
    '["intensity", "dimming", "pwm"].includes(String(mode).toLowerCase())',
  ]) {
    assert.match(source, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }

  assert.doesNotMatch(source, /LightIntensityStepper|Decrease grow LED intensity|Increase grow LED intensity|Set grow LED intensity|Slide to set brightness|locationX/);
});

test("device list replaces blank loading and empty screens with reusable polished states", async () => {
  const source = await readText("../src/screens/DeviceListScreen.tsx");

  for (const requiredText of [
    "SkeletonCard",
    '<EmptyState title="No devices yet"',
    '<FeedbackBanner tone="error" message={error} />',
    "Mock data mode",
    "Add device",
    'Card variant="elevated"',
  ]) {
    assert.match(source, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});

test("hardware health panel starts compact and expands into scan-friendly rows", async () => {
  const source = await readText("../src/components/HardwareHealthPanel.tsx");

  for (const requiredText of [
    "const [expanded, setExpanded]",
    "PanelHeader",
    '<EmptyState title="Waiting for health"',
    "HealthItem title=\"Master\"",
    "HealthItem",
    "Last command",
    'accessibilityRole="button"',
    "expanded ? \"Hide\" : \"Show\"",
    "Dismiss",
    "dismissedAttentionSignature",
    "Reviewed",
    'case "stale":',
    'return "Stale";',
    'case "warning":',
    'return "Warning";',
    'case "waiting":',
    'return "Waiting";',
    'case "unknown":',
    'return "Unknown";',
  ]) {
    assert.match(source, new RegExp(requiredText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }
});
