from pydantic_settings import BaseSettings, SettingsConfigDict

JWT_ALGORITHM = "HS256"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./app.db"
    secret_key: str = "degistirin-guvenli-bir-anahtar-kullanin"
    access_token_expire_minutes: int = 60

    # CORS: virgülle ayrılmış origin listesi
    # Örnek: "https://app.example.com,http://localhost:5173"
    cors_origins: str = "http://localhost:5173"

    groq_api_key: str = ""
    lunch_latitude: float = 39.9564292
    lunch_longitude: float = 32.8526627

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
