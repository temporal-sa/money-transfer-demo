import os
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

def get_config() -> dict:
    web_url = urlparse(os.getenv('PUBLIC_WEB_URL','http://localhost'))
    web_port = os.getenv('WEB_PORT','7070')
    return {
        'name': 'Temporal Payments',
        'temporal': {
            'connection': {
                'target': os.getenv('TEMPORAL_ADDRESS','127.0.0.1:7233'),
                'namespace': os.getenv('TEMPORAL_NAMESPACE','default'),
                'mtls': {
                    'key_file': os.getenv('TEMPORAL_KEY_PATH',''),
                    'cert_chain_file': os.getenv('TEMPORAL_CERT_PATH',''),
                }
            },
            'worker': {
                'task_queue': os.getenv('TEMPORAL_WORKER_TASK_QUEUE')
            },
            'encrypt' : True if os.getenv('ENCRYPT_PAYLOADS','false').lower() == "true" else False
        },
        'web': {
            'url': web_url,
            'port': web_port,
            'connection': {
                'mtls': {
                    'key_file': os.getenv('WEB_CONNECTION_MTLS_KEY_FILE'),
                    'cert_chain_file': os.getenv('WEB_CONNECTION_MTLS_CERT_CHAIN_FILE')
                }
            }
        }
    }