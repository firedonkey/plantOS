import shutil
import subprocess
from pathlib import Path


def test_esp32_grow_light_controller_drives_red_and_white_channels(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    test_src = repo_root / "device/esp32/tests_host/test_light_controller.cpp"
    controller_src = repo_root / "device/esp32/src/actuators/light_controller.cpp"

    assert test_src.exists(), f"missing host test source: {test_src}"
    assert controller_src.exists(), f"missing grow-light controller source: {controller_src}"

    clang = shutil.which("clang++")
    assert clang, "clang++ is required to compile the ESP32 grow-light controller host test"

    sdk_path = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    (tmp_path / "Arduino.h").write_text(
        """
#pragma once

#define HIGH 1
#define LOW 0
#define OUTPUT 1

void pinMode(int pin, int mode);
void digitalWrite(int pin, int level);
void analogWrite(int pin, int duty);
""",
        encoding="utf-8",
    )

    output_binary = tmp_path / "test_light_controller"
    compile_cmd = [
        clang,
        "-std=c++17",
        "-isysroot",
        sdk_path,
        "-I",
        f"{sdk_path}/usr/include/c++/v1",
        "-I",
        str(tmp_path),
        "-I",
        str(repo_root / "device/esp32/src"),
        "-I",
        str(repo_root / "device/esp32/include"),
        str(test_src),
        str(controller_src),
        "-o",
        str(output_binary),
    ]

    subprocess.run(compile_cmd, check=True, cwd=repo_root)
    subprocess.run([str(output_binary)], check=True, cwd=repo_root)
