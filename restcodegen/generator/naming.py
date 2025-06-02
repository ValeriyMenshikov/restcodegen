import re
import builtins
import keyword
from datamodel_code_generator.reference import FieldNameResolver


class NamingUtils:
    @staticmethod
    def to_snake_case(string: str) -> str:
        string = string.replace(" ", "_").replace("/", "_").replace(".", "_")
        string = string.replace("{", "").replace("}", "")
        string = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", string)
        string = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", string)
        string = re.sub("&", "and", string)
        string = string.replace("-", "_").lower()
        string = string.strip("_") if len(string) > 1 else string
        return string

    @classmethod
    def to_camel_case(cls, string: str) -> str:
        return FieldNameResolver().get_valid_name(string, upper_camel=True)

    @classmethod
    def to_param_name(cls, string: str) -> str:
        snake = cls.to_snake_case(string)
        built_in_functions = set(dir(builtins)) | set(keyword.kwlist)
        if snake in built_in_functions:
            return snake + "_"
        return snake

    @classmethod
    def to_type_annotation(cls, string: str) -> str:
        basic_types = [
            "int",
            "str",
            "bool",
            "float",
            "list",
            "dict",
            "tuple",
            "set",
            "Any",
            "None",
            "bytes",
        ]
        if string in basic_types:
            return string
        if "[" in string and "]" in string:
            container, content = string.split("[", 1)
            content = content.rstrip("]")
            if container in basic_types:
                return f"{container}[{content}]"
            container = cls.to_camel_case(container)
            return f"{container}[{content}]"
        return cls.to_camel_case(string)
