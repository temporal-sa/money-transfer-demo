# Rust Money Transfer Worker
A money transfer demo worker written using the Temporal Rust SDK, which is compatable with the Java UI.

See the main [README](../README.md) for instructions on how to use the UI.

## Prerequisites

* a Rust toolchain - install via [rustup](https://rustup.rs), or have `asdf`/`mise` manage it
  from [.tool-versions](../.tool-versions) (see [setup](../README.md#2-install-plugins))
* [protobuf](https://protobuf.dev/) - the Temporal Rust SDK generates its protocol
  code at build time, so `protoc` must be on your `PATH` before compiling

Installing `protoc`:

```bash
# macOS
brew install protobuf

# Debian/Ubuntu
sudo apt-get install -y protobuf-compiler
```

## Compile and Run Worker Locally

```bash
./startlocalworker.sh
```

## Compile and Run Worker on Temporal Cloud
If you haven't updated the setcloudenv.sh file, see the main [README](../README.md) for instructions

```bash
./startcloudworker.sh
```
