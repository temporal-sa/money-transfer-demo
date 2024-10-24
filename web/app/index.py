import secrets
import string
from asyncio import sleep
from typing import cast

from dotenv import load_dotenv
from quart import Quart, render_template, g, jsonify, make_response, request, abort, stream_with_context, redirect, json
from quart_cors import cors

# from clients import get_clients
from quart import Quart, render_template, g, jsonify, make_response, request, abort, stream_with_context, redirect, json
from temporalio.client import Client
from temporalio.service import RPCError

from app.clients import get_clients
from app.config import get_config
from app.messages import TransferInput
from app.models import DEFAULT_WORKFLOW_TYPE
from app.views import get_transfer_money_form, ServerSentEvent

load_dotenv()
app = Quart(__name__, template_folder='../templates', static_folder='../static')
app = cors(app,
           allow_origin='*',
           allow_headers=['X-Namespace', 'Authorization', 'Accept'],
           # allow_credentials=True,
           allow_methods=['GET', 'PUT', 'POST', 'PATCH','OPTIONS', 'DELETE', 'HEAD'],
           expose_headers=['Content-Type', 'Authorization', 'X-Namespace'])

cfg = get_config()

app_info = dict({
    'name': 'Temporal Money Transfer'
})
app_info = {**app_info, **cfg}
app.app_info = app_info

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

# this is a way to expose view helpers for things like url formatting in your templates
@app.context_processor
def url_utils():
    def url_for_namespace():
        conn = cfg.get('temporal',{}).get('connection',{})
        target = conn.get('target','')
        ns = conn.get('namespace', '')

        if 'localhost' in target.lower():
            return 'http://localhost:8233/namespaces/{ns}'.format( ns=ns)
        return 'https://cloud.temporal.io/namespaces/{ns}'.format( ns=ns)

    def url_for_workflow(id):
        return '{ns_url}/workflows/{id}'.format(ns_url=url_for_namespace(),id=id)
    return dict({
        'url_for_namespace': url_for_namespace,
        'url_for_workflow': url_for_workflow
    })

@app.route('/', methods=['GET'])
async def index():
    return redirect(location='/transfers')

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
    return await render_template(template_name_or_list='debug.html')


@app.route('/transfers', methods=['GET'])
async def get_transfers():
    form = await get_transfer_money_form()
    return await render_template(template_name_or_list='index.html', form=form)


@app.route('/transfers',methods=['POST','PUT'])
async def write_transfers():
    temporal_client = cast(Client, app.clients.temporal)
    data = await request.form
    wid = data.get('id','transfer-{id}'.format(id=secrets.choice(string.ascii_lowercase + string.digits)))
    wf_type = data.get('scenario',  DEFAULT_WORKFLOW_TYPE)
    params = TransferInput(
        amount=data.get('amount'),
        fromAccount=data.get('from_account'),
        toAccount=data.get('to_account'),
    )
    print('sending {params}'.format(params=params))

    handle = await temporal_client.start_workflow(wf_type,
                                                  id=wid,
                                                  task_queue='MoneyTransfer',
                                                  arg=params,
                                                  )

    return redirect(location='/transfers/{id}?type={wf_type}'.format(id=handle.id, wf_type=wf_type))

@app.route('/approvals/<workflow_id>', methods=['PUT','POST'])
async def approve(workflow_id):
    temporal_client = cast(Client, app.clients.temporal)
    handle = temporal_client.get_workflow_handle(workflow_id)
    await handle.signal(signal='approveTransfer')
    return redirect(location=f'/transfers/{workflow_id}')

@app.get('/transfers/<id>')
async def transfer(id):
    type = request.args.get('type')
    return await render_template(template_name_or_list='transfer.html', id=id, type=type)

@app.get("/sub/<workflow_id>")
async def sub(workflow_id):
    if "text/event-stream" not in request.accept_mimetypes:
        abort(400)
    @stream_with_context
    async def async_generator():
        while True:

            print('querying {workflow_id}'.format(workflow_id=workflow_id))
            handle = app.clients.temporal.get_workflow_handle(workflow_id)
            state = await handle.query('transferStatus')
            print(state)
            event = ServerSentEvent(data=json.dumps(state), retry=None, id=None,event=None)
            yield event.encode()
            await sleep(2)
    response = await make_response(
        async_generator(),
        {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Transfer-Encoding': 'chunked',
        },
    )
    response.timeout = None
    return response