#!/usr/bin/env python3
"""Pipeline reproductibil de ingestie si verificare pentru SKAB v0.9.

Exemplu:
    python pipeline_ingestie.py --data-dir data --output-dir outputs

Pentru corpusul complet, copiati folderul oficial SKAB/data sub data/skab/.
Scriptul cauta recursiv toate fisierele CSV.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import pandas as pd

SENSOR_COLUMNS = [
    "Accelerometer1RMS",
    "Accelerometer2RMS",
    "Current",
    "Pressure",
    "Temperature",
    "Thermocouple",
    "Voltage",
    "FlowRateRMS",
]
LABEL_COLUMNS = ["anomaly", "changepoint"]
COLUMN_ALIASES = {
    "RateRMS": "FlowRateRMS",
    "Volume Flow RateRMS": "FlowRateRMS",
    "VolumeFlowRateRMS": "FlowRateRMS",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingestie si control de calitate pentru SKAB")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def read_csv_robust(path: Path) -> pd.DataFrame:
    """Citeste CSV SKAB, acceptand separatorul ';' sau ','."""
    last_error: Exception | None = None
    for sep in (";", ","):
        try:
            frame = pd.read_csv(path, sep=sep)
            if frame.shape[1] > 2:
                return frame
        except Exception as exc:  # pragma: no cover - mesajul final pastreaza cauza
            last_error = exc
    raise ValueError(f"Nu am putut citi {path}: {last_error}")


def normalize_frame(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    frame = frame.rename(columns=COLUMN_ALIASES).copy()
    if "datetime" not in frame.columns:
        raise ValueError(f"Lipseste coloana datetime in {path}")

    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce")
    invalid_dates = int(frame["datetime"].isna().sum())
    if invalid_dates:
        raise ValueError(f"{path}: {invalid_dates} timestamp-uri invalide")

    for column in LABEL_COLUMNS:
        if column not in frame.columns:
            frame[column] = 0

    missing_sensors = [col for col in SENSOR_COLUMNS if col not in frame.columns]
    if missing_sensors:
        raise ValueError(f"{path}: lipsesc senzorii {missing_sensors}")

    numeric_columns = SENSOR_COLUMNS + LABEL_COLUMNS
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.sort_values("datetime", kind="mergesort").reset_index(drop=True)
    frame["source_file"] = path.as_posix()
    frame["scenario"] = path.parent.name
    return frame


def inspect_frame(frame: pd.DataFrame, path: Path) -> dict[str, Any]:
    deltas = frame["datetime"].diff().dt.total_seconds().dropna()
    median_step = float(deltas.median()) if not deltas.empty else None
    gap_threshold = 1.5 * median_step if median_step and median_step > 0 else None
    gaps = int((deltas > gap_threshold).sum()) if gap_threshold else 0
    max_gap = float(deltas.max()) if not deltas.empty else 0.0

    return {
        "source_file": path.as_posix(),
        "scenario": path.parent.name,
        "rows": int(len(frame)),
        "start": frame["datetime"].min().isoformat(),
        "end": frame["datetime"].max().isoformat(),
        "duration_s": float((frame["datetime"].max() - frame["datetime"].min()).total_seconds()),
        "median_step_s": median_step,
        "timestamp_gaps": gaps,
        "max_gap_s": max_gap,
        "duplicate_timestamps": int(frame["datetime"].duplicated().sum()),
        "missing_values": int(frame[SENSOR_COLUMNS + LABEL_COLUMNS].isna().sum().sum()),
        "anomaly_rows": int((frame["anomaly"] == 1).sum()),
        "changepoint_rows": int((frame["changepoint"] == 1).sum()),
    }


def assign_file_splits(paths: list[Path], seed: int) -> dict[str, str]:
    """Split 60/20/20 pe fisiere, evitand leakage intre randuri vecine."""
    ordered = sorted(paths, key=lambda p: p.as_posix())
    rng = random.Random(seed)
    rng.shuffle(ordered)
    n = len(ordered)
    n_train = max(1, round(0.60 * n))
    n_val = max(1, round(0.20 * n)) if n >= 3 else 0
    n_train = min(n_train, n - n_val)
    split_map: dict[str, str] = {}
    for index, path in enumerate(ordered):
        if index < n_train:
            split = "train"
        elif index < n_train + n_val:
            split = "validation"
        else:
            split = "test"
        split_map[path.as_posix()] = split
    return split_map


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_paths = sorted(path for path in data_dir.rglob("*.csv") if output_dir not in path.parents)
    if not csv_paths:
        raise SystemExit(f"Nu exista fisiere CSV in {data_dir}")

    split_map = assign_file_splits(csv_paths, args.seed)
    frames: list[pd.DataFrame] = []
    manifest: list[dict[str, Any]] = []

    for path in csv_paths:
        frame = normalize_frame(read_csv_robust(path), path)
        frame["split"] = split_map[path.as_posix()]
        manifest_row = inspect_frame(frame, path)
        manifest_row["split"] = split_map[path.as_posix()]
        manifest.append(manifest_row)
        frames.append(frame)

    combined = pd.concat(frames, ignore_index=True)
    manifest_df = pd.DataFrame(manifest)
    manifest_df.to_csv(output_dir / "manifest.csv", index=False)

    columns = ["datetime", *SENSOR_COLUMNS, *LABEL_COLUMNS, "scenario", "source_file", "split"]
    combined[columns].head(500).to_csv(output_dir / "combined_preview.csv", index=False)

    summary = {
        "dataset": "SKAB v0.9",
        "files_loaded": int(len(csv_paths)),
        "rows_loaded": int(len(combined)),
        "date_start": combined["datetime"].min().isoformat(),
        "date_end": combined["datetime"].max().isoformat(),
        "median_sampling_seconds": float(
            manifest_df["median_step_s"].dropna().median()
        ) if manifest_df["median_step_s"].notna().any() else None,
        "missing_values": int(manifest_df["missing_values"].sum()),
        "duplicate_timestamps": int(manifest_df["duplicate_timestamps"].sum()),
        "timestamp_gaps": int(manifest_df["timestamp_gaps"].sum()),
        "anomaly_rows": int((combined["anomaly"] == 1).sum()),
        "changepoint_rows": int((combined["changepoint"] == 1).sum()),
        "splits": manifest_df["split"].value_counts().to_dict(),
        "seed": args.seed,
        "note": "Splitul este pe fisiere/experimente. Pentru antrenare se folosesc numai randurile normale din fisierele de train.",
    }
    (output_dir / "ingestion_report.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
