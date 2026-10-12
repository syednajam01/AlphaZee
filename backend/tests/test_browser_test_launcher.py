import os
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import start_browser_test


def test_launcher_refuses_development_database(tmp_path, monkeypatch):
    profile = tmp_path / 'unsafe.env'
    profile.write_text('APP_ENV=test\nTEST_CHECKOUT_ENABLED=true\n'
                       'DATABASE_URL=postgresql://u:p@localhost:5433/alphazee_dev\n'
                       'ADMIN_API_KEY=sample-only\n')
    monkeypatch.setattr('sys.argv', ['start_browser_test.py', '--env-file', str(profile)])
    launch = Mock()
    monkeypatch.setattr(start_browser_test.subprocess, 'run', launch)
    with pytest.raises(SystemExit) as error:
        start_browser_test.main()
    assert error.value.code == 2
    launch.assert_not_called()


def test_launcher_passes_isolated_configuration_only_to_child(tmp_path, monkeypatch):
    profile = tmp_path / 'safe.env'
    profile.write_text('APP_ENV=test\nTEST_CHECKOUT_ENABLED=true\n'
                       'DATABASE_URL=postgresql://u:p@localhost:5433/alphazee_browser_test\n'
                       'ADMIN_API_KEY=sample-only\n')
    monkeypatch.setattr('sys.argv', ['start_browser_test.py', '--env-file', str(profile)])
    before = dict(os.environ)
    launch = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(start_browser_test.subprocess, 'run', launch)
    with pytest.raises(SystemExit) as error:
        start_browser_test.main()
    assert error.value.code == 0
    command = launch.call_args.args[0]
    assert command[-4:] == ['--host', '127.0.0.1', '--port', '8001']
    assert launch.call_args.kwargs['env']['DATABASE_URL'].endswith('/alphazee_browser_test')
    assert dict(os.environ) == before
