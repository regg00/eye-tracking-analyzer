from pathlib import Path
from typing import Iterable, List

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Analyze eye-tracking data from exported CSV files.")
console = Console()


def _strip_aoi_prefix(col_name: str, stimulus_name: str) -> str:
    """Strip Tobii AOI column prefix. 'AOI hit [1_Pré - Ballon]' → 'Ballon'."""
    prefix = f"AOI hit [{stimulus_name} - "
    if col_name.startswith(prefix) and col_name.endswith("]"):
        return col_name[len(prefix):-1]
    return col_name


def _prepare_dataframe(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, low_memory=False)

    required_columns = {
        "Recording timestamp",
        "Eye movement type",
        "Eye movement event duration",
        "Participant name",
        "Project name",
        "Event",
        "Fixation point X",
        "Fixation point Y",
        "Presented Stimulus name",
    }

    missing_required = required_columns.difference(df.columns)
    if missing_required:
        missing_list = ", ".join(sorted(missing_required))
        raise typer.BadParameter(
            f"CSV file is missing required columns: {missing_list}",
            param_hint="csv-path",
        )

    columns_to_keep: List[str] = sorted(
        required_columns, key=lambda col: df.columns.get_loc(col)  # type: ignore
    )  # type: ignore
    columns_to_keep += [col for col in df.columns if col.startswith("AOI hit")]
    df = df[columns_to_keep]

    df = df.dropna(subset=["Eye movement type"])
    return df


def _collect_metrics(df: pd.DataFrame) -> Iterable[dict]:
    drop_types = {"EyesNotFound", "Unclassified"}
    movement_column = "Eye movement type"

    for stimulus_name, df_sequence_raw in df.groupby(
        "Presented Stimulus name", sort=False
    ):
        if "Pré" not in stimulus_name:  # type: ignore
            continue
        df_sequence_raw = df_sequence_raw.sort_index()
        sequence_total_length = len(df_sequence_raw)
        if sequence_total_length == 0:
            continue

        df_sequence = df_sequence_raw[
            ~df_sequence_raw[movement_column].isin(drop_types)
        ].copy()

        if not df_sequence.empty:
            df_sequence["group"] = (
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
        }


@app.command()
def analyze(
    csv_path: Path = typer.Argument(..., exists=True, readable=True, resolve_path=True)
) -> None:
    """Load a CSV export and display fixation metrics by stimulus."""

    df = _prepare_dataframe(csv_path)
    rows = list(_collect_metrics(df))

    if not rows:
        console.print("[bold yellow]No data to display after filtering.[/]")
        raise typer.Exit(code=0)

    table = Table(title="Eye-Tracking Sequence Metrics", show_lines=False)
    table.add_column("Stimulus", style="bold")
    # table.add_column("Rows", justify="right")
    table.add_column("Fixation Sequences", justify="right")
    # table.add_column("Sequence Lengths", justify="right")
    table.add_column("Avg Fixation Duration (ms)", justify="right")
    table.add_column("Time in Fixation (%)", justify="right")
    table.add_column("AOI Hit Sequence")

    for row in rows:
        avg_ms_display = f"{row['avg_ms']:.2f}" if row["avg_ms"] is not None else "N/A"
        fixation_pct_display = f"{row['fixation_pct']:.2f}"
        aoi_sequence_display = (
            " → ".join(row["aoi_sequence"]) if row["aoi_sequence"] else "-"
        )

        table.add_row(
            row["stimulus"],
            # str(row["rows"]),
            str(row["num_sequences"]),
            # lengths_display,
            avg_ms_display,
            fixation_pct_display,
            aoi_sequence_display,
        )

    console.print(table)


if __name__ == "__main__":
    app()
