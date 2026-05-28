import { useCallback, useEffect, useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { DeviceTimelineFilters, getDeviceTimeline } from "@/api/devices";
import { Card } from "@/components/Card";
import { EmptyState } from "@/components/EmptyState";
import { useSession } from "@/hooks/useSession";
import { theme } from "@/styles/theme";
import { DeviceTimelineEvent } from "@/types";

const EVENT_FILTERS = [
  { label: "All", value: "" },
  { label: "Command done", value: "COMMAND_COMPLETED" },
  { label: "Command failed", value: "COMMAND_FAILED" },
  { label: "OTA failed", value: "OTA_FAILED" },
  { label: "Images", value: "IMAGE_UPLOADED" },
  { label: "Image failed", value: "IMAGE_UPLOAD_FAILED" },
  { label: "Health", value: "DEVICE_HEALTH_CHANGED" },
];

const SEVERITY_FILTERS = [
  { label: "All", value: "" },
  { label: "Info", value: "info" },
  { label: "Warning", value: "warning" },
  { label: "Critical", value: "critical" },
];

export function DeviceTimelinePanel({ deviceId }: { deviceId: string }) {
  const { token } = useSession();
  const [expanded, setExpanded] = useState(false);
  const [events, setEvents] = useState<DeviceTimelineEvent[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());
  const [eventType, setEventType] = useState("");
  const [severity, setSeverity] = useState("");
  const [nextBefore, setNextBefore] = useState<string | undefined>();
  const [usedMock, setUsedMock] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTimeline = useCallback(
    async (options?: { append?: boolean; before?: string }) => {
      const append = options?.append === true;
      try {
        setError(null);
        if (append) {
          setIsLoadingMore(true);
        } else {
          setIsLoading(true);
        }
        const filters: DeviceTimelineFilters = {
          limit: 20,
          before: options?.before,
          eventType: eventType || undefined,
          severity: severity || undefined,
        };
        const result = await getDeviceTimeline(deviceId, filters, token ?? undefined);
        setUsedMock(result.usedMock);
        setEvents((current) => (append ? [...current, ...result.timeline.events] : result.timeline.events));
        setNextBefore(result.timeline.nextBefore);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load device timeline.");
      } finally {
        setIsLoading(false);
        setIsLoadingMore(false);
      }
    },
    [deviceId, eventType, severity, token],
  );

  useEffect(() => {
    if (expanded) {
      void loadTimeline();
    }
  }, [expanded, loadTimeline]);

  const subtitle = useMemo(() => {
    if (!expanded) {
      return "Recent events, commands, OTA progress, and image activity.";
    }
    if (isLoading && events.length === 0) {
      return "Loading recent events.";
    }
    return events.length ? `${events.length} recent event${events.length === 1 ? "" : "s"}` : "No timeline events yet.";
  }, [events.length, expanded, isLoading]);

  const toggleRow = (eventId: string) => {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  };

  return (
    <Card>
      <Pressable accessibilityRole="button" onPress={() => setExpanded((value) => !value)} style={styles.header}>
        <View style={{ flex: 1, gap: 6 }}>
          <Text style={styles.title}>Diagnostics timeline</Text>
          <Text style={styles.subtitle}>{subtitle}</Text>
        </View>
        <View style={styles.headerRight}>
          {usedMock ? <Text style={styles.mockBadge}>Mock</Text> : null}
          <Text style={styles.expandText}>{expanded ? "Hide" : "Show"}</Text>
        </View>
      </Pressable>

      {!expanded ? null : (
        <>
          <FilterRow options={EVENT_FILTERS} value={eventType} onChange={setEventType} />
          <FilterRow options={SEVERITY_FILTERS} value={severity} onChange={setSeverity} />

          {error ? <Text style={styles.errorText}>{error}</Text> : null}
          {isLoading && events.length === 0 ? <Text style={styles.statusText}>Loading timeline...</Text> : null}
          {!isLoading && events.length === 0 ? (
            <EmptyState title="No timeline events" message="Heartbeat, command, OTA, image, and diagnostics events will appear here." />
          ) : null}

          <View style={styles.list}>
            {events.map((event) => (
              <TimelineRow
                key={event.id}
                event={event}
                expanded={expandedIds.has(event.id)}
                onPress={() => toggleRow(event.id)}
              />
            ))}
          </View>

          {nextBefore ? (
            <Pressable
              accessibilityRole="button"
              disabled={isLoading || isLoadingMore}
              onPress={() => void loadTimeline({ append: true, before: nextBefore })}
              style={[styles.loadMoreButton, isLoadingMore ? styles.disabledButton : null]}
            >
              <Text style={styles.loadMoreText}>{isLoadingMore ? "Loading..." : "Load older events"}</Text>
            </Pressable>
          ) : null}
        </>
      )}
    </Card>
  );
}

function FilterRow({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: string }[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterRow}>
      {options.map((option) => {
        const active = option.value === value;
        return (
          <Pressable
            accessibilityRole="button"
            key={`${option.label}-${option.value}`}
            onPress={() => onChange(option.value)}
            style={[styles.filterChip, active ? styles.filterChipActive : null]}
          >
            <Text style={[styles.filterText, active ? styles.filterTextActive : null]}>{option.label}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

function TimelineRow({
  event,
  expanded,
  onPress,
}: {
  event: DeviceTimelineEvent;
  expanded: boolean;
  onPress: () => void;
}) {
  const tone = severityTone(event.severity);
  const detail = removeUndefined({
    event_type: event.eventType,
    severity: event.severity,
    occurred_at: event.occurredAt,
    hardware_device_id: event.hardwareDeviceId,
    node_role: event.nodeRole,
    correlation_id: event.correlationId,
    code: event.code,
    message: event.message,
    data: event.data,
  });

  return (
    <View style={[styles.row, rowToneStyles[tone]]}>
      <Pressable accessibilityRole="button" onPress={onPress} style={styles.rowButton}>
        <View style={[styles.dot, dotToneStyles[tone]]} />
        <View style={styles.rowContent}>
          <View style={styles.summaryLine}>
            <Text style={styles.summary}>{event.summary}</Text>
            <Text style={[styles.severity, severityTextStyles[tone]]}>{formatLabel(event.severity)}</Text>
          </View>
          <Text style={styles.meta}>
            {formatTimestamp(event.occurredAt)}
            {event.nodeRole ? ` | ${event.nodeRole}` : ""}
          </Text>
          {event.hardwareDeviceId ? <Text style={styles.meta}>{event.hardwareDeviceId}</Text> : null}
          {event.correlationId ? <Text style={styles.correlation}>Correlation {event.correlationId}</Text> : null}
        </View>
      </Pressable>
      {expanded ? <Text selectable style={styles.details}>{JSON.stringify(detail, null, 2)}</Text> : null}
    </View>
  );
}

function severityTone(severity: string): "info" | "warning" | "critical" {
  const normalized = severity.toLowerCase();
  if (normalized === "critical" || normalized === "error") {
    return "critical";
  }
  if (normalized === "warning") {
    return "warning";
  }
  return "info";
}

function formatLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

function removeUndefined(input: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(input).filter(([, value]) => value !== undefined));
}

const styles = StyleSheet.create({
  header: { flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.md },
  headerRight: { alignItems: "flex-end", gap: theme.spacing.sm },
  title: { fontSize: theme.typography.sectionTitle, fontWeight: "800", color: theme.colors.textPrimary },
  subtitle: { fontSize: theme.typography.body, color: theme.colors.textSecondary, lineHeight: 20 },
  expandText: { fontSize: theme.typography.meta, fontWeight: "700", color: theme.colors.accent },
  mockBadge: {
    backgroundColor: theme.colors.mockSoft,
    borderRadius: theme.radii.pill,
    color: theme.colors.mock,
    fontSize: theme.typography.caption,
    fontWeight: "700",
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  filterRow: { gap: theme.spacing.sm, paddingVertical: 2 },
  filterChip: {
    borderRadius: theme.radii.pill,
    borderWidth: 1,
    borderColor: theme.colors.border,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  filterChipActive: {
    backgroundColor: theme.colors.accentSoft,
    borderColor: theme.colors.accent,
  },
  filterText: { color: theme.colors.textSecondary, fontSize: theme.typography.meta, fontWeight: "700" },
  filterTextActive: { color: theme.colors.accent },
  statusText: { color: theme.colors.textSecondary, fontSize: theme.typography.body },
  errorText: {
    backgroundColor: theme.colors.dangerSoft,
    borderRadius: theme.radii.md,
    color: theme.colors.danger,
    fontSize: theme.typography.body,
    padding: theme.spacing.md,
  },
  list: { gap: theme.spacing.md },
  row: {
    borderRadius: theme.radii.md,
    borderWidth: 1,
    padding: theme.spacing.md,
  },
  rowButton: { flexDirection: "row", gap: theme.spacing.md, alignItems: "flex-start" },
  rowContent: { flex: 1, gap: 5 },
  summaryLine: { flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" },
  summary: { flex: 1, color: theme.colors.textPrimary, fontSize: theme.typography.body, fontWeight: "800" },
  severity: { fontSize: theme.typography.caption, fontWeight: "800" },
  meta: { color: theme.colors.textSecondary, fontSize: theme.typography.meta },
  correlation: { color: theme.colors.textMuted, fontSize: theme.typography.caption, fontWeight: "700" },
  dot: { borderRadius: 5, height: 10, marginTop: 4, width: 10 },
  details: {
    backgroundColor: theme.colors.surfaceInset,
    borderRadius: theme.radii.md,
    color: theme.colors.textSecondary,
    fontFamily: "Courier",
    fontSize: theme.typography.caption,
    lineHeight: 17,
    marginTop: theme.spacing.md,
    padding: theme.spacing.md,
  },
  loadMoreButton: {
    alignItems: "center",
    borderColor: theme.colors.border,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    padding: theme.spacing.md,
  },
  disabledButton: { opacity: 0.6 },
  loadMoreText: { color: theme.colors.accent, fontSize: theme.typography.body, fontWeight: "800" },
});

const rowToneStyles = StyleSheet.create({
  info: { backgroundColor: theme.colors.surfaceMuted, borderColor: theme.colors.borderSoft },
  warning: { backgroundColor: theme.colors.warningSoft, borderColor: theme.colors.warningSoft },
  critical: { backgroundColor: theme.colors.dangerSoft, borderColor: theme.colors.dangerSoft },
});

const dotToneStyles = StyleSheet.create({
  info: { backgroundColor: theme.colors.accent },
  warning: { backgroundColor: theme.colors.warning },
  critical: { backgroundColor: theme.colors.danger },
});

const severityTextStyles = StyleSheet.create({
  info: { color: theme.colors.accent },
  warning: { color: theme.colors.warning },
  critical: { color: theme.colors.danger },
});
