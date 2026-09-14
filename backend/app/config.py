import base64
import hashlib
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_PORT: int = 8083
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    SECRET_KEY: str = "change-this-default-secret-key-in-production"
    DATABASE_URL: str = "sqlite+aiosqlite:////data/cloner.db"
    MAX_CONCURRENT_JOBS: int = 10
    LOG_LEVEL: str = "INFO"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    def get_encryption_key(self) -> bytes:
        """Derive a URL-safe 32-byte base64 key suitable for Fernet from SECRET_KEY."""
        # Hash SECRET_KEY using SHA-256 to ensure exact 32-byte length
        digest = hashlib.sha256(self.SECRET_KEY.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)


settings = Settings()
