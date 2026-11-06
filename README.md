# Job Market Analytics and Salary Prediction System

A Flask application for exploring the supplied job-market dataset and estimating salaries with the existing Random Forest pipeline. The app does not retrain or modify the notebook or model.

## Requirements

- Python 3.10–3.13 (recommended for the scikit-learn version used to save the model)
- MongoDB Community Server running locally, or a MongoDB URI you can access
- The supplied `cleaned_job_market_dataset.csv` and `final_salary_prediction_model.pkl` in the project root

The saved pipeline was produced with scikit-learn 1.7.2. A small in-memory compatibility adjustment supports newer scikit-learn versions when the saved `SimpleImputer` is missing its renamed dtype attribute; no model is retrained or written back.

## Install and run

Install MongoDB Community Server first. If it is installed as the standard Windows service, start it from an elevated PowerShell window:

```powershell
Get-Service MongoDB
Start-Service MongoDB
mongosh --eval "db.runCommand({ ping: 1 })"
```

Open PowerShell in this project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` if MongoDB is not using the local default URI. The `.env.example` contains local-development defaults only. With MongoDB running, start Flask:

```powershell
python app.py
```

Open <http://127.0.0.1:5000/>.

To use a different model or dataset location, set `MODEL_PATH` or `DATASET_PATH` in `.env`. The default model path points to the supplied `final_salary_prediction_model.pkl`; `salary_prediction_model.pkl` is not substituted automatically.

## Pages and API

- `/` — project landing page
- `/dashboard` — dataset-backed KPIs and interactive charts
- `/analysis` — roles, skills, country openings, and experience analysis
- `/prediction` — salary estimate form
- `/history` — MongoDB-backed search, filter, delete, and clear
- `GET /api/analytics`, `POST /api/predict`, `GET /api/history`
- `DELETE /api/history/<id>`, `DELETE /api/history`

Salary values have no currency field in the supplied dataset. The interface therefore labels them as source-dataset units instead of assuming a currency. A prediction is an estimate, not a guarantee. Executive experience (`EX`) is accepted as an unknown one-hot category and safely ignored by the model's existing encoder; the supplied dataset only includes Entry, Mid, and Senior.

## Verify

Run the app tests with:

```powershell
python -m unittest discover -s tests -v
```

The tests cover dataset-backed analytics, input validation, model feature ordering, and prediction persistence behavior. The prediction workflow requires a reachable MongoDB instance.
