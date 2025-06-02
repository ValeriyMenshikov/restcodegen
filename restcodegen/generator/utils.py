import re
import subprocess
import importlib.metadata
from functools import cache
from pathlib import Path
from urllib.parse import urlparse


def is_url(path: str) -> bool:
    parsed = urlparse(path)
    return bool(parsed.scheme) and bool(parsed.netloc)


def create_and_write_file(file_path: Path, text: str | None = None) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if text:
        file_path.write_text(text, encoding="utf-8")
    else:
        file_path.touch()


def run_command(command: str) -> tuple[int, str | None]:
    result = subprocess.run(
        command,
        shell=True,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.returncode, result.stderr


def format_file() -> None:
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
