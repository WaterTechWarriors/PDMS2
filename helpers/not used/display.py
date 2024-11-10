"""
Display and User Interaction Utilities

This module provides functions for handling user interactions in a terminal interface.
"""

import os
from rich.console import Console
from rich.prompt import Prompt

console = Console()



def select_json_file(directory):
    """
    Prompts user to select JSON file(s) from the specified directory.

    Args:
        directory (str): The directory containing JSON files.

    Returns:
        list: Selected JSON file paths, or empty list if canceled.
    """
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    
    if not json_files:
        console.print("No JSON files found in the output directory!", style="yellow")
        return []

    console.print("\nAvailable JSON files:", style="blue")
    for i, file in enumerate(json_files, 1):
        console.print(f"{i}. {file}")
    console.print("A. Process all files")
    console.print("C. Cancel")
    
    choice = Prompt.ask(
        "\nSelect file", 
        choices=[str(i) for i in range(1, len(json_files) + 1)] + ['a', 'c'],
        show_choices=False
    ).lower()
    
    if choice == 'c':
        return []
    elif choice == 'a':
        return [os.path.join(directory, f) for f in json_files]
    else:
        return [os.path.join(directory, json_files[int(choice) - 1])]
