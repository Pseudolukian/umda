from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class AdapterConfigSection(BaseModel):
    output_config_name: str
    options: dict[str, Any] = Field(default={})
    sections: dict[str, Path] = Field(default={})  # section_name -> file_path


class AdapterConfigMedia(BaseModel):
    media_storage_output: Path
    image_extantion: str = Field(default="webp")
    media_base_url: str = Field(default="")  # e.g. /media — used as URL prefix in MD links


class AdapterConfig(BaseModel):
    doc_output: Path
    mkdocs_path: Path
    config: AdapterConfigSection
    media: AdapterConfigMedia
    swap_list: Path | None = Field(default=None)

    model_config = {"extra": "allow"}


class UMDAConfig(BaseModel):
    doc_input: Path
    model_config = {"extra": "allow"}
