import json
import os
from typing import List

import fitz

def get_json_file_elements(pdf_filename):
    """
    Get the elements from the JSON file associated with a PDF.

    Args:
        pdf_filename (str): The PDF filename (without extension).

    Returns:
        list: The JSON data elements.
    """
    file_path = pdf_filename +'.json'
    with open(file_path, 'r') as file:
        return json.load(file)
    
def get_pdf_page_count(file_path: str) -> int:
    """Get the number of pages in a PDF file."""
    with fitz.open(file_path) as pdf:
        return len(pdf)
    
def get_files_with_extension(directory: str, file_extension: str) -> List[str]:
    """Get list of files in the specified directory."""
    file_list = [
        os.path.join(directory, f) 
        for f in os.listdir(directory) 
        if f.endswith(file_extension)
    ]
    return file_list
