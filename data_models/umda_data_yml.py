from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class UMDAData(BaseModel):
    """Merged data from all YAML files connected via umda.yml routers.

    Accepts any top-level keys contributed by the connected YAMLs.
    """

    model_config = ConfigDict(extra="allow")

    def resolve(self, dot_path: str) -> Any:
        """Return a value by dot-notation path, e.g. 'media.screenshots.diagram'.

        Returns None if any key in the path is missing.
        """
        node: Any = self.model_dump()
        for key in dot_path.split("."):
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return None
        return node
