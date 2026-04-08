import yaml
from pathlib import Path

from data_models.umda_data_yml import UMDAData
from data_models.umda_config import UMDAConfig


class YMLHandler:
    def __init__(self, umda_yml_file: Path = Path("./umda.yml")):
        self.umda_yml_file = Path(umda_yml_file)
        self.base_dir = self.umda_yml_file.parent

        umda_config = self._load_raw(self.umda_yml_file)
        self.config = UMDAConfig(**umda_config.get("config", {}))
        routers = umda_config.get("routers", {})

        merged: dict = {}
        for key, filename in routers.items():
            file_path = self.base_dir / filename
            merged.update(self._load_raw(file_path))

        self.data = UMDAData(**merged)

    def _load_yml(self, file_path: Path) -> UMDAData:
        return UMDAData(**self._load_raw(file_path))

    def _load_raw(self, file_path: Path) -> dict:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
