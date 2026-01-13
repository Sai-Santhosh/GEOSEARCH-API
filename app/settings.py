"""
Production-grade settings management with validation and environment-specific configuration.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation and documentation."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = Field(default="GeoSearch API", description="Application name")
    app_version: str = Field(default="2.0.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment"
    )
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    workers: int = Field(default=1, ge=1, le=32, description="Number of workers")
    
    # Database
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL with PostGIS"
    )
    db_pool_size: int = Field(default=10, ge=1, le=100, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, ge=0, le=100, description="Max overflow connections")
    db_pool_timeout: int = Field(default=30, ge=5, le=300, description="Pool timeout in seconds")
    db_pool_recycle: int = Field(default=1800, ge=60, description="Connection recycle time in seconds")
    
    # Redis
    redis_url: str = Field(
        ...,
        description="Redis connection URL"
    )
    redis_max_connections: int = Field(default=50, ge=1, le=500, description="Max Redis connections")
    
    # Caching
    cache_ttl_seconds: int = Field(default=60, ge=0, le=86400, description="Cache TTL in seconds")
    cache_enabled: bool = Field(default=True, description="Enable Redis caching")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, ge=1, description="Requests per window")
    rate_limit_window: int = Field(default=60, ge=1, description="Rate limit window in seconds")
    
    # Security
    cors_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins"
    )
    api_key_enabled: bool = Field(default=False, description="Enable API key authentication")
    api_keys: str = Field(default="", description="Comma-separated list of valid API keys")
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format"
    )
    
    # Geo settings
    default_radius_m: int = Field(default=1000, ge=50, le=50000, description="Default search radius")
    max_radius_m: int = Field(default=50000, ge=1000, le=100000, description="Maximum search radius")
    geohash_precision: int = Field(default=5, ge=1, le=12, description="Geohash precision level")
    
    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Validate CORS origins format."""
        if not v:
            return "*"
        return v
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @property
    def api_keys_list(self) -> list[str]:
        """Get API keys as a list."""
        if not self.api_keys:
            return []
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
