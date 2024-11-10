import argparse
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from supabase_client_module.supabase_config import get_supabase_client
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_community.embeddings import OpenAIEmbeddings  # Updated import

import uuid
from datetime import datetime
import re
from helpers.enrichments import enrich_json_with_summaries
from pdf2image import convert_from_path
import io
import gc
import time
from tqdm import tqdm
from PIL import Image
import traceback

# Load environment variables from .env file
load_dotenv()

# Access the variables
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

DATA_PATH = "data"
BATCH_SIZE = 3  # Process 3 documents at a time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset the database.")
    args = parser.parse_args()
    
    try:
        if args.reset:
            print("✨ Clearing Database")
            clear_database()

        documents = load_documents()
        process_documents_in_batches(documents)
        print("Processing completed successfully.")
    except Exception as e:
        print(f"An error occurred during processing: {str(e)}")

def load_documents():
    document_loader = PyPDFDirectoryLoader(DATA_PATH)
    documents = document_loader.load()
    
    unique_documents = {}
    for doc in documents:
        pdf_path = doc.metadata['source']
        if pdf_path not in unique_documents:
            unique_documents[pdf_path] = doc
            print(f"Loading document: {pdf_path}")
    
    return list(unique_documents.values())

def process_documents_in_batches(documents):
    total_documents = len(documents)
    for i in range(0, total_documents, BATCH_SIZE):
        batch = documents[i:i+BATCH_SIZE]
        print(f"Processing batch {i//BATCH_SIZE + 1}/{(total_documents + BATCH_SIZE - 1)//BATCH_SIZE}")
        process_documents(batch)
        gc.collect()
        time.sleep(1)  # Short pause between batches

def process_documents(documents):
    supabase_client = get_supabase_client()
    embedding_function = get_embedding_function()

    for doc in tqdm(documents, desc="Processing documents"):
        try:
            process_single_document(supabase_client, embedding_function, doc)
        except Exception as e:
            print(f"Error processing document {doc.metadata['source']}: {str(e)}")

def process_single_document(supabase_client, embedding_function, doc):
    try:
        product_info = extract_product_info(doc)
        product_id = insert_product(supabase_client, product_info)
        document_id = insert_document(supabase_client, doc, product_id)
        
        sections = split_into_sections(doc)
        for i, section in enumerate(sections):
            section_id = insert_section(supabase_client, section, document_id, i+1)
            keywords = extract_keywords(section.page_content)
            insert_keywords(supabase_client, keywords, section_id)
            embedding = embedding_function.embed_query(section.page_content)
            insert_embedding(supabase_client, embedding, section_id, len(section.page_content.split()))

        # Process images in the document
        json_file = doc.metadata['source']
        enrich_json_with_summaries(json_file)
    except Exception as e:
        print(f"Error processing document {doc.metadata['source']}: {str(e)}")
        print(traceback.format_exc())

def extract_product_info(doc):
    filename = os.path.basename(doc.metadata['source'])
    product_name = filename.split('.')[0]
    content = doc.page_content.lower()
    
    pieces_match = re.search(r'([A-Z])\s*$', content.split('\n')[0])
    num_pieces = ord(pieces_match.group(1)) - ord('A') + 1 if pieces_match else None
    
    if "cordless vacuum" in content:
        model_match = re.search(r'(volt\s+fx-\d+li|fx-\d+li)', content, re.IGNORECASE)
        if model_match:
            product_name = f"Cordless Vacuum {model_match.group(1).upper()}"
        else:
            product_name = "Cordless Vacuum " + product_name
    
    doc.metadata['product_name'] = product_name
    doc.metadata['num_pieces'] = num_pieces
    
    return {
        'product_name': product_name,
        'product_category': 'Vacuum Cleaner',
        'manufacturer': 'Unknown',
        'release_date': datetime.now().date().isoformat(),
        'num_pieces': num_pieces
    }

def insert_product(supabase_client, product_info):
    product_info_copy = product_info.copy()
    product_info_copy.pop('num_pieces', None)
    
    for _ in range(3):
        try:
            existing_product = supabase_client.table('products').select('product_id').eq('product_name', product_info_copy['product_name']).execute()
            if existing_product.data:
                return existing_product.data[0]['product_id']
            response = supabase_client.table('products').insert(product_info_copy).execute()
            return response.data[0]['product_id']
        except Exception as e:
            print(f"Error inserting product, retrying: {str(e)}")
            time.sleep(1)
    raise Exception("Failed to insert product after 3 attempts")

def insert_document(supabase_client, doc, product_id):
    document_info = {
        'title': os.path.basename(doc.metadata['source']),
        'product_name': doc.metadata['product_name'],
        'product_id': product_id,
        'version': '1.0',
        'language': 'en',
        'file_path': doc.metadata['source'],
        'num_pieces': doc.metadata.get('num_pieces')
    }
    
    existing_document = supabase_client.table('documents').select('document_id').eq('file_path', document_info['file_path']).execute()
    if existing_document.data:
        return existing_document.data[0]['document_id']
    
    response = supabase_client.table('documents').insert(document_info).execute()
    return response.data[0]['document_id']

def split_into_sections(doc):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents([doc])

def insert_section(supabase_client, section, document_id, order):
    section_info = {
        'document_id': document_id,
        'section_title': f"Section {order}",
        'content': section.page_content,
        'page_number': section.metadata.get('page', 1),
        'order': order
    }
    response = supabase_client.table('sections').insert(section_info).execute()
    return response.data[0]['section_id']

def extract_keywords(text):
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(words))

def insert_keywords(supabase_client, keywords, section_id):
    keyword_data = [{'section_id': section_id, 'keyword': kw, 'importance_score': 1.0} for kw in keywords]
    supabase_client.table('keywords').insert(keyword_data).execute()

def insert_embedding(supabase_client, embedding, section_id, tokens_count):
    embedding_data = {
        'section_id': section_id,
        'embedding': embedding,
        'tokens_count': tokens_count
    }
    supabase_client.table('indexing_metadata').insert(embedding_data).execute()

def insert_image_info(supabase_client, document_id, image_info, image_number):
    image_data = {
        'document_id': document_id,
        'colors': image_info['colors'],
        'description': image_info['description'],
        'image_number': image_number
    }
    try:
        result = supabase_client.table('product_images').insert(image_data).execute()
        return result
    except Exception as e:
        print(f"Error inserting image info: {str(e)}")
        return None

def clear_database():
    supabase_client = get_supabase_client()
    tables = [
        'indexing_metadata',
        'keywords',
        'sections',
        'product_images',
        'documents',
        'products'
    ]
    for table in tables:
        try:
            response = supabase_client.table(table).select('id').execute()
            ids = [item['id'] for item in response.data]
            batch_size = 100
            for i in range(0, len(ids), batch_size):
                batch = ids[i:i+batch_size]
                supabase_client.table(table).delete().in_('id', batch).execute()
            print(f"Cleared table: {table}")
        except Exception as e:
            print(f"Error clearing table {table}: {str(e)}")
    
    print("Database cleared successfully")  # Confirmation of successful database clear

# Embedding function definition
def get_embedding_function():
    """
    Returns an embedding function that can embed text queries.
    """
    embeddings = OpenAIEmbeddings()  # Initialize with necessary API key or configurations

    def embed_query(text):
        """
        Generates an embedding for the given text.
        
        Args:
            text (str): The text to embed.
        
        Returns:
            List[float]: The embedding vector for the text.
        """
        return embeddings.embed_query(text)

    return embed_query


