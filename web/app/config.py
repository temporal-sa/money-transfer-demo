import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

def get_config() -> dict:
    web_url = urlparse(os.getenv('PUBLIC_WEB_URL'))
    return {
        'name': 'Temporal Payments',
        'temporal': {
            'connection': {
                'target': os.getenv('TEMPORAL_CONNECTION_TARGET'),
                'namespace': os.getenv('TEMPORAL_CONNECTION_NAMESPACE'),
                'mtls': {
                    'key_file': os.getenv('TEMPORAL_CONNECTION_MTLS_KEY_FILE'),
                    'cert_chain_file': os.getenv('TEMPORAL_CONNECTION_MTLS_CERT_CHAIN_FILE'),
                }
            },
            'worker': {
                'task_queue': os.getenv('TEMPORAL_WORKER_TASK_QUEUE')
            }
        },
        'web': {
            'url': web_url,
            'connection': {
                'mtls': {
                    'key_file': os.getenv('WEB_CONNECTION_MTLS_KEY_FILE'),
                    'cert_chain_file': os.getenv('WEB_CONNECTION_MTLS_CERT_CHAIN_FILE')
                }
            }
        }
    }