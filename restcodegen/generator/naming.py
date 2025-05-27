"""Utilities for consistent naming conventions across generated code."""

import re
import builtins
import keyword
from typing import Any


class NamingUtils:
    """Utilities for consistent naming conventions across generated code."""

    @staticmethod
    def to_snake_case(string: str) -> str:
        """Convert a string to snake_case."""
        string = string.replace(" ", "_").replace("/", "_").replace(".", "_")
        string = string.replace("{", "").replace("}", "")
        string = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", string)
        string = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", string)
        string = re.sub('&', 'and', string)
        string = string.replace("-", "_").lower().strip("_")
        return string

    @staticmethod
    def _is_abbreviation_part(s: str) -> bool:
        """Проверяет, является ли строка частью аббревиатуры."""
        return all(c.isupper() or c.isdigit() for c in s) and any(c.isalpha() for c in s)

    @classmethod
    def _split_into_words(cls, s: str) -> list[str]:
        """Разбивает строку на слова, сохраняя аббревиатуры."""
        s = re.sub(r'[_\-./]', ' ', s)
        if not s:
            return []
        result = []
        current_word = ""
        current_type = None
        i = 0
        while i < len(s):
            char = s[i]
            if char.isspace():
                if current_word:
                    result.append(current_word)
                    current_word = ""
                    current_type = None
                i += 1
                continue
            new_type = None
            if char.islower():
                if (i > 0 and s[i-1].isdigit() and
                    (i == len(s) - 1 or s[i+1].isspace() or not s[i+1].isalpha())):
                    new_type = 1
                else:
                    new_type = 0
            elif char.isupper():
                new_type = 1
            elif char.isdigit():
                if (i + 1 < len(s) and s[i+1].isalpha()) or (current_type == 1):
                    new_type = 1
                else:
                    new_type = 2
            if current_type is not None and new_type != current_type:
                if current_type == 1 and new_type == 1:
                    current_word += char
                elif current_type == 0 and new_type == 1 and current_word and current_word[0].isupper():
                    result.append(current_word)
                    current_word = char
                elif current_type == 0 and new_type == 1:
                    result.append(current_word)
                    current_word = char
                elif current_type == 1 and new_type == 0 and len(current_word) > 1:
                    result.append(current_word[:-1])
                    current_word = current_word[-1] + char
                else:
                    current_word += char
            else:
                current_word += char
            current_type = new_type
            i += 1
        if current_word:
            result.append(current_word)
        processed_result = []
        for word in result:
            if len(word) >= 2 and word[0].isdigit() and word[1].islower() and len(word) == 2:
                processed_result.append(word[0] + word[1].upper())
            else:
                processed_result.append(word)
        return [word for word in processed_result if word]

    @classmethod
    def _is_abbreviation(cls, word: str) -> bool:
        """Проверяет, является ли слово аббревиатурой."""
        if not any(c.isalpha() for c in word):
            return False
        if len(word) == 2 and word[0].isdigit() and word[1].isalpha():
            return True
        return all(c.isupper() or c.isdigit() for c in word) and len(word) > 1

    @classmethod
    def _normalize_abbreviation(cls, abbr: str) -> str:
        """Нормализует аббревиатуру, делая все буквы заглавными."""
        result = ""
        for char in abbr:
            if char.isalpha():
                result += char.upper()
            else:
                result += char
        return result

    @classmethod
    def to_pascal_case(cls, string: str) -> str:
        """Convert a string to PascalCase (for class names)."""
        string = re.sub(r'[-./]', ' ', string)
        string = re.sub(r'[^\w\d_ ]', '', string)
        words = cls._split_into_words(string)
        if not words:
            return ""
        result = []
        for word in words:
            if cls._is_abbreviation(word):
                result.append(cls._normalize_abbreviation(word))
            else:
                result.append(word[0].upper() + word[1:].lower() if word else "")
        return "".join(result)

    @classmethod
    def to_camel_case(cls, string: str) -> str:
        """Convert a string to camelCase (for variable names)."""
        words = cls._split_into_words(string)
        if not words:
            return ""
        result = []
        first_word = words[0]
        if cls._is_abbreviation(first_word):
            result.append(first_word.lower())
        else:
            result.append(first_word[0].lower() + first_word[1:] if first_word else "")
        for word in words[1:]:
            if cls._is_abbreviation(word):
                result.append(cls._normalize_abbreviation(word))
            else:
                result.append(word[0].upper() + word[1:].lower() if word else "")
        return "".join(result)

    @classmethod
    def to_param_name(cls, string: str) -> str:
        """Convert a string to a valid Python parameter name."""
        snake = cls.to_snake_case(string)
        built_in_functions = set(dir(builtins)) | set(keyword.kwlist)
        if snake in built_in_functions:
            return snake + "_"
        return snake

    @classmethod
    def to_class_name(cls, string: str) -> str:
        """Convert a string to a valid Python class name."""
        return cls.to_pascal_case(string)

    @classmethod
    def to_type_annotation(cls, string: str) -> str:
        """Convert a string to be used as a type annotation."""
        basic_types = ["int", "str", "bool", "float", "list", "dict", "tuple", "set", "Any", "None"]
        if string in basic_types:
            return string
        if "[" in string and "]" in string:
            container, content = string.split("[", 1)
            content = content.rstrip("]")
            if container in basic_types:
                return f"{container}[{content}]"
            container = cls.to_class_name(container)
            return f"{container}[{content}]"
        return cls.to_class_name(string)
