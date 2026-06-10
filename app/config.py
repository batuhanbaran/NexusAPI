from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/nexusapi"
    secret_key: str = "degistirin-guvenli-bir-anahtar-kullanin"
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"


settings = Settings()
