"""
-----------------------------------------------------------------
(C) 2024 Prof. Tiran Dagan, FDU University. All rights reserved.
-----------------------------------------------------------------

Partition JSON Enrichment Module

This module provides functionality to enhance JSON data with LLM-generated
summaries of images using OpenAI's GPT-4 Vision model.
"""

from openai import OpenAI
import json
from .config import global_config
import os
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


console = Console()

def enrich_json_with_summaries(json_file):
    """
    Processes JSON data, generating summaries for images and text that don't have them.
    
    Args:
        json_file (str): Path to the JSON file being processed.
    """
    with open(json_file, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # Retrieve lists of items to enrich
    imageElements = [item for item in json_data if item['type'] == 'Image']
    textElements = [item for item in json_data if item['type'] in ['NarrativeText', 'Title', 'UncategorizedText']]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        
        # Images
        task = progress.add_task(
            f"Enriching images", 
            total=len(imageElements)
        )

        for idx, item in enumerate(imageElements, 1):
            progress.update(task, description=f"Enriching images: {idx}/{len(imageElements)}")
            image_base64 = item['metadata'].get('image_base64')
            if image_base64:
                try:
                    summary = summarize_image(image_base64)
                    item['text'] = summary

                    # Save after each image is processed
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)
                    
                    progress.advance(task)
                except Exception as e:
                    console.print(f"Error processing image: {str(e)}", style="red")
                    logging.error(f"Error processing image: {str(e)}")
            else:
                console.print(f"Skipping image without base64 data: {item.get('text', 'Unnamed image')}", 
                            style="yellow")

        # Text
        task = progress.add_task(
            f"Enriching text", 
            total=len(textElements)
        )

        for idx, item in enumerate(textElements, 1):
            progress.update(task, description=f"Enriching text: {idx}/{len(textElements)}")
            text_content = item.get('text')
            if text_content:
                try:
                    summary = summarize_text(text_content)
                    item['summary'] = summary

                    # Save after each text element is processed
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)
                    
                    progress.advance(task)
                except Exception as e:
                    console.print(f"Error processing text: {str(e)}", style="red")
                    logging.error(f"Error processing text: {str(e)}")
            else:
                console.print(f"Skipping empty text element", style="yellow")

    return

def summarize_image(image_base64):
    """
    Generates a summary of an image using OpenAI's GPT-4 Vision model.

    Args:
        image_base64 (str): Base64-encoded image data.

    Returns:
        str: A text summary of the image content.
    """
    client = OpenAI(api_key=global_config.api_keys.openai_api_key)
    
    prompt = """You are an image summarizing agent. I will be giving you an image and you will provide a summary describing 
    the image, starting with "An image", or "An illustration", or "A diagram:", or "A logo:" or "A symbol:". If it contains a part, 
    you will try to identify the part and if it shows an action (such as a person cleaning 
    a pool or a woman holding a pool cleaning product) you will call those out. If it is a symbol, just give the symbol
    a meaningful name such as "warning symbol" or "attention!"
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=300
    )
    
    return response.choices[0].message.content

def summarize_text(text_content):
    """
    Generates a summary of text content using OpenAI's GPT-4 model, 
    focusing on product documentation features relevant to pool cleaning devices.

    Args:
        text_content (str): The text content to be summarized.

    Returns:
        str: A summarized description of the text content with tags.
    """
    client = OpenAI(api_key=global_config.api_keys.openai_api_key)
    
    prompt = """You are a text summarizing agent for product documentation. I will provide you with text. 
                Begin with the relevant context, such as "A description of," "An explanation of," or 
                "A guide to," based on the content type, and you will create a concise summary describing the 
                text starting with:
                1.	“Product Feature:” if it is a (e.g., battery life, cleaning efficiency) 
                2.	“Usage Context” if it is a (e.g., recommended pool size) 
                3.	“Appearance” if it highlights (e.g., color, visible components 
                4.	“Port/Component Type” if it contains parts.
                5.	“Battery/Charging:” if there is any information mentioning any unique attributes (e.g., “long-lasting battery,” “quick charging”).
                6.	“Comparative Info:”  if text summarizes differences or advantages compared to competitors.
                7.	“AI Features:” if mentioned in the text 
                8.	“Eco-Friendly Attributes:” if text contains information about the environment
                9.	“Customization Options:” if text contains information about customization
                10.	“Warranty/Support:” if text has information focusing on service and reliability
                11.	“Promotions/Seasonality:” if text has information or references timing or campaigns
                12. "Warning:" if text contains a warning
                13. "Product Name:" if text contains the product name
                14. "Instructions:" if text contains instructions
                15. "Safety:" if text contains safety information
                16. "Parts:" if text contains information about parts
                17. "Dimensions:" if text contains information about dimensions
                18. "Certifications:" if text contains information about certifications
                19. "Other:" if text contains other information

    """
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "user",
                "content": prompt + "\n\nText: " + text_content
            }
        ],
        max_tokens=300
    )
    
    summary = response.choices[0].message.content
    logging.info(f"Generated summary: {summary}")  # Add logging to check the summary
    return summary