import os
import json
import yaml
from typing import Union, Dict, Any
from pathlib import Path

def retrieve_file_contents(relative_path: str, is_json: bool = False) -> Union[str, Dict[str, Any]]:
    '''
    Retrieves the contents of a file.

    Args:
        relative_path (str): The relative path to the file. Relative to the CWD.
    Returns:
       Union[str, Dict[str, Any]] : The contents of the file.
    '''
    try:
        file_path = Path(os.getcwd() + relative_path)
        with open(file_path, 'r', encoding='utf-8') as file:
            if not is_json:
                return file.read()
            else:
                return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"The file at {relative_path} was not found.")
    except Exception as e:
        raise Exception(f"An error occurred while reading the file: {e}")

def save_file_contents(relative_path: str, content: Dict[str, Any]) -> None:
    '''
    Saves content to a file. Overwrites the file if it already exists.

    Args:
        relative_path (str): The relative path to the file. Relative to the CWD.
        content (Dict[str, Any]): The content to be saved.
    '''
    try:
        file_path = Path(os.getcwd() + relative_path)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(json.dumps(content, indent=4))
    except Exception as e:
        raise Exception(f"An error occurred while writing to the file: {e}")

def load_config(file_name: str) -> Dict[str, Any]:
    '''
    Loads configuration from a yaml file.

    Args:
        file_name (str): The name of the configuration file.

    Returns:
        Dict[str, Any]: The configuration content.
    '''
    try:
        file_path = Path(os.getcwd()) / "src" / "res" / "configs" / file_name
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.load(file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        raise FileNotFoundError(f"The configuration file at {file_name} was not found.")
    except Exception as e:
        raise Exception(f"An error occurred while reading the configuration file: {e}")