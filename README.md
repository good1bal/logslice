# logslice

Fast log file slicer that filters by time range and severity without loading full files.

## Installation

```bash
pip install logslice
```

## Usage

```bash
# Filter logs by time range and severity
logslice app.log --start "2024-01-15 08:00:00" --end "2024-01-15 09:00:00" --level ERROR
```

```python
import logslice

# Slice a log file programmatically
results = logslice.slice(
    "app.log",
    start="2024-01-15 08:00:00",
    end="2024-01-15 09:00:00",
    level="ERROR"
)

for entry in results:
    print(entry)
```

### Options

| Flag | Description |
|------|-------------|
| `--start` | Start of time range (ISO format) |
| `--end` | End of time range (ISO format) |
| `--level` | Minimum severity level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `--output` | Write results to a file instead of stdout |

### Example

```bash
# Extract warnings and above from the last hour
logslice server.log --start "2024-01-15 12:00:00" --end "2024-01-15 13:00:00" --level WARNING --output filtered.log
```

logslice uses binary search and streaming reads to process large log files efficiently — no full file loading required.

## License

MIT