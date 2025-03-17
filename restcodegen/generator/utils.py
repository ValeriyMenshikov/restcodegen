import importlib.metadata
import pprint
import re
from functools import cache
from pathlib import Path
from subprocess import run, PIPE
from typing import Optional
from urllib.parse import urlparse


def is_url(path: str) -> bool:
    parsed = urlparse(path)
    return bool(parsed.scheme) and bool(parsed.netloc)


def name_to_snake(string: str) -> str:
    string = string.replace(" ", "_").replace("/", "_").replace(".", "_")
    string = string.replace("{", "").replace("}", "")
    string = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", string)
    string = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", string)
    string = string.replace("-", "_").lower().strip("_")
    return string


def snake_to_camel(string: str) -> str:
    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", string)
    camel_case_words = [word[0].upper() + word[1:] for word in words if word]
    camel_case_title = "".join(camel_case_words)
    return camel_case_title


def create_and_write_file(file_path: Path, text: Optional[str] = None) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if text:
        file_path.write_text(text, encoding="utf-8")


def run_command(command: str) -> tuple[int, Optional[str]]:
    result = run(command, shell=True, stderr=PIPE, text=True)  # noqa: S602
    stderr = result.stderr
    return result.returncode, stderr


def format_file() -> None:
    command_format = [
        "ruff",
        "format",
        "./clients/http",
    ]
    run_command(" ".join(command_format))
    command_check = [
        "ruff",
        "check",
        "./clients/http",
        "--fix",
    ]
    run_command(" ".join(command_check))


@cache
def get_dependencies() -> list[dict[str, str]]:
    deps = [
        {"path": dep.name, "version": dep.version}
        for dep in importlib.metadata.distributions()
    ]  # type: ignore[attr-defined]

    return sorted(deps, key=lambda x: x["path"].lower())


@cache
def get_version() -> str:
    deps = get_dependencies()
    pprint.pprint(deps)
    for dep in deps:
        if dep["path"] == "restcodegen":
            return dep["version"]
    return "unknown"

get_version()