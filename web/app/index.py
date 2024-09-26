import sys
import os
import asyncio
from dotenv import load_dotenv

# from clients import get_clients
from quart import Quart, render_template, g, jsonify
from temporalio.service import RPCError

from app.clients import get_clients
from app.config import get_config
from app.views import get_transfer_money_form

load_dotenv()
app = Quart(__name__, template_folder='../templates', static_folder='../static')
cfg = get_config()

app_info = dict({
    'name': 'Temporal Money Transfer'
})
app_info = {**app_info, **cfg}


@app.before_serving
async def startup():
    clients = await get_clients()
    app.clients = clients
    print('clients are available at `app.clients`')


@app.after_serving
async def shutdown():
    app.clients.close()


@app.before_request
def apply_app_info():
    g.app_info = app_info


@app.context_processor
def view_app_info():
    return dict(app_info=g.app_info)


@app.route('/debug')
async def debug():
    health = False
    if app.clients.temporal and app.clients.temporal.service_client is not None:
        try:
            health = await app.temporal.service_client.check_health()
        except RPCError as e:
            health = e.message
    return jsonify({
        'app_info': app_info,
        'temporal_client_health': health,
    })


@app.route('/layout')
async def layout():
    return await render_template(template_name_or_list='layout.html')


@app.route('/')
async def index():
    form = await get_transfer_money_form()
    return await render_template(template_name_or_list='index.html', form=form)