from __future__ import annotations

import copy
import json
from typing import Any


class ComponentSchemaPatcher:
    """Удаляет точки из названий схем и тегов, обновляя все ссылки."""

    def patch(self, swagger_scheme: dict[str, Any]) -> dict[str, Any]:
        spec = copy.deepcopy(swagger_scheme)
        self._ensure_components_exist(spec)

        json_content = json.dumps(spec)
        for name in self._collect_names_with_dots(spec):
            clean_name = name.replace(".", "")
            for marker in (f'/{name}"', f'"{name}"'):
                json_content = json_content.replace(marker, marker.replace(name, clean_name))

        patched = json.loads(json_content)
        self._clean_tags(patched)
        return patched

    @staticmethod
    def _ensure_components_exist(spec: dict[str, Any]) -> None:
        spec.setdefault("components", {})
        spec["components"].setdefault("schemas", {})

    @staticmethod
    def _collect_names_with_dots(spec: dict[str, Any]) -> list[str]:
        schemas = spec.get("components", {}).get("schemas", {}) or spec.get("definitions", {})
        names = [name for name in schemas if "." in name]
        for path_item in spec.get("paths", {}).values():
            for operation in path_item.values():
                for tag in operation.get("tags", []):
                    if "." in tag:
                        names.append(tag)
        return names

    @staticmethod
    def _clean_tags(spec: dict[str, Any]) -> None:
        for path_item in spec.get("paths", {}).values():
            for operation in path_item.values():
                tags = operation.get("tags")
                if tags:
                    operation["tags"] = [tag.replace(".", "") for tag in tags]
