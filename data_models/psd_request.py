from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class PSDRequest(BaseModel):
    psd_path: Path | None
    base: str
    Focuses: list[str] = []
    Frames: list[str] = []
    Crops: list[str] = []
