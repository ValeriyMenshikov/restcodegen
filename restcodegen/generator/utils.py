import importlib.metadata
import re
import subprocess
from functools import cache
from pathlib import Path
from urllib.parse import urlparse
import builtins
import keyword


def is_url(path: str) -> bool:
    """Check if a string is a valid URL."""
    parsed = urlparse(path)
    return bool(parsed.scheme) and bool(parsed.netloc)


def name_to_snake(string: str) -> str:
    """Convert a string to snake_case."""
    string = string.replace(" ", "_").replace("/", "_").replace(".", "_")
    string = string.replace("{", "").replace("}", "")
    string = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", string)
    string = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", string)
    string = re.sub('&', 'and', string)
    string = string.replace("-", "_").lower().strip("_")
    return string


def snake_to_camel(string: str) -> str:
    """Convert a string from snake_case to CamelCase."""
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", string)
    camel_case_words = [word[0].upper() + word[1:] for word in words if word]
    camel_case_title = "".join(camel_case_words)
    return camel_case_title


def rename_python_builtins(name: str) -> str:
    """Append underscore to Python built-in names to avoid conflicts."""
    built_in_functions = set(dir(builtins)) | set(keyword.kwlist)
    if name in built_in_functions:
        return name + "_"
    return name


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
    def is_abbreviation_part(s: str) -> bool:
        """Проверяет, является ли строка частью аббревиатуры."""
        return all(c.isupper() or c.isdigit() for c in s) and any(c.isalpha() for c in s)

    @classmethod
    def split_into_words(cls, s: str) -> list[str]:
        """Разбивает строку на слова, сохраняя аббревиатуры."""
        s = s.replace("_", " ").replace("-", " ").replace(".", " ").replace("/", " ")
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
    def is_abbreviation(cls, word: str) -> bool:
        """Проверяет, является ли слово аббревиатурой."""
        if not any(c.isalpha() for c in word):
            return False
        if len(word) == 2 and word[0].isdigit() and word[1].isalpha():
            return True
        return all(c.isupper() or c.isdigit() for c in word) and len(word) > 1

    @classmethod
    def normalize_abbreviation(cls, abbr: str) -> str:
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
        words = cls.split_into_words(string)
        if not words:
            return ""
        result = []
        for word in words:
            if cls.is_abbreviation(word):
                result.append(cls.normalize_abbreviation(word))
            else:
                result.append(word[0].upper() + word[1:].lower() if word else "")
        return "".join(result)

    @classmethod
    def to_camel_case(cls, string: str) -> str:
        """Convert a string to camelCase (for variable names)."""
        words = cls.split_into_words(string)
        if not words:
            return ""
        result = []
        first_word = words[0]
        if cls.is_abbreviation(first_word):
            result.append(first_word.lower())
        else:
            result.append(first_word[0].lower() + first_word[1:] if first_word else "")
        for word in words[1:]:
            if cls.is_abbreviation(word):
                result.append(cls.normalize_abbreviation(word))
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


def create_and_write_file(file_path: Path, text: str | None = None) -> None:
    """Create a file and write content to it, creating parent directories if needed."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if text:
        file_path.write_text(text, encoding="utf-8")
    else:
        file_path.touch()


def run_command(command: str) -> tuple[int, str | None]:
    """Run a shell command and return its exit code and stderr output."""
    result = subprocess.run(
        command,
        shell=True,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.returncode, result.stderr


def format_file() -> None:
    """Format generated code using ruff formatter and linter."""
    target_dir = "./clients/http"
    format_command = ["ruff", "format", target_dir]
    run_command(" ".join(format_command))
    lint_command = ["ruff", "check", target_dir, "--fix"]
    run_command(" ".join(lint_command))


@cache
def get_dependencies() -> list[dict[str, str]]:
    """Get a sorted list of installed Python packages with their versions."""
    deps = [
        {"path": dep.name, "version": dep.version}
        for dep in importlib.metadata.distributions()
    ]
    return sorted(deps, key=lambda x: x["path"].lower())


@cache
def get_version() -> str:
    """Get the version of the restcodegen package."""
    deps = get_dependencies()
    for dep in deps:
        if dep["path"] == "restcodegen":
            return dep["version"]
    return "unknown"
