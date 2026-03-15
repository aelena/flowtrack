from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://flowtrack:flowtrack_secret@db:5432/flowtrack"
    api_key: str = "ft_dev_key_change_me"
    storage_path: str = "/app/storage"

    class Config:
        env_file = ".env"


settings = Settings()
