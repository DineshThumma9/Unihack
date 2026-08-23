from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MISTRAL_API_KEY: str
    SERPER_API_KEY: str 
    # Model configs
    LLM_MODEL: str = "ministral-14b-2512"
    
    # URLs and Paths
    REDIS_URL: str = "redis://localhost:6379/0"
    FRONTEND_URL: str = "http://localhost:5173"
    
    UPLOADS_DIR: str = "uploads"
    OUTPUTS_DIR: str = "outputs"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()
