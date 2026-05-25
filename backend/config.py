from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str
    pinecone_api_key: str
    pinecone_index: str = "aura-faces"
    firebase_credentials_path: str = "firebase-credentials.json"
    firebase_storage_bucket: str = "aura-app.appspot.com"
    google_calendar_credentials_path: str = "calendar-credentials.json"

    class Config:
        env_file = ".env"


settings = Settings()
