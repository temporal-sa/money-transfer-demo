import os

from dotenv import load_dotenv

from flask import Flask, render_template, g

load_dotenv()

def get_config():
    return {
        'name': 'Temporal Money Transfer',
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
    }