# S3 - SensorTwin SKAB

Pipeline reproductibil pentru incarcarea si verificarea setului **SKAB v0.9**.

## Fisiere generate

- `outputs/manifest.csv`: control de calitate pentru fiecare experiment;
- `outputs/combined_preview.csv`: previzualizare standardizata;
- `outputs/ingestion_report.json`: sumar verificabil;
- splitul este facut **pe fisiere**, nu aleator pe randuri, pentru a evita leakage temporal.

## Sursa

SKAB - Skoltech Anomaly Benchmark, v0.9, DOI: `10.34740/KAGGLE/DSV/1693952`, licenta GPL-3.0.
