import os
from pathlib import Path

def retrieve_file_contents(file_name: str) -> str:
    '''
    Retrieves the contents of a file.

    Args:
        file_name (str): The name of the file.
    Returns:
        str: The contents of the file.
    '''
    try:
        file_path = Path(os.getcwd()) / "src" / "res" / file_name
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"The file at {file_name} was not found.")
    except Exception as e:
        raise Exception(f"An error occurred while reading the file: {e}")
