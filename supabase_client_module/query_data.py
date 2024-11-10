import argparse
import os
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import SupabaseVectorStore
from langchain.schema import Document

from supabase_client_module.populate_database import get_embedding_function

from supabase_client_module.supabase_config import get_supabase_client



# Load environment variables from .env file
load_dotenv()

# Access the variables
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# ANSI escape codes for colors
LIGHT_BLUE = "\033[94m"
RESET_COLOR = "\033[0m"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query_text", type=str, nargs='?', help="The query text.")
    args = parser.parse_args()
    
    if args.query_text:
        query_text = args.query_text
    else:
        query_text = input("Enter your query: ")
    
    query_rag(query_text)

def query_rag(query_text: str):
    print("Creating embedding function...")
    embedding_function = get_embedding_function()
    print("Getting Supabase client...")
    supabase_client = get_supabase_client()

    print(f"Generating embedding for query: {query_text}")
    query_embedding = embedding_function.embed_query(query_text)

    print("Calling match_documents function directly...")
    response = supabase_client.rpc('match_documents', {
        'query_embedding': query_embedding,
        'match_count': 5
    }).execute()

    print(f"Direct function call result: {response.data}")

    if not response.data:
        print("No results found.")
        return

    # Fetch image descriptions
    try:
        image_descriptions = supabase_client.table('product_images').select('document_id, description').execute()
        image_desc_dict = {item['document_id']: item['description'] for item in image_descriptions.data}
    except Exception as e:
        print(f"Error fetching image descriptions: {e}")
        image_desc_dict = {}

    results = []
    for item in response.data:
        document_response = supabase_client.table('documents').select('*').eq('document_id', item['metadata']['document_id']).execute()
        if document_response.data:
            document_info = document_response.data[0]
            item['metadata']['product_name'] = document_info.get('product_name', 'Unknown')
            
            # Add image description if available
            image_description = image_desc_dict.get(item['metadata']['document_id'])
            if image_description:
                item['content'] += f"\n\nImage Description: {image_description}"
        
        results.append(Document(
            page_content=item['content'],
            metadata=item['metadata']
        ))

    # Print detailed information about each retrieved document
    for i, doc in enumerate(results):
        print(f"\nDocument {i+1}:")
        print(f"Content: {doc.page_content[:200]}...")  # Print first 200 characters
        print(f"Metadata: {doc.metadata}")

    context_text = "\n\n---\n\n".join([
        f"Product: {doc.metadata.get('product_name', 'Unknown')}\n"
        f"Number of pieces: {doc.metadata.get('num_pieces', 'Unknown')}\n\n"
        f"{doc.page_content}"
        for doc in results
    ])
    
    if 'color' in query_text.lower():
        color_results = supabase_client.table('product_images').select('*').execute()
        color_data = color_results.data
        
        matching_products = []
        for product in color_data:
            if product['colors'].get(query_color, False):
                matching_products.append(product)
        
        context_text += f"\n\nProducts matching color query: {matching_products}"
    
    # Updated prompt template
    PROMPT_TEMPLATE = """
    Based on the following context about products, answer the question in English. 
    Focus on specific product names, models, features, or the number of pieces mentioned in the context. 
    Each section of the context starts with a "Product:" line and includes the number of pieces.
    Make sure to include these product names and piece counts in your answer when relevant.
    If the information is not explicitly available in the context, say so.

    Context:
    {context}

    Question: {question}

    Answer:
    """
    
    prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt = prompt_template.format(context=context_text, question=query_text)

    model = ChatOpenAI(model="gpt-3.5-turbo")
    response_text = model.invoke(prompt)

    sources = [doc.metadata.get('section_id', None) for doc in results]
    formatted_response = f"{LIGHT_BLUE}Response: {response_text.content}{RESET_COLOR}\nSources: {sources}"
    print(formatted_response)
    return response_text.content

if __name__ == "__main__":
    main()
