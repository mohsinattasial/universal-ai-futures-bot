# ApexQuant — Experimental ML Market Dashboard

Streamlit demo using candlestick market data, technical indicators and a 25-feature XGBoost classifier. **For education and research only—not trading advice.**

## Run
```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Files: `app.py` (UI), `config.py` (settings), `exchange.py` (market fetch), `model.py` (features and classifier), `database.py` (authentication/storage).

Database credentials or a PostgreSQL URL may be required; do not commit secrets. Prediction scores are **not independently validated success probabilities**. Evaluate with time-ordered train/test splits, transaction costs, walk-forward tests and calibration before making any claims about performance. Clearly distinguish fallback/simulated prices from live data. Never load untrusted `.pkl` files.

Author: Mohsin Atta.
