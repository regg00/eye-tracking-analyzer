# Eye-Tracking Analyzer

Typer-based command-line tool for exploring Tobii eye-tracking exports and writing per-stimulus fixation metrics to a CSV file.

## Repository Contents

- `cli.py` — CLI entry point that loads an export, derives fixation metrics, prints a Rich table, and writes the metrics to CSV.
- `tests/` — pytest suite.

## Features

- Loads `.xlsx` (via `python-calamine`) or `.csv` exports while validating required columns.
- Groups rows by `Presented Stimulus name` and reports metrics for stimuli matching `^\d+_PRE$`.
- Drops `EyesNotFound` and `Unclassified` states before computing fixation-only statistics.
- Displays counts, average fixation duration, fixation percentage, and AOI hit counts in a Rich table.
- Writes a `*_metrics.csv` file with one row per stimulus, including session metadata and an optional score.
- Supports batch mode: pass multiple files (or omit args to open a native file picker) to produce one CSV per file.
- Optional scoring of keyboard responses against an `answers.json` answer key keyed by Tobii project name.

## Windows: Download and Run the Prebuilt `.exe`

A standalone Windows executable is published with every release; no Python install required.

1. Open the [Releases page](https://github.com/regg00/eye-tracking-analyzer/releases) and pick the latest tag.
2. Under **Assets**, download `eye-tracking-analyzer-vX.Y.Z.exe`.
3. (Recommended) Move it to a folder of your choice, e.g. `C:\Tools\eye-tracking\`.
4. If Windows SmartScreen blocks it, click **More info → Run anyway** (the binary is unsigned).

### Run from File Explorer

Double-click the `.exe`. A file picker opens; select one or more Tobii exports (`.xlsx`). Each input produces a `<stem>_metrics.csv` next to it. The window stays open until you press Enter.

### Run from PowerShell or cmd

```powershell
cd C:\Tools\eye-tracking
.\eye-tracking-analyzer-v1.0.0.exe path\to\export.xlsx
.\eye-tracking-analyzer-v1.0.0.exe session1.xlsx session2.xlsx --output C:\out\
```

Drop an optional `answers.json` (see [Optional Answer Key](#optional-answer-key-scoring)) next to the `.exe` to enable scoring.

## Run from Source

### Requirements

- Python 3.10+
- Dependencies: `pandas`, `python-calamine`, `typer`, `rich`

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Usage

```bash
python3 cli.py path/to/export.xlsx
python3 cli.py session1.xlsx session2.xlsx --output /tmp/out
```

Without args, a file picker dialog opens (requires Tk; on macOS Homebrew Python install with `brew install python-tk@3.X`).

By default, results land next to the input file as `<stem>_metrics.csv`. With multiple files, `--output` (if given) must be a directory.

### Output columns

Each row in the exported CSV represents one stimulus and contains:

| Column               | Description                                                    |
| -------------------- | -------------------------------------------------------------- |
| `participant_name`   | From `Participant name` column                                 |
| `project_name`       | From `Project name` column                                     |
| `recorded_at`        | From `Recording date` column                                   |
| `score`              | Fraction (0.0–1.0) when scoring was available, blank otherwise |
| `stimulus_name`      | The stimulus identifier                                        |
| `num_sequences`      | Count of fixation sequences                                    |
| `avg_ms`             | Mean fixation duration (ms)                                    |
| `fixation_pct`       | Time-in-fixation percentage                                    |
| `aoi_fixation_count` | Distinct AOIs hit during fixations                             |
| `aoi_sequence`       | Ordered AOIs visited (joined by `->`)                          |
| `aoi_hit_counts`     | JSON object mapping AOI name to hit count                      |

## Input Expectations

The input must include these columns:
`Recording timestamp`, `Eye movement type`, `Eye movement event duration`, `Participant name`, `Project name`, `Recording date`, `Event`, `Fixation point X`, `Fixation point Y`, `Presented Stimulus name`, plus any `AOI hit [...]` columns used for AOI sequences.

## Optional Answer Key (Scoring)

Place an `answers.json` file next to `cli.py` (or the bundled `.exe`). It is keyed by **Tobii project name**, then by **image name** (the `Event value` of each `ImageStimulusStart` event), with the correct answer as the value:

```json
{
  "ProjectA": {
    "Pass1": "Right",
    "1_SS": "4"
  }
}
```

Matching is case-insensitive. If the file is missing or the project is not present, scoring is silently skipped and no score is shown.

## Development

Install dev dependencies and run tests:

```bash
pip install -r requirements-dev.txt
pytest
```

The CLI is implemented in `cli.py` using Typer for argument parsing and Rich for table rendering. Extend `_collect_metrics` to adjust filtering logic or compute additional statistics.
