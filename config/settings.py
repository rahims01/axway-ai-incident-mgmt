from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_debug: bool = False

    # Azure OpenAI — leave blank to use mock LLM
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment_gpt4o: str = "gpt-4o"
    azure_openai_deployment_mini: str = "gpt-4o-mini"
    azure_openai_api_version: str = "2024-12-01-preview"

    # Axway SecureTransport
    mock_axway: bool = True
    axway_admin_url: str = "https://axway-host:444"
    axway_admin_user: str = "admin"
    axway_admin_password: str = ""
    axway_log_path: str = "/opt/axway/SecureTransport/var/log"

    # Database
    database_url: str = "sqlite:///./axway_aiops.db"

    # Notifications
    slack_bot_token: str = ""
    slack_alert_channel: str = "#mft-alerts"
    slack_approval_channel: str = "#mft-ops"
    teams_webhook_url: str = ""

    # ServiceNow
    servicenow_url: str = ""
    servicenow_user: str = ""
    servicenow_password: str = ""

    # Thresholds
    cert_expiry_warn_days: int = 30
    failure_rate_threshold: int = 3
    queue_depth_warn: int = 500
    jvm_heap_warn_pct: int = 85
    disk_warn_pct: int = 80
    auto_fix_confidence_threshold: int = 85

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def mock_llm(self) -> bool:
        return not bool(self.azure_openai_api_key)

    @property
    def slack_enabled(self) -> bool:
        return bool(self.slack_bot_token)

    @property
    def teams_enabled(self) -> bool:
        return bool(self.teams_webhook_url)

    @property
    def servicenow_enabled(self) -> bool:
        return bool(self.servicenow_url and self.servicenow_user)


settings = Settings()
