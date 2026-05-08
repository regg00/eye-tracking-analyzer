# tests/test_metrics.py
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cli import _collect_metrics, _strip_aoi_prefix


def test_strip_aoi_prefix_standard():
    assert _strip_aoi_prefix("AOI hit [1_PRE - Ballon]", "1_PRE") == "Ballon"


def test_strip_aoi_prefix_no_match():
    # When the column doesn't match the AOI hit pattern, return as-is
    assert _strip_aoi_prefix("Some other column", "1_PRE") == "Some other column"


def test_collect_metrics_aoi_hit_counts():
    """aoi_hit_counts should count fixation rows per AOI (prefix stripped)."""
    df = pd.DataFrame({
        "Presented Stimulus name": ["1_PRE"] * 4,
        "Eye movement type": ["Fixation", "Fixation", "Saccade", "Fixation"],
        "Eye movement event duration": [200, 250, 80, 300],
        "Participant name": ["A"] * 4,
        "Project name": ["P"] * 4,
        "Recording date": ["2026-04-01"] * 4,
        "Event": [""] * 4,
        "Fixation point X": [100] * 4,
        "Fixation point Y": [100] * 4,
        "Recording timestamp": [0, 1, 2, 3],
        "AOI hit [1_PRE - Ballon]": [1, 1, 0, 0],
        "AOI hit [1_PRE - Passeur haut]": [0, 0, 0, 1],
    })

    results = list(_collect_metrics(df))
    assert len(results) == 1
    counts = results[0]["aoi_hit_counts"]
    assert counts["Ballon"] == 2
    assert counts["Passeur haut"] == 1


def test_collect_metrics_aoi_sequence_prefix_stripped():
    """aoi_sequence entries should have the stimulus prefix removed."""
    df = pd.DataFrame({
        "Presented Stimulus name": ["1_PRE"] * 3,
        "Eye movement type": ["Fixation", "Fixation", "Fixation"],
        "Eye movement event duration": [200, 250, 300],
        "Participant name": ["A"] * 3,
        "Project name": ["P"] * 3,
        "Recording date": ["2026-04-01"] * 3,
        "Event": [""] * 3,
        "Fixation point X": [100] * 3,
        "Fixation point Y": [100] * 3,
        "Recording timestamp": [0, 1, 2],
        "AOI hit [1_PRE - Ballon]": [1, 0, 0],
        "AOI hit [1_PRE - Passeur haut]": [0, 1, 0],
    })

    results = list(_collect_metrics(df))
    seq = results[0]["aoi_sequence"]
    assert "Ballon" in seq
    assert "Passeur haut" in seq
    assert all("AOI hit" not in s for s in seq)


def test_prepare_dataframe_missing_recording_date_raises():
    """Recording date column must be present or _prepare_dataframe raises."""
    import csv
    import tempfile
    from pathlib import Path

    import pytest
    import typer

    from cli import _prepare_dataframe

    rows = [
        {
            "Recording timestamp": 0,
            "Eye movement type": "Fixation",
            "Eye movement event duration": 200,
            "Participant name": "A",
            "Project name": "P",
            # Recording date intentionally missing
            "Event": "",
            "Fixation point X": 100,
            "Fixation point Y": 100,
            "Presented Stimulus name": "1_PRE",
        }
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        tmp_path = f.name

    with pytest.raises(typer.BadParameter):
        _prepare_dataframe(Path(tmp_path))
