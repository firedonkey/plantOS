from datetime import datetime
from pathlib import Path
import subprocess


class USBCamera:
    def __init__(self, config: dict, mock_mode: bool = False):
        self.config = config
        camera_mock_mode = config.get("mock_mode")
        self.mock_mode = bool(camera_mock_mode) if camera_mock_mode is not None else mock_mode
        self.mock_mode = self.mock_mode or not config.get("enabled", True)
        self.image_dir = Path(config.get("image_dir", "data/images"))
        self.image_dir.mkdir(parents=True, exist_ok=True)

    def capture(self, overrides: dict | None = None) -> str | None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        image_path = self.image_dir / f"plant_{timestamp}.jpg"
        capture_config = dict(self.config)
        if overrides:
            capture_config.update(overrides)

        if self.mock_mode:
            print(f"[camera] mock capture skipped: {image_path}")
            return None

        try:
            import cv2

            camera = cv2.VideoCapture(int(capture_config.get("device_index", 0)))
            resolution = str(capture_config.get("resolution", "1280x720"))
            if "x" in resolution:
                try:
                    width, height = resolution.lower().split("x", 1)
                    camera.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
                    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
                except ValueError:
                    pass
            skip_frames = max(0, int(capture_config.get("skip_frames", 0)))
            for _ in range(skip_frames):
                camera.read()
            ok, frame = camera.read()
            camera.release()
            if not ok:
                raise RuntimeError("USB camera returned no frame")
            cv2.imwrite(str(image_path), frame)
            return str(image_path)
        except ModuleNotFoundError:
            return self._capture_with_fswebcam(image_path, capture_config)
        except Exception as exc:
            print(f"[camera] OpenCV capture failed: {exc}")
            return self._capture_with_fswebcam(image_path, capture_config)

    def _capture_with_fswebcam(self, image_path: Path, capture_config: dict) -> str | None:
        device_path = f"/dev/video{int(capture_config.get('device_index', 0))}"
        resolution = str(capture_config.get("resolution", "1280x720"))
        skip_frames = int(capture_config.get("skip_frames", 0))
        command = [
            "fswebcam",
            "-d",
            device_path,
            "-r",
            resolution,
            "--no-banner",
        ]
        if skip_frames > 0:
            command.extend(["--skip", str(skip_frames)])
        command.append(str(image_path))

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            return str(image_path)
        except FileNotFoundError:
            print("[camera] install fswebcam or python3-opencv to enable capture")
        except subprocess.CalledProcessError as exc:
            print(f"[camera] fswebcam capture failed: {exc.stderr.strip()}")
        return None
