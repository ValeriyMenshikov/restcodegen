from __future__ import annotations

from typing import Any, Iterable, Protocol

from restcodegen.generator.spec.patchers import ComponentSchemaPatcher, InlineSchemaExtractor


class SpecTransform(Protocol):
    def patch(self, spec: dict[str, Any]) -> dict[str, Any]:
        ...


class SpecNormalizer:
    def __init__(self, transforms: Iterable[SpecTransform] | None = None) -> None:
        default_transforms = (InlineSchemaExtractor(), ComponentSchemaPatcher())
        self._transforms = list(transforms or default_transforms)

    def add_transform(self, transform: SpecTransform) -> None:
        self._transforms.append(transform)

    def normalize(self, spec: dict[str, Any]) -> dict[str, Any]:
        if not spec:
            return {}

        normalized = spec
        for transform in self._transforms:
            normalized = transform.patch(normalized)
        return normalized
