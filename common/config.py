"""
Configuration management for the application.
"""
import os
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class DatabaseConfig(BaseSettings):
    """Database connection configuration."""

    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=3306, env="DB_PORT")
    user: str = Field(default="root", env="DB_USER")
    password: str = Field(default="", env="DB_PASSWORD")
    database: str = Field(default="nexus", env="DB_NAME")
    url: Optional[str] = Field(default=None, env="DATABASE_URL")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Override with environment variables directly
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_name = os.getenv('DB_NAME')

        if db_user:
            self.user = db_user
        if db_password:
            self.password = db_password
        if db_name:
            self.database = db_name

    class Config:
        env_prefix = ""
        case_sensitive = False


class OpenAIConfig(BaseSettings):
    """OpenAI API configuration."""

    api_key: str = Field(default="", env="OPENAI_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-large", env="OPENAI_EMBEDDING_MODEL")
    completion_model: str = Field(default="gpt-4o", env="OPENAI_COMPLETION_MODEL")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Override with environment variables directly
        openai_api_key = os.getenv('OPENAI_API_KEY')
        embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL')
        completion_model = os.getenv('OPENAI_COMPLETION_MODEL')

        if openai_api_key:
            self.api_key = openai_api_key
        if embedding_model:
            self.embedding_model = embedding_model
        if completion_model:
            self.completion_model = completion_model

    class Config:
        env_prefix = ""
        case_sensitive = False


class AppConfig(BaseSettings):
    """Application configuration."""

    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_prefix = ""
        case_sensitive = False


class Config(BaseModel):
    """Main configuration container."""

    database: DatabaseConfig
    openai: OpenAIConfig
    app: AppConfig

    @classmethod
    def load(cls) -> "Config":
        """
        Load configuration from environment variables.

        Returns:
            Config: The loaded configuration.
        """
        return cls(
            database=DatabaseConfig(),
            openai=OpenAIConfig(),
            app=AppConfig(),
        )

    def get_database_config(self) -> DatabaseConfig:
        """
        Get database configuration.

        Returns:
            DatabaseConfig: The database configuration.
        """
        return self.database

    def get_openai_config(self) -> OpenAIConfig:
        """
        Get OpenAI API configuration.

        Returns:
            OpenAIConfig: The OpenAI configuration.
        """
        return self.openai

    def get_app_config(self) -> AppConfig:
        """
        Get application configuration.

        Returns:
            AppConfig: The application configuration.
        """
        return self.app


# Global configuration instance
config = Config.load()