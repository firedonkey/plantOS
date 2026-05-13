import shutil
import subprocess
from pathlib import Path


def test_esp32_ble_provisioning_payload_host_test(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    test_src = repo_root / "device/esp32/tests_host/test_ble_provisioning_payload.cpp"
    payload_src = repo_root / "device/esp32/src/provisioning/provisioning_payload.cpp"
    arduino_json = (
        repo_root
        / "device/esp32/.pio/libdeps/esp32-s3-devkitc-1/ArduinoJson/src"
    )

    assert test_src.exists(), f"missing host test source: {test_src}"
    assert payload_src.exists(), f"missing payload source: {payload_src}"
    assert (arduino_json / "ArduinoJson.h").exists(), (
        "missing ArduinoJson dependency; run "
        "`cd device/esp32 && pio run -e esp32-s3-devkitc-1` first"
    )

    clang = shutil.which("clang++")
    assert clang, "clang++ is required to compile the ESP32 BLE provisioning host test"

    sdk_path = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    output_binary = tmp_path / "test_ble_provisioning_payload"
    compile_cmd = [
        clang,
        "-std=c++17",
        "-isysroot",
        sdk_path,
        "-I",
        f"{sdk_path}/usr/include/c++/v1",
        "-I",
        str(repo_root / "device/esp32/src"),
        "-I",
        str(arduino_json),
        str(test_src),
        str(payload_src),
        "-o",
        str(output_binary),
    ]

    subprocess.run(compile_cmd, check=True, cwd=repo_root)
    subprocess.run([str(output_binary)], check=True, cwd=repo_root)
