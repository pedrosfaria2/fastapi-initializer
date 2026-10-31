"""Shared API dependencies."""

from typing import Annotated

from fastapi import Depends

from fastapi_initializr.core.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]
