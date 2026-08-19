
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str 
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    #groq key
    # GROQ_API_KEY: str

    model_config = SettingsConfigDict(
        env_file = ".env",
        extra = "ignore"
    )


# single shared instance 
settings = Settings()