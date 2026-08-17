from pbx_admin import config


def test_env_bool(monkeypatch):
    monkeypatch.setenv("X_FLAG", "TRUE")
    assert config._env_bool("X_FLAG") is True
    monkeypatch.setenv("X_FLAG", "no")
    assert config._env_bool("X_FLAG") is False
    monkeypatch.delenv("X_FLAG", raising=False)
    assert config._env_bool("X_FLAG", default=True) is True
    assert config._env_bool("X_FLAG", default=False) is False


def test_env_int(monkeypatch):
    monkeypatch.setenv("X_NUM", "42")
    assert config._env_int("X_NUM", 1) == 42
    monkeypatch.setenv("X_NUM", "not-a-number")
    assert config._env_int("X_NUM", 7) == 7
    monkeypatch.delenv("X_NUM", raising=False)
    assert config._env_int("X_NUM", 9) == 9
