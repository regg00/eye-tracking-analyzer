# tests/test_metrics.py
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cli import _strip_aoi_prefix, _collect_metrics


def test_strip_aoi_prefix_standard():
    assert _strip_aoi_prefix("AOI hit [1_Pré - Ballon]", "1_Pré") == "Ballon"


def test_strip_aoi_prefix_no_match():
    # When the column doesn't match the expected pattern, return as-is
    assert _strip_aoi_prefix("AOI hit [2_Pré - Ballon]", "1_Pré") == "AOI hit [2_Pré - Ballon]"


def test_collect_metrics_aoi_hit_counts():
    """aoi_hit_counts should count fixation rows per AOI (prefix stripped)."""
    df = pd.DataFrame({
        "Presented Stimulus name": ["1_Pré"] * 4,
        "Eye movement type": ["Fixation", "Fixation", "Saccade", "Fixation"],
        "Eye movement event duration": [200, 250, 80, 300],
        "Participant name": ["A"] * 4,
        "Project name": ["P"] * 4,
        "Recording date": ["2026-04-01"] * 4,
        "Event": [""] * 4,
        "Fixation point X": [100] * 4,
        "Fixation point Y": [100] * 4,
        "Recording timestamp": [0, 1, 2, 3],
        "AOI hit [1_Pré - Ballon]": [1, 1, 0, 0],
        "AOI hit [1_Pré - Passeur haut]": [0, 0, 0, 1],
    })

    results = list(_collect_metrics(df))
    assert len(results) == 1
    counts = results[0]["aoi_hit_counts"]
    # 2 fixation rows hit Ballon, 1 fixation row hits Passeur haut
    assert counts["Ballon"] == 2
    assert counts["Passeur haut"] == 1


def test_collect_metrics_aoi_sequence_prefix_stripped():
    """aoi_sequence entries should have the stimulus prefix removed."""
    df = pd.DataFrame({
        "Presented Stimulus name": ["1_Pré"] * 3,
        "Eye movement type": ["Fixation", "Fixation", "Fixation"],
        "Eye movement event duration": [200, 250, 300],
        "Participant name": ["A"] * 3,
        "Project name": ["P"] * 3,
        "Recording date": ["2026-04-01"] * 3,
        "Event": [""] * 3,
        "Fixation point X": [100] * 3,
        "Fixation point Y": [100] * 3,
        "Recording timestamp": [0, 1, 2],
        "AOI hit [1_Pré - Ballon]": [1, 0, 0],
        "AOI hit [1_Pré - Passeur haut]": [0, 1, 0],
    })

    results = list(_collect_metrics(df))
    seq = results[0]["aoi_sequence"]
    assert "Ballon" in seq
    assert "Passeur haut" in seq
    # No entry should contain "AOI hit"
    assert all("AOI hit" not in s for s in seq)


def test_collect_metrics_recording_date_in_df():
    """Recording date column must be present or _prepare_dataframe raises."""
    import pytest
    import typer
    from cli import _prepare_dataframe
    import tempfile, csv

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
            "Presented Stimulus name": "1_Pré",
        }
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        tmp_path = f.name

    from pathlib import Path
    with pytest.raises(typer.BadParameter):
        _prepare_dataframe(Path(tmp_path))
