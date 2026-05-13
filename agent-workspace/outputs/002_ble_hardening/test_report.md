# Test Report

## Attempt 1

### Detected test commands

#### pytest

`cwd=/Users/gary/plantOS`

`/Users/gary/plantOS/.venv/bin/python -m pytest platform/backend/tests`

#### stdout

```
============================= test session starts ==============================
platform darwin -- Python 3.14.3, pytest-8.3.4, pluggy-1.6.0
rootdir: /Users/gary/plantOS
plugins: anyio-4.13.0
collected 115 items

platform/backend/tests/test_auth.py .......                              [  6%]
platform/backend/tests/test_commands.py .........                        [ 13%]
platform/backend/tests/test_device_nodes.py ...                          [ 16%]
platform/backend/tests/test_device_nodes_api.py ..................       [ 32%]
platform/backend/tests/test_devices.py ................................. [ 60%]
                                                                         [ 60%]
platform/backend/tests/test_esp32_ble_provisioning_host.py .             [ 61%]
platform/backend/tests/test_hardware_api.py ......                       [ 66%]
platform/backend/tests/test_images.py ..........                         [ 75%]
platform/backend/tests/test_models.py .                                  [ 76%]
platform/backend/tests/test_platform_app.py ....                         [ 80%]
platform/backend/tests/test_readings.py .........                        [ 87%]
platform/backend/tests/test_settings.py ..............                   [100%]

=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/routing.py:233: 98 warnings
  /Users/gary/plantOS/.venv/lib/python3.14/site-packages/fastapi/routing.py:233: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    is_coroutine = asyncio.iscoroutinefunction(dependant.call)

.venv/lib/python3.14/site-packages/starlette/_utils.py:39: 102 warnings
platform/backend/tests/test_auth.py: 15 warnings
platform/backend/tests/test_commands.py: 16 warnings
platform/backend/tests/test_device_nodes_api.py: 36 warnings
platform/backend/tests/test_devices.py: 66 warnings
platform/backend/tests/test_hardware_api.py: 14 warnings
platform/backend/tests/test_images.py: 23 warnings
platform/backend/tests/test_platform_app.py: 8 warnings
platform/backend/tests/test_readings.py: 23 warnings
  /Users/gary/plantOS/.venv/lib/python3.14/site-packages/starlette/_utils.py:39: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    return asyncio.iscoroutinefunction(obj) or (callable(obj) and asyncio.iscoroutinefunction(obj.__call__))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 115 passed, 401 warnings in 2.76s =======================
```

Result: PASS

#### npm test (provision_backend)

`cwd=/Users/gary/plantOS/provision_backend`

`npm test`

#### stdout

```

> plantlab-provision-backend@0.1.0 test
> node --test

TAP version 13
# Subtest: attachDevUser preserves an existing trusted user
ok 1 - attachDevUser preserves an existing trusted user
  ---
  duration_ms: 1.079875
  type: 'test'
  ...
# Subtest: attachDevUser fills a dev user when no trusted user exists
ok 2 - attachDevUser fills a dev user when no trusted user exists
  ---
  duration_ms: 0.10475
  type: 'test'
  ...
1..2
# tests 2
# suites 0
# pass 2
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 56.862958
```

Result: PASS

## Attempt 2

### Detected test commands

#### pytest

`cwd=/Users/gary/plantOS`

`/Users/gary/plantOS/.venv/bin/python -m pytest platform/backend/tests`

#### stdout

```
============================= test session starts ==============================
platform darwin -- Python 3.14.3, pytest-8.3.4, pluggy-1.6.0
rootdir: /Users/gary/plantOS
plugins: anyio-4.13.0
collected 115 items

platform/backend/tests/test_auth.py .......                              [  6%]
platform/backend/tests/test_commands.py .........                        [ 13%]
platform/backend/tests/test_device_nodes.py ...                          [ 16%]
platform/backend/tests/test_device_nodes_api.py ..................       [ 32%]
platform/backend/tests/test_devices.py ................................. [ 60%]
                                                                         [ 60%]
platform/backend/tests/test_esp32_ble_provisioning_host.py .             [ 61%]
platform/backend/tests/test_hardware_api.py ......                       [ 66%]
platform/backend/tests/test_images.py ..........                         [ 75%]
platform/backend/tests/test_models.py .                                  [ 76%]
platform/backend/tests/test_platform_app.py ....                         [ 80%]
platform/backend/tests/test_readings.py .........                        [ 87%]
platform/backend/tests/test_settings.py ..............                   [100%]

=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/fastapi/routing.py:233: 98 warnings
  /Users/gary/plantOS/.venv/lib/python3.14/site-packages/fastapi/routing.py:233: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    is_coroutine = asyncio.iscoroutinefunction(dependant.call)

.venv/lib/python3.14/site-packages/starlette/_utils.py:39: 102 warnings
platform/backend/tests/test_auth.py: 15 warnings
platform/backend/tests/test_commands.py: 16 warnings
platform/backend/tests/test_device_nodes_api.py: 36 warnings
platform/backend/tests/test_devices.py: 66 warnings
platform/backend/tests/test_hardware_api.py: 14 warnings
platform/backend/tests/test_images.py: 23 warnings
platform/backend/tests/test_platform_app.py: 8 warnings
platform/backend/tests/test_readings.py: 23 warnings
  /Users/gary/plantOS/.venv/lib/python3.14/site-packages/starlette/_utils.py:39: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    return asyncio.iscoroutinefunction(obj) or (callable(obj) and asyncio.iscoroutinefunction(obj.__call__))

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 115 passed, 401 warnings in 3.11s =======================
```

Result: PASS

#### npm test (provision_backend)

`cwd=/Users/gary/plantOS/provision_backend`

`npm test`

#### stdout

```

> plantlab-provision-backend@0.1.0 test
> node --test

TAP version 13
# Subtest: attachDevUser preserves an existing trusted user
ok 1 - attachDevUser preserves an existing trusted user
  ---
  duration_ms: 1.353083
  type: 'test'
  ...
# Subtest: attachDevUser fills a dev user when no trusted user exists
ok 2 - attachDevUser fills a dev user when no trusted user exists
  ---
  duration_ms: 0.10425
  type: 'test'
  ...
1..2
# tests 2
# suites 0
# pass 2
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 60.250417
```

Result: PASS

