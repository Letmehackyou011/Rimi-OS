from config.settings import Settings, settings, validate_llm_config


def test_config_settings_reexports_root_settings():
    assert isinstance(settings, Settings)
    assert isinstance(settings.ALLOWED_ORIGINS, list)


def test_settings_load_environment_values(monkeypatch):
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv(
        "ALLOWED_ORIGINS", "https://example.com, https://api.example.com"
    )

    configured = Settings()

    assert configured.DEBUG is False
    assert configured.PORT == 9000
    assert configured.ALLOWED_ORIGINS == [
        "https://example.com",
        "https://api.example.com",
    ]


def test_validate_llm_config_requires_provider_key():
    assert validate_llm_config(Settings(ACTIVE_LLM="ollama"))
    assert not validate_llm_config(Settings(ACTIVE_LLM="gemini"))
    assert validate_llm_config(
        Settings(ACTIVE_LLM="gemini", GEMINI_API_KEY="configured")
    )
    assert not validate_llm_config(Settings(ACTIVE_LLM="unsupported"))
