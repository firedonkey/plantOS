import { DeviceCommand } from "@/types";

type CommandActivityPanelProps = {
  commands: DeviceCommand[];
};

export function CommandActivityPanel({ commands }: CommandActivityPanelProps) {
  return (
    <div className="card stack-form">
      <div className="section-header">
        <div>
          <h3>Command activity</h3>
          <p className="subtitle">Recent light and pump commands from the shared backend command history.</p>
        </div>
      </div>

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
    </div>
  );
}

function formatAction(action: DeviceCommand["action"]): string {
  switch (action) {
    case "light_on":
      return "Light on";
    case "light_off":
      return "Light off";
    case "pump_run":
      return "Pump run";
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
