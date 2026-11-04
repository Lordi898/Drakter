# Playwright CLI Reference

Complete reference for all CLI commands and options.

## npx playwright test

### Test Filtering

| Option | Description |
|--------|-------------|
| `[test-filter...]` | Regex patterns matching test file paths |
| `-g, --grep <pattern>` | Only run tests matching regex (default: ".*") |
| `--grep-invert <pattern>` | Skip tests matching regex |
| `--project <name...>` | Run specific projects, supports `*` wildcard |
| `--last-failed` | Only re-run failed tests |
| `--only-changed [ref]` | Run tests changed since git ref (default: uncommitted) |
| `--test-list <file>` | Run tests listed in file |
| `--test-list-invert <file>` | Skip tests listed in file |

### Execution Control

| Option | Description |
|--------|-------------|
| `-j, --workers <n>` | Concurrent workers (default: 50% of CPUs) |
| `--fully-parallel` | Run all tests in parallel |
| `--retries <n>` | Retry count for flaky tests |
| `--repeat-each <n>` | Run each test N times |
| `--max-failures <n>` or `-x` | Stop after N failures |
| `--timeout <ms>` | Test timeout (default: 30000) |
| `--global-timeout <ms>` | Suite timeout |
| `--shard <current/total>` | Shard tests (e.g., "1/3") |
| `--no-deps` | Skip project dependencies |

### Display Options

| Option | Description |
|--------|-------------|
| `--headed` | Show browser window |
| `--debug` | Debug with Playwright Inspector |
| `--ui` | Interactive UI mode |
| `--ui-host <host>` | UI server host |
| `--ui-port <port>` | UI server port |
| `--quiet` | Suppress stdio |
| `--list` | List tests without running |

### Output Options

| Option | Description |
|--------|-------------|
| `--reporter <type>` | Reporter: list, line, dot, json, junit, html, blob |
| `--output <dir>` | Output folder (default: test-results) |
| `--trace <mode>` | Trace mode: on, off, on-first-retry, retain-on-failure |
| `-u, --update-snapshots [mode]` | Update snapshots: all, changed, missing, none |
| `--ignore-snapshots` | Ignore snapshot assertions |

### Configuration

| Option | Description |
|--------|-------------|
| `-c, --config <file>` | Config file path |
| `--tsconfig <path>` | TypeScript config path |
| `--pass-with-no-tests` | Succeed with no tests |
| `--forbid-only` | Fail if test.only used |
| `--fail-on-flaky-tests` | Fail on flaky tests |

## npx playwright codegen

| Option | Description |
|--------|-------------|
| `[url]` | URL to record |
| `-b, --browser <name>` | Browser: chromium, firefox, webkit |
| `-o, --output <file>` | Output file |
| `--target <lang>` | Target: javascript, playwright-test, python, java, csharp |
| `--test-id-attribute <attr>` | Custom test ID attribute |

## npx playwright install

| Option | Description |
|--------|-------------|
| `[browser...]` | Specific browsers to install |
| `--with-deps` | Install system dependencies |
| `--force` | Force reinstall |
| `--dry-run` | Show what would be installed |
| `--only-shell` | Install chromium-headless-shell only |
| `--no-shell` | Skip chromium-headless-shell |

## npx playwright install-deps

| Option | Description |
|--------|-------------|
| `[browser...]` | Install deps for specific browsers |
| `--dry-run` | Show what would be installed |

## npx playwright show-report

| Option | Description |
|--------|-------------|
| `[report]` | Report directory |
| `--host <host>` | Server host (default: localhost) |
| `--port <port>` | Server port (default: 9323) |

## npx playwright show-trace

| Option | Description |
|--------|-------------|
| `[trace]` | Trace file or directory |
| `-b, --browser <name>` | Browser to view trace |
| `-h, --host <host>` | Server host |
| `-p, --port <port>` | Server port |

## npx playwright merge-reports

| Option | Description |
|--------|-------------|
| `<blob dir>` | Directory with blob reports |
| `-c, --config <file>` | Config for output |
| `--reporter <type>` | Output reporter |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `PLAYWRIGHT_BROWSERS_PATH` | Custom browser download path |
| `PLAYWRIGHT_DOWNLOAD_HOST` | Custom download server |
| `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD` | Skip browser download (=1) |
| `PWDEBUG` | Enable debug mode (=1) |
| `DEBUG` | Enable verbose logging (=pw:*) |
| `HTTPS_PROXY` | Proxy for downloads |

## Test List File Format

```
# Comments start with #

# Fully qualified with project:
[chromium] › path/to/test.spec.ts:3:9 › suite › test name

# Without project (runs in all):
path/to/test.spec.ts:3:9 › test name

# Line numbers optional:
test.spec.ts › test name

# Use › or > as separator
[firefox] > test.spec.ts > suite > test
```
