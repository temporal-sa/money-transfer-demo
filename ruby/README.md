# Ruby Money Transfer Worker
A money transfer demo worker written using the Temporal Ruby SDK, which is compatible with the Java UI.

See the main [README](../README.md) for instructions on how to use the UI.

## Prerequisites

* [Ruby](https://www.ruby-lang.org/) ~> 3.2.0
* [Bundler](https://bundler.io/) - Ruby Dependency Management

## Set up Ruby Environment
```bash
bundle install
```

## Run Worker Locally
```bash
./startlocalworker.sh
```

## Start Worker on Temporal Cloud
If you haven't updated the setcloudenv.sh file, see the main [README](../README.md) for instructions

```bash
./startcloudworker.sh
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