"""
-----------------------------------------------------------------
(C) 2024 Prof. Tiran Dagan, FDU University. All rights reserved.
-----------------------------------------------------------------

Markdown Conversion Module

This module provides functionality to convert JSON data from processed PDFs
into markdown format, preserving structure and content types.
"""

import os
import json
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from .config import global_config

PAGE_FOOTER = "\n\n---\nPage {current_page}\n\n---\n\n"
console = Console()

def generate_markdown(json_data, visual=False):
    """
    Converts JSON data to Markdown format.

    Args:
        json_data (list): A list of dictionaries containing structured content.

    Returns:
        str: The formatted Markdown content.
    """
    markdown_content = "\n"
    current_page = None
    page_content = ""
    
    for item in json_data:
        if 'orig_elements' not in item or item['orig_elements'] is None:
            console.print(f"Warning: Missing 'orig_elements' in item {item.get('id', 'unknown')}", style="yellow")
            continue
        
        page_number = item['orig_elements'][0].get('page_number')
        
        if page_number != current_page and current_page is not None:
            markdown_content += page_content
            markdown_content += PAGE_FOOTER.format(current_page=current_page)
            page_content = ""
        
        current_page = page_number
        chunk_text = " > " + "\n> ".join(item['text'].splitlines())
        chunk_id = item['id']
        page_content += f"<details style='weight:bold'>\n<summary>Chunk {chunk_id}</summary>\n\n"
        page_content += f"<details style='color: #583;weight:bold;padding-left: 1em;'>\n<summary>Chunk Text</summary>\n\n{chunk_text}\n\n</details>\n\n"

        page_content += "<details style='color: #1010e0;weight:bold;padding-left: 1em;'>\n<summary>Original Elements</summary>\n\n"
        
        for orig_element in item['orig_elements']:
            category = orig_element.get('type', 'Unknown')
            content = orig_element.get('text', 'No content')
            id = orig_element.get('id', 'No ID')
            
            page_content += f"<div style='font-size: 10px; color: lightgrey; display: block;'>{category} | ID: {id}</div>\n\n"
            if category == 'Title':
                page_content += f"> # {content}\n\n"
            elif category == 'Header':
                page_content += f"<div style='background-color: #f7facc;color: #000;padding: 12px 2px 4px; border-bottom: 1px solid #000;'> {content}\n\n</div>"
            elif category == 'Footer':
                page_content += f"<div style='background-color: #f7facc;color: #000;padding: 12px 2px 4px; border-top: 1px solid #000;'> {content}\n\n</div>"
            elif category in ['NarrativeText', 'UncategorizedText', 'Title']:
                if 'summary' in item:
                    summary = item['summary']
                    page_content += f"| <p style=\"line-height:.9; bgcolor: #000\"><span style=\"font-family:Tahoma; font-size:.7em; color: #24a8fb\">{summary}</span></p> |\n|:--:|\n\n"
            elif category == 'ListItem':
                page_content += f"> - {content}\n"
            elif category == 'Table' or category == 'Image':
                image_base64 = orig_element.get('image')
                if image_base64:
                    # Determine the image format (assuming it's either PNG or JPEG)
                    image_format = 'png' if orig_element.get('image_mime_type') == 'image/png' else 'jpeg'
                    summary = f"<p style=\"line-height:.9; bgcolor: #000\"><span style=\"font-family:Tahoma; font-size:.7em; color: #24a8fb\">{orig_element['text']}</span></p>"
                    image_tag = f"![IMAGE:](data:image/{image_format};base64,{image_base64})"
                    page_content += f"| {image_tag}  |\n|:--:|\n| {summary} |\n\n"
                else:
                    page_content += f"> Image: {content or '?Unknown'}\n\n"
        
        page_content += "</details>\n\n</details>\n\n"
    
    # Add the last page's content
    if page_content:
        markdown_content += page_content
        markdown_content += PAGE_FOOTER.format(current_page=current_page)
    
    return markdown_content

def create_debugging_markdown():
    """Process all markdown files in the output directory with chunking."""
    output_dir = os.path.realpath(global_config.directories.output_dir)
    chunked_dir = os.path.join(output_dir, '02_chunked')
    chunked_files = [f for f in os.listdir(chunked_dir) if f.endswith('.json')]
    
    if not chunked_files:
        console.print("No chunked files to process", style="yellow")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task("Processing chunked files", total=len(chunked_files))
        
        for chunked_file in chunked_files:
            try:
                progress.update(task, description=f"Processing {chunked_file}")
                
                # Full path to the markdown file
                chunked_file_path = os.path.join(chunked_dir, chunked_file)
                base_name = os.path.splitext(chunked_file)[0]
                
                with open(chunked_file_path, 'r') as file:
                    chunks = json.load(file)

                # Convert chunks to JSON-serializable format
                chunks_data = []
                for chunk in chunks:
                    metadata = chunk["metadata"]
                    chunk_id = chunk["element_id"]
                    # Get and decode original elements if they exist
                    orig_elements = None
                    if "orig_elements" in metadata:
                        orig_elements = process_data(metadata["orig_elements"])
                        output_elements = []
                        for orig_element in orig_elements:
                            id = orig_element.id
                            type = orig_element.category
                            coordinates = orig_element.metadata.coordinates
                            text = orig_element.text
                            image = orig_element.metadata.image_base64
                            image_mime_type = orig_element.metadata.image_mime_type
                            page_number = orig_element.metadata.page_number
                            output_dict = {"id": id,
                                                    "type": type, 
                                                    "coordinates": coordinates, 
                                                    "text": text,
                                                    "page_number": page_number}

                            if type == "Image" or type == "Table":
                                output_dict["image"] = image
                                output_dict["image_mime_type"] = image_mime_type
                            
                            output_elements.append(output_dict)
                    else:
                        output_elements = None
                    
                    chunk_dict = {
                        "id": chunk_id,
                        "text": chunk['text'],
                        "type": chunk['type'],
                        "orig_elements": output_elements,
                    }
                       
                    chunks_data.append(chunk_dict)
                
                # Generate the markdown file
                markdown_dir = os.path.join(output_dir, '04_markdown')
                os.makedirs(markdown_dir, exist_ok=True)
                output_file = os.path.join(markdown_dir, f"{base_name}.md")
                
                markdown_content = generate_markdown(chunks_data, visual=False)
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                progress.advance(task)
                logging.info(f"Processed {chunked_file}")
                console.print(f"Created: {os.path.basename(output_file)}", style="green")
                
            except Exception as e:
                console.print(f"Error processing {chunked_file}: {str(e)}", style="red")
                logging.error(f"Error processing {chunked_file}: {str(e)}")


def create_markdowns():
    """
    Creates markdown files from JSON data in the output directory.
    Allows user to select which JSON files to convert.
    """
    output_dir = os.path.realpath(global_config.directories.output_dir)
    unstructured_json_dir = os.path.join(output_dir, '01_partitioned')
    json_files = select_json_file(unstructured_json_dir)
    
    if not json_files:
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task("Converting files to markdown", total=len(json_files))
        
        for json_file in json_files:
            try:
                progress.update(task, description=f"Converting {os.path.basename(json_file)}")
                
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                markdown_content = json_to_markdown(json_data)
                markdown_file = os.path.basename(os.path.splitext(json_file)[0] + '.md')
                markdown_file_path = os.path.join(output_dir, '03_markdown', markdown_file)
                with open(markdown_file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                progress.advance(task)
                logging.info(f"Created markdown file: {markdown_file}")
                console.print(f"Created: {os.path.basename(markdown_file)}", style="green")
                
            except Exception as e:
                console.print(f"Error converting {os.path.basename(json_file)}: {str(e)}", style="red")
                logging.error(f"Error converting {json_file}: {str(e)}")

def process_data(data):
    # Custom logic to process data
    pass
