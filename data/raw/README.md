# Raw historical data staging

Place input CSV files for `signal-validation build-wr-tables` in this directory.

The canonical contract is documented in `docs/DATA_CONTRACT.md`.

Generate a real historical source file with `python scripts/build_real_wr_data.py`, which targets `data/raw/player_weekly_history.csv`.
