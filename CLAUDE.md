# Eye-Tracking Analyzer

CLI tool that parses Tobii eye-tracking exports (.xlsx or .csv) and writes per-stimulus fixation metrics to a CSV file.

## Project Structure

- `cli.py` — single-file CLI; all logic lives here
- `requirements.txt` — runtime deps (`pandas`, `python-calamine`, `typer`, `rich`)
- `requirements-dev.txt` — dev deps
- `.github/workflows/build-release.yml` — builds a Windows `.exe` via PyInstaller

## Running

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 cli.py path/to/export.xlsx
```

Output: a `*_metrics.csv` written next to the input file (override with `--output`).

## Key Implementation Notes

### Required columns

`cli.py` validates these columns at load time:
- `Recording timestamp`
- `Eye movement type`
- `Eye movement event duration`
- `Participant name`
- `Project name`
- `Recording date`
- `Event`
- `Fixation point X` / `Fixation point Y`
- `Presented Stimulus name`
- Any `AOI hit [...]` columns (auto-detected by prefix)

### Filtering logic (`_collect_metrics`)

- Only processes stimuli whose name matches `^\d+_PRE$`
- Drops rows where `Eye movement type` is `EyesNotFound` or `Unclassified`
- Groups consecutive rows of the same movement type into sequences before computing fixation stats

### Optional scoring

If `answers.json` sits next to `cli.py` (or the bundled `.exe`), the tool scores keyboard responses against the answer key keyed by Tobii project name. If the file is missing or the project is not present, scoring is silently skipped.

### Release process

Pushing to `main` triggers the workflow, which produces `eye-tracking-analyzer-vX.Y.Z.exe` as a release asset.
