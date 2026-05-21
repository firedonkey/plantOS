from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("ota_release.py")
SPEC = importlib.util.spec_from_file_location("ota_release", SCRIPT_PATH)
assert SPEC is not None
ota_release = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["ota_release"] = ota_release
SPEC.loader.exec_module(ota_release)


class OtaReleaseScriptTest(unittest.TestCase):
    def test_gcs_artifact_uri_normalizes_bucket_and_prefix(self) -> None:
        self.assertEqual(
            ota_release.gcs_artifact_uri("gs://plantlab-images-garylu/", "/firmware/", "master-0.1.5-gcp.bin"),
            "gs://plantlab-images-garylu/firmware/master-0.1.5-gcp.bin",
        )
        self.assertEqual(
            ota_release.gcs_artifact_uri("plantlab-images-garylu", "", "camera-0.1.5-gcp.bin"),
            "gs://plantlab-images-garylu/camera-0.1.5-gcp.bin",
        )

    def test_publish_gcp_job_uses_backend_cli_and_gcs_artifact(self) -> None:
        target = ota_release.TARGETS["master"]
        command = ota_release.gcp_publish_job_command(
            job_name="plantlab-firmware-release-publish",
            image="us-central1-docker.pkg.dev/demo/plantlab-repo/plantlab-api:test",
            project_id="plantlab-493805",
            region="us-central1",
            service_account="plantlab-run-sa@plantlab-493805.iam.gserviceaccount.com",
            cloud_sql_connection_name="plantlab-493805:us-central1:plantlab",
            db_name="plantlab",
            db_user="plantlab_user",
            release_id="master-0.1.5-gcp",
            target=target,
            version="0.1.5",
            version_code=1005,
            min_current_version=None,
            artifact_path="gs://plantlab-images-garylu/firmware/master-0.1.5-gcp.bin",
            artifact_size=123456,
            checksum="a" * 64,
        )
        rendered = " ".join(command)

        self.assertIn("app.ops.publish_firmware_release", rendered)
        self.assertIn("--set-cloudsql-instances", command)
        self.assertIn("plantlab-493805:us-central1:plantlab", command)
        self.assertIn("gs://plantlab-images-garylu/firmware/master-0.1.5-gcp.bin", rendered)
        self.assertIn("APP_SECRET_KEY=app-secret-key:latest", rendered)
        self.assertIn("DB_PASSWORD=db-password:latest", rendered)


if __name__ == "__main__":
    unittest.main()
