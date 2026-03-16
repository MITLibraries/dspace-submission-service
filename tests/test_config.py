from unittest.mock import patch

import pytest

from submitter.config import Config, configure_sentry

CONFIG = Config()


def test_config_env_var_access():
    assert CONFIG.workspace == "test"


def test_config_optional_env_var_access(monkeypatch):
    monkeypatch.delenv("DSPACE_TIMEOUT")
    assert CONFIG.dspace_timeout


def test_config_required_env_var_access(monkeypatch):
    monkeypatch.delenv("INPUT_QUEUE")
    with pytest.raises(OSError):  # noqa: PT011
        _ = CONFIG.input_queue


def test_config_configures_sentry_if_dsn_present(caplog, monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://1234567890@00000.ingest.sentry.io/123456")
    with patch("sentry_sdk.init") as mock_init:
        configure_sentry()
        mock_init.assert_called_once()
        assert (
            "Sentry DSN found, exceptions will be sent to Sentry with env=test"
            in caplog.text
        )


def test_config_doesnt_configure_sentry_if_dsn_not_present(caplog, monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    configure_sentry()
    assert "No Sentry DSN found, exceptions will not be sent to Sentry" in caplog.text
