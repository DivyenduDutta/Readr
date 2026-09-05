import json
import os
from pathlib import Path
from typing import Any

import yaml


def retrieve_file_contents(
    relative_path: str, is_json: bool = False
) -> str | dict[str, Any]:
    """
    Retrieves the contents of a file.

    Args:
        relative_path (str): The relative path to the file. Relative to the CWD.
        is_json (bool): If True, parse the file as JSON and return a dict.
                        If False (default), return the raw file contents as a string.
    Returns:
       str | dict[str, Any] : The contents of the file.
    Raises:
        FileNotFoundError: If no file exists at relative_path.
    """
    try:
        file_path = Path(os.getcwd() + relative_path)
        with open(file_path, "r", encoding="utf-8") as file:
            if not is_json:
                return file.read()
            else:
                return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"The file at {relative_path} was not found.")


def save_file_contents(relative_path: str, content: dict[str, Any]) -> None:
    """
    Saves content to a file. Overwrites the file if it already exists.

    Args:
        relative_path (str): The relative path to the file. Relative to the CWD.
        content (dict[str, Any]): The content to be saved.
    Raises:
        RuntimeError: If the file cannot be written (I/O error) or content is not
                     JSON-serializable.
    """
    try:
        file_path = Path(os.getcwd() + relative_path)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(json.dumps(content, indent=4))
    except (OSError, TypeError) as e:
        raise RuntimeError(f"Failed to write JSON file '{relative_path}'") from e


def load_config(file_name: str) -> dict[str, Any]:
    """
    Loads configuration from a yaml file.

    Args:
        file_name (str): The name of the configuration file.

    Returns:
        dict[str, Any]: The configuration content.
    Raises:
        FileNotFoundError: If no config file exists with the given name under
                           src/res/configs/.
    """
    try:
        file_path = Path(os.getcwd()) / "src" / "res" / "configs" / file_name
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.load(file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        raise FileNotFoundError(f"The configuration file at {file_name} was not found.")
