import os
from supabase import create_client, Client  # Keep the import as 'supabase'

def get_supabase_client() -> Client:
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    print(f"Connecting to Supabase URL: {url}")
    print(f"Using Supabase key: {key[:5]}...{key[-5:]}")  # Print first and last 5 characters of the key
    
    return create_client(url, key)


