"""Configuration must work regardless of the server's working directory."""

from app.config import PROJECT_ROOT, Settings


def test_env_locations_are_absolute():
    assert Settings.model_config["env_file"] == (
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / "apps/api/.env",
    )
    assert PROJECT_ROOT.is_absolute()


def test_shared_env_accepts_frontend_settings(tmp_path, monkeypatch):
    monkeypatch.delenv("WCL_CLIENT_ID", raising=False)
    env = tmp_path / ".env"
    env.write_text("WCL_CLIENT_ID=test-client\nNEXT_PUBLIC_API_URL=http://localhost:8000\n")
    settings = Settings(_env_file=env)
    assert settings.wcl_client_id == "test-client"
