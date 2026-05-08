import csv
import json
import re
import sys
from pathlib import Path
from typing import Iterable, List

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Analyze eye-tracking data from exported files.")
console = Console()


def _strip_aoi_prefix(col_name: str, stimulus_name: str = "") -> str:
    """Strip Tobii AOI column prefix. 'AOI hit [1_Pre - Ballon]' -> 'Ballon'."""
    if col_name.startswith("AOI hit [") and col_name.endswith("]"):
        inner = col_name[len("AOI hit ["):-1]
        if " - " in inner:
            return inner.split(" - ", 1)[1]
    return col_name


def _load_answer_key(path: Path | None = None) -> dict[str, dict[str, str]]:
    """Load the answer key JSON. Defaults to answers.json next to the script. Returns {} if missing."""
    if path is None:
        base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
        path = base / "answers.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _compute_score(
    df: pd.DataFrame, project_name: str, answers: dict[str, dict[str, str]]
) -> tuple[int, int] | None:
    """Score keyboard responses against the answer key.

    Returns (correct, total) where total may be 0 if no scoreable events were found.
    Returns None if project_name is not in the answer key.
    """
    if project_name not in answers:
        return None

    if "Event value" not in df.columns:
        return (0, 0)

    project_answers = answers[project_name]
    correct = 0
    total = 0

    for kb_idx in df[df["Event"] == "KeyboardEvent"].index:
        prev_starts = df[(df["Event"] == "ImageStimulusStart") & (df.index < kb_idx)]
        if prev_starts.empty:
            continue

        last_start_idx = prev_starts.index[-1]
        last_start_val = str(prev_starts.iloc[-1]["Event value"])

        between_ends = df[
            (df["Event"] == "ImageStimulusEnd")
            & (df.index > last_start_idx)
            & (df.index < kb_idx)
        ]
        if not between_ends.empty:
            continue

        if last_start_val not in project_answers:
            continue

        participant_answer = str(df.loc[kb_idx]["Event value"]).strip()
        correct_answer = str(project_answers[last_start_val]).strip()

        total += 1
        if participant_answer.lower() == correct_answer.lower():
            correct += 1

    return (correct, total)


def _build_batch_summary_row(
    participant: str,
    score_result: tuple[int, int] | None,
    output_path: Path | None,
) -> dict:
    """Build a summary dict for one file in batch mode."""
    if score_result is not None and score_result[1] > 0:
        correct, total = score_result
        score_str = f"{correct} / {total} ({correct / total * 100:.2f}%)"
    else:
        score_str = "N/A"

    return {
        "participant": participant,
        "score_str": score_str,
        "export_ok": output_path is not None,
        "output_path": str(output_path) if output_path is not None else None,
    }


def _export_metrics_csv(
    df: pd.DataFrame,
    rows: list[dict],
    score: float | None,
    output_path: Path,
) -> Path:
    """Write per-stimulus metrics to a CSV file alongside session metadata."""
    first_row = df.iloc[0]
    participant_name = str(first_row["Participant name"])
    project_name = str(first_row["Project name"])
    recorded_at = (
        str(first_row["Recording date"]) if "Recording date" in df.columns else ""
    )
    score_str = "" if score is None else f"{score:.4f}"

    fieldnames = [
        "participant_name",
        "project_name",
        "recorded_at",
        "score",
        "stimulus_name",
        "num_sequences",
        "avg_ms",
        "fixation_pct",
        "aoi_fixation_count",
        "aoi_sequence",
        "aoi_hit_counts",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            avg_ms = row["avg_ms"]
            writer.writerow(
                {
                    "participant_name": participant_name,
                    "project_name": project_name,
                    "recorded_at": recorded_at,
                    "score": score_str,
                    "stimulus_name": row["stimulus"],
                    "num_sequences": row["num_sequences"],
                    "avg_ms": "" if avg_ms is None else f"{avg_ms:.4f}",
                    "fixation_pct": f"{row['fixation_pct']:.4f}",
                    "aoi_fixation_count": row.get("aoi_fixation_count", 0),
                    "aoi_sequence": " -> ".join(row["aoi_sequence"]),
                    "aoi_hit_counts": json.dumps(row["aoi_hit_counts"], ensure_ascii=False),
                }
            )

    return output_path


def _read_eye_tracking_file(file_path: Path) -> pd.DataFrame:
    """Read either an xlsx or csv eye-tracking export into a DataFrame."""
    suffix = file_path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(file_path, engine="calamine")
    if suffix == ".csv":
        return pd.read_csv(file_path, low_memory=False)
    raise typer.BadParameter(
        f"Unsupported file extension: {suffix}. Use .xlsx or .csv.",
        param_hint="file-paths",
    )


def _prepare_dataframe(file_path: Path) -> pd.DataFrame:
    df = _read_eye_tracking_file(file_path)

    required_columns = {
        "Recording timestamp",
        "Eye movement type",
        "Eye movement event duration",
        "Participant name",
        "Project name",
        "Recording date",
        "Event",
        "Fixation point X",
        "Fixation point Y",
        "Presented Stimulus name",
    }

    missing_required = required_columns.difference(df.columns)
    if missing_required:
        missing_list = ", ".join(sorted(missing_required))
        raise typer.BadParameter(
            f"File is missing required columns: {missing_list}",
            param_hint="file-path",
        )

    columns_to_keep: List[str] = sorted(
        required_columns, key=lambda col: df.columns.get_loc(col)  # type: ignore
    )  # type: ignore
    if "Event value" in df.columns:
        columns_to_keep.append("Event value")
    columns_to_keep += [col for col in df.columns if col.startswith("AOI hit")]
    df = df[columns_to_keep]
    return df


_PRE_STIMULUS_RE = re.compile(r"^\d+_PRE$")


def _collect_metrics(df: pd.DataFrame) -> Iterable[dict]:
    drop_types = {"EyesNotFound", "Unclassified"}
    movement_column = "Eye movement type"

    df = df[df["Presented Stimulus name"].apply(
        lambda s: bool(_PRE_STIMULUS_RE.match(str(s)))
    )]

    for stimulus_name, df_sequence_raw in df.groupby(
        "Presented Stimulus name", sort=False
    ):
        df_sequence_raw = df_sequence_raw[df_sequence_raw[movement_column].notna()].sort_index()
        sequence_total_length = len(df_sequence_raw)
        if sequence_total_length == 0:
            continue

        df_sequence = df_sequence_raw[
            ~df_sequence_raw[movement_column].isin(drop_types)
        ].copy()

        if not df_sequence.empty:
            df_sequence.loc[:, "group"] = (
                df_sequence[movement_column] != df_sequence[movement_column].shift()
            ).cumsum()
            fix_groups = df_sequence[
                df_sequence[movement_column] == "Fixation"
            ].groupby("group")

            num_sequences = fix_groups.ngroups
            lengths = fix_groups.size().tolist()
            overall_avg_ms = (
                fix_groups["Eye movement event duration"]
                .mean()
                .reset_index(name="avg_duration_ms")["avg_duration_ms"]
                .mean()
                if num_sequences
                else None
            )
            fixation_count = len(
                df_sequence[df_sequence[movement_column] == "Fixation"]
            )
            fixation_pct = fixation_count / sequence_total_length * 100

            aoi_hit_columns = [
                col_name
                for col_name in df_sequence.columns
                if col_name.startswith("AOI hit")
            ]
            aoi_hit_sequence: List[str] = []
            aoi_hit_counts: dict[str, int] = {}
            if aoi_hit_columns:
                fixation_rows = df_sequence[df_sequence[movement_column] == "Fixation"]
                for col_name in aoi_hit_columns:
                    clean_name = _strip_aoi_prefix(col_name, str(stimulus_name))
                    count = int((fixation_rows[col_name] == 1).sum())
                    if count > 0:
                        aoi_hit_counts[clean_name] = count

                hits_mask = fixation_rows[aoi_hit_columns] == 1
                for row_hits in hits_mask.itertuples(index=False, name=None):
                    for col_name, hit in zip(aoi_hit_columns, row_hits):
                        clean = _strip_aoi_prefix(col_name, str(stimulus_name))
                        if hit and (
                            not aoi_hit_sequence or aoi_hit_sequence[-1] != clean
                        ):
                            aoi_hit_sequence.append(clean)
        else:
            num_sequences = 0
            lengths = []
            overall_avg_ms = None
            fixation_pct = 0.0
            aoi_hit_sequence = []
            aoi_hit_counts = {}

        yield {
            "stimulus": stimulus_name,
            "rows": sequence_total_length,
            "num_sequences": num_sequences,
            "lengths": lengths,
            "avg_ms": overall_avg_ms,
            "fixation_pct": fixation_pct,
            "aoi_sequence": aoi_hit_sequence,
            "aoi_hit_counts": aoi_hit_counts,
            "aoi_fixation_count": sum(
                1 for col in aoi_hit_columns
                if int((df_sequence[df_sequence[movement_column] == "Fixation"][col] == 1).sum()) > 0
            ) if aoi_hit_columns else 0,
        }


def _pick_input_files() -> list[Path]:
    """Open a native file-picker dialog and return chosen export paths."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        console.print(
            "[red]Tk is not available in this Python build, so the file picker cannot open.[/]\n"
            "Pass file paths on the command line, e.g. [bold]python cli.py path/to/export.xlsx[/].\n"
            "On macOS Homebrew Python, install Tk with [bold]brew install python-tk@3.14[/]."
        )
        raise typer.Exit(code=1)

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    chosen = filedialog.askopenfilenames(
        title="Select Tobii export file(s)",
        filetypes=[
            ("Eye-tracking exports", "*.xlsx *.csv"),
            ("Excel files", "*.xlsx"),
            ("CSV files", "*.csv"),
            ("All files", "*.*"),
        ],
    )
    root.destroy()
    if not chosen:
        raise typer.Exit(code=0)
    return [Path(p).resolve() for p in chosen]


def _default_output_path(file_path: Path) -> Path:
    return file_path.with_name(f"{file_path.stem}_metrics.csv")


def _analyze_single(file_path: Path, output_path: Path | None) -> None:
    """Run analysis on a single file, print the table, and export results to CSV."""
    with console.status("[bold green]Analyzing data..."):
        df = _prepare_dataframe(file_path)
        answer_key = _load_answer_key()
        project_name = str(df.iloc[0]["Project name"])
        score_result = _compute_score(df, project_name, answer_key)
        rows = list(_collect_metrics(df))

    score_float: float | None = None
    correct = total = 0
    if score_result is not None and score_result[1] > 0:
        correct, total = score_result
        score_float = round(correct / total, 4)

    target = output_path if output_path is not None else _default_output_path(file_path)

    if not rows:
        console.print("[bold yellow]No fixation data found for matching stimuli.[/]")
        if score_float is not None:
            score_pct = score_float * 100
            console.print(f"\n[bold]Score:[/bold] {correct} / {total} ({score_pct:.2f}%)\n")
        with console.status(f"[bold green]Writing {target.name}..."):
            _export_metrics_csv(df, rows, score=score_float, output_path=target)
        console.print(f"[green]Exported metrics to[/] [bold cyan]{target}[/]")
        return

    table = Table(title="Eye-Tracking Sequence Metrics", show_lines=False)
    table.add_column("Stimulus", style="bold")
    table.add_column("Fixation Sequences", justify="right")
    table.add_column("Avg Fixation Duration (ms)", justify="right")
    table.add_column("Time in Fixation (%)", justify="right")
    table.add_column("AOI distincts", justify="right")

    for row in rows:
        avg_ms_display = f"{row['avg_ms']:.2f}" if row["avg_ms"] is not None else "N/A"
        fixation_pct_display = f"{row['fixation_pct']:.2f}"
        table.add_row(
            row["stimulus"],
            str(row["num_sequences"]),
            avg_ms_display,
            fixation_pct_display,
            str(row["aoi_fixation_count"]),
        )

    console.print(table)

    aoi_counts = [r["aoi_fixation_count"] for r in rows]
    if aoi_counts:
        avg_aoi = sum(aoi_counts) / len(aoi_counts)
        console.print(
            f"[bold]Avg distinct AOIs / clip (over {len(aoi_counts)} clips):[/bold] {avg_aoi:.2f}\n"
        )

    if score_float is not None:
        score_pct = score_float * 100
        console.print(f"\n[bold]Score:[/bold] {correct} / {total} ({score_pct:.2f}%)\n")

    with console.status(f"[bold green]Writing {target.name}..."):
        _export_metrics_csv(df, rows, score=score_float, output_path=target)
    console.print(f"[green]Exported metrics to[/] [bold cyan]{target}[/]")


def _analyze_batch(file_paths: List[Path], output_dir: Path | None) -> None:
    """Run analysis on multiple files, exporting one CSV per file and printing a summary."""
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

    summary_rows: list[dict] = []
    total = len(file_paths)
    answer_key = _load_answer_key()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Processing files...", total=total)

        for i, file_path in enumerate(file_paths, start=1):
            progress.update(task, description=f"[{i}/{total}] {file_path.name}")
            try:
                df = _prepare_dataframe(file_path)
                project_name = str(df.iloc[0]["Project name"])
                score_result = _compute_score(df, project_name, answer_key)
                rows = list(_collect_metrics(df))

                score_float: float | None = None
                if score_result is not None and score_result[1] > 0:
                    correct, total_q = score_result
                    score_float = round(correct / total_q, 4)

                participant = str(df.iloc[0]["Participant name"])
                if output_dir is not None:
                    target = output_dir / f"{file_path.stem}_metrics.csv"
                else:
                    target = _default_output_path(file_path)
                _export_metrics_csv(df, rows, score=score_float, output_path=target)
                summary_rows.append(
                    _build_batch_summary_row(
                        participant=participant,
                        score_result=score_result,
                        output_path=target,
                    )
                )
            except Exception as exc:
                progress.console.print(f"[yellow]Skipped {file_path.name}: {exc}[/]")
                summary_rows.append(
                    _build_batch_summary_row(
                        participant=file_path.stem,
                        score_result=None,
                        output_path=None,
                    )
                )
            progress.advance(task)

    _print_batch_summary(summary_rows)


def _print_batch_summary(summary_rows: list[dict]) -> None:
    """Print the end-of-batch summary table."""
    table = Table(title="Batch Results Summary", show_lines=False)
    table.add_column("Participant", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Export", justify="center")
    table.add_column("Output Path")

    for row in summary_rows:
        export_display = "[green]ok[/]" if row["export_ok"] else "[red]fail[/]"
        path_display = row["output_path"] if row["output_path"] else "-"
        table.add_row(
            row["participant"],
            row["score_str"],
            export_display,
            path_display,
        )

    console.print(table)


@app.command()
def analyze(
    file_paths: List[Path] = typer.Argument(
        None, exists=False, readable=True, resolve_path=True
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output CSV path (single file) or output directory (multiple files).",
    ),
) -> None:
    """Load one or more eye-tracking exports (.xlsx or .csv) and export fixation metrics to CSV."""

    if not file_paths:
        file_paths = _pick_input_files()

    for fp in file_paths:
        if not fp.exists():
            raise typer.BadParameter(f"File not found: {fp}", param_hint="file-paths")

    if len(file_paths) == 1:
        _analyze_single(file_paths[0], output_path=output)
    else:
        if output is not None and output.exists() and not output.is_dir():
            raise typer.BadParameter(
                "When analyzing multiple files, --output must be a directory.",
                param_hint="--output",
            )
        _analyze_batch(file_paths, output_dir=output)

    if getattr(sys, "frozen", False):
        input("\nPress Enter to exit...")


if __name__ == "__main__":
    app()
