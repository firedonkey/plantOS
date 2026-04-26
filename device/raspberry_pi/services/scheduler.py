import time


def run_forever(automation, interval_seconds: int) -> None:
    while True:
        record = automation.run_once()
        print(f"[automation] {record}")
        time.sleep(interval_seconds)
