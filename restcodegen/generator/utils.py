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
