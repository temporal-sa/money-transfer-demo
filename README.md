# Money Transfer 
Demonstrates a simple Money Transfer in Temporal implemented in different languages. 

The workflow is designed so that the "Happy Path" is one workflow and all other scenarios are implemented using a Dyanmic Workflow.

Scenarios currently implemented include
* Happy Path                - everything works as intended
* Advanced Visibility       - updates a Search Attribute (Step) as it progesses through the workflow
* Require Human in the Loop - Shows how to use a signal with timeouts if not approved in time
* API Downtime              - Demonstrates an unreliable API (recovers after the 5th attempt)
* Bug in Workflow           - Purposefully throws/raises an error (fix and redeploy the worker)
* Invalid Account           - How to exit a workflow for business purposes (fail the workflow)

## Running the Demo locally
Start Temporal Locally

```bash
temporal server start-dev
```

Create a Search Attribute 
```bash
temporal operator search-attribute create --name Step --type Keyword
```

### Start the UX 
Next, start the UX which is written using the Java SDK

```bash
cd ui
./startlocalwebui.sh
```

Navigate to http://localhost:7000 in a web browser to interact with the UX

### Start a worker

Now start a worker. You can choose to use the Java, Go or .NET Worker below

#### Java Worker
In a new terminal, start the Java Worker 
```bash
cd java
./startlocalworker.sh
```

#### Golang Worker
In a new terminal, start the Golang Worker

```bash
cd go
./startlocalworker.sh
```

#### .NET Worker
In a new terminal, start the .NET Worker

```bash
cd dotnet
./startlocalworker.sh
```

## Running the Demo on Temporal Cloud
Set up a search attribute in your namespace using the following command

```bash
tcld login
tcld namespace search-attributes add --namespace <namespace>.<accountId> --search-attribute "Step=Keyword"
```

Copy the setcloundenv.example to setcloudenv.sh 
```bash
cp setcloudenv.example setcloudenv.sh
```

Edit setcloudenv.sh to match your Temporal Cloud account:
```bash
export TEMPORAL_ADDRESS=<namespace>.<accountID>.tmprl.cloud:7233
export TEMPORAL_NAMESPACE=<namespace>.<accountID>
export TEMPORAL_CERT_PATH="/path/to/cert.pem"
export TEMPORAL_KEY_PATH="/path/to/key.key"
```

### Start the UX 
Next, start the UX which is written using the Java SDK

```bash
cd ui
./startcloudwebui.sh
```

### Start a Worker

Now start a worker. You can choose to use the Java, Go or .NET Worker below

#### Java Worker
In a new terminal, start the Java Worker
```bash
cd java
./startcloudworker.sh
```

#### Golang Worker
In a new terminal, start the Golang Worker

```bash
cd go
./startcloudworker.sh
```

#### .NET Worker
In a new terminal, start the .NET Worker

```bash
cd dotnet
./startcloudworker.sh
```

#### Web Application

Instead of Flask, this application uses [Quart](https://quart.palletsprojects.com/en/latest/index.html).
If you know Flask, you will "get" Quart, but if you want a doc [here you go](https://quart.palletsprojects.com/en/latest/how_to_guides/flask_migration.html#flask-migration).

To make this easier, I provide an `.env` for the entire stack by looking at [.env.template](.env.template).

Run either with:
```sh
cd web && poetry run python main.py
```

OR, Run with [just](https://github.com/casey/just) and 
```sh
just run_web
```

###### HTML

HTML is templated with [jinja](https://jinja.palletsprojects.com/en/3.1.x/).

There is some use of `block` to achieve the [base layout](web/templates/base.html).

You can provide helper functions like I do in the `@app.context_processor` [here](web/app/index.py).

###### CSS
You can either `cd web && npm run codegen` or `just codegen`.
This will watch your css files configured by [tailwind.config.js](tailwind.config.js) and recompile.

###### JavaTypeScript

There are two  snippets [here](web/templates/index.html) and [here](web/templates/transfer.html).

The `transfer` template uses a Server-Side Event client to connect to `/sub/{{workflowid}}` in order
to receive updates from the Workflow progress. It maps the incoming data to relevant HTML elements
using plain ole DOM (`querySelector`). If you used jQuery, you can use `querySelector`.

#### HTTPS Support

Mixing HTTP and HTTPS can be a pain, even for demos. 
The Web Application supports HTTPS easily. You can provide cert by:
```sh
mkcert -install
mkcert -client localhost
```

Then provide the cert location in the `.env` file for `WEB_CONNECTION_MTLS_XXX` settings.
