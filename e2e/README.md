# E2E Tests for Money Transfer Demo

This folder contains end-to-end tests using Playwright for the money transfer demo.

## Running Tests

Run the complete test suite (installs dependencies and runs tests):
```bash
./run.sh
```

Available flags:
- `--headed` - Run tests with browser visible
- `--verbose` - Enable verbose output
- `--only <worker>` - Run tests for specific worker only (go, ruby, dotnet, java, python, typescript, rust)

Examples:
```bash
./run.sh --headed
./run.sh --verbose
./run.sh --only go
./run.sh --headed --verbose --only python
```

Or run tests manually:
```bash
npm install
npx playwright install
npm test
```

Run tests with browser visible:
```bash
npm run test:headed
```
