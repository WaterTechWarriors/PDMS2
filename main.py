import os
from helpers import *
from helpers.pdf_ingest import PDFProcessor
from helpers.logging import setup_logging
from helpers.generate_markdown import create_debugging_markdown
from supabase_client_module.supabase_config import get_supabase_client
from supabase_client_module.populate_database import main as populate_main
from supabase_client_module.query_data import query_rag
from rich.console import Console
from rich.prompt import Prompt

console = Console()

def is_valid_directory(path):
    return os.path.isdir(path)

def select_task():
    """Prompts user to select a task to perform."""
    tasks = [
        "Ingest PDFs and create JSON & Annotations",
        "Create Debugging Markdowns from partition JSONs",
        "Populate Supabase Database",
        "Query Supabase Database",
        "Exit"
    ]
    
    console.print("\nAvailable tasks:", style="blue")
    for i, task in enumerate(tasks, 1):
        console.print(f"{i}. {task}")
    
    choice = Prompt.ask("\nSelect task", choices=[str(i) for i in range(1, len(tasks) + 1)])
    return tasks[int(choice) - 1]

def main():
    """Main function to run the PDF processing application."""
    console.print("PDF Processing Application", style="bold blue")
    console.print("-" * 50)
    
    setup_logging()
    load_config()
      
    while True:
        task = select_task()
        
        if task == "Ingest PDFs and create JSON & Annotations":
            input_dir = global_config.directories.input_dir
            processor = PDFProcessor()
            pdf_files = get_files_with_extension(input_dir, '.pdf')
            processor.process_pdfs(input_dir, pdf_files)
            
        elif task == "Create Debugging Markdowns from partition JSONs":
            create_debugging_markdown()
        
        elif task == "Populate Supabase Database":
            console.print("Populating the Supabase database...", style="green")
            populate_main()
        
        elif task == "Query Supabase Database":
            question = Prompt.ask("Enter your query")
            response = query_rag(question)
            console.print(f"Response: {response}", style="green")
        
        elif task == "Exit":
            break
        
    console.print("\nApplication completed.", style="green")

if __name__ == "__main__":
    main()