from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Budget Intelligence API"
    debug: bool = False
    db_path: str = str(Path(__file__).parent.parent / "data" / "budget.db")

    # Rate sync
    rate_source: str = "local_only"  # github | google_sheets | onedrive | local_only
    github_rates_url: str = ""
    github_cesta_url: str = ""
    google_sheet_id: str = ""

    # Narrative engine
    narrative_density: str = "normal"  # concise | normal | detailed

    # LLM (optional, Phase 5)
    llm_enabled: bool = False
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
