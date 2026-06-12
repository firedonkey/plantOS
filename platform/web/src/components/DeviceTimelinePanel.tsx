import { useCallback, useEffect, useMemo, useState } from "react";

import { DeviceTimelineFilters, getDeviceTimeline } from "@/api/devices";
import { useSession } from "@/hooks/useSession";
import { DeviceTimelineEvent } from "@/types";

const EVENT_TYPE_OPTIONS = [
  "HEARTBEAT_RECEIVED",
  "DIAGNOSTICS_RECEIVED",
  "COMMAND_QUEUED",
  "COMMAND_SENT",
  "COMMAND_ACKED",
  "COMMAND_COMPLETED",
  "COMMAND_FAILED",
  "COMMAND_TIMED_OUT",
  "COMMAND_REJECTED",
  "OTA_STARTED",
  "OTA_DOWNLOADING",
  "OTA_INSTALLING",
  "OTA_SUCCESS",
  "OTA_FAILED",
  "CAMERA_NODE_CONNECTED",
  "CAMERA_NODE_DISCONNECTED",
];

const SEVERITY_OPTIONS = ["info", "warning", "error", "critical"];
const NODE_ROLE_OPTIONS = ["master", "camera", "sensor", "actuator"];

type TimelineFilters = {
  eventType: string;
  severity: string;
  nodeRole: string;
  correlationId: string;
  search: string;
};

export function DeviceTimelinePanel({ deviceId }: { deviceId: string }) {
  const { getAccessToken, token } = useSession();
  const [events, setEvents] = useState<DeviceTimelineEvent[]>([]);
  const [nextBefore, setNextBefore] = useState<string | undefined>();
  const [usedMock, setUsedMock] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());
  const [filters, setFilters] = useState<TimelineFilters>({
    eventType: "",
    severity: "",
    nodeRole: "",
    correlationId: "",
    search: "",
  });

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
        const query: DeviceTimelineFilters = {
          limit: 30,
          before: options?.before,
          eventType: filters.eventType || undefined,
          severity: filters.severity || undefined,
          nodeRole: filters.nodeRole || undefined,
          correlationId: filters.correlationId.trim() || undefined,
        };
        const accessToken = await getAccessToken();
        const result = await getDeviceTimeline(deviceId, query, accessToken ?? undefined);
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
    [deviceId, filters.correlationId, filters.eventType, filters.nodeRole, filters.severity, getAccessToken, token],
  );

  useEffect(() => {
    void loadTimeline();
  }, [loadTimeline]);

  const visibleEvents = useMemo(() => {
    const searchText = filters.search.trim().toLowerCase();
    if (!searchText) {
      return events;
    }
    return events.filter((event) => {
      const haystack = [
        event.summary,
        event.eventType,
        event.severity,
        event.hardwareDeviceId,
        event.nodeRole,
        event.correlationId,
        event.code,
        event.message,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(searchText);
    });
  }, [events, filters.search]);

  const updateFilter = (key: keyof TimelineFilters, value: string) => {
    setFilters((current) => ({ ...current, [key]: value }));
  };

  const toggleExpanded = (eventId: string) => {
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
    <section className="card stack-form timeline-panel">
      <div className="section-header">
        <div>
          <h3>Recent activity</h3>
          <p className="subtitle">Readable device events first. Expand a row when support-level details are needed.</p>
        </div>
        <div className="header-actions">
          {usedMock ? <span className="chip chip-mock">Mock mode</span> : null}
          <span className="timeline-count">{visibleEvents.length} shown</span>
          <button className="secondary-button" disabled={isLoading || isLoadingMore} onClick={() => void loadTimeline()} type="button">
            {isLoading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      <div className="timeline-filters" aria-label="Timeline filters">
        <label className="timeline-filter">
          <span>Event</span>
          <select value={filters.eventType} onChange={(event) => updateFilter("eventType", event.currentTarget.value)}>
            <option value="">All events</option>
            {EVENT_TYPE_OPTIONS.map((eventType) => (
              <option key={eventType} value={eventType}>
                {formatLabel(eventType)}
              </option>
            ))}
          </select>
        </label>
        <label className="timeline-filter">
          <span>Severity</span>
          <select value={filters.severity} onChange={(event) => updateFilter("severity", event.currentTarget.value)}>
            <option value="">All severities</option>
            {SEVERITY_OPTIONS.map((severity) => (
              <option key={severity} value={severity}>
                {formatLabel(severity)}
              </option>
            ))}
          </select>
        </label>
        <label className="timeline-filter">
          <span>Node</span>
          <select value={filters.nodeRole} onChange={(event) => updateFilter("nodeRole", event.currentTarget.value)}>
            <option value="">All nodes</option>
            {NODE_ROLE_OPTIONS.map((nodeRole) => (
              <option key={nodeRole} value={nodeRole}>
                {formatLabel(nodeRole)}
              </option>
            ))}
          </select>
        </label>
        <label className="timeline-filter timeline-filter-wide">
          <span>Correlation</span>
          <input
            value={filters.correlationId}
            onChange={(event) => updateFilter("correlationId", event.currentTarget.value)}
            placeholder="command id"
          />
        </label>
        <label className="timeline-filter timeline-filter-wide">
          <span>Search</span>
          <input
            value={filters.search}
            onChange={(event) => updateFilter("search", event.currentTarget.value)}
            placeholder="event text"
          />
        </label>
      </div>

      {error ? <p className="status-banner status-banner-error">{error}</p> : null}
      {isLoading && events.length === 0 ? <p className="status-banner">Loading timeline...</p> : null}
      {!isLoading && visibleEvents.length === 0 ? (
        <p className="status-banner">No timeline events match the current filters.</p>
      ) : null}

      <div className="timeline-list">
        {visibleEvents.map((event) => (
          <TimelineEventRow
            key={event.id}
            event={event}
            expanded={expandedIds.has(event.id)}
            onToggle={() => toggleExpanded(event.id)}
          />
        ))}
      </div>

      {nextBefore ? (
        <button
          className="secondary-button timeline-load-more"
          disabled={isLoading || isLoadingMore}
          onClick={() => void loadTimeline({ append: true, before: nextBefore })}
          type="button"
        >
          {isLoadingMore ? "Loading..." : "Load older events"}
        </button>
      ) : null}
    </section>
  );
}

function TimelineEventRow({
  event,
  expanded,
  onToggle,
}: {
  event: DeviceTimelineEvent;
  expanded: boolean;
  onToggle: () => void;
}) {
  const tone = severityTone(event.severity);
  const category = eventCategory(event.eventType);
  const detail = {
    event_type: event.eventType,
    severity: event.severity,
    occurred_at: event.occurredAt,
    hardware_device_id: event.hardwareDeviceId,
    node_role: event.nodeRole,
    correlation_id: event.correlationId,
    code: event.code,
    message: event.message,
    data: event.data,
  };
  return (
    <article className={`timeline-row timeline-row-${tone} timeline-row-category-${category.key}`}>
      <button className="timeline-row-button" onClick={onToggle} type="button" aria-expanded={expanded}>
        <span className={`timeline-icon timeline-icon-${category.key}`} aria-hidden="true">{category.initial}</span>
        <span className="timeline-row-content">
          <span className="timeline-row-topline">
            <span className="timeline-event-label">{category.label}</span>
            <span className="timeline-event-time">{formatTimestamp(event.occurredAt)}</span>
          </span>
          <span className="timeline-summary">{event.summary}</span>
          <span className="timeline-meta">
            {event.nodeRole ? formatLabel(event.nodeRole) : "Device"}
            {event.correlationId ? <span className="timeline-correlation">Thread {shortCorrelation(event.correlationId)}</span> : null}
          </span>
        </span>
        <span className={`timeline-severity severity-token-${tone === "error" ? "critical" : tone}`}>{formatLabel(event.severity)}</span>
      </button>
      {expanded ? (
        <div className="timeline-details-shell">
          <div className="timeline-details-header">
            <strong>Event details</strong>
            <span>{event.hardwareDeviceId ?? "No hardware id"}</span>
          </div>
          <pre className="timeline-details">{JSON.stringify(removeUndefined(detail), null, 2)}</pre>
        </div>
      ) : null}
    </article>
  );
}

function severityTone(severity: string): "info" | "warning" | "error" | "critical" {
  const normalized = severity.toLowerCase();
  if (normalized === "critical") {
    return "critical";
  }
  if (normalized === "error") {
    return "error";
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

function eventCategory(eventType: string): { key: "heartbeat" | "command" | "ota" | "camera" | "image" | "health" | "system"; label: string; initial: string } {
  if (eventType.includes("COMMAND")) {
    return { key: "command", label: "Command", initial: "C" };
  }
  if (eventType.includes("OTA")) {
    return { key: "ota", label: "Update", initial: "U" };
  }
  if (eventType.includes("CAMERA")) {
    return { key: "camera", label: "Camera", initial: "M" };
  }
  if (eventType.includes("IMAGE")) {
    return { key: "image", label: "Image", initial: "I" };
  }
  if (eventType.includes("HEALTH") || eventType.includes("WIFI") || eventType.includes("DIAGNOSTICS")) {
    return { key: "health", label: "Health", initial: "H" };
  }
  if (eventType.includes("HEARTBEAT")) {
    return { key: "heartbeat", label: "Heartbeat", initial: "B" };
  }
  return { key: "system", label: "System", initial: "S" };
}

function shortCorrelation(value: string): string {
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 10)}...${value.slice(-4)}`;
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
