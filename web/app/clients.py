import asyncio

from quart import g, current_app
from typing import Optional
from temporalio.client import Client, TLSConfig

from app.config import get_config

CONST_CLIENTS_KEY = 'clients'
CONST_TEMPORAL_CLIENT_KEY = 'temporal'



async def create_temporal_client() -> Client:
    cfg = get_config()
    temporal_cfg = cfg.get('temporal', {})
    temporal_conn = temporal_cfg.get('connection', {})
    mtls = temporal_conn.get('mtls', {})
    tls = False
    if mtls.get('cert_chain_file', {}) and mtls.get('key_file', {}) is not None:
        server_root_ca_cert: Optional[bytes] = None
        with open(mtls.get('cert_chain_file'), 'rb') as f:
            client_cert = f.read()

        with open(mtls.get('key_file'), "rb") as f:
            client_key = f.read()
        tls = TLSConfig(
            server_root_ca_cert=server_root_ca_cert,
            client_cert=client_cert,
            client_private_key=client_key,
        )

    # Start client
    client = await Client.connect(
        temporal_conn.get('target'),
        namespace=temporal_conn.get('namespace'),
        tls=tls,
        #data_converter=dataclasses.replace(
        #    temporalio.converter.default(), payload_codec=EncryptionCodec()
        #),
    )
    return client

class Clients:
    def __init__(self, temporal):
        self._temporal = temporal

    @property
    def temporal(self) -> Client:
        return self._temporal

    def close(self):
        self._temporal = None


async def get_clients() -> Clients:
    # if g.get(CONST_CLIENTS_KEY, False):
    #     return g.get(CONST_CLIENTS_KEY)


    try:
        temporal_client = await create_temporal_client()
    except:
        temporal_client = None

    return Clients(temporal=temporal_client)

    # if ctx is None:
    #     ctx = current_app.app_context()
    # with current_app.app_context():
    #     clients = g.setdefault(CONST_CLIENTS_KEY, dict({
    #         CONST_TEMPORAL_CLIENT_KEY: temporal_client
    #     }))
    # return clients
