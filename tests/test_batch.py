import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cli import _build_batch_summary_row


def test_row_with_score_and_output():
    row = _build_batch_summary_row(
        participant="Fred",
        score_result=(8, 10),
        output_path=Path("/tmp/fred_metrics.csv"),
    )
    assert row["participant"] == "Fred"
    assert row["score_str"] == "8 / 10 (80.00%)"
    assert row["export_ok"] is True
    assert row["output_path"] == "/tmp/fred_metrics.csv"


def test_row_without_score():
    row = _build_batch_summary_row(
        participant="Marie",
        score_result=None,
        output_path=Path("/tmp/marie_metrics.csv"),
    )
    assert row["score_str"] == "N/A"
    assert row["export_ok"] is True


def test_row_zero_total_score():
    row = _build_batch_summary_row(
        participant="Alice",
        score_result=(0, 0),
        output_path=None,
    )
    assert row["score_str"] == "N/A"
    assert row["export_ok"] is False
    assert row["output_path"] is None


def test_row_failed_export():
    row = _build_batch_summary_row(
        participant="Bob",
        score_result=(3, 5),
        output_path=None,
    )
    assert row["export_ok"] is False
    assert row["score_str"] == "3 / 5 (60.00%)"
