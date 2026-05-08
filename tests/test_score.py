import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from cli import _compute_score, _load_answer_key


def test_load_answer_key_returns_dict_when_file_exists(tmp_path):
    key_file = tmp_path / "answers.json"
    key_file.write_text(json.dumps({"Proj": {"Img1": "4"}}), encoding="utf-8")
    result = _load_answer_key(key_file)
    assert result == {"Proj": {"Img1": "4"}}


def test_load_answer_key_returns_empty_dict_when_file_missing(tmp_path):
    result = _load_answer_key(tmp_path / "answers.json")
    assert result == {}


def _make_event_df(events):
    return pd.DataFrame({
        "Event": [e[0] for e in events],
        "Event value": [e[1] for e in events],
    })


def test_compute_score_all_correct():
    df = _make_event_df([
        ("ImageStimulusStart", "Pass1"),
        ("KeyboardEvent", "Right"),
        ("ImageStimulusEnd", "Pass1"),
        ("ImageStimulusStart", "1_SS"),
        ("KeyboardEvent", "4"),
        ("ImageStimulusEnd", "1_SS"),
    ])
    answers = {"Proj": {"Pass1": "Right", "1_SS": "4"}}
    assert _compute_score(df, "Proj", answers) == (2, 2)


def test_compute_score_some_wrong():
    df = _make_event_df([
        ("ImageStimulusStart", "Pass1"),
        ("KeyboardEvent", "Left"),
        ("ImageStimulusEnd", "Pass1"),
        ("ImageStimulusStart", "1_SS"),
        ("KeyboardEvent", "4"),
        ("ImageStimulusEnd", "1_SS"),
    ])
    answers = {"Proj": {"Pass1": "Right", "1_SS": "4"}}
    assert _compute_score(df, "Proj", answers) == (1, 2)


def test_compute_score_project_not_in_answers_returns_none():
    df = _make_event_df([
        ("ImageStimulusStart", "Pass1"),
        ("KeyboardEvent", "Right"),
        ("ImageStimulusEnd", "Pass1"),
    ])
    assert _compute_score(df, "UnknownProject", {"OtherProject": {}}) is None


def test_compute_score_case_insensitive():
    df = _make_event_df([
        ("ImageStimulusStart", "Pass1"),
        ("KeyboardEvent", "right"),
        ("ImageStimulusEnd", "Pass1"),
    ])
    answers = {"Proj": {"Pass1": "Right"}}
    assert _compute_score(df, "Proj", answers) == (1, 1)


def test_compute_score_keyboard_after_image_ended_is_skipped():
    df = _make_event_df([
        ("ImageStimulusStart", "Pass1"),
        ("ImageStimulusEnd", "Pass1"),
        ("KeyboardEvent", "Right"),
    ])
    answers = {"Proj": {"Pass1": "Right"}}
    assert _compute_score(df, "Proj", answers) == (0, 0)


def test_compute_score_image_not_in_answer_key_is_skipped():
    df = _make_event_df([
        ("ImageStimulusStart", "UnknownImage"),
        ("KeyboardEvent", "4"),
        ("ImageStimulusEnd", "UnknownImage"),
    ])
    answers = {"Proj": {"Pass1": "Right"}}
    assert _compute_score(df, "Proj", answers) == (0, 0)
