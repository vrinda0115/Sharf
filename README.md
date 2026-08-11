
# macOS/Linux
source venv/bin/activate
```

Install Python packages:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Run the Product Prototype

Start the main Streamlit cockpit:

```bash
streamlit run streamlit_app.py
```

Use the local login screen to create a prototype account. Saved score runs and action-plan entries are stored in:

```text
data/app_memory.json
```

That file is local runtime state and should not be committed.

### Run the Static Demo

Open this file in a browser:

```text
UI/prototype/index.html
```

The static prototype uses:

```text
UI/prototype/data/app_data.js
```

Refresh that file after rebuilding datasets:

```bash
python scripts/prepare_app_data.py
```

### Rebuild Analytics Outputs

Run the full pipeline:

```bash
python code/run_pipeline.py
```

Check validation before sharing a demo:

```bash
python code/validate_sharf_dataset.py
```

### Optional Demo Video

After refreshing the static prototype data, rebuild the demo video:

```bash
python scripts/create_demo_video.py
```

This requires `ffmpeg`. The script writes frames and the final MP4 under `videos/`.

## GitHub Publishing Checklist

Before pushing to GitHub:

1. Confirm the app runs with `streamlit run streamlit_app.py`.
2. Run `python code/run_pipeline.py`.
3. Run `python scripts/prepare_app_data.py`.
4. Confirm validation results in `data/final/validation_summary.csv`.
5. Remove local runtime state such as `data/app_memory.json`.
6. Do not commit virtual environments, cache folders, local secrets, or generated logs.
7. Commit `README.md`, `requirements.txt`, source code, docs, and intentionally shared sample data.

Recommended repository topics:

```text
startup-analytics
streamlit
monte-carlo
decision-support
founder-tools
```

## Troubleshooting

If `streamlit` is not recognized, make sure the virtual environment is active and rerun:

```bash
pip install -r requirements.txt
```

If the app cannot find CSV files, run from the repository root and confirm `data/final/` exists.

If video generation fails, install `ffmpeg` and verify:

```bash
ffmpeg -version
```

If Git reports a dubious ownership warning on Windows, fix it only for this repository:

```bash
git config --global --add safe.directory C:/Users/vrind/sps_corps_analytics
```

## Documentation

- [Product Setup](PRODUCT_SETUP.md): local setup, GitHub publishing checklist, operation, and troubleshooting.
- [Research backing](docs/research_backing_for_data.md): plain-language explanation of dataset choices.
- [Empirical basis and assumptions](docs/empirical_basis_and_assumptions.md): assumptions and supporting notes.
