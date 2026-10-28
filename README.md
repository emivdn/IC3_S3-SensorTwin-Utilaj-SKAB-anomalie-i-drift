# CP1 S3 - SensorTwin SKAB

Pipeline reproductibil pentru incarcarea si verificarea setului **SKAB v0.9**.

## Rulare rapida

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python pipeline_ingestie.py --data-dir data --output-dir outputs
```

Arhiva include un extras real din `data/valve1/1.csv`, suficient pentru verificarea pipeline-ului.
Pentru analiza completa:

1. descarca repository-ul oficial `waico/SKAB`;
2. copiaza folderul `SKAB/data` in `data/skab`;
3. ruleaza aceeasi comanda.

## Fisiere generate

- `outputs/manifest.csv`: control de calitate pentru fiecare experiment;
- `outputs/combined_preview.csv`: previzualizare standardizata;
- `outputs/ingestion_report.json`: sumar verificabil;
- splitul este facut **pe fisiere**, nu aleator pe randuri, pentru a evita leakage temporal.

## Sursa

SKAB - Skoltech Anomaly Benchmark, v0.9, DOI: `10.34740/KAGGLE/DSV/1693952`, licenta GPL-3.0.
