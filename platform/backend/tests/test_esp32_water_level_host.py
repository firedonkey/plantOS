import shutil
import subprocess
from pathlib import Path


def test_esp32_water_level_sensor_host(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    test_src = repo_root / "device/esp32/tests_host/test_water_level_sensor.cpp"
    sensor_src = repo_root / "device/esp32/src/sensors/water_level_sensor.cpp"

    assert test_src.exists(), f"missing host test source: {test_src}"
    assert sensor_src.exists(), f"missing water-level sensor source: {sensor_src}"

    clang = shutil.which("clang++")
    assert clang, "clang++ is required to compile the ESP32 water-level host test"

    sdk_path = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
    output_binary = tmp_path / "test_water_level_sensor"
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
        str(repo_root / "device/esp32/include"),
        str(test_src),
        str(sensor_src),
        "-o",
        str(output_binary),
    ]

    subprocess.run(compile_cmd, check=True, cwd=repo_root)
    subprocess.run([str(output_binary)], check=True, cwd=repo_root)


def test_esp32_water_level_pin_ownership_and_removed_onewire_paths():
    repo_root = Path(__file__).resolve().parents[3]
    config = (repo_root / "device/esp32/include/config.h").read_text(encoding="utf-8")
    platformio = (repo_root / "device/esp32/platformio.ini").read_text(encoding="utf-8")
    main = (repo_root / "device/esp32/src/main.cpp").read_text(encoding="utf-8")

    assert "#define WATER_LEVEL_TOP_GPIO 4" in config
    assert "#define WATER_LEVEL_MIDDLE_GPIO 5" in config
    assert "#define WATER_LEVEL_BOTTOM_GPIO 6" in config
    assert "#define WATER_LEVEL_TOP_TOUCH_CHANNEL 4" in config
    assert "#define WATER_LEVEL_MIDDLE_TOUCH_CHANNEL 5" in config
    assert "#define WATER_LEVEL_BOTTOM_TOUCH_CHANNEL 6" in config

    assert "PIN_WATER_LEVEL_TOUCH" not in config
    assert "PIN_WATER_TEMPERATURE_ONEWIRE" not in config
    assert "PIN_DHT22_DATA" not in config
    assert "WaterTemperatureSensor" not in main
    assert "Dht22Sensor" not in main
    assert "DS18B20" not in main
    assert "OneWire" not in platformio
    assert "DallasTemperature" not in platformio
