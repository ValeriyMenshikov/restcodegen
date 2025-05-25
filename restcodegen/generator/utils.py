import importlib.metadata
import re
import subprocess
from functools import cache
from pathlib import Path
from urllib.parse import urlparse
import builtins
import keyword


def is_url(path: str) -> bool:
    """Check if a string is a valid URL.
    
    Args:
        path: String to check
        
    Returns:
        True if the string is a valid URL, False otherwise
    """
    parsed = urlparse(path)
    return bool(parsed.scheme) and bool(parsed.netloc)


def name_to_snake(string: str) -> str:
    """Convert a string to snake_case.
    
    Args:
        string: String to convert
        
    Returns:
        String in snake_case format
    """
    # Replace common separators with underscores
    string = string.replace(" ", "_").replace("/", "_").replace(".", "_")
    string = string.replace("{", "").replace("}", "")
    
    # Handle camelCase and PascalCase
    string = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", string)
    string = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", string)
    
    # Replace special characters
    string = re.sub('&', 'and', string)
    
    # Final cleanup
    string = string.replace("-", "_").lower().strip("_")
    return string


def snake_to_camel(string: str) -> str:
    """Convert a string from snake_case to CamelCase.
    
    Args:
        string: String to convert
        
    Returns:
        String in CamelCase format
    """
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", string)
    camel_case_words = [word[0].upper() + word[1:] for word in words if word]
    camel_case_title = "".join(camel_case_words)
    return camel_case_title


def rename_python_builtins(name: str) -> str:
    """Append underscore to Python built-in names to avoid conflicts.
    
    Args:
        name: Name to check and potentially rename
        
    Returns:
        Original name or name with appended underscore if it's a Python built-in
    """
    built_in_functions = set(dir(builtins)) | set(keyword.kwlist)
    if name in built_in_functions:
        return name + "_"
    return name


class NamingUtils:
    """Utilities for consistent naming conventions across generated code.

    This class provides methods for converting between different naming conventions
    (snake_case, camelCase, PascalCase) and ensures consistent handling of names
    throughout the code generation process.
    """

    @staticmethod
    def to_snake_case(string: str) -> str:
        """Convert a string to snake_case.
        
        Args:
            string: String to convert
            
        Returns:
            String in snake_case format
        """
        # Replace common separators with underscores
        string = string.replace(" ", "_").replace("/", "_").replace(".", "_")
        string = string.replace("{", "").replace("}", "")
        
        # Handle camelCase and PascalCase
        string = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", string)
        string = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", string)
        
        # Replace special characters
        string = re.sub('&', 'and', string)
        
        # Final cleanup
        string = string.replace("-", "_").lower().strip("_")
        return string
    
    @staticmethod
    def is_abbreviation_part(s: str) -> bool:
        """Проверяет, является ли строка частью аббревиатуры.
        
        Args:
            s: Строка для проверки
            
        Returns:
            True, если строка является частью аббревиатуры, иначе False
        """
        # Аббревиатура может содержать заглавные буквы и цифры
        return all(c.isupper() or c.isdigit() for c in s) and any(c.isalpha() for c in s)
    
    @classmethod
    def split_into_words(cls, s: str) -> list[str]:
        """Разбивает строку на слова, сохраняя аббревиатуры.
        
        Args:
            s: Строка для разбиения
            
        Returns:
            Список слов
        """
        # Заменяем разделители на пробелы
        s = s.replace("_", " ").replace("-", " ").replace(".", " ").replace("/", " ")
        
        if not s:
            return []
            
        result = []
        current_word = ""
        current_type = None  # 0 - lowercase, 1 - uppercase/digit part of abbreviation, 2 - digit, None - not set
        
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
            
            # Определяем тип текущего символа
            new_type = None
            if char.islower():
                # Проверяем, может ли это быть частью аббревиатуры с цифрами (например, "1p")
                if (i > 0 and s[i-1].isdigit() and 
                    (i == len(s) - 1 or s[i+1].isspace() or not s[i+1].isalpha())):
                    # Это может быть буква в нижнем регистре, которая на самом деле 
                    # является частью аббревиатуры с цифрой (например, "1p")
                    new_type = 1
                else:
                    new_type = 0
            elif char.isupper():
                new_type = 1
            elif char.isdigit():
                # Цифра может быть частью аббревиатуры, если за ней следует буква
                # или если перед ней была заглавная буква
                if (i + 1 < len(s) and s[i+1].isalpha()) or (current_type == 1):
                    new_type = 1  # Часть аббревиатуры
                else:
                    new_type = 2  # Обычная цифра
            
            # Если тип символа изменился
            if current_type is not None and new_type != current_type:
                # Если текущее слово - аббревиатура и новый символ тоже часть аббревиатуры
                if current_type == 1 and new_type == 1:
                    # Продолжаем аббревиатуру
                    current_word += char
                # Если текущее слово начинается с заглавной и продолжается строчными,
                # а новый символ - заглавная буква или цифра в составе аббревиатуры
                elif current_type == 0 and new_type == 1 and current_word and current_word[0].isupper():
                    # Начинаем новое слово
                    result.append(current_word)
                    current_word = char
                # Если текущее слово - строчные буквы, а новый символ - заглавная буква или цифра в составе аббревиатуры
                elif current_type == 0 and new_type == 1:
                    # Начинаем новое слово
                    result.append(current_word)
                    current_word = char
                # Если текущее слово - аббревиатура, а новый символ - строчная буква
                elif current_type == 1 and new_type == 0 and len(current_word) > 1:
                    # Последняя буква аббревиатуры на самом деле начало нового слова
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
            
        # Дополнительная обработка для выявления аббревиатур с цифрами в нижнем регистре
        processed_result = []
        for word in result:
            if len(word) >= 2 and word[0].isdigit() and word[1].islower() and len(word) == 2:
                # Это может быть аббревиатура вида "1p" в нижнем регистре
                processed_result.append(word[0] + word[1].upper())
            else:
                processed_result.append(word)
            
        return [word for word in processed_result if word]
    
    @classmethod
    def is_abbreviation(cls, word: str) -> bool:
        """Проверяет, является ли слово аббревиатурой.
        
        Args:
            word: Слово для проверки
            
        Returns:
            True, если слово является аббревиатурой, иначе False
        """
        # Аббревиатура должна содержать хотя бы одну букву
        if not any(c.isalpha() for c in word):
            return False
            
        # Специальная проверка для аббревиатур вида "1p"
        if len(word) == 2 and word[0].isdigit() and word[1].isalpha():
            return True
            
        # Аббревиатура должна содержать только заглавные буквы и, возможно, цифры
        return all(c.isupper() or c.isdigit() for c in word) and len(word) > 1
    
    @classmethod
    def normalize_abbreviation(cls, abbr: str) -> str:
        """Нормализует аббревиатуру, делая все буквы заглавными.
        
        Args:
            abbr: Аббревиатура для нормализации
            
        Returns:
            Нормализованная аббревиатура
        """
        # Если аббревиатура содержит цифры, сохраняем их как есть
        result = ""
        for char in abbr:
            if char.isalpha():
                result += char.upper()
            else:
                result += char
        return result
    
    @classmethod
    def to_pascal_case(cls, string: str) -> str:
        """Convert a string to PascalCase (for class names).
        
        Args:
            string: String to convert
            
        Returns:
            String in PascalCase format
        """
        # Разбиваем строку на слова
        words = cls.split_into_words(string)
        
        if not words:
            return ""
        
        result = []
        
        for word in words:
            if cls.is_abbreviation(word):
                # Это аббревиатура, нормализуем ее
                result.append(cls.normalize_abbreviation(word))
            else:
                # Обычное слово, делаем первую букву заглавной, остальные строчными
                result.append(word[0].upper() + word[1:].lower() if word else "")
        
        return "".join(result)
    
    @classmethod
    def to_camel_case(cls, string: str) -> str:
        """Convert a string to camelCase (for variable names).
        
        Args:
            string: String to convert
            
        Returns:
            String in camelCase format
        """
        # Разбиваем строку на слова
        words = cls.split_into_words(string)
        
        if not words:
            return ""
        
        result = []
        
        # Первое слово всегда начинается с маленькой буквы
        first_word = words[0]
        if cls.is_abbreviation(first_word):
            # Если первое слово - аббревиатура, делаем ее строчной
            result.append(first_word.lower())
        else:
            # Иначе делаем первую букву строчной
            result.append(first_word[0].lower() + first_word[1:] if first_word else "")
        
        # Остальные слова как в PascalCase
        for word in words[1:]:
            if cls.is_abbreviation(word):
                # Если слово - аббревиатура, нормализуем ее
                result.append(cls.normalize_abbreviation(word))
            else:
                # Иначе делаем первую букву заглавной, остальные строчными
                result.append(word[0].upper() + word[1:].lower() if word else "")
        
        return "".join(result)
    
    @classmethod
    def to_param_name(cls, string: str) -> str:
        """Convert a string to a valid Python parameter name.
        
        Converts to snake_case and handles Python reserved keywords.
        
        Args:
            string: String to convert
            
        Returns:
            Valid Python parameter name
        """
        snake = cls.to_snake_case(string)
        built_in_functions = set(dir(builtins)) | set(keyword.kwlist)
        if snake in built_in_functions:
            return snake + "_"
        return snake
    
    @classmethod
    def to_class_name(cls, string: str) -> str:
        """Convert a string to a valid Python class name.
        
        Args:
            string: String to convert
            
        Returns:
            Valid Python class name in PascalCase
        """
        return cls.to_pascal_case(string)
    
    @classmethod
    def to_type_annotation(cls, string: str) -> str:
        """Convert a string to be used as a type annotation.
        
        This converts snake_case to PascalCase for class references.
        
        Args:
            string: String to convert
            
        Returns:
            String formatted for use as a type annotation
        """
        # Check if this is a basic type
        basic_types = ["int", "str", "bool", "float", "list", "dict", "tuple", "set", "Any", "None"]
        if string in basic_types:
            return string
        
        # Check if this is a generic type with parameters
        if "[" in string and "]" in string:
            container, content = string.split("[", 1)
            content = content.rstrip("]")
            # Process the container part
            if container in basic_types:
                return f"{container}[{content}]"
            # For non-basic container types, convert to PascalCase
            container = cls.to_class_name(container)
            return f"{container}[{content}]"
        
        # Otherwise, treat as a class name
        return cls.to_class_name(string)


def create_and_write_file(file_path: Path, text: str | None = None) -> None:
    """Create a file and write content to it, creating parent directories if needed.
    
    Args:
        file_path: Path to the file to create
        text: Optional text content to write to the file
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if text:
        file_path.write_text(text, encoding="utf-8")
    else:
        # Just create an empty file if no text provided
        file_path.touch()


def run_command(command: str) -> tuple[int, str | None]:
    """Run a shell command and return its exit code and stderr output.
    
    Args:
        command: Command to run
        
    Returns:
        Tuple of (exit_code, stderr_output)
    """
    result = subprocess.run(
        command, 
        shell=True, 
        stderr=subprocess.PIPE, 
        text=True
    )  # noqa: S602
    
    return result.returncode, result.stderr


def format_file() -> None:
    """Format generated code using ruff formatter and linter."""
    target_dir = "./clients/http"
    
    # Format code
    format_command = ["ruff", "format", target_dir]
    run_command(" ".join(format_command))
    
    # Run linter with auto-fix
    lint_command = ["ruff", "check", target_dir, "--fix"]
    run_command(" ".join(lint_command))


@cache
def get_dependencies() -> list[dict[str, str]]:
    """Get a sorted list of installed Python packages with their versions.
    
    Returns:
        List of dictionaries with package name and version
    """
    deps = [
        {"path": dep.name, "version": dep.version}
        for dep in importlib.metadata.distributions()
    ]  # type: ignore[attr-defined]

    return sorted(deps, key=lambda x: x["path"].lower())


@cache
def get_version() -> str:
    """Get the version of the restcodegen package.
    
    Returns:
        Version string or "unknown" if not found
    """
    deps = get_dependencies()
    for dep in deps:
        if dep["path"] == "restcodegen":
            return dep["version"]
    return "unknown"
