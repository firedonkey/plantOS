import pytest
from sqlalchemy.exc import OperationalError

from app.services.devices import get_device_by_api_token


class FlakyTokenLookupSession:
    def __init__(self):
        self.scalar_calls = 0
        self.rollback_calls = 0

    def scalar(self, _statement):
        self.scalar_calls += 1
        if self.scalar_calls == 1:
            raise OperationalError(
                "SELECT devices WHERE api_token = ...",
                {},
                Exception("consuming input failed: server closed the connection unexpectedly"),
                connection_invalidated=True,
            )
        return "device"

    def rollback(self):
        self.rollback_calls += 1


class FailingTokenLookupSession:
    def __init__(self):
        self.scalar_calls = 0
        self.rollback_calls = 0

    def scalar(self, _statement):
        self.scalar_calls += 1
        raise OperationalError(
            "SELECT devices WHERE api_token = ...",
            {},
            Exception("permission denied for table devices"),
        )

    def rollback(self):
        self.rollback_calls += 1


def test_device_token_lookup_retries_once_after_stale_connection():
    session = FlakyTokenLookupSession()

    device = get_device_by_api_token(session, "token")

    assert device == "device"
    assert session.scalar_calls == 2
    assert session.rollback_calls == 1


def test_device_token_lookup_does_not_retry_non_transient_db_errors():
    session = FailingTokenLookupSession()

    with pytest.raises(OperationalError):
        get_device_by_api_token(session, "token")

    assert session.scalar_calls == 1
    assert session.rollback_calls == 0
