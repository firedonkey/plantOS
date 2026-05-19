from __future__ import annotations

from types import SimpleNamespace

import conftest


def _pytest_config(rootpath):
    return SimpleNamespace(rootpath=rootpath)


def test_non_pi_hosts_ignore_raspberry_pi_test_collection(monkeypatch, tmp_path):
    monkeypatch.setattr(conftest, "_is_raspberry_pi_host", lambda: False)

    collection_path = tmp_path / "device" / "raspberry_pi" / "test_gpio.py"

    assert (
        conftest.pytest_ignore_collect(collection_path, _pytest_config(tmp_path))
        is True
    )


def test_non_pi_hosts_keep_non_raspberry_pi_collection(monkeypatch, tmp_path):
    monkeypatch.setattr(conftest, "_is_raspberry_pi_host", lambda: False)

    collection_path = tmp_path / "device" / "esp32" / "tests_host" / "test_api.py"

    assert (
        conftest.pytest_ignore_collect(collection_path, _pytest_config(tmp_path))
        is None
    )

def test_raspberry_pi_hosts_keep_raspberry_pi_collection(monkeypatch, tmp_path):
    monkeypatch.setattr(conftest, "_is_raspberry_pi_host", lambda: True)

    collection_path = tmp_path / "device" / "raspberry_pi" / "test_gpio.py"

    assert (
        conftest.pytest_ignore_collect(collection_path, _pytest_config(tmp_path))
        is None
    )
