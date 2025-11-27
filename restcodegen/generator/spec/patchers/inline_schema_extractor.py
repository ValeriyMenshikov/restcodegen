from __future__ import annotations

import copy
from typing import Any


class InlineSchemaExtractor:
    """Выносит inline-схемы из paths в components.schemas."""

    def __init__(self) -> None:
        self.swagger_scheme: dict[str, Any] = {}
        self.processed_schemas: set[str] = set()

    def patch(self, swagger_scheme: dict[str, Any]) -> dict[str, Any]:
        self.swagger_scheme = copy.deepcopy(swagger_scheme)
        self._ensure_components_exist()
        self._extract_all_schemas()
        return self.swagger_scheme

    def _ensure_components_exist(self) -> None:
        self.swagger_scheme.setdefault("components", {})
        self.swagger_scheme["components"].setdefault("schemas", {})

    def _extract_all_schemas(self) -> None:
        self._extract_inline_schemas_from_paths()
        self._process_component_schemas()

    def _process_component_schemas(self) -> None:
        schemas = self.swagger_scheme.get("components", {}).get("schemas", {})
        self.processed_schemas = set()

        while True:
            schemas_to_process = set(schemas.keys()) - self.processed_schemas
            if not schemas_to_process:
                break

            for schema_name in schemas_to_process:
                schema = schemas[schema_name]
                self._process_schema(schema, schema_name)
                self.processed_schemas.add(schema_name)

    def _extract_inline_schemas_from_paths(self) -> None:
        for path, methods in self.swagger_scheme.get("paths", {}).items():
            for method_name, method in methods.items():
                operation_id = method.get("operationId", f"{method_name}_{path.replace('/', '_')}")
                self._process_request_body(method, operation_id)
                self._process_responses(method, operation_id)
                self._process_parameters(method, operation_id)

    def _process_request_body(self, method: dict[str, Any], operation_id: str) -> None:
        if "requestBody" not in method or "content" not in method["requestBody"]:
            return

        for _, content in method["requestBody"]["content"].items():
            if "schema" not in content:
                continue

            schema = content["schema"]
            if "$ref" in schema:
                continue

            schema_name = f"{operation_id}_request_body"
            self.swagger_scheme["components"]["schemas"][schema_name] = schema
            content["schema"] = {"$ref": f"#/components/schemas/{schema_name}"}
            self._process_schema(schema, schema_name)

    def _process_responses(self, method: dict[str, Any], operation_id: str) -> None:
        if "responses" not in method:
            return

        for status_code, response in method["responses"].items():
            if "content" not in response:
                continue

            for _, content in response["content"].items():
                if "schema" not in content:
                    continue

                schema = content["schema"]
                if "$ref" in schema:
                    continue

                schema_name = f"{operation_id}_response_{status_code}"
                self.swagger_scheme["components"]["schemas"][schema_name] = schema
                content["schema"] = {"$ref": f"#/components/schemas/{schema_name}"}
                self._process_schema(schema, schema_name)

    def _process_parameters(self, method: dict[str, Any], operation_id: str) -> None:
        if "parameters" not in method:
            return

        for i, param in enumerate(method["parameters"]):
            if "schema" not in param:
                continue

            schema = param["schema"]
            if "$ref" in schema or schema.get("type") != "object":
                continue

            schema_name = f"{operation_id}_param_{param.get('name', i)}"
            self.swagger_scheme["components"]["schemas"][schema_name] = schema
            param["schema"] = {"$ref": f"#/components/schemas/{schema_name}"}
            self._process_schema(schema, schema_name)

    def _process_schema(self, schema: dict[str, Any], schema_name: str) -> None:
        self._process_combined_schemas(schema, schema_name)
        self._process_object_properties(schema, schema_name)
        self._process_array_schema(schema, schema_name)

    def _process_combined_schemas(self, schema: dict[str, Any], schema_name: str) -> None:
        for combiner in ["allOf", "oneOf", "anyOf"]:
            if combiner not in schema:
                continue

            for i, sub_schema in enumerate(schema[combiner]):
                if "$ref" in sub_schema or sub_schema.get("type") != "object":
                    continue

                sub_schema_name = f"{schema_name}_{combiner}_{i}"
                self.swagger_scheme["components"]["schemas"][sub_schema_name] = sub_schema
                schema[combiner][i] = {"$ref": f"#/components/schemas/{sub_schema_name}"}
                self._process_schema(sub_schema, sub_schema_name)

    def _process_object_properties(self, schema: dict[str, Any], schema_name: str) -> None:
        if schema.get("type") != "object" or "properties" not in schema:
            return

        for prop_name, prop_schema in schema["properties"].items():
            if "$ref" in prop_schema:
                continue

            if prop_schema.get("type") == "object" and "properties" in prop_schema:
                nested_schema_name = f"{schema_name}_{prop_name}"
                self.swagger_scheme["components"]["schemas"][nested_schema_name] = prop_schema
                schema["properties"][prop_name] = {"$ref": f"#/components/schemas/{nested_schema_name}"}
                self._process_schema(prop_schema, nested_schema_name)
            elif prop_schema.get("type") == "array" and "items" in prop_schema:
                self._process_array_items(prop_schema, f"{schema_name}_{prop_name}")

    def _process_array_schema(self, schema: dict[str, Any], schema_name: str) -> None:
        if schema.get("type") == "array" and "items" in schema:
            self._process_array_items(schema, schema_name)

    def _process_array_items(self, array_schema: dict[str, Any], schema_name: str) -> None:
        items_schema = array_schema["items"]
        if "$ref" in items_schema:
            return

        needs_extraction = (items_schema.get("type") == "object" and "properties" in items_schema) or any(
            combiner in items_schema for combiner in ["allOf", "oneOf", "anyOf"]
        )

        if needs_extraction:
            items_schema_name = f"{schema_name}_item"
            self.swagger_scheme["components"]["schemas"][items_schema_name] = items_schema
            array_schema["items"] = {"$ref": f"#/components/schemas/{items_schema_name}"}
            self._process_schema(items_schema, items_schema_name)
