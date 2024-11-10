import logging

def setup_logging():
    """Sets up logging for the application."""
    logging.basicConfig(
        filename='pdf_converter.log',
        level=logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filemode='w'
    )
    # Suppress INFO logs from http.client
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    logging.getLogger('').addHandler(console)
    
    logging.getLogger('http.client').setLevel(logging.ERROR)
    logging.getLogger('httpx').setLevel(logging.ERROR)
    logging.getLogger('unstructured').setLevel(logging.ERROR)
    logging.getLogger('unstructured_ingest.v2').setLevel(logging.ERROR)
    logging.getLogger('unstructured_ingest').setLevel(logging.ERROR)
    logging.getLogger('unstructured.trace').setLevel(logging.ERROR)
    