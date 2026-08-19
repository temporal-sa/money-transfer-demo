# Rust Money Transfer Worker
A money transfer demo worker written using the Temporal Rust SDK, which is compatable with the Java UI.

See the main [README](../README.md) for instructions on how to use the UI.

## Prerequisites

* [protobuf](https://protobuf.dev/) - the Temporal Rust SDK generates its protocol
  code at build time, so `protoc` must be on your `PATH` before compiling

```bash
# macOS
brew install protobuf

# Debian/Ubuntu
sudo apt-get install -y protobuf-compiler
```

The Rust toolchain itself is pinned in [.tool-versions](../.tool-versions) and is
installed along with `cargo` by running `asdf install` (or `mise install`) from the
repository root.

## Compile and Run Worker Locally

```bash
./startlocalworker.sh
```

## Compile and Run Worker on Temporal Cloud
If you haven't updated the setcloudenv.sh file, see the main [README](../README.md) for instructions

```bash
./startcloudworker.sh
```
