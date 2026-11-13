# Ruby Money Transfer Worker
A money transfer demo worker written using the Temporal Ruby SDK, which is compatible with the Java UI.

See the main [README](../README.md) for instructions on how to use the UI.

## Prerequisites

* [Ruby](https://www.ruby-lang.org/) ~> 3.4.0
* [Bundler](https://bundler.io/) - Ruby Dependency Management

## Set up Ruby Environment
```bash
bundle install
```

## Run Worker Locally
```bash
./startlocalworker.sh
```

## Run Worker on Temporal Cloud
If you haven't updated the setcloudenv.sh file, see the main [README](../README.md) for instructions

```bash
./startcloudworker.sh
```

## Run Worker as a container
If you want to package the worker as a container image, a [Dockerfile](./Dockerfile) is supplied.

### Build the container
```bash
docker build -t ruby-worker .
```

### Run the container
```bash
docker run --rm --name ruby-worker --network <your-network-name> ruby-worker
```
Note that the worker container must have connectivity to the Temporal service.  One option is to also run Temporal as a container on the same network:

```bash
docker run --rm -p 7233:7233 -p 8233:8233 --name temporal \
--network <your-network-name> \
temporalio/temporal:latest server start-dev --ip 0.0.0.0
```

## Using Encryption
To enable payload encryption, pass `true` as an argument to the worker scripts:

```bash
./startlocalworker.sh true
./startcloudworker.sh true
```

Make sure to also enable encryption in the UI when using encrypted workers.

## Run Tests
```bash
bundle exec rspec
```