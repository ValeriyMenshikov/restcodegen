import os
import re
from pathlib import Path


class ClientModelPatcher:
    """
    Класс для замены названий классов в файлах клиента на основе моделей.

    Attributes:
        models_path (Path): Путь к файлу с моделями.
        client_path (Path): Путь к папке с клиентами.
    """

    def __init__(self, models_path: Path, client_path: Path) -> None:
        self.models_path = models_path
        self.client_path = client_path

    def collect_class_names(self) -> set[str]:
        """
        Собирает названия классов из файла с моделями.

        Returns:
            set[str]: Множество названий классов.
        """
        class_names: set[str] = set()
        with open(self.models_path, "r", encoding="utf-8") as file:
            content = file.read()
            class_pattern = re.compile(r"class\s+(.*)\(")
            matches = class_pattern.findall(content)
            class_names.update(matches)
        return class_names

    @staticmethod
    def replace_class_names_in_client(
        client_file_path: str, class_names: set[str]
    ) -> None:
        """
        Заменяет названия классов в файле клиента, если они совпадают с названиями из моделей.

        Args:
            client_file_path (str): Путь к файлу клиента.
            class_names (Set[str]): Множество названий классов из моделей.
        """
        with open(client_file_path, "r", encoding="utf-8") as file:
            content = file.read()

        for class_name in class_names:
            pattern = re.compile(r"\b" + re.escape(class_name) + r"\b", re.IGNORECASE)
            content = pattern.sub(class_name, content)

        with open(client_file_path, "w", encoding="utf-8") as file:
            file.write(content)

    def patch_client_files(self) -> None:
        class_names = self.collect_class_names()

        for root, _, files in os.walk(self.client_path):
            for file_name in files:
                if file_name.endswith(".py"):
                    client_file_path = os.path.join(root, file_name)
                    self.replace_class_names_in_client(client_file_path, class_names)
