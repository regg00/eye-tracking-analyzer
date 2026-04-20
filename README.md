# Eye-Tracking Analyzer

Typer-based command-line tool for exploring Tobii eye-tracking exports and summarising fixation behaviour per stimulus.

## Repository Contents

- `cli.py` – CLI entry point that loads a CSV export, derives fixation metrics, and prints them in a Rich table.
- `data.csv` – Sample export containing gaze classifications, fixation durations, AOI hit flags, and stimulus metadata.
- `PoC.ipynb` – Original exploratory notebook kept for reference.

## Features

- Loads raw CSV exports with pandas while validating required columns.
- Groups rows by `Presented Stimulus name` and reports metrics only for stimuli whose name contains `Pré`.
- Drops `EyesNotFound` and `Unclassified` states before computing fixation-only statistics.
- Displays counts, sequence lengths, average fixation duration, fixation percentage, and AOI hit sequences in a Rich table.

## Requirements

- Python 3.10+
- Dependencies: `pandas`, `typer`, `rich`

Install them with:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pandas typer rich
```

## Usage

```bash
python3 cli.py path/to/export.csv
```

The command resolves the CSV path, filters out rows with missing eye-movement labels, and prints metrics for each stimulus that contains the substring `Pré`.

### Example Output

```
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Stimulus              ┃ Rows ┃ Fixation Sequences ┃ Sequence Lengths  ┃ Avg Fixation Duration (ms)  ┃ Time in Fixation ┃ AOI Hit Sequence             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
┃ 2v1_Pré               ┃ 1234 ┃ 15                 ┃ 6, 12, 4          ┃ 87.45                        ┃ 68.32%           ┃ AOI hit Region 1 → AOI hit 2 ┃
└───────────────────────┴──────┴────────────────────┴───────────────────┴──────────────────────────────┴──────────────────┴──────────────────────────────┘
```

_Values above are illustrative; run the CLI with your export to see actual data._

### Example Run

[![asciicast](https://asciinema.org/a/zg8DuXGu1c4d3aDC9PHZRPcL5.svg)](https://asciinema.org/a/zg8DuXGu1c4d3aDC9PHZRPcL5)

## Input Expectations

The CSV must include these columns:
`Recording timestamp`, `Eye movement type`, `Gaze event duration`, `Participant name`, `Project name`, `Event`, `Fixation point X`, `Fixation point Y`, `Presented Stimulus name`, plus any `AOI hit*` columns used for AOI sequences.

## Development Notes

- The CLI is implemented in `cli.py` using Typer for argument parsing and Rich for table rendering.
- Extend `_collect_metrics` if you need to adjust filtering logic or compute additional statistics.
