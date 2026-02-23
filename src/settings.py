from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL = "sqlite+aiosqlite:///./online_cinema.db"


settings = Settings()
