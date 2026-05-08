import csv
import json
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cli import _export_metrics_csv


def _make_session_df():
    return pd.DataFrame({
        "Participant name": ["Alice"],
        "Project name": ["Proj"],
        "Recording date": ["2026-04-01"],
    })


def test_export_metrics_csv_writes_one_row_per_stimulus(tmp_path: Path):
    df = _make_session_df()
    rows = [
        {
            "stimulus": "1_PRE",
            "rows": 100,
            "num_sequences": 4,
            "lengths": [3, 4, 5, 6],
            "avg_ms": 250.5,
            "fixation_pct": 73.45,
            "aoi_sequence": ["Ballon", "Passeur"],
            "aoi_hit_counts": {"Ballon": 5, "Passeur": 3},
            "aoi_fixation_count": 2,
        },
        {
            "stimulus": "2_PRE",
            "rows": 80,
            "num_sequences": 0,
            "lengths": [],
            "avg_ms": None,
            "fixation_pct": 0.0,
            "aoi_sequence": [],
            "aoi_hit_counts": {},
            "aoi_fixation_count": 0,
        },
    ]
    out = tmp_path / "out.csv"
    written = _export_metrics_csv(df, rows, score=0.75, output_path=out)
    assert written == out
    assert out.exists()

    with out.open(encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    assert len(records) == 2
    assert records[0]["stimulus_name"] == "1_PRE"
    assert records[0]["participant_name"] == "Alice"
    assert records[0]["project_name"] == "Proj"
    assert records[0]["recorded_at"] == "2026-04-01"
    assert records[0]["score"] == "0.7500"
    assert records[0]["num_sequences"] == "4"
    assert records[0]["aoi_sequence"] == "Ballon -> Passeur"
    assert json.loads(records[0]["aoi_hit_counts"]) == {"Ballon": 5, "Passeur": 3}

    # Empty stimulus row keeps avg_ms blank when None
    assert records[1]["avg_ms"] == ""
    assert records[1]["aoi_sequence"] == ""
    assert json.loads(records[1]["aoi_hit_counts"]) == {}


def test_export_metrics_csv_omits_score_when_none(tmp_path: Path):
    df = _make_session_df()
    rows = [
        {
            "stimulus": "1_PRE",
            "rows": 10,
            "num_sequences": 1,
            "lengths": [10],
            "avg_ms": 100.0,
            "fixation_pct": 50.0,
            "aoi_sequence": [],
            "aoi_hit_counts": {},
            "aoi_fixation_count": 0,
        }
    ]
    out = tmp_path / "out.csv"
    _export_metrics_csv(df, rows, score=None, output_path=out)
    with out.open(encoding="utf-8") as f:
        records = list(csv.DictReader(f))
    assert records[0]["score"] == ""
