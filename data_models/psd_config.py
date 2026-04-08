from __future__ import annotations

from pydantic import BaseModel


class PSDConfig(BaseModel):
    psd_path: str
    base_layer: str
    Frames: list[str] = []
    Focuses: list[str] = []
    Crops: list[str] = []
