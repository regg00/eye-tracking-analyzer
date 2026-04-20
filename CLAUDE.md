# Eye-Tracking Analyzer

CLI tool that parses Tobii eye-tracking CSV exports and reports fixation metrics per stimulus.

## Project Structure

- `cli.py` — single-file CLI; all logic lives here
- `requirements.txt` — runtime deps (`pandas`, `typer`, `rich`)
- `requirements-dev.txt` — dev deps
- `.github/workflows/build-release.yml` — builds a Windows `.exe` via PyInstaller on GitHub release

## Running

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 cli.py path/to/export.csv
```

## Key Implementation Notes

### Required CSV columns

`cli.py` validates these columns at load time:
- `Recording timestamp`
- `Eye movement type`
- `Eye movement event duration` ← renamed from `Gaze event duration` in newer Tobii exports
- `Participant name`
- `Project name`
- `Event`
- `Fixation point X` / `Fixation point Y`
- `Presented Stimulus name`
- Any `AOI hit [...]` columns (auto-detected by prefix)

### Filtering logic (`_collect_metrics`)

- Only processes stimuli whose name contains `Pré`
- Drops rows where `Eye movement type` is `EyesNotFound` or `Unclassified`
- Groups consecutive rows of the same movement type into sequences before computing fixation stats

### Release process

Tagging a GitHub release triggers the workflow, which produces `eye-tracking-analyzer.exe` as a release asset.
