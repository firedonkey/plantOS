from pathlib import Path

from flask import Flask, render_template, send_from_directory

from config import load_config
from services.logger import PlantLogger


config = load_config()
app = Flask(__name__, template_folder="dashboard/templates", static_folder="dashboard/static")
logger = PlantLogger(config["logging"])


@app.route("/")
def index():
    latest = logger.latest()
    image_dir = Path(config["camera"].get("image_dir", "data/images"))
    images = sorted(image_dir.glob("*.jpg"), reverse=True)[:6]
    return render_template(
        "index.html",
        app_name=config.get("app", {}).get("name", "Plant Dashboard"),
        latest=latest,
        images=[str(path) for path in images],
    )


@app.route("/data/images/<path:filename>")
def plant_image(filename):
    image_dir = Path(config["camera"].get("image_dir", "data/images"))
    return send_from_directory(image_dir, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
