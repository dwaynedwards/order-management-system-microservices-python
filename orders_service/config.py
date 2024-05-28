"""
Module that provides the configuration for the API
"""

from functools import lru_cache
from typing import Tuple, Type

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict


class Config(BaseSettings):
    """Envrionment Config"""

    DATABASE_URL: str

    model_config = SettingsConfigDict(case_sensitive=True, env_file_encoding="utf-8")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            dotenv_settings,
        )


@lru_cache
def get_config(filename: str):
    """Gets Config"""
    return Config(_env_file=filename)
