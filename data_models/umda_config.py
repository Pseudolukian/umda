from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class UMDAConfig(BaseModel):
    doc_input: Path
    doc_output: Path
    image_storage_output: Path = Field(default=Path("./out"))
    doc_ymls: list[str] = Field(default=[])
