from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, render_template, send_from_directory

from config import load_config
from services.logger import PlantLogger


config = load_config()
app = Flask(__name__, template_folder="dashboard/templates", static_folder="dashboard/static")
logger = PlantLogger(config["logging"])


@app.route("/")
def index():
    latest = _prepare_status(logger.latest())
    image_dir = Path(config["camera"].get("image_dir", "data/images"))
    images = sorted(image_dir.glob("*.jpg"), reverse=True)[:6]
    mock_images = _mock_growth_images()
    return render_template(
        "index.html",
        app_name=config.get("app", {}).get("name", "Plant Dashboard"),
        latest=latest,
        images=[str(path) for path in images],
        mock_images=mock_images,
        loop_interval=config.get("app", {}).get("loop_interval_seconds", 60),
    )


@app.route("/api/status")
def api_status():
    return jsonify(_prepare_status(logger.latest()))


@app.route("/data/images/<path:filename>")
def plant_image(filename):
    image_dir = Path(config["camera"].get("image_dir", "data/images"))
    return send_from_directory(image_dir, filename)


def _prepare_status(record: dict | None) -> dict | None:
    if not record:
        return None

    prepared = dict(record)
    prepared["display_timestamp"] = _format_timestamp(record.get("timestamp"))
    prepared["light_label"] = "On" if _is_truthy(record.get("light_on")) else "Off"
    prepared["pump_label"] = _format_pump_event(record.get("pump_event"))
    prepared["health_label"] = "Attention" if record.get("errors") else "Healthy"
    prepared["health_tone"] = "warning" if record.get("errors") else "good"
    prepared["moisture_tone"] = _moisture_tone(record.get("moisture_percent"))
    return prepared


def _format_timestamp(value) -> str:
    if not value:
        return "No reading yet"
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return str(value)
    return parsed.strftime("%b %-d, %-I:%M %p")


def _format_pump_event(value) -> str:
    labels = {
        "not_needed": "Not needed",
        "skipped_no_moisture_reading": "No moisture reading",
        "skipped_cooldown": "Cooling down",
    }
    if not value:
        return "No event"
    value = str(value)
    if value.startswith("ran_"):
        return f"Ran {value.removeprefix('ran_')}"
    return labels.get(value, value.replace("_", " ").title())


def _is_truthy(value) -> bool:
    return value is True or str(value).lower() in {"true", "1", "yes", "on"}


def _moisture_tone(value) -> str:
    try:
        moisture = float(value)
    except (TypeError, ValueError):
        return "muted"
    if moisture < float(config["automation"].get("moisture_threshold_percent", 35)):
        return "warning"
    return "good"


def _mock_growth_images() -> list[dict]:
    return [
        {
            "src": "/static/mock/rose-01-seedling.jpg",
            "label": "Seedling",
        },
        {
            "src": "/static/mock/rose-02-young-leaves.jpg",
            "label": "New leaves",
        },
        {
            "src": "/static/mock/rose-03-bud.jpg",
            "label": "Bud",
        },
        {
            "src": "/static/mock/rose-04-bloom.jpg",
            "label": "Opening",
        },
        {
            "src": "/static/mock/rose-05-bloom.jpg",
            "label": "Bloom",
        },
    ]


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
