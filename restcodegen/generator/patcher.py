"""Module for patching generated client code to ensure correct class references."""

import os
import re
from pathlib import Path
from typing import Set

from restcodegen.generator.log import LOGGER


class ClientModelPatcher:
    """Patches client files to ensure correct class name references.
    
    This class handles finding and replacing class names in generated client files
    to ensure they match the exact case and format of the model definitions.
    
    Attributes:
        models_path: Path to the file containing model definitions
        client_path: Path to the directory containing client API files
    """

    def __init__(self, models_path: Path, client_path: Path) -> None:
        """Initialize the patcher with paths to models and client files.
        
        Args:
            models_path: Path to the file with model definitions
            client_path: Path to the directory containing client API files
        """
        self.models_path = models_path
        self.client_path = client_path

    def collect_class_names(self) -> set[str]:
        """Extract class names from the models file.
        
        Parses the models file to identify all class definitions and
        returns their names for use in patching client files.
        
        Returns:
            Set of class names found in the models file
        """
        class_names: set[str] = set()
        
        if not self.models_path.exists():
            LOGGER.warning(f"Models file not found: {self.models_path}")
            return class_names
            
        try:
            with open(self.models_path, "r", encoding="utf-8") as file:
                content = file.read()
                # Find all class definitions
                class_pattern = re.compile(r"class\s+(.*?)\(")
                matches = class_pattern.findall(content)
                class_names.update(matches)
                
            LOGGER.debug(f"Found {len(class_names)} model classes")
        except Exception as e:
            LOGGER.error(f"Error collecting class names: {str(e)}")
            
        return class_names

    @staticmethod
    def replace_class_names_in_client(
        client_file_path: str | Path, class_names: set[str]
    ) -> None:
        """Replace class name references in a client file.
        
        Ensures that all references to model classes in the client file
        use the exact case and format as defined in the models.
        
        Args:
            client_file_path: Path to the client file to patch
            class_names: Set of class names to look for and replace
        """
        if not os.path.exists(client_file_path):
            LOGGER.warning(f"Client file not found: {client_file_path}")
            return
            
        try:
            # Read the client file
            with open(client_file_path, "r", encoding="utf-8") as file:
                content = file.read()

            # Replace each class name reference
            original_content = content
            for class_name in class_names:
                # Match the class name as a whole word, case-insensitive
                pattern = re.compile(r"\b" + re.escape(class_name) + r"\b", re.IGNORECASE)
                content = pattern.sub(class_name, content)

            # Only write if changes were made
            if content != original_content:
                with open(client_file_path, "w", encoding="utf-8") as file:
                    file.write(content)
                LOGGER.debug(f"Patched class references in {client_file_path}")
        except Exception as e:
            LOGGER.error(f"Error patching client file {client_file_path}: {str(e)}")

    def patch_client_files(self) -> None:
        """Patch all client files with correct class name references.
        
        Walks through all Python files in the client directory and
        patches them to use the correct class names from the models.
        """
        LOGGER.info("Patching client files with correct class references")
        
        # Collect class names from models
        class_names = self.collect_class_names()
        if not class_names:
            LOGGER.warning("No class names found to patch")
            return
            
        # Process each Python file in the client directory
        patched_count = 0
        for root, _, files in os.walk(self.client_path):
            for file_name in files:
                if file_name.endswith(".py"):
                    client_file_path = os.path.join(root, file_name)
                    self.replace_class_names_in_client(client_file_path, class_names)
                    patched_count += 1
                    
        LOGGER.info(f"Patched {patched_count} client files")
