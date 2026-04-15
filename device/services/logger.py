import csv
import json
from pathlib import Path


class PlantLogger:
    FIELDNAMES = [
        "timestamp",
        "temperature_c",
        "humidity_percent",
        "moisture_raw",
        "moisture_smoothed_raw",
        "moisture_percent",
        "light_on",
        "pump_event",
        "image_path",
        "errors",
    ]

    def __init__(self, config: dict):
        self.config = config
        self.log_dir = Path(config.get("log_dir", "data/logs"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_format = config.get("format", "csv").lower()
        self.log_path = self.log_dir / config.get("filename", "plant_log.csv")

    def log(self, record: dict) -> None:
        if self.log_format == "json":
            self._log_json(record)
        else:
            self._log_csv(record)

    def latest(self) -> dict | None:
        if not self.log_path.exists():
            return None
        if self.log_format == "json":
            return self._latest_json()
        return self._latest_csv()

    def _log_csv(self, record: dict) -> None:
        exists = self.log_path.exists()
        if exists and self._csv_header_changed():
            self._rewrite_csv_with_current_header()
        with self.log_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.FIELDNAMES)
            if not exists or self.log_path.stat().st_size == 0:
                writer.writeheader()
            writer.writerow({field: record.get(field, "") for field in self.FIELDNAMES})

    def _log_json(self, record: dict) -> None:
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def _latest_csv(self) -> dict | None:
        with self.log_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return self._clean_csv_row(rows[-1]) if rows else None

    def _csv_header_changed(self) -> bool:
        with self.log_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader, [])
        return header != self.FIELDNAMES

    def _rewrite_csv_with_current_header(self) -> None:
        with self.log_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [self._clean_csv_row(row) for row in reader]

        with self.log_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in self.FIELDNAMES})

    def _clean_csv_row(self, row: dict) -> dict:
        cleaned = {key: value for key, value in row.items() if key is not None}
        extra_values = row.get(None) or []
        missing_fields = [field for field in self.FIELDNAMES if field not in cleaned]
        for field, value in zip(missing_fields, extra_values):
            cleaned[field] = value
        return cleaned

    def _latest_json(self) -> dict | None:
        with self.log_path.open("r", encoding="utf-8") as handle:
            lines = [line.strip() for line in handle if line.strip()]
        return json.loads(lines[-1]) if lines else None
