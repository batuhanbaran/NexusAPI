from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./app.db"
    secret_key: str = "degistirin-guvenli-bir-anahtar-kullanin"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"

    groq_api_key: str = ""
    lunch_latitude: float = 39.9564292
    lunch_longitude: float = 32.8526627


settings = Settings()
