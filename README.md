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

## Dependencies

The language runtime versions can be easily installed using [asdf](https://asdf-vm.com/).  **See [full setup instructions below](#asdf)**
```bash
asdf install
```

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

Navigate to http://localhost:7070 in a web browser to interact with the UX

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

#### Python Worker
In a new terminal, start the Python Worker

```bash
cd python
# If you haven't done this yet, install the dependencies
poetry install
./startlocalworker.sh
```

#### TypeScript Worker
In a new terminal, start the TypeScript Worker

```bash
cd typescript
# If you haven't done this yet, install the dependencies
npm install
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
# either using mTLS
export TEMPORAL_ADDRESS=<namespace>.<accountID>.tmprl.cloud:7233
export TEMPORAL_NAMESPACE=<namespace>.<accountID>
export TEMPORAL_CERT_PATH="/path/to/cert.pem"
export TEMPORAL_KEY_PATH="/path/to/key.key"

# or API keys
export TEMPORAL_ADDRESS=<region>.<cloud_provider>.api.temporal.io:7233
export TEMPORAL_NAMESPACE=<namespace>.<accountID>
export TEMPORAL_API_KEY=<api_key>
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

#### Python Worker
In a new terminal, start the Python Worker

```bash
cd python
# If you haven't done this yet, install the dependencies
poetry install
./startcloudworker.sh
```

#### TypeScript Worker
In a new terminal, start the Python Worker

```bash
cd python
# If you haven't done this yet, install the dependencies
npm install
./startcloudworker.sh
```

## Using Encryption
This demo supports encyrption by setting the environment variable ENCRYPT_PAYLOADS to true. To make this easier, each of the start*.sh files will use the first parameter to set this variable. If you want to use encryption, be sure to set this for the UI and the worker that you choose. For example:

### Start the UX 
Next, start the UX which is written using the Java SDK

```bash
cd ui
./startcloudwebui.sh true
```

### Java Worker Example -- works for other SDKs as well
In a new terminal, start the Java Worker
```bash
cd java
./startcloudworker.sh true
```

To view the decrypted data in your browser, you can set the Codec Server to use [https://codec.tmprl-demo.cloud](https://codec.tmprl-demo.cloud). Be sure to enable the "Pass the user access token" slider. This will work as long as you do not change the encryption key. 

# asdf

The runtime versions for the prerequisites identified in this README can be managed
using [asdf](https://asdf-vm.com/). The runtime versions are specified in the [.tool-versions](.tool-versions)
file.

To get all of the needed language runtime versions installed and working should be a quick 3 step process:
1. Install `asdf` for your machine
2. Install the runtime ***plugins*** needed
3. Install the specific runtime ***versions*** needed for the projects for this repository

## 1. Install & Configure

Install and configure `asdf` per the [Getting Started Guide](https://asdf-vm.com/guide/getting-started.html#getting-started)

## 2. Install Plugins

Add [plugins](https://asdf-vm.com/manage/plugins.html) for the tools in [.tool-versions](.tool-versions)

```sh
asdf plugin add dotnet-core
asdf plugin add golang
asdf plugin add java
asdf plugin add nodejs
asdf plugin add pnpm
asdf plugin add poetry
asdf plugin add python
asdf plugin add ruby
```

> [!NOTE]
> Rust is deliberately excluded from the list above. If you already manage Rust with [rustup](https://rustup.rs),
> skip this step — asdf would install a second, standalone Rust toolchain whose shims compete with rustup's on
> your `PATH`. If you do not use rustup and want `asdf` to manage Rust for you, register the plugin:

```sh
asdf plugin add rust
```

> [!NOTE]
> Adding the Plugins does not actually install any runtimes or tools (i.e. a Go runtime) on your machine. You will install the
> runtime versions in the next step

## 3. Install Tool Versions

Ensure you run the following `asdf install` command from within the same directory as this README.md file. This directory
contains the `.tools-verions` file, which will tell `asdf` which specific versions to install and configure for your environment.

```sh
> cd temporal-money-transfer-demo
> asdf install

# Example Output
# for any version that you don't yet have installed, you will see output of asdf downloading and installing, e.g.
Platform 'darwin' supported!
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 72.8M  100 72.8M    0     0  2816k      0  0:00:26  0:00:26 --:--:-- 2847k
verifying checksum
/Users/psullivan/.asdf/downloads/golang/1.23.12/archive.tar.gz: OK
checksum verified

# for any version that you already have installed, you will see output similar to
version 1.23.12 of golang is already installed
```

Once installed, then every time you `cd` into this directory, e.g. `cd temporal-money-transfer-demo` asdf will automatically use these
versions for the tool runtimes invoked, i.e. invoking `go` will specifically use version `1.23.12` installed by asdf in the example
output above, e.g.
```
> cd temporal-money-transfer-demo
> go version
go version go1.23.12 darwin/arm64
```


