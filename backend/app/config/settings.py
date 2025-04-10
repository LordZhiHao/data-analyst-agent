"""
Configuration settings for the Vanna SQL Agent.
Loads from environment variables with defaults.
"""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Settings(BaseSettings):
    """Application settings."""
    
    # API settings
    APP_NAME: str = "Vanna SQL Agent"
    API_V1_PREFIX: str = ""
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # CORS settings - avoid automatic list parsing by using a different name
    CORS_ORIGINS_STR: str = "*"
    
    # Vanna AI settings
    VANNA_API_KEY: str = os.getenv("VANNA_API_KEY", "your_vanna_api_key")
    
    # BigQuery settings
    BIGQUERY_CREDENTIALS_PATH: str = os.getenv(
        "BIGQUERY_CREDENTIALS_PATH", 
        "path/to/your/bigquery_credentials.json"
    )
    DEFAULT_DATASET: str = os.getenv("DEFAULT_DATASET", "")
    
    # Vector database settings
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./vector_db")

    # MongoDB settings
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb+srv://lozhihao15053:cCKcP3ioFZvB18dl@sql-agent-cluster.yb9rokx.mongodb.net/?retryWrites=true&w=majority&appName=sql-agent-cluster")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "sql-agent-project-v1")
    MONGO_COLLECTION_NAME: str = os.getenv("MONGO_COLLECTION_NAME", "sql-agent-cluster")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8",
        extra="ignore",
        # Map CORS_ORIGINS env var to our CORS_ORIGINS_STR field
        env_mapping={"CORS_ORIGINS": "CORS_ORIGINS_STR"}
    )
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Process CORS_ORIGINS string into a list."""
        if not self.CORS_ORIGINS_STR or self.CORS_ORIGINS_STR == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS_STR.split(",")]

# Create a global settings object
settings = Settings()

# Print debug info to verify correct loading
if os.getenv("DEBUG", "False").lower() in ("true", "1", "t"):
    print(f"Loaded CORS_ORIGINS: {settings.CORS_ORIGINS}")