FIELD_CONFIG = {
    'unstructured_api_key': {
        'friendly_name': 'Unstructured API Key',
        'type': 'string',
        'max_length': 60,
        'section': 'API_KEYS'
    },
    'unstructured_url': {
        'friendly_name': 'Unstructured API URL',
        'type': 'string',
        'max_length': 60,
        'section': 'API_KEYS'
    },
    'openai_api_key': {
        'friendly_name': 'OpenAI API Key',
        'type': 'string',
        'max_length': 60,
        'section': 'API_KEYS'
    },
    'input_dir': {
        'friendly_name': 'Input Directory',
        'type': 'string',
        'max_length': 60,
        'section': 'DIRECTORIES'
    },
    'output_dir': {
        'friendly_name': 'Output Directory',
        'type': 'string',
        'max_length': 60,
        'section': 'DIRECTORIES'
    },
    'embedding_model': {
        'friendly_name': 'Embedding Model',
        'type': 'string',
        'max_length': 60,
        'section': 'MODEL'
    },
    'llm_model': {
        'friendly_name': 'Language Model',
        'type': 'list',
        'options': ['gpt-4o', 'gpt-4o mini', 'o1-preview'],
        'section': 'MODEL'
    },
    'save_bbox_images': {
        'friendly_name': 'Save Bounding Box Images',
        'type': 'boolean',
        'section': 'PDF_PROCESSING'
    },
    'save_document_elements': {
        'friendly_name': 'Save Document Elements',
        'type': 'boolean',
        'section': 'PDF_PROCESSING'
    },
    'logging_level': {
        'friendly_name': 'Logging Level',
        'type': 'list',
        'options': ['INFO', 'WARNING', 'CRITICAL'],
        'section': 'PDF_PROCESSING'
    },
    'show_progressbar': {
        'friendly_name': 'Show Progress Bar',
        'type': 'boolean',
        'section': 'PDF_PROCESSING'
    }
}
