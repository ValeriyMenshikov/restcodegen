import json


class SpecPatcher:
    @staticmethod
    def patch(swagger_scheme: dict) -> dict:
        """
        Patch swagger json file to avoid multi files gen.

        :param swagger_scheme: Swagger json
        """
        json_content = json.dumps(swagger_scheme)
        schemas = swagger_scheme.get("components", {}).get(
            "schemas", {}
        ) or swagger_scheme.get("definitions", {})
        schemas_to_patch = [schema for schema in schemas if "." in schema]

        for _, methods in swagger_scheme.get("paths", {}).items():
            for _, method in methods.items():
                for tag in method.get("tags", []):
                    if "." in tag:
                        schemas_to_patch.append(tag)

        for schema in schemas_to_patch:
            for text in [f'/{schema}"', f'"{schema}"']:
                json_content = json_content.replace(text, text.replace(".", ""))

        return json.loads(json_content)
