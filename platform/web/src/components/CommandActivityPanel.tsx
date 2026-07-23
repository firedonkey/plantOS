import { DeviceCommand } from "@/types";

type CommandActivityPanelProps = {
  commands: DeviceCommand[];
};

export function CommandActivityPanel({ commands }: CommandActivityPanelProps) {
  return (
    <details className="card stack-form collapsible-panel">
      <summary className="collapsible-summary">
        <div>
          <h3>Command activity</h3>
          <p className="subtitle">Recent grow LED and capture commands from the shared backend command history.</p>
        </div>
        <span className="chip chip-unknown">{commands.length}</span>
        <span className="collapsible-indicator" aria-hidden="true" />
      </summary>

      {!commands.length ? (
        <p className="subtitle">No recent commands yet. Command activity will appear here after you use the controls.</p>
      ) : (
        <div className="activity-list">
          {commands.map((command) => (
            <div className="activity-row" key={command.id}>
              <div>
                <strong>{formatAction(command.action)}</strong>
                <p className="meta-text">{new Date(command.createdAt).toLocaleString()}</p>
                {command.detail ? <p className="meta-text">{command.detail}</p> : null}
              </div>
              <span className={`chip chip-${chipTone(command.status)}`}>
                {formatStatus(command.status)}
              </span>
            </div>
          ))}
        </div>
      )}
    </details>
  );
}

function formatAction(action: DeviceCommand["action"]): string {
  switch (action) {
    case "light_on":
      return "Grow LED on";
    case "light_off":
      return "Grow LED off";
    case "light_intensity":
      return "Grow LED intensity";
    case "light_red_intensity":
      return "Grow LED red intensity";
    case "light_white_intensity":
      return "Grow LED white intensity";
    case "ambient_belt_color":
      return "Ambient LED belt color";
    case "ambient_belt_off":
      return "Ambient LED belt off";
    case "pump_run":
      return "Legacy command";
    case "capture_image":
      return "Capture image";
  }
}

function formatStatus(status: DeviceCommand["status"]): string {
  switch (status) {
    case "completed":
      return "Completed";
    case "pending":
      return "Pending";
    case "sent":
      return "Sent";
    case "in_progress":
      return "In progress";
    case "failed":
      return "Failed";
  }
}

function chipTone(status: DeviceCommand["status"]) {
  if (status === "completed") {
    return "online";
  }
  if (status === "failed") {
    return "offline";
  }
  return "unknown";
}
